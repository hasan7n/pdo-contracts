# pdo_gui — Developer Notes

A Django web app providing a GUI for the PDO (Private Data Objects) download-contract system.

**Reference script:** `download-contract/test/script_test_v2.sh` — the GUI wraps those same CLI commands so users can create signature authorities, policies, sign credentials, and download data through a browser.

---

## File Structure

```
pdo_gui/
├── manage.py
├── requirements.txt                   # django>=4.2, cryptography>=41.0
├── scripts/
│   ├── env_wrapper.sh                 # Sources PDO env (venv, PDO_HOME) and execs any command
│   └── run_startup.sh                 # Creates user keys (run.sh minus last 2 lines) + runs setup_test.sh
├── config/
│   ├── settings.py                    # PDO_DATA_DIR, CHANNEL_KEYS_DIR, DOWNLOADS_DIR, SIGNED_CREDENTIALS_DIR
│   ├── urls.py                        # Includes app.urls
│   └── wsgi.py
└── app/
    ├── apps.py                        # Triggers startup.initialize() on runserver (RUN_MAIN guard)
    ├── models.py                      # See models section below
    ├── pdo_runner.py                  # All PDO CLI invocations (the key utility module)
    ├── startup.py                     # Startup logic: scripts, channel keys, DB seeding
    ├── urls.py                        # All URL patterns
    ├── views/
    │   ├── home.py                    # GET / → index
    │   ├── signature_authority.py     # create, dashboard, sign_credential
    │   ├── policy.py                  # create, dashboard, register_authority, set_policy_data
    │   └── download.py                # download_data (POST), get_channel_public_key (GET)
    ├── templates/
    │   ├── base.html
    │   ├── index.html
    │   ├── signature_authority_create.html
    │   ├── signature_authority_dashboard.html
    │   ├── policy_create.html
    │   └── policy_dashboard.html      # Three tabs: Trusted Authorities, Policy Data, Download
    ├── migrations/
    │   └── 0001_initial.py
    └── static/
        ├── css/styles.css
        └── js/
            ├── signature_authority.js  # Loading overlay on create; dynamic claims form on dashboard
            ├── policy.js               # Tab nav; register-authority AJAX; set-policy-data AJAX
            └── download.js             # Download AJAX; popup modal showing decrypted data path
```

---

## Running

```bash
cd pdo_gui
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

On first `runserver`, startup automatically:

1. Runs `scripts/run_startup.sh` → creates PDO user keys + initializes service/groups DBs via `setup_test.sh`
2. Generates RSA-2048 channel keys at `/tmp/pdo_gui/channel_keys/<username>/`
3. Seeds DB with `user1`–`user5` (DID = their PDO public key) and 3 credential templates

---

## Models

- **User**: `name`, `did` (DID = PDO public key PEM from `policies_client/user_keys/`)
- **SignatureAuthority**: `user` (FK), `name`, `description`, `signing_context` (= name, used as `--path`)
- **Policy**: `user` (FK), `name`, `description`, `policy_data` (JSON), `guardian_url`, `guardian_port`
- **PolicyTrustedAuthority**: `policy` (FK), `signature_authority` (FK), `credential_type`
- **CredentialTemplate**: `template_type`, `claims_keys` (JSON list) — note: field is `template_type` not `type_` (Django forbids trailing `_`)
- **VerifiableCredential**: `user` (FK), `signature_authority` (FK), `vc` (JSON)

---

## Key Design Decisions

### PDO Environment (`env_wrapper.sh`)

All PDO CLI calls go through `scripts/env_wrapper.sh`, which sources:

- `${PDO_SOURCE_ROOT}/build/common-config.sh` (sets PDO_HOME)
- `${PDO_HOME}/bin/lib/common.sh`
- `${PDO_INSTALL_ROOT}/bin/activate` (the PDO virtualenv)

It then `exec "$@"` the passed command. Every `pdo_runner.run([...])` call inherits the full PDO environment.

### PDO OPTS

`pdo_runner.get_opts()` returns the standard PDO flags pointing to:

- `F_CONTEXT_FILE = download-contract/test/test_context.toml`
- `F_SERVICE_GROUPS_DB_FILE = download-contract/test/hasan-HP-ZBook-15-G3_groups_db`
- `F_SERVICE_DB_FILE = download-contract/test/hasan-HP-ZBook-15-G3_db`
- `PDO_LEDGER_URL = http://127.0.0.1:6600`

### Template Dirs (lazy-cached)

`get_identity_templates_dir()` and `get_context_templates_dir()` query `F_IDENTITY_TEMPLATES` and `F_CONTEXT_TEMPLATES` from env_wrapper.sh once and cache per process.

### Startup Guard

`apps.py` only runs startup when `'runserver' in sys.argv` AND (`RUN_MAIN == 'true'` OR `--noreload` in argv). Prevents double-run with autoreloader; skips during `migrate`/`makemigrations`.

### Startup Idempotency

- `_run_environment_setup()` skips if `F_SERVICE_DB_FILE` already exists
- `_create_channel_keys()` skips per-user if `private_key.pem` already exists
- `_create_users()` and `_create_credential_templates()` use `get_or_create`

### Channel Keys

RSA-2048 keys at `CHANNEL_KEYS_DIR/<username>/{private_key.pem, public_key.pem}`.
Used at download time to decrypt the encrypted data blob.

### Download Flow

1. Collect user's `VerifiableCredential` rows, build `{sa.signing_context: vc.vc}` dict
2. Write `combined.json`, call `download_policy issue_credential` → `combined_vc.json`
3. Call `download_token do_download` → `encrypted_data.bin`
4. Call `read_data.py` (via env_wrapper) to decrypt → `decrypted_data.txt`
5. Return path to frontend; JS shows a popup modal

---

## PDO Contract Naming Conventions

Given a `name` (e.g. `membership_authority`):

- SA contract: `identity.<name>.signature_authority`
- Policy contract: `download.<name>.policy_agent`
- Token issuer: `token.<name>.token_issuer`
- Token object: `token.<name>.token_object`
- Token 1: `token.<name>.token_object.token_1`

SA `signing_context` = `name` (used as `--path` in register and sign_credential commands).

---

## Hardcoded Paths

- `PDO_CONTRACTS_ROOT = /home/hasan/work/pdos/pdo-contracts`
- `PDO_INSTALL_ROOT = /home/hasan/work/pdos/pdo_install`
- `USER_KEYS_FOLDER = /home/hasan/work/pdos/policies_client/user_keys`
- `F_SERVICE_HOST = hasan-HP-ZBook-15-G3`
- `PDO_DATA_DIR = /tmp/pdo_gui` (channel keys, downloads, signed credentials)
