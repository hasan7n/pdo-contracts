/* Copyright 2026 Intel Corporation
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

#include <stddef.h>
#include <stdint.h>

#include "Dispatch.h"

#include "Environment.h"
#include "Message.h"
#include "Response.h"
#include "Util.h"

#include "contract/base.h"
#include "identity/identity.h"
#include "identity/policy_agent.h"
#include "identity/rego_policy_agent.h"

// -----------------------------------------------------------------
// policy_agent specialization hook.
//   The inherited ww::identity::policy_agent::set_policy_data validates the
//   incoming policy data against this schema. Policy data is opaque to this
//   contract (it is handed straight to the Rego as input.policy_data), so the
//   schema is permissive. The get_claims_schemas / policy_agent_function hooks
//   are only referenced by policy_agent methods this contract does NOT register
//   (issue_policy_credential / get_requirements) and are dropped by the linker.
// -----------------------------------------------------------------
#define REGO_POLICY_AGENT_POLICY_DATA_SCHEMA "{}"

const char* ww::identity::policy_agent::get_policy_data_schema()
{
    return REGO_POLICY_AGENT_POLICY_DATA_SCHEMA;
}

// -----------------------------------------------------------------
// METHOD: initialize_contract
//   Creation hook. The whole setup -- identity signing contexts, the issuer
//   path used to sign issued credentials, the policy-data store, and the
//   trusted-issuers map -- is inherited from policy_agent. It does NOT mark the
//   contract initialized; the inherited identity::initialize method does that.
// -----------------------------------------------------------------
bool initialize_contract(const Environment& env, Response& rsp)
{
    ASSERT_SUCCESS(rsp, ww::identity::policy_agent::initialize_contract(env),
                   "unexpected error: failed to initialize the contract");
    return rsp.success(true);
}

// -----------------------------------------------------------------
contract_method_reference_t contract_method_dispatch_table[] = {
    // mark the contract initialized: inherited from identity (takes a description)
    CONTRACT_METHOD2(initialize, ww::identity::identity::initialize),

    // set/replace the Rego modules + requirements (owner-only, repeatable), and read them back
    CONTRACT_METHOD2(set_rego_policy, ww::identity::rego_policy_agent::set_rego_policy),
    CONTRACT_METHOD2(get_rego_policy, ww::identity::rego_policy_agent::get_rego_policy),
    CONTRACT_METHOD2(get_requirements, ww::identity::rego_policy_agent::get_requirements),

    // trusted issuers + policy data: inherited from policy_agent, still editable
    CONTRACT_METHOD2(register_trusted_issuer, ww::identity::policy_agent::register_trusted_issuer),
    CONTRACT_METHOD2(list_trusted_issuers, ww::identity::policy_agent::list_trusted_issuers),
    CONTRACT_METHOD2(set_policy_data, ww::identity::policy_agent::set_policy_data),
    CONTRACT_METHOD2(get_policy_data, ww::identity::policy_agent::get_policy_data),

    // evaluate every provisioned module, verify the returned tasks, issue a decision credential
    CONTRACT_METHOD2(evaluate, ww::identity::rego_policy_agent::evaluate),

    {NULL, NULL}};
