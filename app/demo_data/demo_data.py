from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
import random
import string
import logging

demo_data_bp = Blueprint('demo_data', __name__)








@demo_data_bp.route('/manage_demo_data', methods=['GET'])
def manage_demo_data():
    role0 = session.get('role')
    
    if not role0:
        flash("Role is missing in session, please log in again.", "warning")
        return redirect(url_for('main.index'))

    try:
        # Get session information
        user_id = session.get('user_id')
        username = session.get('username', 'Guest')
        role = session.get('role', 'User')

        if not user_id:
            flash("User ID is missing. Please log in.", "warning")
            return redirect(url_for('main.index'))

        # Fetch demo data and district name for the logged-in user
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT 
                        demo_data.*, 
                        scores.marks_scores_sku,
                        users.username,
                        districts.district_name,
                        CASE 
                            WHEN scores.demo_data_id IS NOT NULL THEN 'Assessed'
                            ELSE 'Unassessed'
                        END AS assessment_status,
                        users.first_name,
                        users.last_name
                    FROM demo_data
                    LEFT JOIN users ON demo_data.user_id = users.id
                    LEFT JOIN scores ON demo_data.id = scores.demo_data_id
                    LEFT JOIN districts 
                        ON demo_data.district_id = districts.id
                    WHERE demo_data.user_id = %s
                    GROUP BY demo_data.id
                    ORDER BY demo_data.created_at
                """, (user_id,))
                demo_data = cursor.fetchall()

        # Render the appropriate template based on role
        if role0 == "Principal_Investigator":
            return render_template(
                'demo_data/manage_demo_data.html',
                username=username,
                role=role,
                demo_data=demo_data
            )
        elif role0 == "Research_Assistant":
            return render_template(
                'demo_data/assessor_manage_demo_data.html',
                username=username,
                role=role,
                demo_data=demo_data
            )
        else:
            flash("Unauthorized role access.", "warning")
            return redirect(url_for('main.index'))

    except Exception as e:
        logging.exception("Error in manage_demo_data")  # Log the full traceback
        flash(f"An error occurred while fetching respondent data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))













@demo_data_bp.route('/edit_demo_data/<int:demo_data_id>', methods=['GET', 'POST'])
def edit_demo_data(demo_data_id):
    role0 = session.get('role')
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
    if role0 == "Principal_Investigator":
        return render_template('demo_data/edit_demo_data.html',
                               username=session.get('username'),
                               role=session.get('role'),
                               demo_data=demo_data)
    elif role0 == "School Practice Supervisor":
        return render_template('demo_data/assessor_edit_demo_data.html',
                               username=session.get('username'),
                               role=session.get('role'),
                               demo_data=demo_data)














def generate_id_number():
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"teacher{suffix}"







@demo_data_bp.route('/add_demo_data', methods=['GET', 'POST'])
def add_demo_data():
    role0 = session.get('role')
    user_id = session.get('user_id')

    # Check if user_id exists in session
    if not user_id:
        flash("You must be logged in to add demo data.", 'danger')
        return redirect(url_for('auth.login'))  # Or whatever the login route is

    # Fetch districts based on user role
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT d.id, d.district_name
                FROM assign_research_assistant a
                INNER JOIN districts d ON a.district_id = d.id 
                WHERE a.research_assistant_id = %s
            """, (user_id,))
            districts = cursor.fetchall()  # Fetch all districts for the user
            if not districts:
                flash("No districts found for your role.", 'warning')
            print(districts)
    except Exception as e:
        app.logger.error(f"Error fetching districts: {str(e)}")
        flash("An error occurred while fetching districts.", 'danger')
        return redirect(url_for('demo_data.add_demo_data'))

    if request.method == 'POST':
        # Retrieve form data
        sex = request.form.get('sex')
        age_group = request.form.get('age_group')
        employment_status = request.form.get('employment_status')
        years_at_school = request.form.get('years_at_school')
        district_id = request.form.get('district_id')  # Retrieve selected district_id

        # Validate required fields
        if not all([sex, age_group, employment_status, years_at_school, district_id]):
            flash("All fields are required!", 'danger')
            return redirect(url_for('demo_data.add_demo_data'))

        # Generate ID number for demo data
        id_number = generate_id_number()

        # Insert demo data into the database
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    INSERT INTO demo_data (
                        id_number, sex, age_group, employment_status, years_at_school, user_id, district_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (id_number, sex, age_group, employment_status, years_at_school, user_id, district_id))

                conn.commit()

            flash(f"Entry added successfully! ID: {id_number}", 'success')
            return redirect(url_for('demo_data.manage_demo_data'))

        except Exception as e:
            app.logger.error(f"Error inserting demo data: {str(e)}")
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('demo_data.add_demo_data'))

    # Render templates based on role
    if role0 == "Principal_Investigator":
        return render_template('demo_data/add_demo_data.html',
                               username=session.get('username'),
                               role=session.get('role'),
                               districts=districts)
    elif role0 == "Research_Assistant":
        return render_template('demo_data/assessor_add_demo_data.html',
                               username=session.get('username'),
                               role=session.get('role'),
                               districts=districts)
    else:
        flash("Invalid role. You do not have permission to add demo data.", 'danger')
        return redirect(url_for('home'))  # Redirect to a home or permission denied page








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
