package subpolicy

import rego.v1

# -----------------------------------------------------------------
# Sample subpolicy A.
#
# A subpolicy is one composable unit of the overall policy. It MUST declare
# both rules below in `package subpolicy`; the rego_policy_agent evaluates them
# in their own engine and merges the results with the other subpolicies.
# -----------------------------------------------------------------

# data.subpolicy.requirements -- the roles/credential-types this subpolicy needs.
# Evaluated by set_rego_policy with NO input, so it must be static.
requirements := {"applicant": ["dummy"]}

# data.subpolicy.result -- evaluated by issue_policy_credential with input =
# { presentations, trusted_issuers, policy_data }. The standardized credential
# view is { type, issuer, subject, claims, index }.

# allow when the applicant presents a "dummy" credential
default decision := false

decision if {
    some cred in input.presentations.applicant
    cred.type == "dummy"
}

# flag every applicant credential for signature verification (by global index);
# the rego_policy_agent verifies these in C++ against the trusted issuers
verification_tasks := [{"index": cred.index} |
    some cred in input.presentations.applicant
]

# contribute the applicant's "property" claim to the merged operation parameters
operation := {"name": "do_operation", "parameters": {"applicant_property": prop}} if {
    some cred in input.presentations.applicant
    prop := cred.claims.property
}

result := {
    "decision": decision,
    "verification_tasks": verification_tasks,
    "operation": operation,
}
