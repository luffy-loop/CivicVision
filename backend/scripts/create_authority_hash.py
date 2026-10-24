"""Generate a PBKDF2 password hash suitable for AUTHORITY_USERS configuration."""
from getpass import getpass
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.auth import hash_password

if __name__ == "__main__":
    password = getpass("New authority password: ")
    confirmation = getpass("Confirm password: ")
    if not password or password != confirmation:
        raise SystemExit("Passwords were empty or did not match.")
    print(hash_password(password))
