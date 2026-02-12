/* Copyright 2023 Intel Corporation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <string>
#include <stddef.h>
#include <stdint.h>

#include "Dispatch.h"

#include "Cryptography.h"
#include "KeyValue.h"
#include "Environment.h"
#include "Message.h"
#include "Response.h"
#include "Types.h"
#include "Util.h"
#include "Value.h"
#include "WasmExtensions.h"

#include "contract/base.h"
#include "identity/identity.h"
#include "identity/policy_agent.h"
#include "identity/common/Credential.h"
#include "identity/common/VerifyingContext.h"

static KeyValueStore trusted_issuer_store("issuer_store");
static KeyValueStore policy_metadata_store("policy_metadata_store");
static KeyValueStore issuer_type_mapping("issuer_type_mapping");

const std::string md_issuer_path("issuer_path");
const std::string md_policy_data("policy_data");
const std::string initial_issuer_path("__ISSUER__");


bool ww::identity::policy_agent::what(const Message &msg, const Environment &env, Response &rsp)
{
    ASSERT_SENDER_IS_OWNER(env, rsp);
    ww::identity::VerifyingContext verifier;
    std::vector<std::string> prefix_path;
    prefix_path.push_back("gg");

    std::string valid_pem_key = "-----BEGIN PUBLIC KEY-----\nMHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEiEnWZtKnzHZutccKe15hpBKelgqHQC2J\n5Wqae1bfbLZgsVNBzaU7OjFRgUjkOoJAKcPmPIC+NGMAA6DIe/YDOkMjm1yCGWgJ\ndyYf0W2V3UfvCd/auxn+D5D1wWFw4gEB\n-----END PUBLIC KEY-----";
    std::string valid_chain_code = "MTIzNDU2Nzg5MGFiY2RlZjEyMzQ1Njc4OTBhYmNkZWY="; // base64 32 bytes
    ASSERT_SUCCESS(rsp, verifier.initialize(prefix_path, valid_pem_key, valid_chain_code),
                   "invalid request, invalid issuer public key/chain code");
    return rsp.success(true);
}


// -----------------------------------------------------------------
// FUNCTION: save_trusted_issuer
// -----------------------------------------------------------------
bool ww::identity::policy_agent::save_trusted_issuer(
    const std::string &issuer_id,
    const ww::identity::VerifyingContext &vc,
    const std::string &credential_type)
{
    // ---------- save the trusted issuer ----------
    ww::value::Value trusted_issuer;
    ERROR_IF_NOT(vc.serialize(trusted_issuer),
                 "unexpected error, failed to serialize trusted issuer");

    std::string trusted_issuer_str;
    ERROR_IF_NOT(trusted_issuer.serialize(trusted_issuer_str),
                 "unexpected error, failed to serialize trusted issuer");

    // TODO: atomic store of both the trusted issuer and its type?
    ERROR_IF_NOT(issuer_type_mapping.set(issuer_id, credential_type),
                 "unexpected error, failed to save issuer type mapping");

    return trusted_issuer_store.set(issuer_id, trusted_issuer_str);
}

// -----------------------------------------------------------------
// FUNCTION: fetch_trusted_issuer
// -----------------------------------------------------------------
bool ww::identity::policy_agent::fetch_trusted_issuer(
    const std::string &issuer_id,
    ww::identity::VerifyingContext &vc,
    const std::string &credential_type)
{
    // ---------- fetch the trusted issuer ----------
    std::string trusted_issuer_str;
    ERROR_IF_NOT(trusted_issuer_store.get(issuer_id, trusted_issuer_str),
                 "unexpected error, failed to fetch trusted issuer");

    // verify issuer type
    std::string stored_credential_type;
    ERROR_IF_NOT(issuer_type_mapping.get(issuer_id, stored_credential_type),
                 "unexpected error, failed to fetch issuer type mapping");
    ERROR_IF_NOT(stored_credential_type == credential_type,
                 "invalid request, credential type does not match issuer type");

    ww::value::Object trusted_issuer;
    ERROR_IF_NOT(trusted_issuer.deserialize(trusted_issuer_str.c_str()),
                 "unexpected error, failed to deserialize trusted issuer");
    ERROR_IF_NOT(vc.deserialize(trusted_issuer),
                 "unexpected error, failed to deserialize verifying context");

    return true;
}

// -----------------------------------------------------------------
// FUNCTION: verify_credential
// -----------------------------------------------------------------
bool ww::identity::policy_agent::verify_credential(
    const ww::value::Object &vc_object,
    ww::identity::VerifiableCredential &vc,
    const std::string &credential_type)
{
    ERROR_IF_NOT(vc.deserialize(vc_object), "invalid request, ill-formed credential");

    // Verify the credential signature

    // The signature was computed over the base64 encoded credential so we
    // do not need to decode the credential before checking the signature
    const std::string serialized_credential(vc.get_serialized_credential());
    ww::types::ByteArray message(serialized_credential.begin(), serialized_credential.end());

    ww::types::ByteArray signature;
    ERROR_IF_NOT(ww::crypto::b64_decode(vc.proof_.proofValue_, signature),
                 "invalid request, ill-formed signature");

    ww::identity::VerifyingContext verifier;
    ERROR_IF_NOT(fetch_trusted_issuer(vc.proof_.verificationMethod_.id_, verifier, credential_type),
                 "invalid request, unknown issuer");

    ERROR_IF_NOT(verifier.extend_context_path(vc.proof_.verificationMethod_.context_path_),
                 "invalid request, ill-formed context path");

    ERROR_IF_NOT(verifier.verify_signature(message, signature),
                 "invalid request, signature verification failed");

    return true;
}

// -----------------------------------------------------------------
// FUNCTION: issue_credential
// -----------------------------------------------------------------
bool ww::identity::policy_agent::issue_credential(
    const std::string &originator,
    const std::string &contract_id,
    const ww::identity::Credential &credential,
    ww::identity::VerifiableCredential &vc)
{
    // the context path that we are using is the path configured in the policy
    // agent (initially the initial_issuer_path) plus the hash of the originator's
    // public key. the originator's public key is hashed to ensure that the context path
    // is unique to the originator.

    // hash the originator's public key
    ww::types::ByteArray originator_bytes(originator.begin(), originator.end());
    ww::types::ByteArray originator_hash;
    ERROR_IF_NOT(ww::crypto::hash::sha256_hash(originator_bytes, originator_hash),
                 "unexpected error, failed to hash the originator");

    std::string encoded_originator;
    ERROR_IF_NOT(ww::crypto::b64_encode(originator_hash, encoded_originator),
                 "unexpected error, failed to encode the originator");

    // setup the context path
    std::vector<std::string> context_path = {initial_issuer_path, encoded_originator};
    ww::identity::SigningContext context;
    std::vector<std::string> extended_path;

    ww::identity::SigningContextManager manager = ww::identity::identity::get_context_manager();
    ERROR_IF_NOT(manager.find_context(context_path, extended_path, context),
                 "unexpected error, failed to locate the policy issuer context");

    context.set_context_path(extended_path);

    // std::vector<const std::string>::iterator path_element;
    // for (path_element = extended_path.begin(); path_element < extended_path.end(); path_element++)
    //     context_path.push_back(*path_element);

    // Sign the credential using the signing context just created
    ww::identity::VerifiableCredential vc_out;
    const ww::identity::IdentityKey identity(contract_id, context_path);

    ww::value::Object credential_object;
    ERROR_IF_NOT(credential.serialize(credential_object),
                 "unexpected error, failed to serialize the credential");

    ERROR_IF_NOT(vc.build(credential_object, identity, context),
                 "unexpected error, failed to build the credential");

    return true;
}

// -----------------------------------------------------------------
// METHOD: initialize_contract
//   contract initialization method
//
// JSON PARAMETERS:
//   none
//
// RETURNS:
//   true if successfully initialized
// -----------------------------------------------------------------
bool ww::identity::policy_agent::initialize_contract(const Environment &env)
{
    // ---------- initialize the base contract ----------
    if (!ww::identity::identity::initialize_contract(env))
        return false;

    // ----------initialize the trusted issuer ----------
    // the trusted issuer is the path to the root key used to
    // sign credentials that are generated by this policy agent
    if (!policy_metadata_store.set(md_issuer_path, initial_issuer_path))
        return false;

    std::vector<std::string> context_path = {initial_issuer_path};
    const std::string description("initial issuer path");
    const bool extensible = true;

    ww::identity::SigningContextManager manager = ww::identity::identity::get_context_manager();
    if (!manager.add_context(extensible, description, context_path))
        return false;

    return true;
}

// -----------------------------------------------------------------
// METHOD: register_trusted_issuer
//   Register the public key and chain code of a trusted issuer, note
//   that for the moment this is implemented with the assumption that
//   the invoker (the owner of the contract) is the only one who can
//   register trusted issuers.  This could be expanded to allow for
//   formal registration of endpoints including proof that a specific
//   contract object exists.
//
//   Any duplicate registration for a given ID will, for the moment,
//   fail. This is a simple policy that may be changed by others using
//   this approach.
//
// JSON PARAMETERS:
//   POLICY_AGENT_REGISTER_ISSUER_PARAM_SCHEMA
//
// RETURNS:
//   true if the registration succeeds
// -----------------------------------------------------------------
bool ww::identity::policy_agent::register_trusted_issuer(const Message &msg, const Environment &env, Response &rsp)
{
    ASSERT_SENDER_IS_OWNER(env, rsp);
    ASSERT_INITIALIZED(rsp);

    ASSERT_SUCCESS(rsp, msg.validate_schema(POLICY_AGENT_REGISTER_ISSUER_PARAM_SCHEMA),
                   "invalid request, missing required parameters");

    const std::string issuer_identity(msg.get_string("issuer_identity"));
    const std::string credential_type(msg.get_string("credential_type"));
    const std::string public_key_str(msg.get_string("public_key"));
    const std::string chain_code_str(msg.get_string("chain_code"));

    // Get and validate the path parameter. This is the path TO the
    // key relative to the contract object, any verification key from
    // this issuer must be prefixed by this key path; note that this
    // is not the same as the context_path field in Context objects
    // which describes the path to the key FROM the context.
    std::vector<std::string> prefix_path;
    ASSERT_SUCCESS(rsp, ww::identity::identity::get_context_path(msg, prefix_path, 0),
                   "invalid request, ill-formed context path");

    // ---------- create the verifying context ----------
    ww::identity::VerifyingContext verifier;
    ASSERT_SUCCESS(rsp, verifier.initialize(prefix_path, public_key_str, chain_code_str),
                   "invalid request, invalid issuer public key/chain code");
    ASSERT_SUCCESS(rsp, save_trusted_issuer(issuer_identity, verifier, credential_type),
                   "unexpected error, failed to save issuer information");

    // ---------- RETURN ----------
    return rsp.success(true);
}

// -----------------------------------------------------------------
// METHOD: issue_policy_credential
//   Verify the incoming credential, process the policy decision and emit a new credential
//
// JSON PARAMETERS:
//   POLICY_AGENT_ISSUE_POLICY_CREDENTIAL_PARAM_SCHEMA
// RETURNS:
//   true signature is verified
// -----------------------------------------------------------------
bool ww::identity::policy_agent::issue_policy_credential(const Message &msg, const Environment &env, Response &rsp)
{
    ASSERT_INITIALIZED(rsp);

    ASSERT_SUCCESS(rsp, msg.validate_schema(POLICY_AGENT_ISSUE_POLICY_CREDENTIAL_PARAM_SCHEMA),
                   "invalid request, missing required parameters");

    // Get the credential parameter
    ww::value::Object vc_objects;
    ASSERT_SUCCESS(rsp, msg.get_value("credential", vc_objects), "missing required parameter; credential");

    // Get the membership parameter
    ww::value::Object membership_vc_object;
    ASSERT_SUCCESS(rsp, vc_objects.get_value("membership", membership_vc_object), "missing required parameter; membership");

    // Verify the credential signature
    ww::identity::VerifiableCredential membership_vc;
    ASSERT_SUCCESS(rsp, verify_credential(membership_vc_object, membership_vc, "membership"), "invalid request, ill-formed credential");

    // Get the consent parameter
    ww::value::Object consent_vc_object;
    ASSERT_SUCCESS(rsp, vc_objects.get_value("consent", consent_vc_object), "missing required parameter; consent");

    // Verify the credential signature
    ww::identity::VerifiableCredential consent_vc;
    ASSERT_SUCCESS(rsp, verify_credential(consent_vc_object, consent_vc, "consent"), "invalid request, ill-formed credential");

    // Get the key parameter
    ww::value::Object key_vc_object;
    ASSERT_SUCCESS(rsp, vc_objects.get_value("public_key", key_vc_object), "missing required parameter; public_key");

    // Verify the credential signature
    ww::identity::VerifiableCredential key_vc;
    ASSERT_SUCCESS(rsp, verify_credential(key_vc_object, key_vc, "public_key"), "invalid request, ill-formed credential");

    // get the policy data
    std::string policy_data_str;
    ASSERT_SUCCESS(rsp, policy_metadata_store.get(md_policy_data, policy_data_str),
                   "unexpected error, failed to fetch policy data");

    ww::value::Object policy_data_object;

    ASSERT_SUCCESS(rsp, policy_data_object.deserialize(policy_data_str.c_str()),
                   "unexpected error, failed to fetch policy data");

    // And build the veriable credential; just wanted to note that it would be
    // completely appropriate to make a constructor for VC's that took the
    // information for build; however, there are no exceptions with our current
    // WASM interpreter so failure in the constructor would be a catastrophic
    // failure for the contract

    // ---------- RETURN ----------
    ww::identity::Credential credential_out;
    CONTRACT_SAFE_LOG(3, "prepare to evaluate the policy");
    ASSERT_SUCCESS(rsp, policy_agent_function(membership_vc.credential_, consent_vc.credential_, key_vc.credential_, credential_out, policy_data_object),
                   "policy failed");

    credential_out.issuer_.id_ = env.contract_id_;

    ww::identity::VerifiableCredential vc_out;
    ASSERT_SUCCESS(rsp, issue_credential(env.originator_id_, env.contract_id_, credential_out, vc_out),
                   "unexpected error, failed to create the new credential");

    ww::value::Object serialized_vc_out;
    ASSERT_SUCCESS(rsp, vc_out.serialize(serialized_vc_out),
                   "unexpected error, failed to serialized the credential");

    return rsp.value(serialized_vc_out, false);
}

// -----------------------------------------------------------------
// METHOD: issue_policy_credential
//   Verify the incoming credential, process the policy decision and emit a new credential
//
// JSON PARAMETERS:
//   POLICY_AGENT_ISSUE_POLICY_CREDENTIAL_PARAM_SCHEMA
// RETURNS:
//   true signature is verified
// -----------------------------------------------------------------
bool ww::identity::policy_agent::set_policy_data(const Message &msg, const Environment &env, Response &rsp)
{
    ASSERT_SENDER_IS_OWNER(env, rsp);
    ASSERT_INITIALIZED(rsp);

    ASSERT_SUCCESS(rsp, msg.validate_schema(POLICY_AGENT_SET_POLICY_DATA_PARAM_SCHEMA),
                   "invalid request, missing required parameters");

    ww::value::Object policy_data;
    ASSERT_SUCCESS(rsp, msg.get_value("data", policy_data), "missing required parameter; credential");

    std::string serialized_policy_data;
    ASSERT_SUCCESS(rsp, policy_data.serialize(serialized_policy_data), "failed to serialize policy data");

    ASSERT_SUCCESS(rsp, policy_metadata_store.set(md_policy_data, serialized_policy_data), "failed to save policy data");

    return rsp.success(true);
}
