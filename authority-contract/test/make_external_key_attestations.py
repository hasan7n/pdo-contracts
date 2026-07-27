# Copyright 2026 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Helper for the external_key_authority end-to-end test. It plays the part of the
# person who owns a wallet and wants to bind an external RSA key pair to it:
#
#   1. generate the external rsa key pair locally                       (keys)
#   2. build the payload { "identity": "<wallet did>", "session_key": "<rsa pub>" }
#      and sign it with the rsa PRIVATE key -> session_key_attestation   (build)
#   3. the wallet signs the SAME payload with its own contract key (done
#      on-chain by the wallet contract's sign_with_contract_key method);
#      this helper just assembles that signature into the wallet_attestation
#                                                                        (wallet_attestation)
#
# The external_key_authority then verifies the wallet's signature against the
# wallet's ledger-attested verifying key (SHA-256 ECDSA, ww::crypto::ecdsa) and
# the rsa signature against the public key in the payload (RSASSA-PKCS1-v1_5 /
# SHA-256), confirms the two payloads match, and issues a publicKeyCredential for the session key.
#
# There is NO ec key here: the wallet's signature is produced by the wallet
# contract, not modeled locally.

import argparse
import base64
import json
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

RSA_PRIVATE = "session_rsa_private.pem"
RSA_PUBLIC = "session_rsa_public.pem"


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _read_text(path):
    with open(path, "r") as f:
        return f.read()


def _b64(data):
    return base64.b64encode(data).decode()


def _rsa_sign(rsa_key, message):
    # RSASSA-PKCS1-v1_5 over SHA-256 -- matches RSAPublicKey::VerifySignature
    return rsa_key.sign(message, padding.PKCS1v15(), hashes.SHA256())


def generate_keys(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _write(os.path.join(out_dir, RSA_PRIVATE), rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    _write(os.path.join(out_dir, RSA_PUBLIC), rsa_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo))


def _build_payload(out_dir, wallet_did):
    # the payload string is exactly what both parties sign and what the contract
    # verifies over
    session_public_pem = _read_text(os.path.join(out_dir, RSA_PUBLIC))
    return json.dumps({"identity": wallet_did, "session_key": session_public_pem})


# -----------------------------------------------------------------
# subcommands
# -----------------------------------------------------------------
def cmd_keys(args):
    generate_keys(args.dir)


def cmd_build(args):
    payload = _build_payload(args.dir, args.wallet_did)

    # the wallet signs this exact payload file with its contract key on-chain
    with open(args.payload_out, "w") as f:
        f.write(payload)

    # the session (rsa) attestation
    with open(os.path.join(args.dir, RSA_PRIVATE), "rb") as f:
        rsa_key = serialization.load_pem_private_key(f.read(), password=None)
    session_key_attestation = {"payload": payload, "signature": _b64(_rsa_sign(rsa_key, payload.encode()))}
    with open(args.session_out, "w") as f:
        json.dump(session_key_attestation, f, indent=4)


def cmd_wallet_attestation(args):
    # assemble the wallet attestation from the payload and the wallet's contract-key
    # signature (produced on-chain by the wallet contract)
    payload = _read_text(args.payload_file)
    signature = _read_text(args.signature_file).strip()
    with open(args.out, "w") as f:
        json.dump({"payload": payload, "signature": signature}, f, indent=4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("keys", help="generate the external rsa key pair")
    p.add_argument("dir")
    p.set_defaults(func=cmd_keys)

    p = sub.add_parser("build", help="build the payload file and the session-key attestation")
    p.add_argument("dir")
    p.add_argument("wallet_did")
    p.add_argument("payload_out")
    p.add_argument("session_out")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("wallet_attestation", help="assemble the wallet attestation from its contract-key signature")
    p.add_argument("payload_file")
    p.add_argument("signature_file")
    p.add_argument("out")
    p.set_defaults(func=cmd_wallet_attestation)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
