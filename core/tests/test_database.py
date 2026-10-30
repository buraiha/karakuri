from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase
from core.models import App, AuditEvent, User
from config.database import database_config


class DatabaseConfigTests(SimpleTestCase):
    def test_default_sqlite_without_postgres_password(self):
        db = database_config({}, Path('/project'))
        self.assertEqual(db['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(db['NAME'], Path('/project/.data/db.sqlite3'))

    def test_sqlite_path_can_be_relative_or_absolute(self):
        for path, expected in [('custom.sqlite3', '/project/custom.sqlite3'),
                               ('/data/custom.sqlite3', '/data/custom.sqlite3')]:
            db = database_config({'DB_BACKEND': 'sqlite', 'SQLITE_PATH': path}, Path('/project'))
            self.assertEqual(db['NAME'], Path(expected))

    def test_postgres_uses_configured_parameters(self):
        env = {'DB_BACKEND': 'postgresql', 'POSTGRES_PASSWORD': 'test-only', 'POSTGRES_DB': 'test-db',
               'POSTGRES_USER': 'test-user', 'POSTGRES_HOST': 'db', 'POSTGRES_PORT': '5433'}
        db = database_config(env, Path('/project'))
        self.assertEqual(db, {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'test-db',
                             'USER': 'test-user', 'PASSWORD': 'test-only', 'HOST': 'db', 'PORT': '5433'})

    def test_postgres_without_password_fails_instead_of_falling_back(self):
        with self.assertRaises(ImproperlyConfigured):
            database_config({'DB_BACKEND': 'postgresql'}, Path('/project'))

    def test_unknown_backend_fails_instead_of_falling_back(self):
        for value in ['', 'postgres', 'sqltie']:
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                database_config({'DB_BACKEND': value}, Path('/project'))

    def test_mysql_uses_utf8mb4_and_strict_mode(self):
        env = {'DB_BACKEND': 'mysql', 'MYSQL_PASSWORD': 'test-only', 'MYSQL_DATABASE': 'test-db',
               'MYSQL_USER': 'test-user', 'MYSQL_HOST': 'mysql', 'MYSQL_PORT': '3307'}
        db = database_config(env, Path('/project'))
        self.assertEqual(db['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual((db['NAME'], db['USER'], db['PASSWORD'], db['HOST'], db['PORT']),
                         ('test-db', 'test-user', 'test-only', 'mysql', '3307'))
        self.assertEqual(db['OPTIONS']['charset'], 'utf8mb4')
        self.assertIn('STRICT_TRANS_TABLES', db['OPTIONS']['init_command'])
        self.assertEqual(db['TEST']['CHARSET'], 'utf8mb4')

    def test_mysql_missing_password_fails_instead_of_falling_back(self):
        with self.assertRaises(ImproperlyConfigured):
            database_config({'DB_BACKEND': 'mysql'}, Path('/project'))


class DatabaseRoundTripTests(TestCase):
    def test_japanese_emoji_and_json_roundtrip(self):
        user = User.objects.create_user(username='unicode-check', email='unicode@example.test', password=None)
        app = App.objects.create(slug='unicode-check', name='日本語の道具 🎣')
        event = AuditEvent.objects.create(actor=user, target=f'core.App:{app.pk}',
                                          before={}, after={'name': app.name, 'allowed': True})
        app.refresh_from_db()
        event.refresh_from_db()
        self.assertEqual(app.name, '日本語の道具 🎣')
        self.assertEqual(event.after, {'name': '日本語の道具 🎣', 'allowed': True})

    def test_duplicate_user_email_rejected_by_database(self):
        from django.db import IntegrityError, transaction
        User.objects.create_user(username='first', email='duplicate@example.test', password=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username='second', email='duplicate@example.test', password=None)

    def test_duplicate_google_subject_rejected_by_database(self):
        from allauth.socialaccount.models import SocialAccount
        from django.db import IntegrityError, transaction
        first = User.objects.create_user(username='first', email='first@example.test', password=None)
        second = User.objects.create_user(username='second', email='second@example.test', password=None)
        SocialAccount.objects.create(user=first, provider='google', uid='unique-google-subject')
        with self.assertRaises(IntegrityError), transaction.atomic():
            SocialAccount.objects.create(user=second, provider='google', uid='unique-google-subject')
