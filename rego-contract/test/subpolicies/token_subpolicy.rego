package subpolicy

import rego.v1

# -----------------------------------------------------------------
# Token subpolicy.
#
# This is the rego analog of the download policy_agent: it gates a token
# capability on a presented credential. It requires the "applicant" role to
# present a "public_key" credential whose claims carry the channel key, then
# emits a "do_download" operation carrying that key as its parameters. The
# rego_policy_agent carries that merged operation as the claims of the
# "policy_decision" credential it issues; the rego_token parses it to build the
# guardian capability.
# -----------------------------------------------------------------

# data.subpolicy.requirements -- one "public_key" credential under role "applicant".
# Evaluated by set_rego_policy with NO input, so it must be static.
requirements := {"applicant": ["public_key"]}

# data.subpolicy.result -- evaluated by issue_policy_credential with input =
# { presentations, trusted_issuers, policy_data }. The standardized credential
# view is { type, issuer, subject, claims, index }.

# allow when the applicant presents a public_key credential carrying a key claim
default decision := false

decision if {
    some cred in input.presentations.applicant
    cred.claims.key
}

# flag every applicant credential for signature verification (by global index);
# the rego_policy_agent verifies these in C++ against the trusted issuers
verification_tasks := [{"index": cred.index} |
    some cred in input.presentations.applicant
]

# name the "do_download" guardian operation and carry the channel key as its
# parameters so the rego_token can build the capability from the issued
# policy_decision credential
operation := {"name": "do_download", "parameters": {"channel_key": key}} if {
    some cred in input.presentations.applicant
    key := cred.claims.key
}

result := {
    "decision": decision,
    "verification_tasks": verification_tasks,
    "operation": operation,
}
