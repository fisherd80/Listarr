"""
Unit tests for crypto_utils.py - Encryption and decryption utilities.

Tests cover:
- Key generation and persistence
- Key loading from file and environment
- Encryption/decryption roundtrip
- Error handling for missing or invalid keys
- Instance path handling
"""

import os
import tempfile

import pytest
from cryptography.fernet import Fernet

from listarr.services.crypto_utils import (
    _get_key_path,
    decrypt_data,
    encrypt_data,
    generate_key,
    get_fernet,
    load_encryption_key,
)


class TestKeyGeneration:
    """Tests for encryption key generation."""

    def test_generate_key_creates_file(self):
        """Test that generate_key creates a valid key file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key = generate_key(instance_path=tmpdir)

            # Verify key is valid Fernet key
            assert key is not None
            assert isinstance(key, bytes)
            assert len(key) == 44  # Fernet keys are 44 bytes base64-encoded

            # Verify file was created
            key_path = os.path.join(tmpdir, ".fernet_key")
            assert os.path.exists(key_path)

            # Verify file contents match returned key
            with open(key_path, "rb") as f:
                file_key = f.read()
            assert file_key == key

    def test_generate_key_creates_directory_if_missing(self):
        """Test that generate_key creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "subdir", "instance")
            key = generate_key(instance_path=nested_path)

            assert key is not None
            key_path = os.path.join(nested_path, ".fernet_key")
            assert os.path.exists(key_path)

    def test_generate_key_returns_valid_fernet_key(self):
        """Test that generated key can be used to create Fernet instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key = generate_key(instance_path=tmpdir)

            # Should not raise exception
            fernet = Fernet(key)
            assert fernet is not None


class TestKeyLoading:
    """Tests for encryption key loading."""

    def test_load_encryption_key_from_file(self):
        """Test loading key from .fernet_key file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create key file
            expected_key = Fernet.generate_key()
            key_path = os.path.join(tmpdir, ".fernet_key")
            with open(key_path, "wb") as f:
                f.write(expected_key)

            # Load key
            loaded_key = load_encryption_key(instance_path=tmpdir)

            assert loaded_key == expected_key

    def test_load_encryption_key_from_environment(self, monkeypatch):
        """Test loading key from FERNET_KEY environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set environment variable
            expected_key = Fernet.generate_key().decode()
            monkeypatch.setenv("FERNET_KEY", expected_key)

            # Load key (should use env var, not file)
            loaded_key = load_encryption_key(instance_path=tmpdir)

            assert loaded_key == expected_key.encode()

    def test_load_encryption_key_prefers_environment_over_file(self, monkeypatch):
        """Test that environment variable takes precedence over file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create key file
            file_key = Fernet.generate_key()
            key_path = os.path.join(tmpdir, ".fernet_key")
            with open(key_path, "wb") as f:
                f.write(file_key)

            # Set different key in environment
            env_key = Fernet.generate_key().decode()
            monkeypatch.setenv("FERNET_KEY", env_key)

            # Load key
            loaded_key = load_encryption_key(instance_path=tmpdir)

            # Should use environment key, not file key
            assert loaded_key == env_key.encode()
            assert loaded_key != file_key

    def test_load_encryption_key_raises_error_when_missing(self):
        """Test that RuntimeError is raised when key is not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError) as exc_info:
                load_encryption_key(instance_path=tmpdir)

            assert "Encryption key not found" in str(exc_info.value)

    def test_load_encryption_key_with_allow_generate(self):
        """Test that key is generated when allow_generate=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key = load_encryption_key(instance_path=tmpdir, allow_generate=True)

            assert key is not None
            assert isinstance(key, bytes)

            # Verify file was created
            key_path = os.path.join(tmpdir, ".fernet_key")
            assert os.path.exists(key_path)

    def test_load_encryption_key_validates_key_format(self):
        """Test that RuntimeError is raised for invalid key format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid key file
            key_path = os.path.join(tmpdir, ".fernet_key")
            with open(key_path, "wb") as f:
                f.write(b"invalid_key_format")

            with pytest.raises(RuntimeError) as exc_info:
                load_encryption_key(instance_path=tmpdir)

            assert "Invalid encryption key format" in str(exc_info.value)


class TestGetKeyPath:
    """Tests for _get_key_path helper function."""

    def test_get_key_path_with_explicit_instance_path(self):
        """Test that _get_key_path uses provided instance_path."""
        test_path = "/test/instance"
        result = _get_key_path(instance_path=test_path)

        assert result == os.path.join(test_path, ".fernet_key")

    def test_get_key_path_with_flask_app_context(self, app):
        """Test that _get_key_path uses Flask app.instance_path."""
        with app.app_context():
            result = _get_key_path(instance_path=None)
            # Should use app.instance_path
            assert ".fernet_key" in result


class TestGetFernet:
    """Tests for get_fernet function."""

    def test_get_fernet_returns_fernet_instance(self):
        """Test that get_fernet returns a valid Fernet instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            fernet = get_fernet(instance_path=tmpdir)

            assert fernet is not None
            assert isinstance(fernet, Fernet)

    def test_get_fernet_can_encrypt_and_decrypt(self):
        """Test that returned Fernet instance can encrypt/decrypt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            fernet = get_fernet(instance_path=tmpdir)

            original = b"test data"
            encrypted = fernet.encrypt(original)
            decrypted = fernet.decrypt(encrypted)

            assert decrypted == original


class TestEncryptData:
    """Tests for encrypt_data function."""

    def test_encrypt_data_with_valid_key(self):
        """Test encrypting data with valid key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            data = "sensitive_api_key"

            encrypted = encrypt_data(data, instance_path=tmpdir)

            assert encrypted is not None
            assert isinstance(encrypted, str)
            assert encrypted != data  # Should be encrypted

    def test_encrypt_data_returns_different_ciphertext_each_time(self):
        """Test that encrypting same data produces different ciphertext (due to nonce)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            data = "test_data"

            encrypted1 = encrypt_data(data, instance_path=tmpdir)
            encrypted2 = encrypt_data(data, instance_path=tmpdir)

            assert encrypted1 != encrypted2  # Different due to nonce

    def test_encrypt_data_with_empty_string(self):
        """Test encrypting empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)

            encrypted = encrypt_data("", instance_path=tmpdir)

            assert encrypted is not None
            assert isinstance(encrypted, str)

    def test_encrypt_data_with_special_characters(self):
        """Test encrypting data with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            data = "key!@#$%^&*()_+{}|:<>?~`"

            encrypted = encrypt_data(data, instance_path=tmpdir)

            assert encrypted is not None
            assert isinstance(encrypted, str)

    def test_encrypt_data_with_unicode(self):
        """Test encrypting Unicode data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            data = "Test 测试 тест 🔑"

            encrypted = encrypt_data(data, instance_path=tmpdir)

            assert encrypted is not None
            assert isinstance(encrypted, str)


class TestDecryptData:
    """Tests for decrypt_data function."""

    def test_decrypt_data_with_valid_token(self):
        """Test decrypting valid encrypted data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            original = "secret_api_key"
            encrypted = encrypt_data(original, instance_path=tmpdir)

            decrypted = decrypt_data(encrypted, instance_path=tmpdir)

            assert decrypted == original

    def test_decrypt_data_with_invalid_token(self):
        """Test that ValueError is raised for invalid token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)

            with pytest.raises(ValueError) as exc_info:
                decrypt_data("invalid_token", instance_path=tmpdir)

            assert "Invalid token" in str(exc_info.value)

    def test_decrypt_data_with_wrong_key(self):
        """Test that decryption fails with different key."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                # Encrypt with first key
                generate_key(instance_path=tmpdir1)
                encrypted = encrypt_data("secret", instance_path=tmpdir1)

                # Try to decrypt with different key
                generate_key(instance_path=tmpdir2)

                with pytest.raises(ValueError) as exc_info:
                    decrypt_data(encrypted, instance_path=tmpdir2)

                assert "Invalid token" in str(exc_info.value)

    def test_decrypt_data_with_empty_token(self):
        """Test that ValueError is raised for empty token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)

            with pytest.raises(ValueError):
                decrypt_data("", instance_path=tmpdir)

    def test_decrypt_data_with_special_characters(self):
        """Test decrypting data with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            original = "api_key!@#$%^&*()"
            encrypted = encrypt_data(original, instance_path=tmpdir)

            decrypted = decrypt_data(encrypted, instance_path=tmpdir)

            assert decrypted == original

    def test_decrypt_data_with_unicode(self):
        """Test decrypting Unicode data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            original = "密钥 🔐 ключ"
            encrypted = encrypt_data(original, instance_path=tmpdir)

            decrypted = decrypt_data(encrypted, instance_path=tmpdir)

            assert decrypted == original


class TestEncryptionRoundtrip:
    """Integration tests for full encryption/decryption workflow."""

    def test_encryption_roundtrip_with_instance_path(self):
        """Test full encrypt/decrypt cycle with explicit instance path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            original = "my_secret_api_key_12345"

            encrypted = encrypt_data(original, instance_path=tmpdir)
            decrypted = decrypt_data(encrypted, instance_path=tmpdir)

            assert decrypted == original

    def test_encryption_roundtrip_with_long_data(self):
        """Test encryption/decryption with long string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)
            original = "A" * 10000  # Long string

            encrypted = encrypt_data(original, instance_path=tmpdir)
            decrypted = decrypt_data(encrypted, instance_path=tmpdir)

            assert decrypted == original

    def test_encryption_preserves_data_integrity(self):
        """Test that encryption/decryption preserves exact data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_key(instance_path=tmpdir)

            test_cases = [
                "simple",
                "with spaces",
                "with\nnewlines\n",
                "with\ttabs",
                "123456789",
                "",
                "!@#$%^&*()",
                "MixedCASE123",
            ]

            for original in test_cases:
                encrypted = encrypt_data(original, instance_path=tmpdir)
                decrypted = decrypt_data(encrypted, instance_path=tmpdir)
                assert decrypted == original, f"Failed for: {original}"


class TestErrorHandling:
    """Tests for error handling in crypto utilities."""

    def test_encrypt_data_without_key_raises_error(self):
        """Test that encrypting without key raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError):
                encrypt_data("data", instance_path=tmpdir)

    def test_decrypt_data_without_key_raises_error(self):
        """Test that decrypting without key raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError):
                decrypt_data("token", instance_path=tmpdir)

    def test_get_fernet_without_key_raises_error(self):
        """Test that get_fernet without key raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError):
                get_fernet(instance_path=tmpdir)
