"""
Unit tests for User model password hashing and authentication methods.
"""

import pytest
from sqlalchemy.exc import IntegrityError

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
