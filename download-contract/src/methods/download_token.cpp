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
#include "download/download_token.h"
// #include "identity/identity.h"
#include "identity/common/Context.h"
#include "identity/common/VerifyingContext.h"
#include "exchange/token_object.h"
#include "download/download_token.h"

// TODO: change includes and comment/uncomment verifying context below to see behaviour

// -----------------------------------------------------------------
// do_download
//
// This generates a capability that can be fed to the sample guardian
// contract to do download with an openvino model
// -----------------------------------------------------------------

bool ww::download::download_token::my_method(
    const Message &msg,
    const Environment &env,
    Response &rsp)
{
    ASSERT_INITIALIZED(rsp);
    ASSERT_SENDER_IS_OWNER(env, rsp);
    std::vector<std::string> prefix_path;
    std::string pem_key = "-----BEGIN PUBLIC KEY-----\nMHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEiEnWZtKnzHZutccKe15hpBKelgqHQC2J\n5Wqae1bfbLZgsVNBzaU7OjFRgUjkOoJAKcPmPIC+NGMAA6DIe/YDOkMjm1yCGWgJ\ndyYf0W2V3UfvCd/auxn+D5D1wWFw4gEB\n-----END PUBLIC KEY-----";
    std::string chain_code = "MTIzNDU2Nzg5MGFiY2RlZjEyMzQ1Njc4OTBhYmNkZWY=";

    prefix_path.push_back("path");
    ww::identity::VerifyingContext verifier;
    ASSERT_SUCCESS(rsp, verifier.initialize(prefix_path, pem_key, chain_code),
                   "invalid request, invalid issuer public key/chain code");

    return rsp.success(true);
}
