#!/bin/bash
set -e

: "${F_GUARDIAN_HOST?Missing environment variable F_GUARDIAN_HOST}"

SCRIPTDIR="$(dirname $(readlink --canonicalize ${BASH_SOURCE}))"
source ${SCRIPTDIR}/setup_test.sh

TEST_ROOT=$(mktemp -d /tmp/test.XXXXXXXXX)

# -----------------------------------------------------------------
# setup the contexts that will be used later for the tests
# -----------------------------------------------------------------
cd "${SOURCE_ROOT}"

# create any necessary contexts here
try pdo-context load ${OPTS} --import-file ${F_IDENTITY_TEMPLATES}/signature_authority.toml \
    --bind identity membership_authority --bind user user1

try pdo-context load ${OPTS} --import-file ${F_IDENTITY_TEMPLATES}/signature_authority.toml \
    --bind identity consent_authority --bind user user2

try pdo-context load ${OPTS} --import-file ${F_IDENTITY_TEMPLATES}/signature_authority.toml \
    --bind identity public_key_authority --bind user user3

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/policy_agent.toml \
    --bind identity simple_download --bind user user4

try pdo-context load ${OPTS} --import-file ${F_CONTEXT_TEMPLATES}/tokens.toml \
    --bind token test1 --bind user user5 --bind url http://${F_GUARDIAN_HOST}:7900

# -----------------------------------------------------------------
# start the tests
# -----------------------------------------------------------------

# =================================================================

########### setup: membership_authority
yell create a membership_authority and register signing context
try id_signature_authority create ${OPTS} --contract identity.membership_authority.signature_authority \
    -d 'Membership Authority: issues institution membership credentials'

try id_signature_authority register ${OPTS} --contract identity.membership_authority.signature_authority \
    -d 'fixed key satest' --fixed --path membership


########### setup: consent_authority
yell create a consent_authority and register signing context
try id_signature_authority create ${OPTS} --contract identity.consent_authority.signature_authority \
    -d 'Consent Authority: issues consent credentials'

try id_signature_authority register ${OPTS} --contract identity.consent_authority.signature_authority \
    -d 'fixed key satest' --fixed --path consent


########### setup: public_key_authority
yell create a public_key_authority and register signing context
try id_signature_authority create ${OPTS} --contract identity.public_key_authority.signature_authority \
    -d 'Public Key Authority: issues public key credentials'

try id_signature_authority register ${OPTS} --contract identity.public_key_authority.signature_authority \
    -d 'fixed key satest' --fixed --path public_key


########### setup: data_download policy agent
try download_policy create ${OPTS} --contract download.simple_download.policy_agent \
    -d 'data download policy agent: accepts membership, consent, and public key VCs.'

yell register issuer1 with the policy agent
try download_policy register ${OPTS} --contract download.simple_download.policy_agent \
    --issuer identity.membership_authority.signature_authority --path membership --credential-type membership


yell register issuer2 with the policy agent
try download_policy register ${OPTS} --contract download.simple_download.policy_agent \
    --issuer identity.consent_authority.signature_authority --path consent --credential-type consent


yell register issuer3 with the policy agent
try download_policy register ${OPTS} --contract download.simple_download.policy_agent \
    --issuer identity.public_key_authority.signature_authority --path public_key --credential-type public_key

yell configure the policy agent
try download_policy set_policy ${OPTS} --contract download.simple_download.policy_agent \
    --data ${SCRIPTDIR}/policy_data.json


########### setup: data download token

yell create a token issuer and mint the tokens
try ex_token_issuer create ${OPTS} --contract token.test1.token_issuer
try download_token mint_tokens ${OPTS} --contract token.test1.token_object

yell register a trusted VC issuer for token1
try download_token register ${OPTS}  --contract token.test1.token_object.token_1 \
    --issuer download.simple_download.policy_agent --path __ISSUER__ --credential-type download

########### start
yell generating user channel key
python3 ${SCRIPTDIR}/generate_channel_key.py ${TEST_ROOT}/user_channel_key

yell sign membership credential
try id_signature_authority sign_credential ${OPTS} --contract identity.membership_authority.signature_authority \
    --path membership --credential ${SCRIPTDIR}/credential_membership.json --signed-credential ${TEST_ROOT}/membership_vc.json

yell sign consent credential
try id_signature_authority sign_credential ${OPTS} --contract identity.consent_authority.signature_authority \
    --path consent --credential ${SCRIPTDIR}/credential_consent.json --signed-credential ${TEST_ROOT}/consent_vc.json

yell sign public key credential
try id_signature_authority sign_credential ${OPTS} --contract identity.public_key_authority.signature_authority \
    --path public_key --credential ${TEST_ROOT}/user_channel_key/credential_key.json --signed-credential ${TEST_ROOT}/public_key_vc.json

yell combine credentials
python3 ${SCRIPTDIR}/combine.py \
    ${TEST_ROOT}/membership_vc.json \
    ${TEST_ROOT}/consent_vc.json \
    ${TEST_ROOT}/public_key_vc.json \
    ${TEST_ROOT}/combined.json


yell issue a credential
try download_policy issue_credential ${OPTS} --contract download.simple_download.policy_agent \
    --signed-credential ${TEST_ROOT}/combined.json --issued-credential ${TEST_ROOT}/combined_vc.json


yell download data
try download_token do_download ${OPTS}  --contract token.test1.token_object.token_1 \
    --vc-file ${TEST_ROOT}/combined_vc.json \
    --output-file ${TEST_ROOT}/encrypted_data.bin

yell read data

python3 ${SCRIPTDIR}/read_data.py ${TEST_ROOT}/encrypted_data.bin \
    ${TEST_ROOT}/user_channel_key/private_key.pem ${TEST_ROOT}/decrypted_data.txt

cat ${TEST_ROOT}/decrypted_data.txt
echo

yell All tests passed
