"""
Utility for running PDO CLI commands from the Django application.

All commands are executed through env_wrapper.sh, which sources the full
PDO environment (virtualenv, PDO_HOME, etc.) before running the command.
"""

import json
import os
import subprocess
import tempfile

# === PDO Installation Paths ===
PDO_CONTRACTS_ROOT = "/home/hasan/work/pdos/pdo-contracts"
PDO_SOURCE_ROOT = os.path.join(PDO_CONTRACTS_ROOT, "private-data-objects")
PDO_INSTALL_ROOT = "/home/hasan/work/pdos/pdo_install"
USER_KEYS_FOLDER = "/home/hasan/work/pdos/policies_client/user_keys"
LEDGER_WS = "/tmp/ledger_ws"
PDO_LEDGER_URL = "http://127.0.0.1:6600"
F_SERVICE_HOST = "hasan-HP-ZBook-15-G3"

# === Download Contract Paths ===
DOWNLOAD_CONTRACT_ROOT = os.path.join(PDO_CONTRACTS_ROOT, "download-contract")
DOWNLOAD_CONTRACT_TEST_DIR = os.path.join(DOWNLOAD_CONTRACT_ROOT, "test")
F_CONTEXT_FILE = os.path.join(DOWNLOAD_CONTRACT_TEST_DIR, "test_context.toml")
F_SERVICE_GROUPS_DB_FILE = os.path.join(DOWNLOAD_CONTRACT_TEST_DIR, f"{F_SERVICE_HOST}_groups_db")
F_SERVICE_DB_FILE = os.path.join(DOWNLOAD_CONTRACT_TEST_DIR, f"{F_SERVICE_HOST}_db")

# Scripts
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
ENV_WRAPPER = os.path.join(SCRIPTS_DIR, 'env_wrapper.sh')
READ_DATA_SCRIPT = os.path.join(DOWNLOAD_CONTRACT_TEST_DIR, "read_data.py")


def get_opts():
    """Return the standard PDO command options as a list of arguments."""
    return [
        "--logfile", "__screen__",
        "--loglevel", "warn",
        "--ledger", PDO_LEDGER_URL,
        "--groups-db", F_SERVICE_GROUPS_DB_FILE,
        "--service-db", F_SERVICE_DB_FILE,
        "--context-file", F_CONTEXT_FILE,
    ]


def run(args, check=True, capture_output=True):
    """Execute a command through the PDO environment wrapper."""
    cmd = [ENV_WRAPPER] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"PDO command failed (code {result.returncode}):\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDERR: {result.stderr}\n"
            f"STDOUT: {result.stdout}"
        )
    return result


def _query_env_var(var_name):
    """Read a single environment variable as exported by env_wrapper.sh."""
    result = subprocess.run(
        [ENV_WRAPPER, 'bash', '-c', f'echo "${var_name}"'],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


# Cache template dirs so we only call env_wrapper once per process
_identity_templates_dir = None
_context_templates_dir = None


def get_identity_templates_dir():
    global _identity_templates_dir
    if _identity_templates_dir is None:
        _identity_templates_dir = _query_env_var('F_IDENTITY_TEMPLATES')
    return _identity_templates_dir


def get_context_templates_dir():
    global _context_templates_dir
    if _context_templates_dir is None:
        _context_templates_dir = _query_env_var('F_CONTEXT_TEMPLATES')
    return _context_templates_dir


# ============================================================
# High-level PDO operations
# ============================================================

def create_signature_authority(name, user_name, description):
    """Run the three PDO commands needed to create a signature authority."""
    identity_templates = get_identity_templates_dir()
    opts = get_opts()

    run(['pdo-context', 'load'] + opts + [
        '--import-file', os.path.join(identity_templates, 'signature_authority.toml'),
        '--bind', 'identity', name,
        '--bind', 'user', user_name,
    ])

    run(['id_signature_authority', 'create'] + opts + [
        '--contract', f'identity.{name}.signature_authority',
        '-d', description,
    ])

    run(['id_signature_authority', 'register'] + opts + [
        '--contract', f'identity.{name}.signature_authority',
        '-d', 'fixed key satest',
        '--fixed',
        '--path', name,
    ])


def create_policy(name, user_name, description, guardian_url, guardian_port):
    """Run the PDO commands needed to create a download policy with its token."""
    context_templates = get_context_templates_dir()
    opts = get_opts()

    run(['pdo-context', 'load'] + opts + [
        '--import-file', os.path.join(context_templates, 'policy_agent.toml'),
        '--bind', 'identity', name,
        '--bind', 'user', user_name,
    ])

    run(['pdo-context', 'load'] + opts + [
        '--import-file', os.path.join(context_templates, 'tokens.toml'),
        '--bind', 'token', name,
        '--bind', 'user', user_name,
        '--bind', 'url', f'http://{guardian_url}:{guardian_port}',
    ])

    run(['download_policy', 'create'] + opts + [
        '--contract', f'download.{name}.policy_agent',
        '-d', description,
    ])

    run(['ex_token_issuer', 'create'] + opts + [
        '--contract', f'token.{name}.token_issuer',
    ])

    run(['download_token', 'mint_tokens'] + opts + [
        '--contract', f'token.{name}.token_object',
    ])

    run(['download_token', 'register'] + opts + [
        '--contract', f'token.{name}.token_object.token_1',
        '--issuer', f'download.{name}.policy_agent',
        '--path', '__ISSUER__',
        '--credential-type', 'download',
    ])


def register_trusted_authority(policy_name, sa_name, sa_signing_context, credential_type):
    """Register a signature authority with a policy as a trusted VC issuer."""
    opts = get_opts()
    run(['download_policy', 'register'] + opts + [
        '--contract', f'download.{policy_name}.policy_agent',
        '--issuer', f'identity.{sa_name}.signature_authority',
        '--path', sa_signing_context,
        '--credential-type', credential_type,
    ])


def set_policy_data(policy_name, policy_data_dict):
    """Write policy_data to a temp file and call download_policy set_policy."""
    opts = get_opts()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(policy_data_dict, f)
        tmp_path = f.name
    try:
        run(['download_policy', 'set_policy'] + opts + [
            '--contract', f'download.{policy_name}.policy_agent',
            '--data', tmp_path,
        ])
    finally:
        os.unlink(tmp_path)


def sign_credential(sa_name, sa_signing_context, credential_dict, output_path):
    """Sign a credential JSON using a signature authority and write the result to output_path."""
    opts = get_opts()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(credential_dict, f)
        cred_path = f.name
    try:
        run(['id_signature_authority', 'sign_credential'] + opts + [
            '--contract', f'identity.{sa_name}.signature_authority',
            '--path', sa_signing_context,
            '--credential', cred_path,
            '--signed-credential', output_path,
        ])
    finally:
        os.unlink(cred_path)


def issue_and_download(policy_name, combined_vc_dict, output_dir):
    """
    Issue a credential from the policy agent and download the encrypted data.

    Returns (encrypted_path, decrypted_path) where decrypted_path does not
    yet exist — the caller is responsible for decrypting.
    """
    opts = get_opts()
    os.makedirs(output_dir, exist_ok=True)

    combined_path = os.path.join(output_dir, 'combined.json')
    combined_vc_path = os.path.join(output_dir, 'combined_vc.json')
    encrypted_path = os.path.join(output_dir, 'encrypted_data.bin')
    decrypted_path = os.path.join(output_dir, 'decrypted_data.txt')

    with open(combined_path, 'w') as f:
        json.dump(combined_vc_dict, f, indent=4)

    run(['download_policy', 'issue_credential'] + opts + [
        '--contract', f'download.{policy_name}.policy_agent',
        '--signed-credential', combined_path,
        '--issued-credential', combined_vc_path,
    ])

    run(['download_token', 'do_download'] + opts + [
        '--contract', f'token.{policy_name}.token_object.token_1',
        '--vc-file', combined_vc_path,
        '--output-file', encrypted_path,
    ])

    return encrypted_path, decrypted_path


def decrypt_data(encrypted_path, private_key_path, decrypted_path):
    """Decrypt a downloaded data file using the user's channel private key."""
    run(['python3', READ_DATA_SCRIPT, encrypted_path, private_key_path, decrypted_path])
