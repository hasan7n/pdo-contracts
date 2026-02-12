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
#include "exchange/token_object.h"
#include "identity/policy_agent.h"
#include "download/download_token.h"

bool ww::download::download_token::do_download(
    const Message &msg,
    const Environment &env,
    Response &rsp)
{
    ASSERT_INITIALIZED(rsp);

    ASSERT_SUCCESS(rsp, msg.validate_schema(DOWNLOAD_PARAM_SCHEMA),
                   "invalid request, missing required parameters");

    ww::value::Object vc_object_in;
    ASSERT_SUCCESS(rsp, msg.get_value("download_vc", vc_object_in), "missing required parameter; download_vc");

    ww::identity::VerifiableCredential vc_in;
    ASSERT_SUCCESS(rsp, ww::identity::policy_agent::verify_credential(vc_object_in, vc_in, "download"), "invalid request, ill-formed credential");

    // extract claims
    const char *op = vc_in.credential_.credentialSubject_.claims_.get_string("operation");
    const char *channel_key = vc_in.credential_.credentialSubject_.claims_.get_string("channel_key");

    ASSERT_SUCCESS(rsp, op != NULL, "no operation claim");
    ASSERT_SUCCESS(rsp, channel_key != NULL, "no channel_key claim");

    ww::value::Structure params(DOWNLOAD_CAPABILITY_SCHEMA);
    ASSERT_SUCCESS(rsp, params.set_string("op", op),
                   "unexpected error: failed to store operation parameter");

    ASSERT_SUCCESS(rsp, params.set_string("channel_key", channel_key),
                   "unexpected error: failed to store channel_key parameter");

    ww::value::Object result;
    ASSERT_SUCCESS(rsp, ww::exchange::token_object::create_operation_package("do_download", params, result),
                   "unexpected error: failed to generate capability");

    // this assumes that generating the capability does not change state, depending on
    //                                                                        how the nonce is created this may need to change.
    return rsp.value(result, false);
    // ww::identity::VerifyingContext verifier;
    // std::vector<std::string> prefix_path;
    // prefix_path.push_back("gg");

    // std::string valid_pem_key = "-----BEGIN PUBLIC KEY-----\nMHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEiEnWZtKnzHZutccKe15hpBKelgqHQC2J\n5Wqae1bfbLZgsVNBzaU7OjFRgUjkOoJAKcPmPIC+NGMAA6DIe/YDOkMjm1yCGWgJ\ndyYf0W2V3UfvCd/auxn+D5D1wWFw4gEB\n-----END PUBLIC KEY-----";
    // std::string valid_chain_code = "MTIzNDU2Nzg5MGFiY2RlZjEyMzQ1Njc4OTBhYmNkZWY="; // base64 32 bytes
    // // ASSERT_SUCCESS(rsp, verifier.initialize(prefix_path, valid_pem_key, valid_chain_code),
    // //                "invalid request, invalid issuer public key/chain code");
    // pdo_contracts::crypto::signing::PublicKey public_key;
    // ww::types::ByteArray ss(valid_pem_key.begin(), valid_pem_key.end());
    // ww::types::ByteArray vv;
    // pdo_contracts::crypto::SHA256Hash(ss, vv);
    // std::string gg(vv.begin(), vv.end());
    // ww::value::String s(gg.c_str());
    // // ERROR_IF_NOT(public_key.Deserialize(valid_pem_key), "Invalid public key");
    // // return rsp.success(false);
    // return rsp.value(s, false);
}
