import hashlib
import hmac
import secrets

ITERATIONS = 120000
SESSION_DAYS = 30
MAX_FAILS = 5
LOCK_MINUTES = 10


def hash_password(password: str, salt: str | None = None, iterations: int = ITERATIONS):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return digest.hex(), salt, iterations


def verify_password(password: str, salt: str, expected: str, iterations: int) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(digest.hex(), expected)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
