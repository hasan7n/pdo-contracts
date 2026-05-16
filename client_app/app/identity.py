"""
Public key / identity abstraction layer.
The current identity is the public_key field of the singleton AppConfig.
"""

from .models import AppConfig


def get_current_identity():
    """Return the current public key (username) or empty string."""
    return AppConfig.get_instance().public_key


def set_current_identity(public_key):
    """Set the current identity (public key / username)."""
    config = AppConfig.get_instance()
    config.public_key = public_key
    config.save(update_fields=['public_key'])


def is_configured():
    return bool(get_current_identity())
