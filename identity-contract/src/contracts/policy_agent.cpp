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
#include "identity/signature_authority.h"
#include "identity/policy_agent.h"

// -----------------------------------------------------------------
// FUNCTION: echo_policy
//
// This is a simple policy function that is useful for testing. It
// simply reissues the credential that it receives.
// -----------------------------------------------------------------


static bool is_institution_allowed(const std::string& institution_to_check, const ww::value::Array& allowed_institutions) {
    size_t count = allowed_institutions.get_count();
    for (size_t i = 0; i < count; i++) {
        const char* institution = allowed_institutions.get_string(i);
        if (institution != NULL && institution_to_check == institution) {
            return true;  // Found it!
        }
    }
    return false;  // Not found
}

bool ww::identity::policy_agent::policy_agent_function(
    const ww::identity::Credential& membership_vc,
    const ww::identity::Credential& consent_vc,
    const ww::identity::Credential& key_vc,
    ww::identity::Credential& credential_out,
    const ww::value::Object& policy_data)
{
    // -----------------------------------------------------------------
    // -----------------------------------------------------------------
    ww::value::Array allowed_institutions;
    ERROR_IF_NOT(policy_data.get_value("allowed_institutions", allowed_institutions),
                "unexpected error, failed to get allowed institutions")
    
    const ww::value::Object& membership_claims = membership_vc.credentialSubject_.claims_;
    
    const char* institution = membership_claims.get_string("member_of");
    ERROR_IF_NOT(institution != NULL,
                 "membership credential missing member_of claim");
    
    std::string institution_str(institution);

    ERROR_IF_NOT(is_institution_allowed(institution_str, allowed_institutions),
                "Institution is not allowed");

    // -----------------------------------------------------------------
    // -----------------------------------------------------------------
    const char* consent_document = policy_data.get_string("consent_document");
    ERROR_IF_NOT(consent_document != NULL,
                "unexpected error, failed to get consent document");
    std::string consent_document_str(consent_document);

    const ww::value::Object& consent_claims = consent_vc.credentialSubject_.claims_;
    const char* signed_doc = consent_claims.get_string("document");
    ERROR_IF_NOT(signed_doc != NULL,
                 "consent credential missing document claim");
    
    std::string signed_doc_str(signed_doc);
    
    ERROR_IF_NOT(signed_doc_str == consent_document_str,
                "Didn't consent");
    
    // -----------------------------------------------------------------
    // -----------------------------------------------------------------
    const std::string& membership_vc_sub = membership_vc.credentialSubject_.subject_.id_;
    const std::string& consent_vc_sub = consent_vc.credentialSubject_.subject_.id_;
    const std::string& key_vc_sub = key_vc.credentialSubject_.subject_.id_;
    ERROR_IF_NOT(membership_vc_sub == consent_vc_sub && membership_vc_sub == key_vc_sub,
                "VCs not issued to the same subject");

    // -----------------------------------------------------------------
    // -----------------------------------------------------------------
    const char* channel_key = key_vc.credentialSubject_.claims_.get_string("key");
    ERROR_IF_NOT(channel_key != NULL,
                 "missing key claim");
    
    // -----------------------------------------------------------------
    // Build output credential
    // -----------------------------------------------------------------
    credential_out.credentialSubject_.subject_.id_ = membership_vc_sub;
    
    // Set the claims
    credential_out.credentialSubject_.claims_.set_string("operation", "get");
    credential_out.credentialSubject_.claims_.set_string("channel_key", channel_key);

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
bool initialize_contract(const Environment& env, Response& rsp)
{
    // ---------- initialize the base contract ----------
    ASSERT_SUCCESS(rsp, ww::identity::policy_agent::initialize_contract(env),
                   "unexpected error: failed to initialize the contract");

    return rsp.success(true);
}

// -----------------------------------------------------------------
// -----------------------------------------------------------------
contract_method_reference_t contract_method_dispatch_table[] = {
    CONTRACT_METHOD2(initialize, ww::identity::identity::initialize),

    CONTRACT_METHOD2(get_verifying_key, ww::identity::identity::get_verifying_key),
    CONTRACT_METHOD2(get_extended_verifying_key, ww::identity::identity::get_extended_verifying_key),
    CONTRACT_METHOD2(register_signing_context, ww::identity::identity::register_signing_context),
    CONTRACT_METHOD2(describe_signing_context, ww::identity::identity::describe_signing_context),

    // Not sure if these are appropriate for this contract
    CONTRACT_METHOD2(sign, ww::identity::identity::sign),
    CONTRACT_METHOD2(verify, ww::identity::identity::verify),

    CONTRACT_METHOD2(register_trusted_issuer, ww::identity::policy_agent::register_trusted_issuer),
    CONTRACT_METHOD2(issue_policy_credential, ww::identity::policy_agent::issue_policy_credential),
    CONTRACT_METHOD2(set_policy_data, ww::identity::policy_agent::set_policy_data),

    // This is used to verify credentials that are generated by the policy agent
    CONTRACT_METHOD2(verify_credential, ww::identity::signature_authority::verify_credential),

    { NULL, NULL }
};
