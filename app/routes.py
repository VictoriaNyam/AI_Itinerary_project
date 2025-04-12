
from flask import Blueprint, session, request, render_template, redirect, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user
from app import db, bcrypt
from app.models import User, Itinerary, POI, Upload, Like, Comment
from app.forms import RegistrationForm, LoginForm
from app.forms import UploadForm
from app.Itinerary import load_poi_data, normalize_coordinates, filter_pois_by_activity, apply_kmeans, select_representative_pois, generate_itineraries
import pandas as pd
import json  # For serializing POIs data
from datetime import datetime
import folium  # For rendering interactive maps
from werkzeug.utils import secure_filename
import os
from flask import current_app

# Blueprint to handle routes related to the main functionalities (home, user, and admin tasks)
main = Blueprint('main', __name__)

# Home Route - Render the base home page
@main.route('/')
def home():
    return render_template("index.html")

# Register Route - Handle user registration (GET for form, POST for processing data)
@main.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Check if the email or username already exists
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash("A user with that email or username already exists. Please log in or use different credentials.", "danger")
            return redirect(url_for("main.register"))

        # Hash password with bcrypt and store it securely
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Save the user to the database
        user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(user)
        try:
            db.session.commit()  # Commit to save the user to the database
        except Exception as e:
            db.session.rollback()  # In case of failure, rollback the transaction
            flash("Registration failed. Please try again.", "danger")
            return redirect(url_for("main.register"))

        flash("Registration Successful", "success")
        return redirect(url_for("main.login"))  # Redirect to the login page after successful registration

    return render_template("register.html", form=form)

# Login Route - Handle user login (GET for form, POST for validating credentials)
@main.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit(): 
        username = form.username.data 
        password = form.password.data

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):  # Check credentials
            login_user(user)  # Log the user in

            # Redirect to the appropriate dashboard based on user type
            if user.is_admin:
                return redirect(url_for("main.admin_dashboard"))  # Admin dashboard
            else:
                return redirect(url_for("main.dashboard"))  # Regular user dashboard
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("main.login"))

    return render_template("login.html", form=form)

# Admin Dashboard Route - Display admin-specific dashboard (e.g., total users, recent uploads)
@main.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:  # Ensure only admins can access this
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.dashboard'))  # Redirect to user dashboard
    
    # Admin-related data
    total_users = User.query.count()
    total_uploads = Upload.query.count()
    recent_uploads = Upload.query.order_by(Upload.timestamp.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', total_users=total_users, total_uploads=total_uploads, recent_uploads=recent_uploads)

# Manage Users Route - Admin can manage users (view, edit, delete)
@main.route('/admin/manage_users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    users = User.query.all()  # Retrieve all users from the database
    return render_template('manage_users.html', users=users)

# Delete User Route - Admin can delete a user
@main.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to delete this user.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)  # Fetch the user to delete
    db.session.delete(user)
    db.session.commit()  # Commit to remove the user from the database
    flash(f'User {user.username} deleted successfully!', 'success')
    return redirect(url_for('admin.manage_users'))

# Plan Trip Route - Allows users to plan a trip (select activities, generate itinerary)
@main.route('/plan_trip', methods=['GET', 'POST'])
@login_required
def plan_trip():
    # Load and prepare the dataset for POIs (points of interest)
    df = load_poi_data()
    df = normalize_coordinates(df)  # Normalize the coordinates for clustering

    # List of available activity types for filtering POIs
    activity_cols = [
        'nature', 'nightlife', 'drink', 'music', 'dance', 'history',
        'sports', 'art', 'museum', 'walk', 'restaurant', 'movie'
    ]

    # Process form data when the user selects activities and submits the form
    if request.method == 'POST':
        days = int(request.form['days'])
        selected_activities = request.form.getlist('interests')  # Selected activities

        # Filter POIs based on selected activities
        filtered_df = filter_pois_by_activity(df, selected_activities)

        # Apply K-Means clustering to POIs
        clustered_df, kmeans = apply_kmeans(filtered_df, days)

        # Select representative POIs based on clusters
        representative_pois = select_representative_pois(clustered_df, kmeans)

        # Generate itineraries based on the selected POIs and activities
        itineraries = generate_itineraries(representative_pois, selected_activities, days)

        return render_template('show_itinerary.html', itineraries=itineraries)

    return render_template('plan_trip.html', activities=activity_cols)

# Save Itinerary Route - Allow users to save their generated itinerary
@main.route('/save_itinerary', methods=['POST'])
@login_required
def save_itinerary():
    itinerary_name = request.form['itinerary_name']
    pois_data = request.form['pois']  # POI data submitted by the user

    if not itinerary_name or not pois_data:  # Ensure both name and POIs are provided
        flash("Itinerary name and POIs cannot be empty", "danger")
        return redirect(url_for('main.plan_trip'))

    try:
        poi_dict_list = json.loads(pois_data)  # Parse POI data from JSON format
        print("POI List:", poi_dict_list)
    except json.JSONDecodeError:
        flash("Invalid POI data", "danger")
        return redirect(url_for('main.plan_trip'))

    flat_pois = [poi for day in poi_dict_list for poi in day]  # Flatten the POI list
    poi_instances = []  # List to store POI instances for saving to DB

    # Create POI instances and append to the list
    for poi in flat_pois:
        if not isinstance(poi, dict):
            flash("There was an issue with your POI data. Please check and try again.", "danger")
            return redirect(url_for('main.plan_trip'))

        day_value = poi.get('day', 1)  # Default day is 1 if not provided
        poi_instance = POI(
            name=poi.get('name'),
            address=poi.get('address', ''),
            latitude=poi.get('latitude'),
            longitude=poi.get('longitude'),
            original_latitude=poi.get('original_latitude', poi.get('latitude')),
            original_longitude=poi.get('original_longitude', poi.get('longitude')),
            day=day_value
        )
        poi_instances.append(poi_instance)

    # Create and save the itinerary
    new_itinerary = Itinerary(
        name=itinerary_name,
        user_id=current_user.id,
        pois=poi_instances,
        date_created=datetime.utcnow()
    )

    try:
        db.session.add(new_itinerary)
        db.session.commit()  # Commit to save itinerary to the database
        flash("Itinerary saved successfully!", "success")
    except Exception as e:
        db.session.rollback()  # Rollback if there is an error
        print(f"Error saving itinerary: {e}")
        flash("There was an error saving your itinerary. Please try again.", "danger")

    return redirect(url_for('main.view_itineraries'))

# View Itineraries Route - Display a list of all saved itineraries for the user
@main.route('/view_itineraries')
@login_required
def view_itineraries():
    itineraries = Itinerary.query.filter_by(user_id=current_user.id).all()
    itineraries_grouped = []

    # Group the POIs in each itinerary by day
    for itinerary in itineraries:
        pois_by_day = {}
        for poi in itinerary.pois:
            pois_by_day.setdefault(poi.day, []).append(poi)
        
        # Sort the POIs by day
        grouped_pois = sorted(pois_by_day.items(), key=lambda item: item[0])
        
        itineraries_grouped.append({
            'itinerary': itinerary,
            'grouped_pois': grouped_pois
        })
    
    return render_template('view_itineraries.html', itineraries_grouped=itineraries_grouped)

# View Itinerary Map Route - Display a map for a specific itinerary
@main.route('/view_itinerary_map/<int:itinerary_id>')
@login_required
def view_itinerary_map(itinerary_id):
    itinerary = Itinerary.query.get_or_404(itinerary_id)

    # Find the first POI with valid original coordinates
    first_poi = next((p for p in itinerary.pois if p.original_latitude and p.original_longitude), None)
    if not first_poi:
        flash("No valid coordinates to display map.", "danger")
        return redirect(url_for('main.view_itineraries'))

    map_center = [first_poi.original_latitude, first_poi.original_longitude]
    m = folium.Map(location=map_center, zoom_start=12)

    for poi in itinerary.pois:
        if poi.original_latitude is None or poi.original_longitude is None:
            print(f"Skipping POI {poi.name} due to missing coordinates.")
            continue

        folium.Marker(
            [poi.original_latitude, poi.original_longitude],
            popup=folium.Popup(poi.name, parse_html=True),
            icon=folium.Icon(color="blue")
        ).add_to(m)

    map_html = m._repr_html_()
    return render_template('itinerary_map.html', map_html=map_html)


# Route to display the dashboard after user login
@main.route('/dashboard')
@login_required
def dashboard():
    # Pass the user's username to the dashboard template
    return render_template('dashboard.html', username=current_user.username)

# Upload route
@main.route('/upload', methods=['GET', 'POST'])
@login_required  # Ensures that the user must be logged in to upload content
def upload():
    form = UploadForm()  # Instantiate the form

    if request.method == 'POST':
        print("POST request received")
        upload_type = request.form.get('upload_type')  # Get the type of upload (blog or vlog)
        print(f"Upload type: {upload_type}")

        # Handling blog file uploads
        if upload_type == 'blog':
            file = request.files.get('blog_file')  # Get the uploaded file
            print(f"File received: {file}")

            # Check if the file is valid and has an allowed extension
            if file and file.filename.endswith(('.txt', '.md', '.pdf')):
                filename = secure_filename(file.filename)  # Secure the file name
                upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'uploads')  # Folder to save the upload
                os.makedirs(upload_folder, exist_ok=True)  # Create the folder if it doesn't exist
                file_path = os.path.join(upload_folder, filename)  # Path to save the file
                file.save(file_path)  # Save the file
                print(f"File saved at: {file_path}")

                # Create a new upload record in the database
                new_upload = Upload(user_id=current_user.id, upload_type='blog', filename=filename)
                print(f"New blog upload: {new_upload}") 

                db.session.add(new_upload)  # Add the new upload to the session
                db.session.commit()  # Commit the changes to the database
                flash('Blog uploaded successfully!', 'success')  # Notify the user of success
            else:
                flash('Only .txt, .md, or .pdf files are allowed.', 'danger')  # Notify the user if the file type is not allowed

        # Handling vlog uploads
        elif upload_type == 'vlog':
            vlog_url = request.form.get('vlog_url')  # Get the vlog URL
            vlog_title = request.form.get('vlog_title')  # Get the vlog title
            file = request.files.get('vlog_file')  # Get the uploaded vlog file

            # If a URL is provided, save it to the database
            if vlog_url:
                new_upload = Upload(user_id=current_user.id, upload_type='vlog', vlog_url=vlog_url, vlog_title=vlog_title)
                db.session.add(new_upload)
                db.session.commit()
                flash('Vlog link submitted successfully!', 'success')  # Notify the user of success

            # If a file is uploaded, check if it has the correct format
            elif file and file.filename.endswith(('.mp4', '.mov')):
                filename = secure_filename(file.filename)  # Secure the file name
                upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'uploads')  # Folder to save the upload
                os.makedirs(upload_folder, exist_ok=True)  # Create the folder if it doesn't exist
                file_path = os.path.join(upload_folder, filename)  # Path to save the file
                file.save(file_path)  # Save the file

                # Generate the file URL to access it from the frontend
                vlog_file_url = url_for('static', filename='uploads/' + filename)
                new_upload = Upload(user_id=current_user.id, upload_type='vlog', vlog_url=vlog_file_url, vlog_title=vlog_title)
                db.session.add(new_upload)
                db.session.commit()
                flash('Video uploaded successfully!', 'success')  # Notify the user of success
            else:
                flash('Please provide a video URL or upload a video file (.mp4, .mov).', 'danger')  # Notify if the file type is invalid

        return redirect(url_for('main.dashboard'))  # Redirect the user to the dashboard after upload

    return render_template('upload.html', form=form)  # Render the upload form for GET requests


# Gallery route to display all blogs and vlogs uploaded by users
@main.route('/gallery')
@login_required  # Ensures that the user must be logged in to view the gallery
def gallery():
    blogs = Upload.query.filter_by(upload_type='blog').all()  # Get all blog uploads from the database
    vlogs = Upload.query.filter_by(upload_type='vlog').all()  # Get all vlog uploads from the database
    return render_template('gallery.html', blogs=blogs, vlogs=vlogs)  # Render the gallery page with the uploads


# Route to delete an upload
@main.route('/delete_upload/<int:upload_id>', methods=['POST'])
@login_required  # Ensures that the user must be logged in to delete an upload
def delete_upload(upload_id):
    # Find the upload by its ID
    upload = Upload.query.get_or_404(upload_id)

    # Check if the logged-in user is the one who uploaded the content
    if upload.user_id != current_user.id:
        flash('You do not have permission to delete this upload.', 'danger')  # Notify if the user is not the owner
        return redirect(url_for('main.gallery'))

    # If the user is the owner, delete the file from the server (for blogs)
    if upload.upload_type == 'blog':
        upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
        file_path = os.path.join(upload_folder, upload.filename)

        # Ensure the file exists before attempting to delete it
        if os.path.exists(file_path):
            os.remove(file_path)  # Delete the file
        else:
            flash('File not found, it may have been already deleted.', 'warning')  # Notify if the file was already removed

    # Delete the upload record from the database
    db.session.delete(upload)
    db.session.commit()

    flash('Upload deleted successfully!', 'success')  # Notify the user of success
    return redirect(url_for('main.gallery'))  # Redirect to the gallery after deletion


# Route to like an upload
@main.route('/like_upload/<int:upload_id>', methods=['POST'])
@login_required  # Ensures that the user must be logged in to like an upload
def like_upload(upload_id):
    # Check if the user has already liked this upload
    existing_like = Like.query.filter_by(user_id=current_user.id, upload_id=upload_id).first()

    if existing_like:
        flash('You already liked this upload!', 'warning')  # Notify the user if they already liked the upload
        return redirect(url_for('main.gallery'))
    
    # Create a new like if not already liked
    like = Like(user_id=current_user.id, upload_id=upload_id)
    db.session.add(like)
    db.session.commit()

    flash('You liked this upload!', 'success')  # Notify the user of success
    return redirect(url_for('main.gallery'))  # Redirect to the gallery after liking


# Route to comment on an upload
@main.route('/comment_upload/<int:upload_id>', methods=['POST'])
@login_required  # Ensures that the user must be logged in to comment on an upload
def comment_upload(upload_id):
    content = request.form.get('content')  # Get the comment content
    if content:
        comment = Comment(user_id=current_user.id, upload_id=upload_id, content=content)  # Create a new comment
        db.session.add(comment)
        db.session.commit()

        flash('Comment posted successfully!', 'success')  # Notify the user of success
    else:
        flash('Comment cannot be empty!', 'danger')  # Notify the user if the comment is empty

    return redirect(url_for('main.gallery'))  # Redirect to the gallery after commenting


# Logout Route - User logout
@main.route("/logout")
@login_required
def logout():
    logout_user()  # Log out the current user
    flash("You have been logged out.", "info")
    return redirect(url_for('main.home'))  # Redirect to the homepage after logout
>>>>>>> beb1998 (Intial commit)
