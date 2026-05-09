import os


# -----------------------------------------------------------------
# Required environment variables (mirrors setup_test.sh)
# -----------------------------------------------------------------
os.environ["LEDGER_WS"] = "/tmp/ledger_ws"
# os.environ["LEDGER_WS"] = "/home/hasan/work/pdos/pdo-contracts/docker/xfer"
os.environ["PDO_LEDGER_URL"] = "http://127.0.0.1:6600"
os.environ["F_SERVICE_HOST"] = "hasan-HP-ZBook-15-G3"
os.environ["USER_KEYS_FOLDER"] = (
    "/home/hasan/work/pdos/tmp-policies/policies_client/user_keys"
)


# -----------------------------------------------------------------
# Defaults for environment variables our helpers depend on
# -----------------------------------------------------------------

os.environ["PDO_INSTALL_ROOT"] = "/home/hasan/work/pdos/pdo_install"
os.environ["PDO_HOME"] = f"{os.environ['PDO_INSTALL_ROOT']}/opt/pdo"
os.environ["PDO_LEDGER_KEY_ROOT"] = f"{os.environ['PDO_HOME']}/etc/keys/ledger"
os.environ["PDO_LEDGER_TYPE"] = "ccf"


# -----------------------------------------------------------------
# Paths and runtime config
# -----------------------------------------------------------------
PDO_HOME = os.environ["PDO_HOME"]
PDO_LEDGER_KEY_ROOT = os.environ["PDO_LEDGER_KEY_ROOT"]
PDO_LEDGER_URL = os.environ["PDO_LEDGER_URL"]
F_SERVICE_HOST = os.environ["F_SERVICE_HOST"]
LEDGER_WS = os.environ["LEDGER_WS"]
USER_KEYS_FOLDER = os.environ["USER_KEYS_FOLDER"]

TEST_ROOT = "/home/hasan/work/pdos/pdo-contracts/download-contract/test/test_ws"
SCRATCH_DIR = f"{TEST_ROOT}/scratch"

F_SERVICE_SITE_FILE = f"{PDO_HOME}/etc/sites/{F_SERVICE_HOST}.toml"
F_SERVICE_GROUPS_DB_FILE = f"{SCRATCH_DIR}/groups_db"
F_SERVICE_DB_FILE = f"{SCRATCH_DIR}/service_db"
F_LOGFILE = os.environ.get("PDO_LOG_FILE", "__screen__")
F_LOGLEVEL = os.environ.get("PDO_LOG_LEVEL", "warn")


# -----------------------------------------------------------------
# CLI knobs
# -----------------------------------------------------------------
PREFERRED_ESERVICE_URL = "http://localhost:7101"
