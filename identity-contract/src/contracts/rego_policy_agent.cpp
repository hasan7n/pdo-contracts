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
#include "identity/rego_policy_agent.h"

// -----------------------------------------------------------------
// METHOD: initialize_contract
// -----------------------------------------------------------------
bool initialize_contract(const Environment& env, Response& rsp)
{
    ASSERT_SUCCESS(rsp, ww::identity::rego_policy_agent::initialize_contract(env),
                   "unexpected error: failed to initialize the contract");
    return rsp.success(true);
}

// -----------------------------------------------------------------
contract_method_reference_t contract_method_dispatch_table[] = {
    CONTRACT_METHOD2(set_rego_policy, ww::identity::rego_policy_agent::set_rego_policy),
    CONTRACT_METHOD2(get_rego_policy, ww::identity::rego_policy_agent::get_rego_policy),
    CONTRACT_METHOD2(evaluate, ww::identity::rego_policy_agent::evaluate),
    {NULL, NULL}};
