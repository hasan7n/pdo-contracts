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

#define REGO_POLICY_AGENT_SET_POLICY_PARAM_SCHEMA \
    "{" SCHEMA_KW(policy, "") "}"

// Only `rule` has a fixed shape (string). `input` may be any JSON value
// (object, array, scalar) so it is checked for presence separately rather
// than via schema validation.
#define REGO_POLICY_AGENT_EVALUATE_PARAM_SCHEMA \
    "{" SCHEMA_KW(rule, "") "}"

namespace ww
{
namespace identity
{
namespace rego_policy_agent
{
    bool initialize_contract(const Environment& env);

    bool set_rego_policy(const Message& msg, const Environment& env, Response& rsp);
    bool get_rego_policy(const Message& msg, const Environment& env, Response& rsp);
    bool evaluate(const Message& msg, const Environment& env, Response& rsp);

}; // rego_policy_agent
}; // identity
}; // ww
