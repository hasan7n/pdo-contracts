#!/bin/bash

# Copyright 2023 Intel Corporation
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
# End-to-end CLI test for the rego_token + rego_policy_agent flow. It mirrors
# the download-contract script test: a rego_policy_agent issues a signed
# "policy_decision" credential (whose claims are the merged Rego operation) and a
# rego_token turns that credential into a guardian capability that returns the
# encrypted data.
# -----------------------------------------------------------------
: "${PDO_LEDGER_URL?Missing environment variable PDO_LEDGER_URL}"
: "${PDO_HOME?Missing environment variable PDO_HOME}"
: "${PDO_SOURCE_ROOT?Missing environment variable PDO_SOURCE_ROOT}"

# -----------------------------------------------------------------
# -----------------------------------------------------------------
source ${PDO_HOME}/bin/lib/common.sh
check_python_version

if ! command -v pdo-shell &> /dev/null ; then
    yell unable to locate pdo-shell
    exit 1
fi

# -----------------------------------------------------------------
# -----------------------------------------------------------------
if [ "${PDO_LEDGER_TYPE}" == "ccf" ]; then
    if [ ! -f "${PDO_LEDGER_KEY_ROOT}/networkcert.pem" ]; then
        die "CCF ledger keys are missing, please copy and try again"
    fi
fi

# -----------------------------------------------------------------
# Process command line arguments
# -----------------------------------------------------------------
COMMON_CONTRACT_ROOT=${PDO_HOME}/contracts/contracts

SCRIPTDIR="$(dirname $(readlink --canonicalize ${BASH_SOURCE}))"
SOURCE_ROOT="$(realpath ${SCRIPTDIR}/..)"

F_SCRIPT=$(basename ${BASH_SOURCE[-1]} )
F_SERVICE_HOST=${PDO_HOSTNAME}
F_GUARDIAN_HOST=${PDO_HOSTNAME}
F_LEDGER_URL=${PDO_LEDGER_URL}
F_LOGLEVEL=${PDO_LOG_LEVEL:-debug}
F_LOGFILE=${PDO_LOG_FILE:-__screen__}
F_CONTEXT_FILE=${SOURCE_ROOT}/test/test_context.toml
F_CONTEXT_TEMPLATES=${PDO_HOME}/contracts/rego/context
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
        -1|--ledger) F_LEDGER_URL="$2" ; shift 2 ;;
        -p|--preferred) F_PREFERRED="$2" ; shift 2 ;;
        --loglevel) F_LOGLEVEL="$2" ; shift 2 ;;
        --logfile) F_LOGFILE="$2" ; shift 2 ;;
        --help) echo "Usage: ${SCRIPT_NAME} ${F_USAGE}"; exit 0 ;;
        --) shift ; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
done

F_SERVICE_SITE_FILE=${PDO_HOME}/etc/sites/${F_SERVICE_HOST}.toml
if [ ! -f ${F_SERVICE_SITE_FILE} ] ; then
    die unable to locate the service information file ${F_SERVICE_SITE_FILE}; \
        please copy the site.toml file from the service host
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
# Make sure the keys and eservice database are created and up to date
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

TEST_ROOT=$(mktemp -d /tmp/test.XXXXXXXXX)

if [ ! -f ${PDO_HOME}/keys/guardian_service.pem ]; then
    yell create keys for the guardian service
    ${KEYGEN} --keyfile ${PDO_HOME}/keys/guardian_service --format pem
    F_KEY_FILES+=(${PDO_HOME}/keys/guardian_service.pem)

    ${KEYGEN} --keyfile ${PDO_HOME}/keys/guardian_sservice --format pem
    F_KEY_FILES+=(${PDO_HOME}/keys/guardian_sservice.pem)
fi

# -----------------------------------------------------------------
function cleanup {
    read -p "Press Enter to continue..."
    rm -f ${F_SERVICE_GROUPS_DB_FILE} ${F_SERVICE_GROUPS_DB_FILE}-lock
    rm -f ${F_SERVICE_DB_FILE} ${F_SERVICE_DB_FILE}-lock
    rm -f ${F_CONTEXT_FILE}
    for key_file in ${F_KEY_FILES[@]} ; do
        rm -f ${key_file}
    done

    yell "shutdown guardian and storage service"
    ${COMMON_CONTRACT_ROOT}/scripts/gs_stop.sh
    ${COMMON_CONTRACT_ROOT}/scripts/ss_stop.sh

}

trap cleanup EXIT



# -----------------------------------------------------------------
# Start the guardian service and the storage service
# -----------------------------------------------------------------
try ${COMMON_CONTRACT_ROOT}/scripts/ss_start.sh -c -o ${PDO_HOME}/logs -- \
    --loglevel debug \
    --config guardian_service.toml \
    --config-dir ${PDO_HOME}/etc/contracts \
    --identity guardian_sservice

sleep 3

try ${COMMON_CONTRACT_ROOT}/scripts/gs_start.sh -c -o ${PDO_HOME}/logs -- \
    --loglevel debug \
    --config guardian_service.toml \
    --config-dir ${PDO_HOME}/etc/contracts \
    --identity guardian_service \
    --bind host ${F_GUARDIAN_HOST} \
    --bind service_host ${F_SERVICE_HOST}
# -----------------------------------------------------------------




# -----------------------------------------------------------------
# create the service and groups databases from a site file; the site
# file is assumed to exist in ${PDO_HOME}/etc/sites/${SERVICE_HOST}.toml
#
# by default, the groups will include all available services from the
# service host
# -----------------------------------------------------------------
yell create the service and groups database for host ${F_SERVICE_HOST}
try pdo-service-db import ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE}
try pdo-eservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default \
    --preferred ${F_PREFERRED}
try pdo-pservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default
try pdo-sservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default \
             --replicas 1 --duration 60

# -----------------------------------------------------------------
# setup the contexts that will be used later for the tests
# -----------------------------------------------------------------
cd "${SOURCE_ROOT}"

rm -f ${F_CONTEXT_FILE}

# create any necessary contexts here
try pdo-context load ${OPTS} --import-file ${F_IDENTITY_TEMPLATES}/signature_authority.toml \
    --bind identity public_key_authority --bind user user1

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/rego_policy_agent.toml \
    --bind identity rego_download --bind user user4

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/tokens.toml \
    --bind token test1 --bind user user4 --bind url http://${F_GUARDIAN_HOST}:7900

try pdo-context load ${OPTS} --import-file ${F_IDENTITY_TEMPLATES}/identity.toml \
    --bind identity downloader --bind user user5


# -----------------------------------------------------------------
# Test data: the token subpolicy (requires role "applicant" -> "public_key")
# -----------------------------------------------------------------
F_TOKEN_SUBPOLICY=${SCRIPTDIR}/subpolicies/token_subpolicy.rego

# -----------------------------------------------------------------
# start the tests
# -----------------------------------------------------------------

# =================================================================

########### setup: public_key_authority
yell create a public_key_authority and register signing context
try id_signature_authority create ${OPTS} --contract identity.public_key_authority.signature_authority \
    -d 'Public Key Authority: issues public key credentials'

try id_signature_authority register ${OPTS} --contract identity.public_key_authority.signature_authority \
    -d 'fixed key satest' --fixed --path public_key


########### setup: rego policy agent
try rego_policy_agent create ${OPTS} --contract identity.rego_download.rego_policy_agent \
    -d 'rego download policy agent: accepts a public key VC and emits a channel key.'

yell register the public_key_authority as a trusted issuer for type "public_key"
try rego_policy_agent register ${OPTS} --contract identity.rego_download.rego_policy_agent \
    --issuer identity.public_key_authority.signature_authority --path public_key --credential-types public_key

yell set the rego policy (token subpolicy)
try rego_policy_agent set_rego_policy ${OPTS} --contract identity.rego_download.rego_policy_agent \
    --module token_subpolicy ${F_TOKEN_SUBPOLICY}

yell set the (opaque) policy data
try rego_policy_agent set_policy ${OPTS} --contract identity.rego_download.rego_policy_agent \
    --data ${SCRIPTDIR}/policy_data.json


########### setup: rego download token

yell create a token issuer and mint the tokens
try ex_token_issuer create ${OPTS} --contract token.test1.token_issuer
try rego_token mint_tokens ${OPTS} --contract token.test1.token_object

yell register the rego policy agent as the trusted VC issuer for token1
try rego_token register ${OPTS}  --contract token.test1.token_object.token_1 \
    --issuer identity.rego_download.rego_policy_agent --path __ISSUER__ --credential-types policy_decision

########### setup: downloader wallet

yell create an identity contract
try id_wallet create ${OPTS} --contract identity.downloader.wallet \
    -d 'idtest identity'

########### start
yell generating user channel key
python3 ${SCRIPTDIR}/python/generate_channel_key.py ${TEST_ROOT}/user_channel_key

yell sign public key credential
try id_signature_authority sign_credential ${OPTS} --contract identity.public_key_authority.signature_authority \
    --path public_key --credential ${TEST_ROOT}/user_channel_key/credential_key.json --signed-credential ${TEST_ROOT}/public_key_vc.json

yell add credential to wallet
try id_wallet add_vc ${OPTS} --contract identity.downloader.wallet \
    --credential ${TEST_ROOT}/public_key_vc.json

yell generating a VP
try id_wallet get_vp ${OPTS} --contract identity.downloader.wallet \
    --types public_key --file ${TEST_ROOT}/vp.json

# wrap the presentation under the required role: { "applicant": <VP> }
echo "{\"applicant\": $(cat ${TEST_ROOT}/vp.json)}" > ${TEST_ROOT}/presentation.json

yell issue a policy decision credential
try rego_policy_agent issue_credential ${OPTS} --contract identity.rego_download.rego_policy_agent \
    --presentation ${TEST_ROOT}/presentation.json --issued-credential ${TEST_ROOT}/policy_vc.json

yell download data
try rego_token do_operation ${OPTS}  --contract token.test1.token_object.token_1 \
    --vc-file ${TEST_ROOT}/policy_vc.json \
    --output-file ${TEST_ROOT}/encrypted_data.bin

yell read data

python3 ${SCRIPTDIR}/python/read_data.py ${TEST_ROOT}/encrypted_data.bin \
    ${TEST_ROOT}/user_channel_key/private_key.pem ${TEST_ROOT}/decrypted_data.txt

cat ${TEST_ROOT}/decrypted_data.txt
echo

########### other tests
yell test some other endpoints
try rego_token list_issuers ${OPTS} --contract token.test1.token_object.token_1

yell All tests passed
