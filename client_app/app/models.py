from django.db import models


class AppConfig(models.Model):
    """Singleton application configuration."""
    ledger_url = models.CharField(max_length=200, default='http://127.0.0.1:6600')
    asset_registry_url = models.CharField(max_length=200, default='http://127.0.0.1:8001')
    template_registry_url = models.CharField(max_length=200, default='http://127.0.0.1:8002')
    public_key = models.TextField(default='')  # user identity (username for now)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_configured(self):
        return bool(self.public_key)

    def __str__(self):
        return f"AppConfig(pk={self.pk})"


class Entity(models.Model):
    """A PDO contract owned by this client.

    For each contract this client created, we keep:
      - ``save_basename``: the basename (no extension) of the .pdo file the
        plugins write
      - ``save_blob``: the actual .pdo bytes — restaged into a fresh tempdir
        per logical operation so contract state stays isolated and we never
        rely on a long-lived DataDirectory.

    For ASSET entities, ``extra_data`` additionally holds the policy + token
    contracts' basenames and blobs (base64-encoded), since one logical asset
    spans three contracts.
    """
    ENTITY_TYPES = [
        ('WALLET', 'Wallet'),
        ('ISSUER', 'Issuer'),
        ('ASSET', 'Asset'),
    ]

    did = models.CharField(max_length=500, unique=True)
    name = models.CharField(max_length=200)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    contract_name = models.CharField(max_length=200, default='')
    owner_key = models.TextField(default='')

    save_basename = models.CharField(max_length=200, default='')
    save_blob = models.BinaryField(default=b'')

    # ASSET-only fields. {policy_basename, policy_blob_b64, token_basename,
    # token_blob_b64, guardian_url, guardian_port}
    extra_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.entity_type}:{self.name}"
