from pdo.download.utils import AsymmetricEncryption
import sys

input_data_file = sys.argv[1]
private_key_file = sys.argv[2]
out_data = sys.argv[3]

with open(input_data_file, "rb") as f:
    encrypted_data = f.read()

with open(private_key_file, "rb") as f:
    private_key = f.read()


data = AsymmetricEncryption().decrypt(private_key, encrypted_data)

with open(out_data, "wb") as f:
    f.write(data)
