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

#include <stdlib.h>
#include <stdint.h>
#include <string>

#include "Dispatch.h"
#include "KeyValue.h"
#include "Environment.h"
#include "Message.h"
#include "Response.h"
#include "Util.h"
#include "Value.h"
#include "WasmExtensions.h"

#include "contract/base.h"
#include "exchange/common/Common.h"
#include "identity/rego_policy_agent.h"

extern "C" {
#include "regorus/regorus.h"
}

// Custom allocator hooks called by regorus (custom_allocator feature). The
// wawaka runtime's malloc returns wasm-default-aligned pointers and aligned
// new is explicitly unsupported (see common/Util.cpp). Over-allocate and
// stash the raw base pointer in the slot preceding the aligned address so
// regorus_free can recover it.
extern "C" uint8_t* regorus_aligned_alloc(size_t alignment, size_t size)
{
    if (alignment < sizeof(void*))
        alignment = sizeof(void*);
    const size_t total = size + alignment + sizeof(void*);
    void* raw = malloc(total);
    if (raw == nullptr)
        return nullptr;
    uintptr_t aligned = ((uintptr_t)raw + sizeof(void*) + alignment - 1)
                        & ~(uintptr_t)(alignment - 1);
    ((void**)aligned)[-1] = raw;
    return (uint8_t*)aligned;
}

extern "C" void regorus_free(uint8_t* ptr)
{
    if (ptr == nullptr)
        return;
    free(((void**)ptr)[-1]);
}

static KeyValueStore rego_policy_store("rego_policy_store");
static const std::string md_policy("policy");
static const std::string policy_module_name("policy.rego");

// -----------------------------------------------------------------
bool ww::identity::rego_policy_agent::initialize_contract(const Environment& env)
{
    if (! ww::contract::base::initialize_contract(env))
        return false;
    if (! rego_policy_store.set(md_policy, std::string("")))
        return false;
    if (! ww::contract::base::mark_initialized())
        return false;
    return true;
}

// -----------------------------------------------------------------
// METHOD: set_rego_policy
//   Persist a Rego policy in the contract's KV store. Only the owner
//   may invoke this.
//
// JSON PARAMETERS:
//   REGO_POLICY_AGENT_SET_POLICY_PARAM_SCHEMA
// -----------------------------------------------------------------
bool ww::identity::rego_policy_agent::set_rego_policy(
    const Message& msg, const Environment& env, Response& rsp)
{
    ASSERT_SENDER_IS_OWNER(env, rsp);
    ASSERT_INITIALIZED(rsp);
    ASSERT_SUCCESS(rsp, msg.validate_schema(REGO_POLICY_AGENT_SET_POLICY_PARAM_SCHEMA),
                   "invalid request, missing required parameter 'policy'");

    const char* policy_text = msg.get_string("policy");
    ASSERT_SUCCESS(rsp, policy_text != nullptr, "policy text is null");

    ASSERT_SUCCESS(rsp, rego_policy_store.set(md_policy, std::string(policy_text)),
                   "failed to persist Rego policy");
    return rsp.success(true);
}

// -----------------------------------------------------------------
// METHOD: get_rego_policy
//   Return the currently stored Rego policy as a string.
// -----------------------------------------------------------------
bool ww::identity::rego_policy_agent::get_rego_policy(
    const Message& msg, const Environment& env, Response& rsp)
{
    ASSERT_INITIALIZED(rsp);
    std::string policy_text;
    ASSERT_SUCCESS(rsp, rego_policy_store.get(md_policy, policy_text),
                   "failed to fetch Rego policy");
    ww::value::String out(policy_text.c_str());
    return rsp.value(out, false);
}

// -----------------------------------------------------------------
// METHOD: evaluate
//   Evaluate the stored Rego policy against caller-supplied input.
//
// JSON PARAMETERS:
//   { "input": <any JSON value>, "rule": "<rego rule path>" }
//
// RETURNS:
//   The value produced by the rule, as a JSON value.
// -----------------------------------------------------------------
bool ww::identity::rego_policy_agent::evaluate(
    const Message& msg, const Environment& env, Response& rsp)
{
    ASSERT_INITIALIZED(rsp);
    ASSERT_SUCCESS(rsp, msg.validate_schema(REGO_POLICY_AGENT_EVALUATE_PARAM_SCHEMA),
                   "invalid request, missing 'input' or 'rule'");

    const char* rule = msg.get_string("rule");
    ASSERT_SUCCESS(rsp, rule != nullptr, "'rule' is null");

    // `input` is a JSON document encoded as a string; passed straight to
    // regorus_engine_set_input_json below.
    const char* input_json = msg.get_string("input");
    ASSERT_SUCCESS(rsp, input_json != nullptr, "'input' missing");

    std::string policy_text;
    ASSERT_SUCCESS(rsp, rego_policy_store.get(md_policy, policy_text),
                   "failed to load Rego policy");
    ASSERT_SUCCESS(rsp, ! policy_text.empty(), "no Rego policy has been set");

    RegorusEngine* engine = regorus_engine_new();
    ASSERT_SUCCESS(rsp, engine != nullptr, "failed to create regorus engine");

    std::string error_msg;
    std::string output_json;
    bool ok = true;

    RegorusResult r = regorus_engine_add_policy(engine, policy_module_name.c_str(), policy_text.c_str());
    if (r.status != Ok) {
        error_msg.assign(r.error_message ? r.error_message : "add_policy failed");
        ok = false;
    }
    regorus_result_drop(r);

    if (ok) {
        r = regorus_engine_set_input_json(engine, input_json);
        if (r.status != Ok) {
            error_msg.assign(r.error_message ? r.error_message : "set_input_json failed");
            ok = false;
        }
        regorus_result_drop(r);
    }

    if (ok) {
        r = regorus_engine_eval_rule(engine, rule);
        if (r.status != Ok) {
            error_msg.assign(r.error_message ? r.error_message : "eval_rule failed");
            ok = false;
        } else if (r.output != nullptr) {
            output_json.assign(r.output);
        }
        regorus_result_drop(r);
    }

    regorus_engine_drop(engine);

    ASSERT_SUCCESS(rsp, ok, error_msg.c_str());

    // regorus output may be any JSON type (bool, array, object, ...). Parse it
    // with parson directly and adopt it via set(), which (unlike deserialize)
    // does not type-check against a fixed expected type.
    JSON_Value* parsed = json_parse_string(output_json.c_str());
    ASSERT_SUCCESS(rsp, parsed != nullptr, "failed to parse regorus output");

    ww::value::Value result;
    result.set(parsed);
    json_value_free(parsed);

    return rsp.value(result, false);
}
