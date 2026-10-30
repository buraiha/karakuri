from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model('core', 'App').objects.get_or_create(slug='voice-relay', defaults={'name': '文章連携'})


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
