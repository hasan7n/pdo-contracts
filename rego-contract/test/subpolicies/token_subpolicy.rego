package subpolicy

import rego.v1

# -----------------------------------------------------------------
# Token subpolicy.
#
# This is the rego analog of the download policy_agent: it gates a token
# capability on a presented credential. It requires the "applicant" role to
# present a "public_key" credential whose claims carry the channel key, then
# emits that key (and the operation) as the merged context. The rego_policy_agent
# carries that merged context as the claims of the "policy_decision" credential it
# issues; the rego_token reads operation + channel_key from those claims to build
# the guardian capability, exactly as download_token does.
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

# carry the channel key + operation as the merged context so the rego_token can
# turn the issued policy_decision credential into a guardian capability
context := {"operation": "get", "channel_key": key} if {
    some cred in input.presentations.applicant
    key := cred.claims.key
}

result := {
    "decision": decision,
    "verification_tasks": verification_tasks,
    "context": context,
}
