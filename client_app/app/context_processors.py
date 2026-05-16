from .models import AppConfig


def app_context(request):
    config = AppConfig.get_instance()
    return {
        'app_config': config,
        'current_identity': config.public_key,
    }
