from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AppConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ledger_url', models.CharField(default='http://127.0.0.1:6600', max_length=200)),
                ('asset_registry_url', models.CharField(default='http://127.0.0.1:8001', max_length=200)),
                ('template_registry_url', models.CharField(default='http://127.0.0.1:8002', max_length=200)),
                ('public_key', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('did', models.CharField(max_length=500, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('entity_type', models.CharField(
                    choices=[('WALLET', 'Wallet'), ('ISSUER', 'Issuer'), ('ASSET', 'Asset')],
                    max_length=20,
                )),
                ('contract_name', models.CharField(default='', max_length=200)),
                ('owner_key', models.TextField(default='')),
                ('save_basename', models.CharField(default='', max_length=200)),
                ('save_blob', models.BinaryField(default=b'')),
                ('extra_data', models.JSONField(blank=True, default=dict)),
            ],
        ),
    ]
