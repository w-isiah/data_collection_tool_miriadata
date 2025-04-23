from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session,jsonify
from app.db import get_db_connection
import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from io import BytesIO
from app import app
import mysql.connector  # Ensure the MySQL connector is imported
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
import logging
logging.basicConfig(level=logging.INFO)

# Initialize blueprint
assign_assessor_bp = Blueprint('assign_assessor', __name__)


    

def fetch_programmes_and_terms():
    """Fetch programmes and terms for dropdowns."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, programme_name FROM programmes")
    programmes = cursor.fetchall()
    cursor.execute("SELECT id, term FROM terms")
    terms = cursor.fetchall()
   
    cursor.close()
    conn.close()

    return programmes, terms


















@assign_assessor_bp.route('/manage_students', methods=['GET', 'POST'])
def manage_student():
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
            a.assessor_id IS NOT NULL AS assigned,  -- Assigned status based on presence of assessor in assign_assessor table
            u.username AS assessor_name  -- Assessor's name
        FROM student_info si
        LEFT JOIN programmes p ON si.programme_id = p.id
        LEFT JOIN terms t ON si.term_id = t.id
        LEFT JOIN assign_assessor a ON si.id = a.student_id AND si.term_id = a.term_id  -- Join on both student_id and term_id
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
        return render_template('assign_assessor/manage_student.html', 
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














@assign_assessor_bp.route('/assign_assessor', methods=['GET', 'POST'])
def assign_assessor():
    if request.method == 'POST':
        # Get form data
        assessor_id = request.form.get('assessor')  # Assessor selected
        student_ids = request.form.getlist('student_ids')  # List of selected student IDs
        assigned_by = session['id']  # Current user's ID from session
        
        # Establish a connection to the database
        connection = get_db_connection()
        cursor = connection.cursor()

        # List for collecting flash messages
        flash_messages = []

        try:
            for student_id in student_ids:
                # Get the term_id for the student from the student_info table
                term_query = """
                SELECT term_id FROM student_info WHERE id = %s
                """
                cursor.execute(term_query, (student_id,))
                term_result = cursor.fetchone()

                if term_result is None:
                    # If no term_id is found, skip this student
                    flash_messages.append(f'No term found for student {student_id}, skipping assignment.')
                    continue

                term_id = term_result[0]

                # Check if the student has already been assigned to the same assessor for this term
                check_assignment_query = """
                SELECT * FROM assign_assessor 
                WHERE student_id = %s AND term_id = %s AND assessor_id = %s
                """
                cursor.execute(check_assignment_query, (student_id, term_id, assessor_id))
                existing_assignment = cursor.fetchone()

                if existing_assignment:
                    # If the student is already assigned to this assessor for the same term, skip assignment
                    flash_messages.append(f'Student {student_id} is already assigned to this assessor for this term.')
                    continue
                else:
                    # If the student has not been assigned to this assessor for the term, proceed with assignment
                    insert_query = """
                    INSERT INTO assign_assessor (assessor_id, student_id, assigned_by, term_id)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (assessor_id, student_id, assigned_by, term_id))

            # Commit the transaction
            connection.commit()

            # Flash all messages collected during the loop
            for message in flash_messages:
                flash(message, 'warning' if 'skipping' in message else 'success')

        except mysql.connector.Error as e:
            # Handle any errors that occur during the insertion
            connection.rollback()  # Rollback in case of error
            flash(f'Error assigning assessors: {str(e)}', 'danger')

        finally:
            # Close the cursor and connection
            cursor.close()
            connection.close()

        # Redirect back to the manage students page
        return redirect(url_for('assign_assessor.manage_student'))









@assign_assessor_bp.route('/un_assign_manage_students', methods=['GET', 'POST'])
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
            LEFT JOIN assign_assessor a ON si.id = a.student_id AND si.term_id = a.term_id
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

        return render_template('assign_assessor/unassign_assessor.html',
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














@assign_assessor_bp.route('/unassign_assessor', methods=['POST'])
def unassign_assessor():
    if request.method == 'POST':
        assign_ids = request.form.getlist('assign_ids')  # List of selected assign_ids to un-assign
        
        # Establish a connection to the database
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Loop through the selected assign_ids and delete the corresponding records
            for assign_id in assign_ids:
                delete_assignment_query = """
                DELETE FROM assign_assessor WHERE id = %s
                """
                cursor.execute(delete_assignment_query, (assign_id,))
                flash(f"Assessor unassigned", "success")
                #flash(f"Assessor unassigned from student with ID: {assign_id}", "success")

            # Commit the transaction
            connection.commit()
        
        except mysql.connector.Error as err:
            # Handle MySQL-specific errors
            logging.error(f"MySQL error: {err}")
            connection.rollback()
            flash(f"Error unassigning assessors: {str(err)}", 'danger')

        except Exception as e:
            # Handle other errors
            logging.error(f"Error: {e}")
            connection.rollback()
            flash(f"Error unassigning assessors: {str(e)}", 'danger')

        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('assign_assessor.un_assign_manage_students'))











@assign_assessor_bp.route('/m_manage_students', methods=['GET', 'POST'])
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
            a.assessor_id IS NOT NULL AS assigned,  -- Assigned status based on presence of assessor in assign_assessor table
            u.username AS assessor_name  -- Assessor's name
        FROM student_info si
        LEFT JOIN programmes p ON si.programme_id = p.id
        LEFT JOIN terms t ON si.term_id = t.id
        LEFT JOIN m_assign_assessor a ON si.id = a.student_id AND si.term_id = a.term_id  -- Join on both student_id and term_id
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
        return render_template('assign_assessor/m_assessor_manage_student.html', 
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














@assign_assessor_bp.route('/m_assign_assessor', methods=['GET', 'POST'])
def m_assign_assessor():
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
                SELECT * FROM m_assign_assessor 
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
                    INSERT INTO m_assign_assessor (assessor_id, student_id, assigned_by, term_id)
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
        return redirect(url_for('assign_assessor.m_manage_student'))
