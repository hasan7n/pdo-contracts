#!/bin/bash

# Copyright 2026 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -----------------------------------------------------------------
# End-to-end CLI test for the external_key_authority. It mirrors the use case: a
# person who owns a PDO wallet binds an external RSA key pair to it.
#
# Setup: the person creates a wallet_key_authority and an external_key_authority,
# and registers the wallet_key_authority as a trusted issuer of the external one.
#
# Then, to bind an external key:
#   1. the consumer gets a WalletVerifyingKeyCredential for their wallet from the
#      trusted wallet_key_authority (which verifies the wallet's ledger attestation)
#   2. generates the external rsa key pair and builds the payload
#      { identity: <wallet did>, session_key: <rsa pub> }, signing it with the rsa
#      private key
#   3. has the WALLET sign the same payload with its own contract key
#      (sign_with_contract_key)
#   4. submits the WalletVerifyingKeyCredential + both signatures to the
#      external_key_authority
#
# The authority verifies the WalletVerifyingKeyCredential against its trusted issuer,
# takes the wallet DID (subject) and verifying key (claim) from it, verifies the
# wallet's signature against that key (SHA-256 ECDSA) and the rsa signature against
# the public key in the payload (RSASSA-PKCS1-v1_5 / SHA-256), confirms the payloads
# match, and issues a publicKeyCredential for the session key. Everything signs
# on-chain -- there is no locally modeled wallet key.
#
# Requires a live PDO deployment (ledger + enclave/provisioning/storage services).
# -----------------------------------------------------------------
: "${PDO_LEDGER_URL?Missing environment variable PDO_LEDGER_URL}"
: "${PDO_HOME?Missing environment variable PDO_HOME}"
: "${PDO_SOURCE_ROOT?Missing environment variable PDO_SOURCE_ROOT}"

source ${PDO_HOME}/bin/lib/common.sh
check_python_version

if ! command -v pdo-shell &> /dev/null ; then
    yell unable to locate pdo-shell
    exit 1
fi

if [ "${PDO_LEDGER_TYPE}" == "ccf" ]; then
    if [ ! -f "${PDO_LEDGER_KEY_ROOT}/networkcert.pem" ]; then
        die "CCF ledger keys are missing, please copy and try again"
    fi
fi

# -----------------------------------------------------------------
SCRIPTDIR="$(dirname $(readlink --canonicalize ${BASH_SOURCE}))"
SOURCE_ROOT="$(realpath ${SCRIPTDIR}/..)"

F_SCRIPT=$(basename ${BASH_SOURCE[-1]} )
F_SERVICE_HOST=${PDO_HOSTNAME}
F_LEDGER_URL=${PDO_LEDGER_URL}
F_LOGLEVEL=${PDO_LOG_LEVEL:-debug}
F_LOGFILE=${PDO_LOG_FILE:-__screen__}
F_CONTEXT_FILE=${SOURCE_ROOT}/test/external_context.toml
F_CONTEXT_TEMPLATES=${PDO_HOME}/contracts/authority/context
F_IDENTITY_TEMPLATES=${PDO_HOME}/contracts/identity/context
F_PREFERRED=http://localhost:7101

F_USAGE='--host service-host | --ledger url | --loglevel [debug|info|warn] | --logfile file | --preferred [host]'
SHORT_OPTS='h:l:p:'
LONG_OPTS='host:,ledger:,loglevel:,logfile:,preferred:'

TEMP=$(getopt -o ${SHORT_OPTS} --long ${LONG_OPTS} -n "${F_SCRIPT}" -- "$@")
if [ $? != 0 ] ; then echo "Usage: ${F_SCRIPT} ${F_USAGE}" >&2 ; exit 1 ; fi

eval set -- "$TEMP"
while true ; do
    case "$1" in
        -h|--host) F_SERVICE_HOST="$2" ; shift 2 ;;
        -l|--ledger) F_LEDGER_URL="$2" ; shift 2 ;;
        -p|--preferred) F_PREFERRED="$2" ; shift 2 ;;
        --loglevel) F_LOGLEVEL="$2" ; shift 2 ;;
        --logfile) F_LOGFILE="$2" ; shift 2 ;;
        --help) echo "Usage: ${F_SCRIPT} ${F_USAGE}"; exit 0 ;;
        --) shift ; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
done

F_SERVICE_SITE_FILE=${PDO_HOME}/etc/sites/${F_SERVICE_HOST}.toml
if [ ! -f ${F_SERVICE_SITE_FILE} ] ; then
    die unable to locate the service information file ${F_SERVICE_SITE_FILE}
fi

F_SERVICE_GROUPS_DB_FILE=${SOURCE_ROOT}/test/${F_SERVICE_HOST}_groups_db
F_SERVICE_DB_FILE=${SOURCE_ROOT}/test/${F_SERVICE_HOST}_db

_COMMON_=("--logfile ${F_LOGFILE}" "--loglevel ${F_LOGLEVEL}")
_COMMON_+=("--ledger ${F_LEDGER_URL}")
_COMMON_+=("--groups-db ${F_SERVICE_GROUPS_DB_FILE}")
_COMMON_+=("--service-db ${F_SERVICE_DB_FILE}")
SHORT_OPTS=${_COMMON_[@]}

_COMMON_+=("--context-file ${F_CONTEXT_FILE}")
OPTS=${_COMMON_[@]}

# -----------------------------------------------------------------
F_KEY_FILES=()
KEYGEN=${PDO_SOURCE_ROOT}/build/__tools__/make-keys

yell create keys for the contracts
for i in 1 2 3 4 5 ; do
    if [ ! -f ${PDO_HOME}/keys/user${i}_private.pem ] ; then
        ${KEYGEN} --keyfile ${PDO_HOME}/keys/user${i} --format pem
        F_KEY_FILES+=(${PDO_HOME}/keys/user${i}_{private,public}.pem)
    fi
done

TEST_ROOT=$(mktemp -d /tmp/external_test.XXXXXXXXX)

function cleanup {
    rm -f ${F_SERVICE_GROUPS_DB_FILE} ${F_SERVICE_GROUPS_DB_FILE}-lock
    rm -f ${F_SERVICE_DB_FILE} ${F_SERVICE_DB_FILE}-lock
    rm -f ${F_CONTEXT_FILE}
    rm -rf ${TEST_ROOT}
    for key_file in ${F_KEY_FILES[@]} ; do
        rm -f ${key_file}
    done
}
trap cleanup EXIT

# -----------------------------------------------------------------
# service and groups databases
# -----------------------------------------------------------------
yell create the service and groups database for host ${F_SERVICE_HOST}
try pdo-service-db import ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE}
try pdo-eservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default \
    --preferred ${F_PREFERRED}
try pdo-pservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default
try pdo-sservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default \
             --replicas 1 --duration 60

# -----------------------------------------------------------------
# contexts: the operator (user1) runs the two authorities; the consumer (user2)
# owns the wallet. Because the wallet's creator is read from the ledger and passed
# to the authority, the operator can attest the consumer's wallet.
# -----------------------------------------------------------------
cd "${SOURCE_ROOT}"
rm -f ${F_CONTEXT_FILE}

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/wallet_key_authority.toml \
    --bind identity wka --bind user user1

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/external_key_authority.toml \
    --bind identity eka --bind user user1

try pdo-context load ${OPTS} --import-file ${F_IDENTITY_TEMPLATES}/identity.toml \
    --bind identity wallet --bind user user2

# =================================================================
# start the tests
# =================================================================

########### setup: the operator creates both authorities and links their trust
yell create the wallet key authority and install the ledger root of trust
try wallet_key_authority create ${OPTS} --contract identity.wka.wallet_key_authority \
    -d 'Wallet Key Authority: attests wallet verifying keys from ledger attestations'

yell create the external key authority
try external_key_authority create ${OPTS} --contract identity.eka.external_key_authority \
    -d 'External Key Authority: binds external session keys to wallets'

yell trust the wallet key authority as an issuer of WalletVerifyingKeyCredentials
try external_key_authority register ${OPTS} --contract identity.eka.external_key_authority \
    --issuer identity.wka.wallet_key_authority --path wallet_key_authority \
    --credential-types WalletVerifyingKeyCredential

########### setup: the consumer's wallet
yell create the consumer wallet
try id_wallet create ${OPTS} --contract identity.wallet.wallet \
    -d 'the consumer''s pdo wallet'

# the consumer discovers their wallet id by listing their contracts from the
# ledger. The user_contracts table is keyed by the user's verifying key; user2
# owns only the wallet, so it is the single entry.
yell list the consumer wallets from the ledger to find the wallet id
try pdo-ledger user-contracts --url ${F_LEDGER_URL} \
    --key-file ${PDO_HOME}/keys/user2_private.pem --path entries > ${TEST_ROOT}/user_contracts.json
WALLET_ID=$(python3 -c "import json; print(json.load(open('${TEST_ROOT}/user_contracts.json'))[0]['contract_id'])")
WALLET_DID="did:pdo:${WALLET_ID}"
say "wallet DID: ${WALLET_DID}"

########### the consumer gets a WalletVerifyingKeyCredential from the trusted issuer
yell get a WalletVerifyingKeyCredential for the wallet from the wallet key authority
try wallet_key_authority sign_credential ${OPTS} \
    --contract identity.wka.wallet_key_authority \
    --wallet identity.wallet.wallet \
    --credential ${TEST_ROOT}/wallet_verifying_key_vc.json

########### the consumer builds and signs the binding payload
yell generate the external rsa key and build the payload + session-key attestation
try python3 ${SCRIPTDIR}/make_external_key_attestations.py keys ${TEST_ROOT}/keys
try python3 ${SCRIPTDIR}/make_external_key_attestations.py build \
    ${TEST_ROOT}/keys "${WALLET_DID}" \
    ${TEST_ROOT}/payload.json ${TEST_ROOT}/session_key_attestation.json

yell the wallet signs the same payload with its contract key
try id_wallet sign_with_contract_key ${OPTS} --contract identity.wallet.wallet \
    --message ${TEST_ROOT}/payload.json --signature ${TEST_ROOT}/wallet_signature.txt

try python3 ${SCRIPTDIR}/make_external_key_attestations.py wallet_attestation \
    ${TEST_ROOT}/payload.json ${TEST_ROOT}/wallet_signature.txt ${TEST_ROOT}/wallet_attestation.json

########### bind the external session key
yell verify everything and issue a publicKeyCredential for the session key
try external_key_authority sign_credential ${OPTS} \
    --contract identity.eka.external_key_authority \
    --wallet-verifying-key-credential ${TEST_ROOT}/wallet_verifying_key_vc.json \
    --wallet-attestation ${TEST_ROOT}/wallet_attestation.json \
    --session-key-attestation ${TEST_ROOT}/session_key_attestation.json \
    --credential ${TEST_ROOT}/session_key_vc.json

say issued credential:
cat ${TEST_ROOT}/session_key_vc.json
echo

if ! grep -q "publicKeyCredential" ${TEST_ROOT}/session_key_vc.json ; then
    die "issued credential is not a publicKeyCredential"
fi

########### verify the issued credential against the authority
yell verify the issued credential against the authority
try external_key_authority verify_credential ${OPTS} \
    --contract identity.eka.external_key_authority \
    --signed-credential ${TEST_ROOT}/session_key_vc.json

yell All tests passed
