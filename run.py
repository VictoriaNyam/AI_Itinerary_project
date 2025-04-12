
# Import the create_app function from the app module to initialize the Flask app
from app import create_app

# Create the app instance by calling the create_app function
app = create_app()

# Check if the script is run directly (not imported), then run the app
# debug=True enables auto-reloading and detailed error messages during development
if __name__ == '__main__':
    app.run(debug=True)

