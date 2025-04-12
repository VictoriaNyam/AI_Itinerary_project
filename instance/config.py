
# instance/config.py
SECRET_KEY = 'asecretkey12345678'  # Secret key used for session management and cryptographic operations like signing cookies
SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'  # URI for the SQLite database
SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disables Flask-SQLAlchemy's modification tracking to save resources


