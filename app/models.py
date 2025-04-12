
from datetime import datetime 
from app import db, bcrypt  # Import initialized database and Bcrypt objects from __init__.py
from flask_login import UserMixin  # Import UserMixin from flask_login to handle user sessions

# User model that integrates Flask-Login
class User(UserMixin, db.Model):
    # The 'User' class represents a user in the application, with authentication and relationships to itineraries
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the user
    username = db.Column(db.String(100), unique=True, nullable=False)  # Unique username
    email = db.Column(db.String(100), unique=True, nullable=False)  # Unique email
    password_hash = db.Column(db.String(128), nullable=False)  # Hashed password
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)  # Date the user joined (defaults to current time)
    is_admin = db.Column(db.Boolean, default=False)  # Flag to check if the user is an admin

    # Relationship to itineraries: One-to-many (one user can have many itineraries)
    itineraries = db.relationship('Itinerary', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        # String representation of the User object
        return f'<User {self.username}>'

    # Password hashing with Bcrypt: Set the password and hash it
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')  # Generate hashed password

    # Check the user's entered password against the hashed password
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

# Itinerary model
class Itinerary(db.Model):
    # The 'Itinerary' class represents a travel itinerary linked to a specific user
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the itinerary
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key to link itinerary to user
    name = db.Column(db.String(100), nullable=False)  # Name of the itinerary (e.g., "Summer Vacation")
    date_created = db.Column(db.DateTime, default=datetime.utcnow)  # Date the itinerary was created (defaults to current time)

    # Relationship to POIs: One-to-many (one itinerary can have many POIs)
    pois = db.relationship('POI', back_populates='itinerary', cascade='all, delete-orphan')

    # Relationship to User: One-to-one (each itinerary belongs to one user)
    user = db.relationship('User', back_populates='itineraries')

    def __repr__(self):
        # String representation of the Itinerary object
        return f'<Itinerary {self.name}>'

# POI model for individual points of interest
class POI(db.Model):
    # The 'POI' class represents a point of interest (location, activity, etc.)
    __tablename__ = 'poi'  # Explicitly define the table name in case of naming conflicts

    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the POI
    name = db.Column(db.String(255), nullable=False)  # Name of the point of interest
    address = db.Column(db.String(255))  # Optional address of the POI
    latitude = db.Column(db.Float)  # Latitude of the POI (for geolocation)
    longitude = db.Column(db.Float)  # Longitude of the POI (for geolocation)
    original_latitude = db.Column(db.Float)  # Original latitude (before any transformations)
    original_longitude = db.Column(db.Float)  # Original longitude (before any transformations)
    day = db.Column(db.Integer, nullable=False)  # The day number (NOT NULL), represents which day the POI appears on in the itinerary
    itinerary_id = db.Column(db.Integer, db.ForeignKey('itinerary.id'), nullable=False)  # Foreign key to link POI to itinerary

    # Relationship to Itinerary: Many-to-one (many POIs belong to one itinerary)
    itinerary = db.relationship('Itinerary', back_populates='pois')

    def __repr__(self):
        # String representation of the POI object
        return f"<POI {self.name}>"

# Upload model for user-generated content (blogs or vlogs)
class Upload(db.Model):
    # The 'Upload' class represents user uploads (either a blog or vlog)
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the upload
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key to link the upload to a user
    upload_type = db.Column(db.String(10), nullable=False)  # Type of upload ('blog' or 'vlog')
    filename = db.Column(db.String(120), nullable=True)  # Filename for the blog (if it's a blog)
    vlog_url = db.Column(db.String(255), nullable=True)  # URL for the vlog (if it's a vlog, could be YouTube or local path)
    vlog_title = db.Column(db.String(120), nullable=True)  # Title for the vlog (optional)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())  # Timestamp of when the upload was created (defaults to current time)

    # Relationship to User: One-to-many (one user can have multiple uploads)
    user = db.relationship('User', backref=db.backref('uploads', lazy=True))

# Like model for handling user likes on uploads
class Like(db.Model):
    # The 'Like' class represents a like on an upload (blog or vlog)
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the like
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key to link the like to a user
    upload_id = db.Column(db.Integer, db.ForeignKey('upload.id'), nullable=False)  # Foreign key to link the like to an upload
    
    # Relationship to User: One-to-many (one user can like many uploads)
    user = db.relationship('User', backref='likes')

    # Relationship to Upload: One-to-many (one upload can be liked by many users)
    upload = db.relationship('Upload', backref='likes')

    def __repr__(self):
        # String representation of the Like object
        return f'<Like {self.id}>'

# Comment model for handling user comments on uploads
class Comment(db.Model):
    # The 'Comment' class represents a comment on a blog or vlog upload
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the comment
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key to link the comment to a user
    upload_id = db.Column(db.Integer, db.ForeignKey('upload.id'), nullable=False)  # Foreign key to link the comment to an upload
    content = db.Column(db.Text, nullable=False)  # Content of the comment
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of when the comment was made (defaults to current time)

    # Relationship to User: One-to-many (one user can write many comments)
    user = db.relationship('User', backref='comments')

    # Relationship to Upload: One-to-many (one upload can have many comments)
    upload = db.relationship('Upload', backref='comments')

    def __repr__(self):
        # String representation of the Comment object
        return f'<Comment {self.id}>'

