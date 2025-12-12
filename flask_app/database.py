from flask_sqlalchemy import SQLAlchemy

# Initialize the extension
# We do not bind it to the app here; that happens in app.py
db = SQLAlchemy()