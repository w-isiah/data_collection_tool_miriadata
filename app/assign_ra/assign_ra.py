from datetime import datetime
import os
import random
import string
from io import BytesIO

import pandas as pd
from flask import (
    Flask, Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, send_file
)
from werkzeug.utils import secure_filename

from app import app
from app.db import get_db_connection



import mysql.connector  # Ensure the MySQL connector is imported
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
import logging
logging.basicConfig(level=logging.INFO)

# Initialize blueprint
assign_ra_bp = Blueprint('assign_ra', __name__)
















@assign_ra_bp.route('/manage_districts', methods=['GET'])
def manage_districts():
    try:
        # Connect to the database using a context manager
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # Fetch assessors (School Practice Supervisors)
            assessors_query = """
            SELECT id, username FROM users 
            WHERE role != 'admin' AND role != 'Head of Department'
            """
            cursor.execute(assessors_query)
            assessors = cursor.fetchall()

            # Base query for district information (without conditions)
            query = """
            SELECT 
                d.id AS district_id,
                d.district_name,  
                d.region, 
                d.country, 
                d.created_at,
                a.research_assistant_id IS NOT NULL AS assigned,  -- Assigned status based on presence of research assistant in assign_research_assistant table
                u.username AS assessor_name  -- Assessor's name
            FROM districts d
            LEFT JOIN assign_research_assistant a ON d.id = a.district_id  -- Join to check if district is assigned
            LEFT JOIN users u ON a.research_assistant_id = u.id  -- Join with users to get assessor's name
            """
            cursor.execute(query)
            districts = cursor.fetchall()

        # Ensure session data is present
        if 'username' not in session or 'role' not in session:
            flash("You must be logged in to manage districts.", 'warning')
            return redirect(url_for('auth.login'))

        # Render the manage_districts template with the fetched data
        return render_template('assign_ra/manage_districts.html',
                               users=assessors,
                               username=session['username'], 
                               role=session['role'], 
                               districts=districts)
    
    except Exception as e:
        # Log the error and provide feedback to the user
        print(f"Error occurred: {str(e)}")  # Consider using a logger in production
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))
















@assign_ra_bp.route('/assign_ra', methods=['GET', 'POST'])
def assign_ra():
    # Retrieve the user_id from the session (ensure the user is logged in)
    user_id = session.get('user_id')
    
    if not user_id:
        flash("You must be logged in to add demo data.", 'danger')
        return redirect(url_for('auth.login'))  # Redirect to login page if not logged in

    # Ensure 'id' exists in the session before proceeding
    assigned_by = session.get('id')  # Get the assigned_by value from the session
    if not assigned_by:
        flash("Session 'id' is missing. Please log in again.", 'danger')
        return redirect(url_for('auth.login'))  # Redirect to login if 'id' is missing

    if request.method == 'POST':
        # Extract form data
        research_assistant_id = request.form.get('assessor')  # Assessor is the research assistant id
        district_ids = request.form.getlist('district_ids')

        # Initialize the database connection and cursor
        connection = get_db_connection()
        cursor = connection.cursor()

        flash_messages = []  # Collect flash messages for feedback

        try:
            for district_id in district_ids:
                # Check if RA is already assigned to the district
                check_assignment_query = """
                SELECT * FROM assign_research_assistant
                WHERE research_assistant_id = %s AND district_id = %s
                """
                cursor.execute(check_assignment_query, (research_assistant_id, district_id))
                existing_assignment = cursor.fetchone()

                if existing_assignment:
                    flash_messages.append(f'Research Assistant {research_assistant_id} is already assigned to district {district_id}.')
                    continue  # Skip if already assigned
                else:
                    # Assign RA to district if not already assigned
                    insert_query = """
                    INSERT INTO assign_research_assistant (research_assistant_id, assigned_by, district_id)
                    VALUES (%s, %s, %s)
                    """
                    cursor.execute(insert_query, (research_assistant_id, assigned_by, district_id))
                    flash_messages.append(f'Research Assistant {research_assistant_id} successfully assigned to district {district_id}.')
            
            # Commit changes to the database
            connection.commit()

            # Display appropriate flash messages (warnings for skipped assignments, success for new assignments)
            for message in flash_messages:
                flash(message, 'warning' if 'already assigned' in message else 'success')

        except mysql.connector.Error as e:
            # Handle database errors and rollback the transaction
            connection.rollback()
            flash(f'Error assigning research assistants: {str(e)}', 'danger')

        finally:
            # Close the database cursor and connection
            cursor.close()
            connection.close()

        # Redirect to manage districts page
        return redirect(url_for('assign_ra.manage_districts'))













@assign_ra_bp.route('/un_assign_manage_students', methods=['GET', 'POST'])
def un_assign_manage_students():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        programmes, terms = fetch_programmes_and_terms()

        assessors_query = "SELECT id, username FROM users WHERE role != 'admin' AND role != 'Head of Department'"
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        query = """
            SELECT
                si.id AS student_id,
                si.student_teacher,
                si.reg_no,
                si.subject,
                si.class_name,
                si.topic,
                si.subtopic,
                si.teaching_time,
                p.programme_name,
                p.description AS programme_description,
                t.term AS term,
                t.id AS term_id,
                a.assessor_id IS NOT NULL AS assigned,
                u.username AS assessor_name,
                u.id AS assessor_id,
                a.id AS assign_id
            FROM student_info si
            LEFT JOIN programmes p ON si.programme_id = p.id
            LEFT JOIN terms t ON si.term_id = t.id
            LEFT JOIN assign_ra a ON si.id = a.student_id AND si.term_id = a.term_id
            LEFT JOIN users u ON a.assessor_id = u.id
            WHERE a.assessor_id IS NOT NULL  -- This condition ensures that only students with an assessor assigned are included
        """

        params = []
        student_info = []

        if request.method == 'POST':
            conditions = []

            if programme := request.form.get('programme'):
                conditions.append("si.programme_id = %s")
                params.append(programme)

            if term := request.form.get('term'):
                conditions.append("si.term_id = %s")
                params.append(term)

            if reg_no := request.form.get('reg_no'):
                conditions.append("si.reg_no LIKE %s")
                params.append(f"%{reg_no}%")

            if conditions:
                query += " AND " + " AND ".join(conditions)  # Adjusted query with additional conditions
                cursor.execute(query, params)
                student_info = cursor.fetchall()
        else:
            cursor.execute(query, params)
            student_info = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('assign_ra/unassign_ra.html',
                               username=session['username'],
                               role=session['role'],
                               students=student_info,  # Corrected variable name
                               programmes=programmes,
                               terms=terms,
                               assessors=assessors)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))














@assign_ra_bp.route('/unassign_ra', methods=['POST'])
def unassign_ra():
    if request.method == 'POST':
        district_ids = request.form.getlist('district_ids')  # List of selected district IDs to unassign

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Loop through the selected district_ids and delete assignments
            for district_id in district_ids:
                delete_query = """
                DELETE FROM assign_research_assistant 
                WHERE district_id = %s
                """
                cursor.execute(delete_query, (district_id,))
                flash(f"Research Assistant unassigned from District ID {district_id}", "success")

            connection.commit()

        except mysql.connector.Error as err:
            logging.error(f"MySQL error: {err}")
            connection.rollback()
            flash(f"MySQL error while unassigning: {str(err)}", 'danger')

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            connection.rollback()
            flash(f"Error occurred while unassigning: {str(e)}", 'danger')

        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('assign_ra.manage_assigned_districts'))  # Replace with your actual view name












@assign_ra_bp.route('/m_manage_students', methods=['GET', 'POST'])
def m_manage_student():
    try:
        # Database connection and fetching programmes and terms
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        programmes, terms = fetch_programmes_and_terms()

        # Fetch assessors
        assessors_query = "SELECT id, username FROM users WHERE role != 'admin' AND role != 'Head of Department'"
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        # Base query for student information (without conditions)
        query = """
        SELECT 
            si.id AS student_id,
            si.student_teacher,  
            si.reg_no, 
            si.subject,
            si.class_name, 
            si.topic, 
            si.subtopic, 
            si.teaching_time,
            p.programme_name, 
            p.description AS programme_description,
            t.term AS term,
            t.id AS term_id,
            a.assessor_id IS NOT NULL AS assigned,  -- Assigned status based on presence of assessor in assign_ra table
            u.username AS assessor_name  -- Assessor's name
        FROM student_info si
        LEFT JOIN programmes p ON si.programme_id = p.id
        LEFT JOIN terms t ON si.term_id = t.id
        LEFT JOIN m_assign_ra a ON si.id = a.student_id AND si.term_id = a.term_id  -- Join on both student_id and term_id
        LEFT JOIN users u ON a.assessor_id = u.id  -- Join with users to get assessor name
        """

        params = []
        student_info = []

        # Handle dynamic filtering based on POST request
        if request.method == 'POST':
            conditions = []

            # Apply filtering based on front-end form values
            if programme := request.form.get('programme'):
                conditions.append("si.programme_id = %s")
                params.append(programme)
            
            if term := request.form.get('term'):
                conditions.append("si.term_id = %s")
                params.append(term)

            # Add filtering by registration number (Reg No)
            if reg_no := request.form.get('reg_no'):
                conditions.append("si.reg_no LIKE %s")
                params.append(f"%{reg_no}%")

            # If there are any conditions, apply them to the query
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                cursor.execute(query, params)
                student_info = cursor.fetchall()

        # Always close the connection after the query is executed
        cursor.close()
        conn.close()

        # Pass the filtered student information to the template
        return render_template('assign_ra/m_assessor_manage_student.html', 
                               username=session['username'], 
                               role=session['role'],
                               student_info=student_info, 
                               programmes=programmes, 
                               terms=terms,
                               assessors=assessors)

    except Exception as e:
        # Log the error and provide feedback to the user
        print(f"Error occurred: {str(e)}")  # For debugging
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))














@assign_ra_bp.route('/m_assign_ra', methods=['GET', 'POST'])
def m_assign_ra():
    if request.method == 'POST':
        # Get form data
        assessor_id = request.form.get('assessor')  # Assessor selected
        student_ids = request.form.getlist('student_ids')  # List of selected student IDs
        assigned_by = session['id']  # Current user's ID from session
        
        # Establish a connection to the database
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            for student_id in student_ids:
                # Get the term_id for the student from the student_info table
                term_query = """
                SELECT term_id FROM student_info WHERE id = %s
                """
                cursor.execute(term_query, (student_id,))
                term_result = cursor.fetchone()

                if term_result:
                    term_id = term_result[0]
                else:
                    # If no term_id is found, skip this student
                    flash(f'No term found for student {student_id}, skipping assignment.', 'warning')
                    continue

                # Check if the student has already been assigned to the same assessor for this term
                check_assignment_query = """
                SELECT * FROM m_assign_ra 
                WHERE student_id = %s AND term_id = %s AND assessor_id = %s
                """
                cursor.execute(check_assignment_query, (student_id, term_id, assessor_id))
                existing_assignment = cursor.fetchone()

                if existing_assignment:
                    # If the student is already assigned to this assessor for the same term, skip assignment
                    flash(f'Student {student_id} is already assigned to this assessor for this term.', 'warning')
                    continue
                else:
                    # If the student has not been assigned to this assessor for the term, proceed with assignment
                    insert_query = """
                    INSERT INTO m_assign_ra (assessor_id, student_id, assigned_by, term_id)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (assessor_id, student_id, assigned_by, term_id))

            # Commit the transaction
            connection.commit()

            # Provide a success message
            flash('Assessors successfully assigned!', 'success')

        except mysql.connector.Error as e:
            # Handle any errors that occur during the insertion
            connection.rollback()  # Rollback in case of error
            flash(f'Error assigning assessors: {str(e)}', 'danger')

        finally:
            # Close the cursor and connection
            cursor.close()
            connection.close()

        # Redirect back to the manage students page
        return redirect(url_for('assign_ra.m_manage_student'))
