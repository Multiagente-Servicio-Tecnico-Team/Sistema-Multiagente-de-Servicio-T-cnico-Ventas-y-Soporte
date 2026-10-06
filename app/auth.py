"""Generación de hashes para usuarios del portal; nunca guardar claves en claro."""
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
    return salt + ":" + digest.hex()


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt, expected = encoded.split(":")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    import getpass
    import json
    username = input("Usuario: ").strip()
    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    if not username or len(password) < 12:
        raise SystemExit("Usuario o contraseña inválidos")
    print(json.dumps({username: hash_password(password)}))
