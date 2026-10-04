"""Password hashing with scrypt (Python standard library, no extra dependency).

scrypt is a memory-hard key-derivation function: each guess costs ~16 MB of memory and
tens of milliseconds, which makes brute-forcing stolen hashes expensive. Every password
gets its own random salt, and the parameters are stored with the hash so they can be
raised later without breaking existing accounts.

Stored format:  scrypt$<n>$<r>$<p>$<salt base64>$<hash base64>
"""

import base64
import hashlib
import hmac
import secrets

N, R, P = 2**14, 8, 1  # ~16 MB, standard interactive-login parameters
SALT_BYTES, KEY_BYTES = 16, 32
MIN_LENGTH, MAX_LENGTH = 8, 128


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    key = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=KEY_BYTES)
    return f"scrypt${N}${R}${P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, key = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(key)
        actual = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)  # constant time: no timing leaks


def password_problem(password: str) -> str | None:
    """A reason the password is not acceptable, or None."""
    if len(password) < MIN_LENGTH:
        return f"Use at least {MIN_LENGTH} characters."
    if len(password) > MAX_LENGTH:
        return f"Use at most {MAX_LENGTH} characters."
    if password.isdigit() or password.isalpha():
        return "Mix letters with numbers or symbols."
    return None


def new_session_token() -> str:
    """256 random bits, URL-safe. Only its SHA-256 is stored in the database."""
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
