from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
import random
import string

demo_data_bp = Blueprint('demo_data', __name__)









@demo_data_bp.route('/manage_demo_data', methods=['GET'])
def manage_demo_data():
    try:
        # Using context manager to handle the DB connection and cursor
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                # SQL query to fetch all demo data along with the associated username
                cursor.execute("""
                    SELECT demo_data.*, users.username
                    FROM demo_data
                    LEFT JOIN users ON demo_data.user_id = users.id ORDER BY created_at 
                """)
                demo_data = cursor.fetchall()

        # Ensure the session contains the required user info
        user_id = session.get('user_id')
        username = session.get('username', 'Guest')
        role = session.get('role', 'User')

        if user_id:
            # Optionally, you could fetch additional user info, like their full name
            with get_db_connection() as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT first_name, last_name FROM users WHERE id = %s", (user_id,))
                    user_info = cursor.fetchone()

                    if user_info:
                        full_name = f"{user_info['first_name']} {user_info['last_name']}"
                    else:
                        full_name = "User"

        # Rendering the template with the fetched data
        return render_template(
            'demo_data/manage_demo_data.html',
            username=username,
            role=role,
            demo_data=demo_data,
            full_name=full_name if user_id else None
        )
    except Exception as e:
        # Log the error for debugging purposes
        logging.error(f"Error fetching demo data: {str(e)}")
        
        # Flashing an error message in case of an exception
        flash(f"An error occurred while fetching demo data: {str(e)}", 'danger')
        
        # Redirecting to a safe page (main index or another fallback page)
        return redirect(url_for('main.index'))








@demo_data_bp.route('/edit_demo_data/<int:demo_data_id>', methods=['GET', 'POST'])
def edit_demo_data(demo_data_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the existing entry
    cursor.execute("SELECT * FROM demo_data WHERE id = %s", (demo_data_id,))
    demo_data = cursor.fetchone()

    if not demo_data:
        flash("Respondent data not found!", 'danger')
        return redirect(url_for('demo_data.manage_demo_data'))

    if request.method == 'POST':
        # Get updated form values
        sex = request.form.get('sex')
        age_group = request.form.get('age_group')
        employment_status = request.form.get('employment_status')
        years_at_school = request.form.get('years_at_school')

        # Validate input
        if not all([sex, age_group, employment_status, years_at_school]):
            flash("All fields are required!", 'danger')
            return redirect(url_for('demo_data.edit_demo_data', demo_data_id=demo_data_id))

        try:
            # Update record in DB
            cursor.execute("""
                UPDATE demo_data 
                SET sex = %s, 
                    age_group = %s, 
                    employment_status = %s, 
                    years_at_school = %s 
                WHERE id = %s
            """, (sex, age_group, employment_status, years_at_school, demo_data_id))
            conn.commit()
            flash("Respondent data updated successfully!", 'success')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')
        finally:
            conn.close()

        return redirect(url_for('demo_data.manage_demo_data'))

    conn.close()
    return render_template('demo_data/edit_demo_data.html',
                           username=session.get('username'),
                           role=session.get('role'),
                           demo_data=demo_data)












def generate_id_number():
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"respondent{suffix}"

@demo_data_bp.route('/add_demo_data', methods=['GET', 'POST'])
def add_demo_data():
    if request.method == 'POST':
        # Retrieve current user_id from the session (assumed to be stored in session)
        user_id = session.get('user_id')  # Ensure your session contains the 'user_id'

        # Check if user is authenticated (optional check)
        if not user_id:
            flash("You must be logged in to add demo data.", 'danger')
            return redirect(url_for('auth.login'))  # Redirect to login page if user is not authenticated

        # Generate ID number for demo data
        id_number = generate_id_number()

        # Retrieve form data
        sex = request.form.get('sex')
        age_group = request.form.get('age_group')
        employment_status = request.form.get('employment_status')
        years_at_school = request.form.get('years_at_school')

        # Check for required fields
        if not all([sex, age_group, employment_status, years_at_school]):
            flash("All fields are required!", 'danger')
            return redirect(url_for('demo_data.add_demo_data'))

        # Insert into database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO demo_data (
                    id_number, sex, age_group, employment_status, years_at_school, user_id
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_number, sex, age_group, employment_status, years_at_school, user_id))

            conn.commit()
            conn.close()

            flash(f"Entry added successfully! ID: {id_number}", 'success')
            return redirect(url_for('demo_data.manage_demo_data'))

        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('demo_data.add_demo_data'))

    # GET request (render form)
    return render_template('demo_data/add_demo_data.html',
                           username=session.get('username'),
                           role=session.get('role'))





# Route to delete a specific demo_data
@demo_data_bp.route('/delete_demo_data/<int:demo_data_id>', methods=['GET'])
def delete_demo_data(demo_data_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if demo_data exists
        cursor.execute("SELECT * FROM demo_data WHERE id = %s", (demo_data_id,))
        demo_data = cursor.fetchone()

        if not demo_data:
            flash("Demo data not found!", 'danger')
            return redirect(url_for('demo_data.manage_demo_data'))

        # Delete the demo_data by ID
        cursor.execute("DELETE FROM demo_data WHERE id = %s", (demo_data_id,))
        conn.commit()

        flash("Demo data deleted successfully!", 'success')

    except Exception as e:
        # Handle any exceptions and errors that occur during the delete operation
        flash(f"An error occurred: {str(e)}", 'danger')
    finally:
        conn.close()

    return redirect(url_for('demo_data.manage_demo_data'))
