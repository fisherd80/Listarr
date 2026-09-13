"""
Unit tests for User model password hashing and authentication methods.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from listarr import db
from listarr.models.user_model import User


class TestUserModel:
    """Test User model password functionality."""

    def test_set_password_hashes_password(self, app):
        """Test that set_password stores a hash, not plaintext."""
        with app.app_context():
            user = User(username="hashtest")
            user.set_password("mypassword123")

            # Password hash should not match plaintext
            assert user.password_hash != "mypassword123"
            # Password hash should be a non-empty string
            assert isinstance(user.password_hash, str)
            assert len(user.password_hash) > 0

    def test_check_password_valid(self, app):
        """Test that check_password returns True for correct password."""
        with app.app_context():
            user = User(username="validtest")
            user.set_password("correctpassword")
            db.session.add(user)
            db.session.commit()

            assert user.check_password("correctpassword") is True

    def test_check_password_invalid(self, app):
        """Test that check_password returns False for wrong password."""
        with app.app_context():
            user = User(username="invalidtest")
            user.set_password("correctpassword")
            db.session.add(user)
            db.session.commit()

            assert user.check_password("wrongpassword") is False

    def test_different_passwords_different_hashes(self, app):
        """Test that two different passwords produce different hashes."""
        with app.app_context():
            user1 = User(username="user1")
            user1.set_password("password1")

            user2 = User(username="user2")
            user2.set_password("password2")

            assert user1.password_hash != user2.password_hash

    def test_user_mixin_properties(self, app):
        """Test that UserMixin properties work correctly."""
        with app.app_context():
            user = User(username="mixintest")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()

            # UserMixin properties
            assert user.is_authenticated is True
            assert user.is_active is True
            assert user.is_anonymous is False
            assert user.get_id() == str(user.id)

    def test_username_unique_constraint(self, app):
        """Test that duplicate username raises IntegrityError."""
        with app.app_context():
            # Create first user
            user1 = User(username="duplicate")
            user1.set_password("pass1")
            db.session.add(user1)
            db.session.commit()

            # Attempt to create second user with same username
            user2 = User(username="duplicate")
            user2.set_password("pass2")
            db.session.add(user2)

            with pytest.raises(IntegrityError):
                db.session.commit()

            db.session.rollback()


class TestPasswordHashBackCompat:
    """Guard stored Werkzeug password hashes across dependency pins."""

    PASSWORD = "phase15-password"
    PBKDF2_HASH = (
        "pbkdf2:sha256:1000000$A7dL9dFMSdsoD4PD$efe82f2be1ed7b52ac660ea330753b02324efb3d6fc5fb7af1cf4038004b95f4"
    )
    SCRYPT_HASH = (
        "scrypt:32768:8:1$jDuzVddkx7yOFNsg$"
        "3d8d5c152ebb2d12583e0d23264c4f390d67df0cbff879a9408a2e8d706a59d4f55eac3f1ab1d399bf9e346bf63971982b88248dc55041091048d6f424f91e61"
    )

    def test_pbkdf2_hash_still_verifies(self):
        """Existing pbkdf2 Werkzeug hashes remain valid."""
        assert check_password_hash(self.PBKDF2_HASH, self.PASSWORD) is True

    def test_scrypt_hash_still_verifies(self):
        """Existing scrypt Werkzeug hashes remain valid."""
        assert check_password_hash(self.SCRYPT_HASH, self.PASSWORD) is True

    def test_user_password_round_trip_still_verifies(self, app):
        """Fresh User password writes and reads still round-trip."""
        with app.app_context():
            user = User(username="roundtrip")
            user.set_password(self.PASSWORD)

            assert user.check_password(self.PASSWORD) is True
