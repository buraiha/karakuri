from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from core.models import App, AppAccess, AuditEvent, User


class FoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='member', email='member@example.test', password=None)
        self.admin = User.objects.create_user(username='manager', email='manager@example.test', password=None,
                                              is_staff=True, approval='approved')
        self.app = App.objects.get(slug='voice-relay')

    def authenticated(self, user=None, expires=None, client=None):
        # テスト内限定。アプリにはこの状態を作るURLや設定を設けない。
        client = client or self.client
        client.force_login(user or self.user)
        session = client.session
        session['google_authenticated'] = True
        session['absolute_expires_at'] = (expires or timezone.now() + timedelta(days=14)).timestamp()
        session.set_expiry(timezone.now() + timedelta(days=14))
        session.save()
        return client

    def grant(self, user=None, **kwargs):
        user = user or self.user
        user.approval = 'approved'
        user.save()
        return AppAccess.objects.create(user=user, app=self.app, allowed=True, **kwargs)

    def test_anonymous_routes(self):
        for path in ['/', '/status/', '/apps/voice-relay/', '/api/apps/voice-relay/', '/admin/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 302)

    def test_no_password_or_signup_urls(self):
        for path in ['/accounts/login/', '/accounts/signup/', '/accounts/password/reset/',
                     '/accounts/google/login/token/', '/dev/login/']:
            self.assertEqual(self.client.post(path, {'email': self.user.email, 'password': 'anything'}).status_code, 404)
        self.assertFalse(self.client.login(username=self.user.username, password='anything'))

    def test_force_login_without_google_proof_is_rejected(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_pending_and_rejected(self):
        for state in ['pending', 'rejected']:
            self.user.approval = state
            self.user.save()
            self.authenticated()
            self.assertRedirects(self.client.get('/'), '/status/')
            self.assertContains(self.client.get('/status/'), self.user.get_approval_display())
            self.assertEqual(self.client.get('/apps/voice-relay/').status_code, 403)
            self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 403)

    def test_approved_without_grant(self):
        self.user.approval = 'approved'
        self.user.save()
        self.authenticated()
        self.assertContains(self.client.get('/'), '利用権限がありません')
        self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 403)

    def test_free_allowed_and_revocation(self):
        access = self.grant(charged=False)
        self.authenticated()
        self.assertContains(self.client.get('/apps/voice-relay/'), 'まだできません')
        self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 200)
        access.allowed = False
        access.save()
        self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 403)

    def test_charged_does_not_grant_access(self):
        self.grant(charged=True)
        AppAccess.objects.filter(user=self.user).update(allowed=False)
        self.authenticated()
        self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 403)

    def test_global_revocation_applies_next_request(self):
        self.grant()
        self.authenticated()
        self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 200)
        User.objects.filter(pk=self.user.pk).update(approval='rejected')
        self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 403)

    def test_admin_has_no_implicit_app_access(self):
        self.authenticated(self.admin)
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 403)

    def test_member_cannot_manage_or_self_approve(self):
        self.authenticated()
        before = (self.user.approval, self.user.is_staff)
        for path, data in [('/admin/login/', {'username': 'manager', 'password': 'anything'}),
                           (f'/admin/core/user/{self.user.pk}/change/', {'approval': 'approved', 'is_staff': 'on'}),
                           ('/admin/core/appaccess/add/', {'user': self.user.pk, 'app': self.app.pk, 'allowed': 'on', 'charged': 'on'})]:
            response = self.client.post(path, data)
            self.assertIn(response.status_code, [302, 403])
        self.user.refresh_from_db()
        self.assertEqual((self.user.approval, self.user.is_staff), before)
        self.assertFalse(AppAccess.objects.exists())

    def test_admin_updates_status_and_audits(self):
        self.authenticated(self.admin)
        response = self.client.post(f'/admin/core/user/{self.user.pk}/change/',
                                    {'approval': 'approved', 'is_staff': 'on', 'is_superuser': 'on'})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.approval, 'approved')
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        audit = AuditEvent.objects.get()
        self.assertEqual(audit.before, {'approval': 'pending'})
        self.assertEqual(audit.after, {'approval': 'approved'})
        self.assertEqual(audit.actor, self.admin)
        self.assertFalse(AppAccess.objects.filter(user=self.user).exists())

    def test_admin_grant_changes_are_isolated(self):
        other = App.objects.create(slug='other', name='Other')
        untouched = AppAccess.objects.create(user=self.admin, app=other, allowed=False, charged=False)
        self.authenticated(self.admin)
        response = self.client.post('/admin/core/appaccess/add/',
                                    {'user': self.user.pk, 'app': self.app.pk, 'allowed': 'on', 'charged': 'on'})
        self.assertEqual(response.status_code, 302)
        access = AppAccess.objects.get(user=self.user)
        self.assertTrue(access.allowed and access.charged)
        response = self.client.post(f'/admin/core/appaccess/{access.pk}/change/',
                                    {'user': self.admin.pk, 'app': other.pk, 'charged': 'on'})
        self.assertEqual(response.status_code, 302)
        access.refresh_from_db()
        untouched.refresh_from_db()
        self.assertFalse(access.allowed)
        self.assertTrue(access.charged)
        self.assertEqual(access.user, self.user)
        self.assertEqual(access.app, self.app)
        self.assertFalse(untouched.allowed or untouched.charged)
        self.assertEqual(AuditEvent.objects.count(), 2)

    def test_unique_user_app(self):
        self.grant()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AppAccess.objects.create(user=self.user, app=self.app)

    def test_database_persists_after_relogin(self):
        self.grant(charged=True)
        self.authenticated()
        self.client.post('/logout/')
        fresh = Client()
        self.authenticated(client=fresh)
        self.assertEqual(fresh.get('/api/apps/voice-relay/').status_code, 200)
        self.assertTrue(AppAccess.objects.get(user=self.user).charged)

    def test_logout_is_post_only_and_revokes_old_cookie(self):
        self.authenticated()
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(self.client.get('/logout/').status_code, 405)
        self.assertEqual(self.client.post('/logout/').status_code, 302)
        self.assertFalse(Session.objects.filter(session_key=cookie).exists())
        attacker = Client()
        attacker.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self.assertEqual(attacker.get('/').status_code, 302)

    def test_csrf_for_logout_and_admin_change(self):
        strict = self.authenticated(self.admin, client=Client(enforce_csrf_checks=True))
        self.assertEqual(strict.post('/logout/').status_code, 403)
        self.assertEqual(strict.post(f'/admin/core/user/{self.user.pk}/change/', {'approval': 'approved'}).status_code, 403)

    def test_fixed_deadline_survives_session_changes(self):
        self.grant()
        deadline = timezone.now() + timedelta(days=14)
        self.authenticated(expires=deadline)
        expiry = self.client.session.get_expiry_date()
        for day in [1, 7, 13]:
            with patch('core.middleware.timezone.now', return_value=deadline - timedelta(days=14-day)):
                self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, 200)
                session = self.client.session
                session['arbitrary_change'] = day
                session.save()
                self.assertEqual(session['absolute_expires_at'], deadline.timestamp())
                self.assertEqual(session.get_expiry_date(), expiry)
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        new_browser = Client()
        new_browser.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self.assertEqual(new_browser.get('/api/apps/voice-relay/').status_code, 200)

    def test_exact_deadline_boundary(self):
        self.grant()
        deadline = timezone.now() + timedelta(days=14)
        for offset, expected in [(-1, 200), (0, 302), (1, 302)]:
            self.authenticated(expires=deadline)
            with patch('core.middleware.timezone.now', return_value=deadline + timedelta(seconds=offset)):
                self.assertEqual(self.client.get('/api/apps/voice-relay/').status_code, expected)

    def test_missing_or_corrupt_deadline_rejected(self):
        for value in [None, 'invalid', float('inf')]:
            self.authenticated()
            session = self.client.session
            session['absolute_expires_at'] = value
            session.save()
            self.assertEqual(self.client.get('/status/').status_code, 302)

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_production_rejects_unverified_session(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_bootstrap_requires_google_subject_and_confirmation(self):
        with self.assertRaises(CommandError):
            call_command('bootstrap_admin', 'not-registered', confirm_subject='not-registered')
        SocialAccount.objects.create(user=self.user, provider='google', uid='google-subject')
        with self.assertRaises(CommandError):
            call_command('bootstrap_admin', 'google-subject', confirm_subject='wrong')
        call_command('bootstrap_admin', 'google-subject', confirm_subject='google-subject', verbosity=0)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(self.user.approval, 'approved')
        self.assertEqual(AuditEvent.objects.count(), 1)

    @override_settings(GOOGLE_AUTH_CONFIGURED=False)
    def test_missing_google_config_fails_closed(self):
        self.assertContains(self.client.get('/login/'), '設定準備中')
        self.assertEqual(self.client.post('/accounts/google/login/').status_code, 503)
        self.assertEqual(self.client.get('/accounts/google/login/callback/?code=anything').status_code, 503)


@override_settings(GOOGLE_AUTH_CONFIGURED=True, SOCIALACCOUNT_PROVIDERS={'google': {
    'SCOPE': ['openid', 'email', 'profile'], 'OAUTH_PKCE_ENABLED': True,
    'APPS': [{'client_id': 'test-client', 'secret': 'test-secret', 'key': ''}]}})
class OAuthFlowTests(TestCase):
    def start(self, next_url=None):
        response = self.client.post('/accounts/google/login/', {'next': next_url or '/'})
        self.assertEqual(response.status_code, 302)
        params = parse_qs(urlsplit(response.url).query)
        self.assertTrue(params['code_challenge'])
        return params['state'][0]

    def finish(self, state, email='new@example.test', subject='test-google-sub', verified=True):
        token_response = Mock(status_code=200, headers={'content-type': 'application/json'})
        token_response.json.return_value = {'access_token': 'test-access-token', 'token_type': 'Bearer'}
        user_response = Mock(ok=True)
        user_response.json.return_value = {'id': subject, 'email': email, 'verified_email': verified, 'name': 'Test User'}
        with patch('requests.sessions.Session.request', side_effect=[token_response, user_response]) as request_mock:
            response = self.client.get('/accounts/google/login/callback/', {'code': 'test-code', 'state': state})
        self.assertEqual(request_mock.call_count, 2)
        self.assertTrue(request_mock.call_args_list[0].kwargs['data']['code_verifier'])
        return response

    def test_new_signup_and_relogin_preserves_status_with_new_deadline(self):
        now = timezone.now()
        with patch('core.auth.timezone.now', return_value=now):
            self.assertEqual(self.finish(self.start()).status_code, 302)
        user = User.objects.get()
        self.assertEqual(user.approval, 'pending')
        self.assertFalse(user.is_staff)
        self.assertEqual(self.client.session['absolute_expires_at'], (now + timedelta(days=14)).timestamp())
        self.assertRedirects(self.client.get('/'), '/status/')
        self.assertFalse(user.has_usable_password())
        user.approval = 'rejected'
        user.save()
        self.client.post('/logout/')
        later = now + timedelta(days=1)
        with patch('core.auth.timezone.now', return_value=later):
            self.assertEqual(self.finish(self.start()).status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.approval, 'rejected')
        self.assertEqual(self.client.session['absolute_expires_at'], (later + timedelta(days=14)).timestamp())
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_state_fails_without_token_exchange(self):
        self.start()
        with patch('requests.sessions.Session.request') as exchange:
            response = self.client.get('/accounts/google/login/callback/', {'code': 'test-code', 'state': 'wrong'})
        self.assertEqual(response.status_code, 401)
        exchange.assert_not_called()
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_state_cannot_be_replayed(self):
        state = self.start()
        self.finish(state)
        with patch('requests.sessions.Session.request') as exchange:
            self.assertEqual(self.client.get('/accounts/google/login/callback/', {'code': 'test-code', 'state': state}).status_code, 401)
        exchange.assert_not_called()

    def test_unverified_email_rejected(self):
        self.assertEqual(self.finish(self.start(), verified=False).status_code, 401)
        self.assertFalse(User.objects.exists())

    def test_same_email_does_not_link_different_google_identity(self):
        existing = User.objects.create_user(username='existing', email='new@example.test', password=None)
        SocialAccount.objects.create(user=existing, provider='google', uid='different-subject')
        self.assertEqual(self.finish(self.start()).status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(SocialAccount.objects.count(), 1)

    def test_cancelled_login_and_external_redirect(self):
        state = self.start('https://attacker.example/')
        self.assertEqual(self.finish(state).url, '/')
        self.client.post('/logout/')
        state = self.start()
        response = self.client.get('/accounts/google/login/callback/', {'error': 'access_denied', 'state': state})
        self.assertRedirects(response, '/accounts/social/cancelled/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_google_login_requires_csrf(self):
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post('/accounts/google/login/').status_code, 403)

    def test_invalid_id_token_does_not_create_session(self):
        state = self.start()
        token_response = Mock(status_code=200, headers={'content-type': 'application/json'})
        token_response.json.return_value = {'access_token': 'test-token', 'id_token': 'invalid.token.value'}
        with patch('requests.sessions.Session.request', return_value=token_response):
            response = self.client.get('/accounts/google/login/callback/', {'code': 'test-code', 'state': state})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertFalse(User.objects.exists())

    def test_failed_token_exchange_does_not_create_session(self):
        state = self.start()
        token_response = Mock(status_code=400, headers={'content-type': 'application/json'}, content=b'failure')
        with patch('requests.sessions.Session.request', return_value=token_response):
            response = self.client.get('/accounts/google/login/callback/', {'code': 'test-code', 'state': state})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertFalse(User.objects.exists())


class LogSafetyTests(TestCase):
    def test_oauth_query_not_in_access_log(self):
        import logging
        from core.logging import OAuthQueryFilter
        record = logging.LogRecord('django.server', logging.INFO, '', 0, '"%s" %s %s',
                                   ('GET /accounts/google/login/callback/?code=secret-code&state=secret-state HTTP/1.1', 302, 0), None)
        OAuthQueryFilter().filter(record)
        self.assertNotIn('secret-code', record.getMessage())
        self.assertNotIn('secret-state', record.getMessage())
        self.assertIn('/accounts/google/login/callback/', record.getMessage())
