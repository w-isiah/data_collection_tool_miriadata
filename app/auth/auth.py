from datetime import timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from PIL import Image
import mysql.connector
import os
from app import app
from app.db import get_db_connection

# Initialize the Blueprint
users_bp = Blueprint('auth', __name__)

# Configuration Constants
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = app.config.get('UPLOAD_FOLDER')  # Ensure this is defined in your app config

# Utility Function to Check File Extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login Route
@users_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            with get_db_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = cursor.fetchone()

                    if user:
                        stored_password = user['password']
                        if password == stored_password:
                            session.update({
                                'loggedin': True,
                                'id': user['id'],
                                'username': user['username'],
                                'first_name': user['first_name'],
                                'last_name': user['last_name'],
                                'profile_image': user['profile_image'],
                                'role': user['role'],
                                'last_activity': datetime.utcnow()
                            })
                            session.permanent = True
                            flash('Login successful!', 'success')
                            return redirect(url_for('main.index'))
                        else:
                            flash('Invalid username or password.', 'danger')
                    else:
                        flash('Invalid username or password.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')

    return render_template('accounts/login.html')




@users_bp.route('/logout')
def logout():
    session.clear()  # Clear session data
    flash('You have logged out successfully.', 'success')
    return redirect(url_for('auth.login'))  # Redirect to login page

# User Management Routes (Admin/Head of Department)

@users_bp.route('/manage_users')
def manage_users():
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                if session['role'] == 'admin':
                    cursor.execute("SELECT * FROM users WHERE role != 'admin'")
                elif session['role'] == 'Head of Department':
                    cursor.execute("SELECT * FROM users WHERE role NOT IN ('admin', 'Head of Department', 'Dean')")
                users = cursor.fetchall()

                num = len(users)
    except Exception as e:
        flash(f"Error fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))

    template = 'accounts/manage_users.html' if session['role'] == 'admin' else 'accounts/moderator/manage_users.html'
    return render_template(template, username=session['username'], role=session['role'], num=num, users=users)

@users_bp.route('/api/manage_users_count', methods=['GET'])
def get_users_count():
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'")
                num = cursor.fetchone()[0]  # Extract count value from tuple
        return jsonify({"count": num})

    except Exception as e:
        return jsonify({"error": f"Error fetching data: {str(e)}"}), 500


# User Profile Management Routes (Add, Edit, Delete, Update)

@users_bp.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        other_name = request.form['other_name']
        
        # Handle profile image upload (if present)
        profile_image = None
        if 'profile_image' in request.files:
            image_file = request.files['profile_image']
            if image_file and allowed_file(image_file.filename):
                profile_image = handle_image_upload(image_file)

        # Store password directly without hashing
        plain_password = password

        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Check if the username already exists
                cursor.execute('SELECT 1 FROM users WHERE username = %s', (username,))
                if cursor.fetchone():
                    flash('Username already exists. Please choose a different one.', 'danger')
                    return render_template('accounts/add_user.html', role=session.get('role'), username=session.get('username'))

                try:
                    cursor.execute(''' 
                        INSERT INTO users (username, password, role, first_name, last_name, other_name, profile_image)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (username, plain_password, role, first_name, last_name, other_name, profile_image))
                    connection.commit()
                    flash('User added successfully!', 'success')
                except mysql.connector.Error as err:
                    flash(f'Error: {err}', 'danger')

        return redirect(url_for('main.index'))  # Redirect to user management page

    template = 'accounts/add_user.html' if session['role'] == 'admin' else 'accounts/moderator/add_user.html'
    return render_template(template, role=session.get('role'), username=session.get('username'))




# Image upload helper function
def handle_image_upload(image_file):
    filename = secure_filename(image_file.filename)
    profile_image_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        img = Image.open(image_file)
        max_width, max_height = 500, 500
        width, height = img.size
        if width > max_width or height > max_height:
            img.thumbnail((max_width, max_height))
            img.save(profile_image_path, optimize=True, quality=85)
        else:
            img.save(profile_image_path)
    except Exception as e:
        flash(f"Error processing image: {e}", 'danger')
        return None

    return os.path.join(UPLOAD_FOLDER, filename)






# Handle the form submission
@users_bp.route('/edit_user/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    with get_db_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            if request.method == 'POST':
                # Getting user data from the form
                username = request.form['username']
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                other_name = request.form['other_name']
                password = request.form['password']
                role = request.form['role']
                profile_image = request.files.get('profile_image')

                # New internal and external roles (optional, could be None if not provided)
                a_internal_role = request.form.get('a_internal_role')  # No default value
                a_external_role = request.form.get('a_external_role')  # No default value

                # Use the new password if provided, otherwise keep the current one
                if password:
                    plain_password = password
                else:
                    cursor.execute("SELECT password FROM users WHERE id = %s", (id,))
                    result = cursor.fetchone()
                    plain_password = result['password'] if result else ''

                # Handle profile image if uploaded
                profile_image_path = handle_profile_image(cursor, profile_image, id)

                # Update the user information in the database
                try:
                    cursor.execute('''
                        UPDATE users 
                        SET username = %s, first_name = %s, last_name = %s, other_name = %s, password = %s, role = %s, 
                            profile_image = %s, a_internal_role = %s, a_external_role = %s 
                        WHERE id = %s
                    ''', (
                        username, first_name, last_name, other_name, plain_password, role, 
                        profile_image_path, a_internal_role, a_external_role, id
                    ))
                    connection.commit()
                    flash('User updated successfully!', 'success')
                except mysql.connector.Error as err:
                    flash(f'Error: {err}', 'danger')

                return redirect(url_for('main.index'))  # Redirect back to the home page or user list

            # Retrieve the user information from the database to pre-fill the form
            cursor.execute('SELECT * FROM users WHERE id = %s', (id,))
            user = cursor.fetchone()

    template = 'accounts/edit_user.html' if session['role'] == 'admin' else 'accounts/moderator/edit_user.html'
    return render_template(template, role=session.get('role'), username=session.get('username'), user=user)




    

def get_user_password(cursor, user_id):
    cursor.execute('SELECT password FROM users WHERE id = %s', (user_id,))
    return cursor.fetchone()['password']

def handle_profile_image(cursor, profile_image, user_id):
    if profile_image and allowed_file(profile_image.filename):
        filename = secure_filename(profile_image.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        profile_image.save(file_path)
        return filename
    else:
        cursor.execute('SELECT profile_image FROM users WHERE id = %s', (user_id,))
        return cursor.fetchone()['profile_image']

# Route for deleting a user
@users_bp.route('/delete_user/<int:id>', methods=['GET'])
def delete_user(id):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM users WHERE id = %s', (id,))
                connection.commit()
                flash('User deleted successfully!', 'success')
            except mysql.connector.Error as err:
                flash(f'Error: {err}', 'danger')

    return redirect(url_for('main.index'))








@users_bp.route('/edit_user_profile/<int:id>', methods=['GET', 'POST'])
def edit_user_profile(id):
    with get_db_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            
            # POST request - Handle profile update
            if request.method == 'POST':
                # Collect form data
                username = request.form['username']
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                other_name = request.form['other_name']
                password = request.form['password']
                profile_image = request.files.get('profile_image')

                # Use new password if provided, otherwise keep current one
                if password:
                    plain_password = password
                else:
                    cursor.execute("SELECT password FROM users WHERE id = %s", (id,))
                    result = cursor.fetchone()
                    plain_password = result['password'] if result else ''

                # Process profile image
                profile_image_path = handle_profile_image(cursor, profile_image, id)

                try:
                    # Update user details in the database
                    cursor.execute('''
                        UPDATE users 
                        SET username = %s, first_name = %s, last_name = %s, other_name = %s, password = %s, profile_image = %s
                        WHERE id = %s
                    ''', (username, first_name, last_name, other_name, plain_password, profile_image_path, id))
                    connection.commit()
                    flash('User updated successfully!', 'success')
                except mysql.connector.Error as err:
                    flash(f'Error: {err}', 'danger')

                # Redirect after successful update
                return redirect(url_for('main.index'))

            # GET request - Fetch user data to populate the edit form
            cursor.execute('SELECT * FROM users WHERE id = %s', (id,))
            user = cursor.fetchone()

            # If user not found, show error and redirect
            if not user:
                flash('User not found!', 'danger')
                return redirect(url_for('auth.manage_users'))

    # Render the appropriate template based on the role
    role = session.get('role')
    username = session.get('username')
    if role == "Head of Department":
        return render_template('accounts/h_edit_user_profile.html', role=role, username=username, user=user)
    elif role == "School Practice Supervisor":
        return render_template('accounts/a_edit_user_profile.html', role=role, username=username, user=user)

