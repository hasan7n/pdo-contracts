package subpolicy

import rego.v1

# -----------------------------------------------------------------
# Sample subpolicy B.
#
# It requires the same role as subpolicy A ("applicant" presenting "dummy"), so
# the requirements combinator merges them to a single role with the union of
# the required credential types. Its decision and operation are merged with the
# other subpolicies (all decisions must be true; operations are unioned).
# -----------------------------------------------------------------

requirements := {"applicant": ["dummy"]}

# allow when the applicant credential carries a "property" claim
default decision := false

decision if {
    some cred in input.presentations.applicant
    cred.claims.property
}

verification_tasks := [{"index": cred.index} |
    some cred in input.presentations.applicant
]

operation := {"name": "do_operation", "parameters": {"checked_by": "subpolicy_b"}}

result := {
    "decision": decision,
    "verification_tasks": verification_tasks,
    "operation": operation,
}
