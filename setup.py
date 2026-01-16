import os
from pathlib import Path
from listarr import create_app, db
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

    # STEP 2: Now create app (key exists, so it won't fail)
    app = create_app()

    # STEP 3: Create database if needed
    db_path = Path(app.instance_path) / "listarr.db"
    if not db_path.exists():
        print(">>> Creating database tables...")
        with app.app_context():
            db.create_all()
        print(f">>> Database created at {db_path}")
    else:
        print(">>> Database already exists, skipping creation.")

    print(">>> Setup complete. You can now run `python run.py` to start the app.")

if __name__ =="__main__":
    main()
