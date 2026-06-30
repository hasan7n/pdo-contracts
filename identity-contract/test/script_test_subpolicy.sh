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
# End-to-end CLI test for the rego_policy_agent (subpolicy + combinator flow).
#
# It creates a credential holder (wallet), a signature authority (trusted
# issuer), and a rego_policy_agent; provisions two subpolicies; then issues a
# policy credential whose claims are the merged subpolicy context.
# -----------------------------------------------------------------

# -----------------------------------------------------------------
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
# Process command line arguments
# -----------------------------------------------------------------
SCRIPTDIR="$(dirname $(readlink --canonicalize ${BASH_SOURCE}))"
SOURCE_ROOT="$(realpath ${SCRIPTDIR}/..)"

F_SCRIPT=$(basename ${BASH_SOURCE[-1]} )
F_SERVICE_HOST=${PDO_HOSTNAME}
F_LEDGER_URL=${PDO_LEDGER_URL}
F_LOGLEVEL=${PDO_LOG_LEVEL:-info}
F_LOGFILE=${PDO_LOG_FILE:-__screen__}
F_CONTEXT_FILE=${SOURCE_ROOT}/test/subpolicy_test_context.toml
F_CONTEXT_TEMPLATES=${PDO_HOME}/contracts/identity/context
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

F_SERVICE_GROUPS_DB_FILE=${SOURCE_ROOT}/test/${F_SERVICE_HOST}_subpolicy_groups_db
F_SERVICE_DB_FILE=${SOURCE_ROOT}/test/${F_SERVICE_HOST}_subpolicy_db

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
for i in 1 2 3 ; do
    if [ ! -f ${PDO_HOME}/keys/user${i}_private.pem ] ; then
        ${KEYGEN} --keyfile ${PDO_HOME}/keys/user${i} --format pem
        F_KEY_FILES+=(${PDO_HOME}/keys/user${i}_{private,public}.pem)
    fi
done

TEST_ROOT=$(mktemp -d /tmp/subpolicy_test.XXXXXXXXX)

# -----------------------------------------------------------------
function cleanup {
    rm -f ${F_SERVICE_GROUPS_DB_FILE} ${F_SERVICE_GROUPS_DB_FILE}-lock
    rm -f ${F_SERVICE_DB_FILE} ${F_SERVICE_DB_FILE}-lock
    rm -f ${F_CONTEXT_FILE}
    for key_file in ${F_KEY_FILES[@]} ; do
        rm -f ${key_file}
    done
    # rm -rf ${TEST_ROOT}
}

trap cleanup EXIT

# -----------------------------------------------------------------
yell create the service and groups database for host ${F_SERVICE_HOST}
try pdo-service-db import ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE}
try pdo-eservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default \
    --preferred ${F_PREFERRED}
try pdo-pservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default
try pdo-sservice create_from_site ${SHORT_OPTS} --file ${F_SERVICE_SITE_FILE} --group default \
             --replicas 1 --duration 60

# -----------------------------------------------------------------
# setup the contexts used below
# -----------------------------------------------------------------
cd "${SOURCE_ROOT}"
rm -f ${F_CONTEXT_FILE}

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/identity.toml \
    --bind identity idtest --bind user user1

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/signature_authority.toml \
    --bind identity satest --bind user user2

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/rego_policy_agent.toml \
    --bind identity rptest --bind user user3

# -----------------------------------------------------------------
# Test data: the sample subpolicies (both require role "applicant" -> "dummy")
# -----------------------------------------------------------------
F_SUBPOLICY_A=${SCRIPTDIR}/subpolicies/subpolicy_a.rego
F_SUBPOLICY_B=${SCRIPTDIR}/subpolicies/subpolicy_b.rego

# =================================================================
yell create the credential holder (wallet)
try id_wallet create ${OPTS} --contract identity.idtest.wallet -d 'idtest identity'
try id_wallet register ${OPTS} --contract identity.idtest.wallet \
    -d 'fixed key idtest.fixed' --fixed --path idtest fixed
try id_wallet register ${OPTS} --contract identity.idtest.wallet \
    -d 'extended key idtest.ext1' --extensible --path idtest ext1

# =================================================================
yell create the signature authority (the trusted issuer)
try id_signature_authority create ${OPTS} --contract identity.satest.signature_authority \
    -d 'satest signature authority'
try id_signature_authority register ${OPTS} --contract identity.satest.signature_authority \
    -d 'extended key satest.ext1' --extensible --path satest ext1

yell sign the "dummy" credential with the signature authority
try id_signature_authority sign_credential ${OPTS} --contract identity.satest.signature_authority \
    --path satest ext1 --credential ${SCRIPTDIR}/credential1.json \
    --signed-credential ${TEST_ROOT}/sa_credential1.json

yell store the signed credential in the holder wallet
try id_wallet add_vc ${OPTS} --contract identity.idtest.wallet \
    --credential ${TEST_ROOT}/sa_credential1.json

# =================================================================
yell create the rego policy agent
try id_rego_policy_agent create ${OPTS} --contract identity.rptest.rego_policy_agent \
    -d 'rptest rego policy agent'

yell register the signature authority as a trusted issuer for type "dummy"
try id_rego_policy_agent register ${OPTS} --contract identity.rptest.rego_policy_agent \
    --issuer identity.satest.signature_authority --path satest ext1 --credential-types dummy

yell set the rego policy (subpolicy_a + subpolicy_b)
try id_rego_policy_agent set_rego_policy ${OPTS} --contract identity.rptest.rego_policy_agent \
    --module subpolicy_a ${F_SUBPOLICY_A} \
    --module subpolicy_b ${F_SUBPOLICY_B}

yell fetch the stored policy
try id_rego_policy_agent get_rego_policy ${OPTS} --contract identity.rptest.rego_policy_agent

yell fetch the merged requirements (expect role "applicant" -> [dummy])
F_REQUIREMENTS=$(id_rego_policy_agent get_requirements ${OPTS} \
    --contract identity.rptest.rego_policy_agent)
say "merged requirements: ${F_REQUIREMENTS}"
if [[ "${F_REQUIREMENTS}" != *"applicant"* || "${F_REQUIREMENTS}" != *"dummy"* ]] ; then
    die "expected merged requirements to contain role 'applicant' and type 'dummy', got: ${F_REQUIREMENTS}"
fi

# =================================================================
yell build a verifiable presentation for the "dummy" credential
try id_wallet get_vp ${OPTS} --contract identity.idtest.wallet \
    --types dummy --file ${TEST_ROOT}/vp1.json

# wrap the presentation under the required role: { "applicant": <VP> }
echo "{\"applicant\": $(cat ${TEST_ROOT}/vp1.json)}" > ${TEST_ROOT}/presentation.json

yell issue the policy credential (claims = merged subpolicy context)
try id_rego_policy_agent issue_credential ${OPTS} --contract identity.rptest.rego_policy_agent \
    --presentation ${TEST_ROOT}/presentation.json \
    --issued-credential ${TEST_ROOT}/rp_credential.json

say issued policy credential is:
say $(<${TEST_ROOT}/rp_credential.json)

yell extract the issued credential (claims should carry the merged context)
try id_credential extract --signed-credential ${TEST_ROOT}/rp_credential.json

# =================================================================
yell All rego_policy_agent subpolicy tests passed
