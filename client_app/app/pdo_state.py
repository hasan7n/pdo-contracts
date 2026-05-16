"""PDO state singleton for the webui.

The decentralized helpers all take ``state`` as their first argument; we
build it once at app start (via ``startup.initialize``) and hand it out
through ``get_state``. ``parse_shell_command_line`` also seeds the
process-wide ``pdo.common.config.shared_configuration`` while it runs, so
no extra init is needed.
"""

import sys
import threading

from pdo.client.builder.shell import parse_shell_command_line

from .pdo_config import (
    F_LOGFILE,
    F_LOGLEVEL,
    F_SERVICE_DB_FILE,
    F_SERVICE_GROUPS_DB_FILE,
    PDO_LEDGER_URL,
    SCRATCH_DIR,
)

_lock = threading.Lock()
_state = None
_bindings = None


def setup_pdo_state():
    args = [
        "--logfile", F_LOGFILE,
        "--loglevel", F_LOGLEVEL,
        "--ledger", PDO_LEDGER_URL,
        "--groups-db", F_SERVICE_GROUPS_DB_FILE,
        "--service-db", F_SERVICE_DB_FILE,
        "--data-dir", SCRATCH_DIR,
    ]
    env = parse_shell_command_line(args)
    if env is None:
        sys.exit("failed to initialize PDO environment")
    state, bindings, _ = env
    return state, bindings


def get_state():
    if _state is None:
        raise RuntimeError("PDO state not initialized — call startup.initialize() first.")
    return _state


def get_bindings():
    if _bindings is None:
        raise RuntimeError("PDO bindings not initialized — call startup.initialize() first.")
    return _bindings


def _set(state, bindings):
    global _state, _bindings
    with _lock:
        _state = state
        _bindings = bindings
