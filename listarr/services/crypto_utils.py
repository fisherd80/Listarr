import os

from cryptography.fernet import Fernet, InvalidToken

# Default key filename (path will be constructed from Flask's instance folder)
KEY_FILENAME = ".fernet_key"

def _get_key_path(instance_path=None):
    """
    Get the full path to the encryption key file.
    If instance_path is not provided, attempts to get it from Flask current_app.
    """
    if instance_path:
        # Try to get from Flask's current app context
        return os.path.join(instance_path, KEY_FILENAME)

    try:
        from flask import current_app
        instance_path = current_app.instance_path
    except (ImportError, RuntimeError):
        # Fallback to relative path from project root (2 levels up from this file)
        instance_path = os.path.join(os.path.dirname(__file__), "../../instance")

    return os.path.join(instance_path, KEY_FILENAME)


def generate_key(instance_path=None) -> bytes:
    """
    Generate a new Fernet key and return it.
    Saves it to the instance folder for persistence.
    """
    path = _get_key_path(instance_path)
    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(key)
    return key


def load_encryption_key(*, instance_path=None, allow_generate=False) -> bytes:
    """
    Load and validate the encryption key.
    - Checks FERNET_KEY environment variable first.
    - Checks .fernet_key file in instance folder.
    - Optionally generates a key if not found and allow_generate=True.
    Raises RuntimeError if no valid key is found.
    """
    path = _get_key_path(instance_path)
    key_bytes = None

    # 1️⃣ Check environment variable
    env_key = os.environ.get("FERNET_KEY")
    if env_key:
        key_bytes = env_key.encode()

    # 2️⃣ Check file
    elif os.path.exists(path):
        with open(path, "rb") as f:
            key_bytes = f.read()

    # 3️⃣ Optionally generate
    elif allow_generate:
        key_bytes = generate_key(instance_path=instance_path)
        print(f"[INFO] Generated new Fernet key and saved to {path}")

    else:
        raise RuntimeError(
            "Encryption key not found! Set FERNET_KEY environment variable "
            "or place .fernet_key in the instance folder."
        )

    # 4️⃣ Validate key format
    try:
        Fernet(key_bytes)
    except (ValueError, TypeError):
        raise RuntimeError(
            "Invalid encryption key format! Must be a 32-byte base64-encoded string."
        )

    return key_bytes


def get_fernet(instance_path=None) -> Fernet:
    """
    Return a Fernet object for encryption/decryption.
    """
    key = load_encryption_key(instance_path=instance_path)
    return Fernet(key)


# -----------------------------
# Utility functions
# -----------------------------

def encrypt_data(data: str, instance_path=None) -> str:
    f = get_fernet(instance_path=instance_path)
    token = f.encrypt(data.encode())
    return token.decode()


def decrypt_data(token: str, instance_path=None) -> str:
    f = get_fernet(instance_path=instance_path)
    try:
        data = f.decrypt(token.encode())
        return data.decode()
    except InvalidToken:
        raise ValueError("Invalid token: cannot decrypt")
