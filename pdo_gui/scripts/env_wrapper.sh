#!/bin/bash
# Sources the full PDO environment and executes the provided command.
# Usage: env_wrapper.sh <command> [args...]
set -e

export PDO_CONTRACTS_ROOT="/home/hasan/work/pdos/pdo-contracts"
export PDO_SOURCE_ROOT="${PDO_CONTRACTS_ROOT}/private-data-objects"
export PDO_INSTALL_ROOT="/home/hasan/work/pdos/pdo_install"
export USER_KEYS_FOLDER="/home/hasan/work/pdos/policies_client/user_keys"
export F_SERVICE_HOST="hasan-HP-ZBook-15-G3"
export LEDGER_WS="/tmp/ledger_ws"
export PDO_LEDGER_URL="http://127.0.0.1:6600"
export F_GUARDIAN_HOST="localhost"

# Save the command to run, then clear $@ so sourced scripts that parse
# positional parameters (e.g. common-config.sh) don't see our arguments.
cmd=("$@")
set --

source "${PDO_SOURCE_ROOT}/build/common-config.sh"
source "${PDO_HOME}/bin/lib/common.sh"
source "${PDO_INSTALL_ROOT}/bin/activate"

export F_IDENTITY_TEMPLATES="${PDO_HOME}/contracts/identity/context"
export F_CONTEXT_TEMPLATES="${PDO_HOME}/contracts/download/context"

exec "${cmd[@]}"