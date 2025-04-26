from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import get_db_connection  # Import get_db_connection from app/db.py

# Initialize blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Check if the user is logged in
    if 'loggedin' in session:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor()
        


        cursor.execute("SELECT COUNT(*) FROM users ")
        data = cursor.fetchone() # Extract count value from the tuple
        

        # Get the count of users who are not admins
        cursor.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'")
        num = cursor.fetchone() # Extract count value from the tuple

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Check the role and render appropriate template
        if session['role'] == "admin":
            return render_template('admin/index.html', username=session['username'], role=session['role'], user_count=num)
        elif session['role'] == "Principal_Investigator":
            return render_template('moderator/index.html', username=session['username'], role=session['role'], user_count=num)
        else:
            return render_template('assessor/index.html', username=session['username'], role=session['role'], user_count=num)
    
    # Redirect to login page if not logged in
    return redirect(url_for('auth.login'))
