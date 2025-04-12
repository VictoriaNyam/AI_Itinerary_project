
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os

# Initialize core extensions
db = SQLAlchemy()            # Handles ORM and database interactions
bcrypt = Bcrypt()            # Used for hashing user passwords securely
login_manager = LoginManager()  # Manages user session and authentication
login_manager.login_view = "main.login"  # Redirect unauthenticated users to the login page

def create_app():
    # Create and configure the Flask application
    app = Flask(__name__)

    # Load settings from the config file inside the instance folder
    app.config.from_pyfile('../instance/config.py')

    # Define the path for file uploads (e.g., blogs, vlogs)
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')

    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize all extensions with the app
    bcrypt.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    # Import the User model here to avoid circular imports
    from .models import User

    # Function used by Flask-Login to load a user from the database
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register the blueprint with routes after initializing the app
    from .routes import main
    app.register_blueprint(main)

    return app

# Create the app instance
app = create_app()
>>>>>>> beb1998 (Intial commit)
