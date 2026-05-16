import os
import sys
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ClientAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        is_runserver = 'runserver' in sys.argv
        is_main_process = os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv

        if is_runserver and is_main_process:
            from .startup import initialize
            try:
                initialize()
            except Exception:
                logger.exception("Client app startup initialization failed")
