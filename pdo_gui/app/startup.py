"""
Application startup logic.

On server start this module:
  1. Runs run_startup.sh (creates user keys + initializes PDO service DBs).
  2. Generates RSA channel keys for each discovered user if not already present.
  3. Populates the database with users (DID = PDO public key), credential templates,
     and policy templates — all read from config/templates.json.

All operations are idempotent — safe to call multiple times.
"""

import glob
import json
import logging
import os
import subprocess

from django.conf import settings

from . import pdo_runner

logger = logging.getLogger(__name__)

STARTUP_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'scripts', 'run_startup.sh')
)
TEMPLATES_CONFIG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'config', 'templates.json')
)


def initialize():
    _run_environment_setup()
    _create_channel_keys()
    _populate_database()


def _discover_users():
    """Return sorted list of usernames found in USER_KEYS_FOLDER via *_public.pem glob."""
    pattern = os.path.join(pdo_runner.USER_KEYS_FOLDER, '*_public.pem')
    paths = glob.glob(pattern)
    users = []
    for path in sorted(paths):
        basename = os.path.basename(path)
        if basename.endswith('_public.pem'):
            username = basename[: -len('_public.pem')]
            users.append(username)
    return users


def _load_templates_config():
    with open(TEMPLATES_CONFIG) as f:
        return json.load(f)


def _run_environment_setup():
    """Run run_startup.sh unless the PDO service DB already exists."""
    if os.path.exists(pdo_runner.F_SERVICE_DB_FILE):
        logger.info("PDO service DB already exists — skipping environment setup")
        return

    logger.info("Running PDO environment setup scripts...")
    result = subprocess.run(['bash', STARTUP_SCRIPT], capture_output=False, text=True)
    if result.returncode != 0:
        logger.error("run_startup.sh exited with code %d", result.returncode)


def _create_channel_keys():
    """Generate RSA-2048 channel key pairs for each discovered user if not already on disk."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    os.makedirs(settings.CHANNEL_KEYS_DIR, exist_ok=True)

    for username in _discover_users():
        user_dir = os.path.join(settings.CHANNEL_KEYS_DIR, username)
        private_key_path = os.path.join(user_dir, 'private_key.pem')

        if os.path.exists(private_key_path):
            continue

        os.makedirs(user_dir, exist_ok=True)
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        public_key_path = os.path.join(user_dir, 'public_key.pem')
        with open(public_key_path, 'wb') as f:
            f.write(private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ))

        logger.info("Created channel keys for %s", username)


def _populate_database():
    _create_users()
    _create_credential_templates()
    _create_policy_templates()


def _create_users():
    """Register discovered users in the DB using their PDO public keys as DIDs."""
    from .models import User

    for username in _discover_users():
        public_key_path = os.path.join(pdo_runner.USER_KEYS_FOLDER, f'{username}_public.pem')

        if os.path.exists(public_key_path):
            with open(public_key_path, 'r') as f:
                did = f.read().strip()
        else:
            logger.warning("PDO public key not found for %s at %s", username, public_key_path)
            did = f'did:pdo:{username}'

        _, created = User.objects.get_or_create(name=username, defaults={'did': did})
        if created:
            logger.info("Registered user: %s", username)


def _create_credential_templates():
    """Seed credential templates from config/templates.json."""
    from .models import CredentialTemplate

    config = _load_templates_config()
    for tpl in config.get('credential_templates', []):
        _, created = CredentialTemplate.objects.get_or_create(
            template_type=tpl['template_type'],
            defaults={'claims_keys': tpl['claims_keys']},
        )
        if created:
            logger.info("Created credential template: %s", tpl['template_type'])


def _create_policy_templates():
    """Seed policy templates from config/templates.json."""
    from .models import PolicyTemplate

    config = _load_templates_config()
    for tpl in config.get('policy_templates', []):
        _, created = PolicyTemplate.objects.get_or_create(name=tpl['name'])
        if created:
            logger.info("Created policy template: %s", tpl['name'])
