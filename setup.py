import os
from pathlib import Path

from listarr import create_app
from listarr.services.crypto_utils import generate_key


def main():
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
