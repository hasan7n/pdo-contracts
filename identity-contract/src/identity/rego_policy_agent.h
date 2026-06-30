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
// [ duo_id, source ] pairs. May be called any number of times; each call
// replaces the whole policy. The method derives and stores the per-role
// requirements and the evaluate() input schema from the DUOs themselves.
#define REGO_POLICY_AGENT_SET_POLICY_PARAM_SCHEMA \
    "{" SCHEMA_KW(rego_modules, []) "}"

// evaluate: supply the presentations to judge as an object keyed by role,
// { role: <verifiable presentation>, ... }. The detailed shape (which roles,
// each value a verifiable presentation) is checked against the schema that
// set_rego_policy stored, so this top-level schema only requires an object.
#define REGO_POLICY_AGENT_EVALUATE_PARAM_SCHEMA \
    "{" SCHEMA_KW(presentations, {}) "}"

namespace ww
{
namespace identity
{
namespace rego_policy_agent
{
    // set (or replace) the Rego modules and the per-role credential requirements
    bool set_rego_policy(const Message& msg, const Environment& env, Response& rsp);

    // read a module's source (optional "duo_id"; otherwise the whole map)
    bool get_rego_policy(const Message& msg, const Environment& env, Response& rsp);

    // return the per-role credential requirements set by set_rego_policy
    bool get_requirements(const Message& msg, const Environment& env, Response& rsp);

    // evaluate every provisioned module, then perform the verification tasks the
    // Rego returns and issue a signed decision credential
    bool evaluate(const Message& msg, const Environment& env, Response& rsp);

}; // rego_policy_agent
}; // identity
}; // ww
