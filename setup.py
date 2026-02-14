import os
import sys
from getpass import getpass
from pathlib import Path

from listarr import create_app
from listarr.services.crypto_utils import generate_key


def reset_user_password():
    """Interactive password reset via CLI."""
    project_root = Path(__file__).parent
    instance_path = project_root / "instance"

    # Check instance folder exists
    if not instance_path.exists():
        print("Error: Instance folder not found. Run setup first.")
        return

    from listarr import create_app, db
    from listarr.models.user_model import User

    app = create_app()
    with app.app_context():
        user = User.query.first()
        if not user:
            print("No user found. Run setup first (visit the app in browser).")
            return

        print(f"Resetting password for user: {user.username}")
        new_password = getpass("New password: ")
        confirm_password = getpass("Confirm password: ")

        if new_password != confirm_password:
            print("Passwords do not match.")
            return

        if not new_password:
            print("Password cannot be empty.")
            return

        user.set_password(new_password)
        db.session.commit()
        print("Password reset successfully.")


def main():
    # Check for --reset-password flag
    if "--reset-password" in sys.argv:
        reset_user_password()
        return

    # Determine instance path (Flask default: <project_root>/instance)
    project_root = Path(__file__).parent
    instance_path = project_root / "instance"

    # Create instance folder if it doesn't exist
    os.makedirs(instance_path, exist_ok=True)

    # Path to encryption key in Flask's instance folder
    key_path = instance_path / ".fernet_key"

    # STEP 1: Generate encryption key BEFORE creating app
    if not key_path.exists():
        print(">>> Generating Encryption Key...")
        generate_key(instance_path=str(instance_path))
        print(f">>> Encryption Key created at {key_path}")
    else:
        print(f">>> Encryption Key already exists at {key_path}.")

    # STEP 2: Now create app
    # This will automatically initialize the database tables via create_app() -> db.create_all()
    app = create_app()

    # Verify database file creation
    db_path = Path(app.instance_path) / "listarr.db"
    if db_path.exists():
        print(f">>> Database initialized at {db_path}")

    print(">>> Setup complete. You can now run `python run.py` to start the app.")


if __name__ == "__main__":
    main()
