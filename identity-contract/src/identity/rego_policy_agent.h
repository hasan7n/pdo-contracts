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

#pragma once

#include <string>

#include "Environment.h"
#include "Message.h"
#include "Response.h"
#include "Util.h"

// The contract initialization hook, the trusted-issuer methods, and the
// policy-data methods are all inherited from ww::identity::policy_agent
// (registered directly in the dispatch table); only the Rego-specific methods
// are declared here.

// set_rego_policy: set (or replace) the Rego policy -- a list of
// [ subpolicy_id, source ] pairs. May be called any number of times; each call
// replaces the whole policy. The method derives and stores the per-role
// requirements and the issue_policy_credential() input schema from the subpolicies.
#define REGO_POLICY_AGENT_SET_POLICY_PARAM_SCHEMA \
    "{" SCHEMA_KW(rego_modules, []) "}"

// issue_policy_credential: supply the presentations to judge under the
// "presentation" keyword (singular, so this can share the inherited policy_agent
// issue op) as an object keyed by role, { role: <verifiable presentation>, ... }.
// The detailed shape (which roles, each value a verifiable presentation) is
// checked against the schema that set_rego_policy stored, so this top-level
// schema only requires an object.
#define REGO_POLICY_AGENT_ISSUE_PARAM_SCHEMA \
    "{" SCHEMA_KW(presentation, {}) "}"

// Schemas for the two rules every subpolicy must expose. The contract validates a
// subpolicy's output against the matching schema before using it.
//   data.subpolicy.requirements -> { role: [credential_type, ...], ... }
// (roles are arbitrary keys, so the schema can only require an object)
#define REGO_SUBPOLICY_REQUIREMENTS_SCHEMA "{}"

//   data.subpolicy.result -> { decision, verification_tasks, context }
#define REGO_SUBPOLICY_RESULT_SCHEMA                                          \
    "{"                                                                 \
        SCHEMA_KW(decision, true) ","                                   \
        SCHEMA_KWS(verification_tasks, "[{" SCHEMA_KW(index, 0) "}]") ","\
        SCHEMA_KW(context, {})                                         \
    "}"

namespace ww
{
namespace identity
{
namespace rego_policy_agent
{
    // set (or replace) the Rego policy (a list of [ subpolicy_id, source ] pairs)
    bool set_rego_policy(const Message& msg, const Environment& env, Response& rsp);

    // return the whole list of [ subpolicy_id, source ] pairs
    bool get_rego_policy(const Message& msg, const Environment& env, Response& rsp);

    // return the merged per-role credential requirements set by set_rego_policy
    bool get_requirements(const Message& msg, const Environment& env, Response& rsp);

    // run every subpolicy, merge the results, verify the flagged credentials, and --
    // if the policy allows -- issue a signed credential whose claims are the
    // merged context
    bool issue_policy_credential(const Message& msg, const Environment& env, Response& rsp);

}; // rego_policy_agent
}; // identity
}; // ww
