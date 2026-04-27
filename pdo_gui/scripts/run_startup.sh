#!/bin/bash
# Runs at application startup:
#   1. Creates PDO user keys (from run.sh, minus the last two lines)
#   2. Runs setup_test.sh to initialize the PDO service/groups databases
set -e

# --- Step 1: Create user keys if they don't already exist ---
export LEDGER_WS=/tmp/ledger_ws
export PDO_LEDGER_URL="http://127.0.0.1:6600"
export F_SERVICE_HOST="hasan-HP-ZBook-15-G3"
export USER_KEYS_FOLDER=/home/hasan/work/pdos/policies_client/user_keys

mkdir -p "${USER_KEYS_FOLDER}"
for i in 1 2 3 4 5; do
    if [ ! -f "${USER_KEYS_FOLDER}/user${i}_private.pem" ]; then
        echo "Creating PDO keys for user${i}..."
        docker run --rm \
            --volume "${USER_KEYS_FOLDER}:/tmp/users_keys" \
            --entrypoint /project/pdo/run/bin/python \
            pdo_client:0.4.29 \
            /project/pdo/src/build/__tools__/make-keys \
            --keyfile "/tmp/users_keys/user${i}" \
            --format pem
    fi
done

# --- Step 2: Initialize PDO service and groups databases ---
echo "Running setup_test.sh..."
bash /home/hasan/work/pdos/pdo-contracts/download-contract/test/setup_test.sh
