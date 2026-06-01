# Sample policy for the rego_policy_agent smoke test.
#
# Input shape: a list of lists of (already signature-verified) verifiable
# credentials. Each VC is an object with at least `issuer` and
# `credentialSubject.id` fields.
#
# `crosslinked` is true if there exist two distinct VCs (in any sublist)
# where the issuer of one is the subject of the other. This is the
# canonical "issuer of VC1 == subject of VC2" relationship.

package policy

default crosslinked := false

crosslinked if {
    some i, j, k, l
    [i, k] != [j, l]
    input[i][k].issuer == input[j][l].credentialSubject.id
}

# Convenience rule that returns every cross-link found, as pairs of
# (issuer_vc_path, subject_vc_path).
links contains {"issuer_path": [i, k], "subject_path": [j, l]} if {
    some i, j, k, l
    [i, k] != [j, l]
    input[i][k].issuer == input[j][l].credentialSubject.id
}
