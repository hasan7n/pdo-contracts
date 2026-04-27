from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('did', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='CredentialTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('template_type', models.CharField(max_length=100, unique=True)),
                ('claims_keys', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='SignatureAuthority',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField()),
                ('signing_context', models.CharField(max_length=100)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.user')),
            ],
        ),
        migrations.CreateModel(
            name='Policy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField()),
                ('policy_data', models.JSONField(blank=True, null=True)),
                ('guardian_url', models.CharField(max_length=200)),
                ('guardian_port', models.IntegerField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.user')),
            ],
        ),
        migrations.CreateModel(
            name='PolicyTrustedAuthority',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credential_type', models.CharField(max_length=100)),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trusted_authorities', to='app.policy')),
                ('signature_authority', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.signatureauthority')),
            ],
        ),
        migrations.CreateModel(
            name='VerifiableCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vc', models.JSONField()),
                ('signature_authority', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.signatureauthority')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verifiable_credentials', to='app.user')),
            ],
        ),
    ]
