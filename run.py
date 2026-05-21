import os

from listarr import create_app

app = create_app()

if __name__ == "__main__":
    # Use FLASK_DEBUG environment variable, default to False for safety
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode)
