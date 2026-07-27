import secrets
import os

os.system('cls')  # Clears the screen so it's clean

print("ANOMALY KEYGEN v1.0")
print("=" * 30)

name = input("Enter client name: ").strip()

if not name:
    print("\nERROR: Name can't be blank.")
    input("\nPress Enter to exit...")
    exit()

# Generate 16-character random hex
random_part = secrets.token_hex(8).upper()
key = f"{name.upper()}-{random_part}"

# Save it
with open("valid_keys.txt", "a") as f:
    f.write(key + "\n")

print("\n" + "=" * 30)
print("LICENSE GENERATED:")
print(key)
print("=" * 30)
print("\nSaved to valid_keys.txt")
print("Warden will accept this key.\n")

input("Press Enter to close...")