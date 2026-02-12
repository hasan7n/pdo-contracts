import json
import sys


def main():
    membership = sys.argv[1]
    consent = sys.argv[2]
    public_key = sys.argv[3]
    output_file = sys.argv[-1]

    combined = {}

    with open(membership, "r") as f:
        cred = json.load(f)
        combined["membership"] = cred

    with open(consent, "r") as f:
        cred = json.load(f)
        combined["consent"] = cred

    with open(public_key, "r") as f:
        cred = json.load(f)
        combined["public_key"] = cred

    with open(output_file, "w") as f:
        json.dump(combined, f, indent=4)


if __name__ == "__main__":
    main()
