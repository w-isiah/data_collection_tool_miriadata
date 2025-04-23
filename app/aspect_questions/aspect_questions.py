from datetime import timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.db import get_db_connection  # Now importing from the db module
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from psycopg2 import Error
import logging

# Initialize blueprint
aspect_qns_bp = Blueprint('aspect_qns_bp', __name__)
# Initialize the blueprint


@aspect_qns_bp.route('/moderator_view_aspect_questions/<int:id>', methods=['GET', 'POST'])
def moderator_view_aspect_questions(id):
    # Get the database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all records for the given aspect_id
    cursor.execute("SELECT * FROM assessment_criteria WHERE aspect_id = %s", (id,))
    questions = cursor.fetchall()  # This will fetch all the records

    # Close the connection
    conn.close()

    # Pass the questions list to the template
    return render_template('aspect_questions/moderator_aspect_questions.html',username=session['username'],role=session['role'], questions=questions)



@aspect_qns_bp.route('/view_aspect_questions/<int:aspect_id>', methods=['GET', 'POST'])
def view_aspect_questions(aspect_id):
    # Get the database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all records for the given aspect_id
    cursor.execute("SELECT * FROM assessment_criteria WHERE aspect_id = %s", (aspect_id,))
    questions = cursor.fetchall()  # This will fetch all the records

    # Close the connection
    conn.close()

    # Pass the questions list to the template
    return render_template('aspect_questions/aspect_questions.html' ,username=session['username'],role=session['role'],questions=questions)






@aspect_qns_bp.route('/add_aspect_question', methods=['GET', 'POST'])
def add_aspect_question():
    # Establish database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all aspects from the database
    cursor.execute("SELECT * FROM aspect")
    aspects = cursor.fetchall()

    if request.method == 'POST':
        # Get form data
        criteria_name = request.form['criteria_name']
        aspect_id = request.form['aspect_id']

        # Insert new record into the assessment_criteria table
        try:
            cursor.execute("""
                INSERT INTO assessment_criteria (criteria_name, aspect_id)
                VALUES (%s, %s)
            """, (criteria_name, aspect_id))

            # Commit changes to the database
            conn.commit()

            flash('Assessment criteria added successfully!', 'success')
            return redirect(url_for('aspect_qns_bp.add_aspect_question'))

        except Exception as e:
            flash(f"Error: Unable to add the criteria. {str(e)}", 'danger')
            return redirect(url_for('aspect_qns_bp.add_aspect_question'))

    # Close resources
    cursor.close()
    conn.close()

    # Render the form page
    return render_template('aspect_questions/add_aspect_question.html', 
                           username=session['username'], role=session['role'], aspects=aspects)







@aspect_qns_bp.route('/edit_criteria_question/<int:criteria_id>', methods=['GET', 'POST'])
def edit_criteria_question(criteria_id):
    # If the request is GET, fetch the existing data from the database
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM assessment_criteria WHERE criteria_id = %s", (criteria_id,))
        data = cur.fetchone()
        cur.close()

        # If no data found, redirect back or show an error page
        if not data:
            return redirect(url_for('index'))  # Or render an error template

        # Pass the data to the template
        return render_template('aspect_questions/edit_aspect_question.html', username=session['username'],role=session['role'],criteria=data)

    # If the request is POST, update the data in the database
    if request.method == 'POST':
        # Get data from the form
        serial_number = request.form['serial_number']
        criteria_name = request.form['criteria_name']
        aspect_id = request.form['aspect_id']

        # Update the database
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)


        cur.execute("""
            UPDATE assessment_criteria
            SET serial_number = %s, criteria_name = %s, aspect_id = %s
            WHERE criteria_id = %s
        """, (serial_number, criteria_name, aspect_id, criteria_id))
        conn.commit()
        cur.close()
        flash("Record Updated successfully")

        # Redirect to a confirmation page or back to the main page
        return redirect(url_for('aspects.manage_aspects'))  # Or redirect to another page after successful update




@aspect_qns_bp.route('/delete_criteria/<string:get_id>', methods=['POST'])
def delete_criteria(get_id):
    try:
        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Delete the assessment criteria using the criteria_id
        cursor.execute("DELETE FROM assessment_criteria WHERE criteria_id=%s", (get_id,))
        conn.commit()

        # Flash a success message upon successful deletion
        flash('Assessment criteria deleted successfully', 'success')

    except Exception as e:
        # If an error occurs, flash the error message
        flash(f'Error deleting criteria: {e}', 'danger')
    
    finally:
        # Ensure the cursor and connection are closed
        cursor.close()
        conn.close()

    # Redirect back to the criteria list page (or another appropriate page)
    return redirect(url_for('aspect_qns_bp.manage_aspects'))  # Adjust route as needed
