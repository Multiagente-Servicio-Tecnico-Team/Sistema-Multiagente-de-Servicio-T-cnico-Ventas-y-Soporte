"""Password hashing (bcrypt), signed session cookie and sign-in attempt limiting."""
import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

import bcrypt


def hash_password(password: str, rounds: int = 12) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        # Password longer than 72 bytes or a malformed hash.
        return False


def dummy_hash(rounds: int = 12) -> str:
    """Hash of a random password, compared in constant time when the email does not exist."""
    return hash_password(secrets.token_urlsafe(32), rounds)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def password_fingerprint(password_hash: str, secret: str) -> str:
    """Fingerprint of the current hash: when the password changes, earlier cookies stop being valid."""
    return hmac.new(secret.encode("utf-8"), password_hash.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def sign_session(user_id: int, secret: str, max_age_seconds: int, fingerprint: str = "", now: float | None = None) -> str:
    expires = int((now or time.time()) + max_age_seconds)
    payload = _b64(f"{user_id}.{expires}.{fingerprint}".encode("ascii"))
    signature = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session(token: str | None, secret: str, now: float | None = None) -> tuple[int, str] | None:
    """Returns (user id, fingerprint) if the cookie is authentic and unexpired; otherwise None."""
    if not token or token.count(".") != 1:
        return None
    payload, signature = token.split(".")
    expected = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        user_id, expires, fingerprint = _unb64(payload).decode("ascii").split(".")
        if int(expires) < (now or time.time()):
            return None
        return int(user_id), fingerprint
    except (ValueError, UnicodeDecodeError):
        return None


def new_reset_token() -> tuple[str, str]:
    """256-bit token for the link and its SHA-256 hash to store in recovery_tokens."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_reset_token(raw)


def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class LoginLimiter:
    """Counts failed attempts per email within a time window (process memory)."""

    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque:
        attempts = self._failures[key]
        while attempts and attempts[0] <= now - self.window:
            attempts.popleft()
        return attempts

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) >= self.max_failures

    def fail(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
