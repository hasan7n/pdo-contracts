from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import json
import sys
import os

out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)

# Generate private key
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Get public key
public_key = private_key.public_key()

# Serialize private key to PEM format
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

# Serialize public key to PEM format
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

# Or save to files
with open(os.path.join(out_dir, "private_key.pem"), "wb") as f:
    f.write(private_pem)

with open(os.path.join(out_dir, "public_key.pem"), "wb") as f:
    f.write(public_pem)

cred = {
    "type": ["public_key"],
    "issuer": {"id": "A6QBclbcAayAvw7BggM7iMz_Xa6NEn_YGT94mpkQmEk="},
    "credentialSubject": {
        "subject": {"id": "SMeYjWc5IOdvI3KJtPbx4WHlRvkdL5A__xcHayDj9+0="},
        "claims": {"key": public_pem.decode()},
    },
    "name": "credential3",
    "description": "test credential",
}
with open(os.path.join(out_dir, "credential_key.json"), "w") as f:
    json.dump(cred, f, indent=4)
