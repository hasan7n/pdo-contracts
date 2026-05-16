"""PDO bootstrap on Django app start.

Mirrors the decentralized test ``startup.py``:
  1. Set env vars (via ``pdo_config`` import side effect).
  2. Copy the network cert, site.toml, and user keys into ``PDO_HOME``.
  3. Initialize ``state`` + the local service registries (eservice / pservice
     / sservice) via the ``do_*`` commands.
"""

import logging
import os
import shutil
import threading

# Importing pdo_config sets the env vars that pdo.* modules read at import.
from . import pdo_config as cfg
from . import pdo_state
from .models import AppConfig

logger = logging.getLogger(__name__)
_init_lock = threading.Lock()
_initialized = False


def _bootstrap_files():
    os.makedirs(cfg.SCRATCH_DIR, exist_ok=True)
    os.makedirs(cfg.DOWNLOAD_OUTPUT_DIR, exist_ok=True)

    os.makedirs(cfg.PDO_LEDGER_KEY_ROOT, exist_ok=True)
    src_cert = os.path.join(cfg.LEDGER_WS, "ccf/keys/networkcert.pem")
    if os.path.exists(src_cert):
        shutil.copy(src_cert, cfg.PDO_LEDGER_KEY_ROOT)
    else:
        logger.warning("network cert not found at %s — skipping copy", src_cert)

    os.makedirs(os.path.dirname(cfg.F_SERVICE_SITE_FILE), exist_ok=True)
    if os.path.exists(cfg.SITE_TOML_SOURCE):
        shutil.copy(cfg.SITE_TOML_SOURCE, cfg.F_SERVICE_SITE_FILE)
    else:
        logger.warning("site.toml not found at %s — skipping copy", cfg.SITE_TOML_SOURCE)

    keys_dir = os.path.join(cfg.PDO_HOME, "keys")
    os.makedirs(keys_dir, exist_ok=True)
    if os.path.isdir(cfg.USER_KEYS_FOLDER):
        for fname in os.listdir(cfg.USER_KEYS_FOLDER):
            src = os.path.join(cfg.USER_KEYS_FOLDER, fname)
            if os.path.isfile(src):
                shutil.copy(src, keys_dir)
    else:
        logger.warning("user keys folder %s missing", cfg.USER_KEYS_FOLDER)


def _setup_local_databases(state, bindings):
    from pdo.client.commands.eservice import do_eservice
    from pdo.client.commands.pservice import do_pservice
    from pdo.client.commands.service_db import do_service_db
    from pdo.client.commands.sservice import do_sservice

    do_service_db(state, bindings, ["import", "--file", cfg.F_SERVICE_SITE_FILE])
    do_eservice(state, bindings, [
        "create_from_site", "--file", cfg.F_SERVICE_SITE_FILE,
        "--group", "default",
        "--preferred", cfg.PREFERRED_ESERVICE_URL,
    ])
    do_pservice(state, bindings, [
        "create_from_site", "--file", cfg.F_SERVICE_SITE_FILE,
        "--group", "default",
    ])
    do_sservice(state, bindings, [
        "create_from_site", "--file", cfg.F_SERVICE_SITE_FILE,
        "--group", "default",
        "--replicas", "1",
        "--duration", "60",
    ])


def initialize():
    global _initialized
    with _init_lock:
        if _initialized:
            return
        AppConfig.get_instance()  # ensure singleton row exists
        _bootstrap_files()
        state, bindings = pdo_state.setup_pdo_state()
        _setup_local_databases(state, bindings)
        pdo_state._set(state, bindings)
        _initialized = True
        logger.info("PDO state initialized for webui.")
