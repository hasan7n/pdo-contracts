from django.db import models


class User(models.Model):
    name = models.CharField(max_length=100, unique=True)
    did = models.TextField()

    def __str__(self):
        return self.name


class SignatureAuthority(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    signing_context = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class PolicyTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Policy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template = models.ForeignKey('PolicyTemplate', null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    policy_data = models.JSONField(null=True, blank=True)
    guardian_url = models.CharField(max_length=200)
    guardian_port = models.IntegerField()

    def __str__(self):
        return self.name


class PolicyTrustedAuthority(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='trusted_authorities')
    signature_authority = models.ForeignKey(SignatureAuthority, on_delete=models.CASCADE)
    credential_type = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.policy.name} trusts {self.signature_authority.name} ({self.credential_type})"


class CredentialTemplate(models.Model):
    template_type = models.CharField(max_length=100, unique=True)
    claims_keys = models.JSONField()

    def __str__(self):
        return self.template_type


class VerifiableCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifiable_credentials')
    signature_authority = models.ForeignKey(SignatureAuthority, on_delete=models.CASCADE)
    vc = models.JSONField()

    def __str__(self):
        return f"VC for {self.user.name} by {self.signature_authority.name}"
