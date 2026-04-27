import os
import sys
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Only run startup when serving (not during migrate, makemigrations, shell, etc.)
        # RUN_MAIN is set to 'true' in the autoreloader child process (the actual server).
        # When --noreload is used, check for 'runserver' in argv directly.
        is_runserver = 'runserver' in sys.argv
        is_main_process = os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv

        if is_runserver and is_main_process:
            from .startup import initialize
            try:
                initialize()
            except Exception:
                logger.exception("Startup initialization failed")
