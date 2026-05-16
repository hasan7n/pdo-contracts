"""
DID parsing and construction utilities.

DID format: did:pdo:<contract_id>  or  did:pdo:<contract_id>/<signing_context_path>
"""


def parse_did(did):
    """
    Parse a PDO DID string.

    Returns (contract_id, context_path) where context_path may be None.

    Examples:
        parse_did("did:pdo:abc123")        -> ("abc123", None)
        parse_did("did:pdo:abc123/mypath") -> ("abc123", "mypath")
    """
    if not did.startswith('did:pdo:'):
        raise ValueError(f"Invalid PDO DID: {did!r}")

    rest = did[len('did:pdo:'):]
    if '/' in rest:
        contract_id, context_path = rest.split('/', 1)
        return contract_id, context_path
    return rest, None


def make_did(contract_id, path=None):
    """
    Construct a PDO DID string.

    Examples:
        make_did("abc123")          -> "did:pdo:abc123"
        make_did("abc123", "mypath") -> "did:pdo:abc123/mypath"
    """
    if path:
        return f"did:pdo:{contract_id}/{path}"
    return f"did:pdo:{contract_id}"
