from datetime import timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.db import get_db_connection  # Now importing from the db module
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from psycopg2 import Error
import pandas as pd
from flask import send_file
import io
import logging
# Initialize blueprint
d_f_assessment_bp = Blueprint('d_f_assessment', __name__)

# Assessment check route - for viewing the status of assessments for students
@d_f_assessment_bp.route('/assessment_check')
def assessment_check():


    # Get the logged-in user's ID (assessor)
    
    username=session['username']
    role0=session['role']
    role2='School Practice Supervisor'
    role1='Head OF Deaprtment'
    assessor_id = session.get('id')
    
    if not assessor_id:
        return redirect(url_for('auth.login'))  # Redirect to login page if not authenticated

    query = """
    SELECT s.id AS student_id,
           s.student_teacher,
           s.year,
           s.programme_id,
           s.reg_no,
           s.subject,
           s.term_id,
           s.class_name,
           s.topic,
           s.subtopic,
           s.teaching_time,
           IF(sc.assessor_id = %s, 'assessed', 'unassessed') AS status
    FROM student_info s
    LEFT JOIN scores sc ON s.id = sc.student_id
    GROUP BY s.id, s.student_teacher, s.year, s.programme_id, s.reg_no, s.subject,
             s.term_id, s.class_name, s.topic, s.subtopic, s.teaching_time
    """
    
    try:
        # Use context manager to handle connection and cursor to prevent leakage
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, (assessor_id,))
                data = cursor.fetchall()  # Fetch all assessment data
    except Exception as e:
        # Log error and show a friendly message
        current_app.logger.error(f"Error fetching assessment data: {e}")
        return render_template('error.html', message="An error occurred while retrieving data.")
    if role0==role1:
        return render_template('assessment_v1/assessment_check.html', data=data)
    elif role0==role2:
        return render_template('assessment_v1/assessor/assessment_check.html', data=data)











@d_f_assessment_bp.route('/check_student', methods=['GET', 'POST'])
def check_student():
    role = session.get('role')  # Get the logged-in user's role
    user_id = session.get('id')  # Get the logged-in user's ID

    if not user_id:
        return redirect(url_for('login'))  # Redirect if the user is not logged in

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            reg_no = request.form.get('reg_no')  # Get registration number from form input

            # Fetch student details from the student_info table
            cursor.execute("SELECT * FROM student_info WHERE reg_no = %s", (reg_no,))
            student = cursor.fetchone()

            if not student:
                message = "No student found with the given registration number."
                return render_template('student_assessment/check_student_2.html', role=role, message=message)

            # Fetch student marks ONLY for the logged-in assessor
            cursor.execute("""
                SELECT * FROM marks 
                WHERE student_id = %s AND assessor_id = %s
            """, (student['id'], user_id))  # Filter by assessor_id
            student_marks = cursor.fetchall()

            # Get term IDs from student_info for the student
            cursor.execute("SELECT DISTINCT term_id FROM student_info WHERE reg_no = %s", (reg_no,))
            student_terms = cursor.fetchall()
            student_term_ids = [term['term_id'] for term in student_terms]

            # If no marks are found, mark the student as "Not Assessed"
            if not student_marks:
                message = "Student has not been assessed yet. Please assess them."
                return render_template('student_assessment/check_student_2.html', username=session['username'], role=role, student=student, message=message)

            # Prepare results for each term (fetch term and marks)
            results = []
            all_term_ids = sorted(set(student_term_ids + [mark['term_id'] for mark in student_marks]))  # All unique term IDs (from student_info and marks)

            for term in all_term_ids:
                result = {
                    'term_id': term,
                    'message': 'Not Assessed',  # Default message
                    'marks': None  # Initially, marks are None if not assessed
                }

                # Find matching mark for each term
                for mark in student_marks:
                    if mark['term_id'] == term:
                        result['marks'] = mark['marks']
                        result['assessment_type'] = mark['assessment_type']
                        result['date_awarded'] = mark['date_awarded']
                        result['message'] = 'Assessed'  # Mark as assessed if marks exist
                        break

                results.append(result)

            return render_template('student_assessment/check_student_2.html', username=session['username'], role=role, student=student, results=results)

        # Handle GET requests (show the initial form)
        return render_template('student_assessment/check_student_2.html', username=session['username'], role=role)

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        flash("An error occurred while processing the request.", "danger")
        return render_template('student_assessment/check_student_2.html', username=session['username'], role=role)

    finally:
        cursor.close()
        connection.close()













@d_f_assessment_bp.route('/check_student_v1/<string:reg_no>', methods=['GET', 'POST'])
def check_student_v1(reg_no):
    role = session.get('role')  # Get logged-in user's role
    user_id = session.get('id')  # Get logged-in user's ID

    # Redirect if user is not logged in
    if not user_id:
        return redirect(url_for('login'))

    # Establish a database connection
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            # Get registration number from the form input (if POST request)
            reg_no = request.form.get('reg_no')

            # Fetch student details from the database
            cursor.execute("SELECT * FROM student_info WHERE reg_no = %s", (reg_no,))
            student = cursor.fetchone()

            if not student:
                message = "No student found with the given registration number."
                template = 'student_assessment/check_student_2.html' if role == 'Head of Department' else 'student_assessment/assessor/check_student_2.html'
                return render_template(template, role=role, message=message)

            # Fetch student's marks for the logged-in assessor
            cursor.execute("""
                SELECT * FROM marks 
                WHERE student_id = %s AND assessor_id = %s
            """, (student['id'], user_id))
            student_marks = cursor.fetchall()

            # Get terms from student_info table (for student)
            cursor.execute("SELECT DISTINCT term_id FROM student_info WHERE reg_no = %s", (reg_no,))
            student_terms = cursor.fetchall()
            student_term_ids = [term['term_id'] for term in student_terms]

            # If no marks are found, inform the user
            if not student_marks:
                message = "Student has not been assessed yet. Please assess them."
                template = 'student_assessment/check_student_2.html' if role == 'Head of Department' else 'student_assessment/assessor/check_student_2.html'
                return render_template(template, username=session['username'], role=role, student=student, message=message)

            # Prepare results for each term
            results = []
            all_term_ids = sorted(set(student_term_ids + [mark['term_id'] for mark in student_marks]))

            for term in all_term_ids:
                result = {
                    'term_id': term,
                    'message': 'Not Assessed',
                    'marks': None
                }

                for mark in student_marks:
                    if mark['term_id'] == term:
                        result.update({
                            'marks': mark['marks'],
                            'assessment_type': mark['assessment_type'],
                            'date_awarded': mark['date_awarded'],
                            'message': 'Assessed'
                        })
                        break

                results.append(result)

            # Render template based on user role
            template = 'student_assessment/check_student_2.html' if role == 'Head of Department' else 'student_assessment/assessor/check_student_2.html'
            return render_template(template, username=session['username'], role=role, student=student, results=results)

        else:
            # Handle GET request (render form initially)
            template = 'student_assessment/check_student_2.html' if role == 'Head of Department' else 'student_assessment/assessor/check_student_2.html'
            return render_template(template, username=session['username'], role=role)

    except Exception as e:
        logging.error(f"Error occurred while processing request for {reg_no}: {e}")
        flash("An error occurred while processing the request.", "danger")
        template = 'student_assessment/check_student_2.html' if role == 'Head of Department' else 'student_assessment/assessor/check_student_2.html'
        return render_template(template, username=session['username'], role=role)

    finally:
        cursor.close()
        connection.close()














@d_f_assessment_bp.route('/assess_v1/<int:student_id>', methods=['GET', 'POST'])
def assess_v1(student_id):
    # Get session details
    role = session.get('role')
    assessor_id = session.get('id')

    # If role or ID is missing from session, redirect to login or show error
    if not role or not assessor_id:
        return redirect(url_for('login'))  # Or return an error message
    
    # Establish a database connection
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Fetch student data
        cursor.execute("SELECT * FROM student_info WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        # Check if the student exists
        if not student:
            return f"Student with ID {student_id} not found", 404

        # Fetch schools data
        cursor.execute("SELECT * FROM schools")
        schools = cursor.fetchall()

    except Exception as e:
        # Handle database errors (if any)
        return f"An error occurred while fetching data: {str(e)}", 500

    finally:
        # Ensure resources are closed after execution
        cursor.close()
        connection.close()

    # Render the appropriate template based on user role
    template = 'd_f_assessment_v1/add_assessment.html' if role == 'Head of Department' else 'd_f_assessment_v1/assessor/add_assessment.html'
    return render_template(template,
                           schools=schools,
                           username=session.get('username'),
                           role=role,
                           student_id=student_id,
                           assessor_id=assessor_id,
                           student=student)


































@d_f_assessment_bp.route('/assessment_report', methods=['GET', 'POST'])
def assessment_report():
    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch Programmes and Terms for filters
        cursor.execute("SELECT id, programme_name FROM programmes")
        programmes = cursor.fetchall()

        cursor.execute("SELECT id, term, year FROM terms ORDER BY term")
        terms = cursor.fetchall()

        # Initialize variables
        pivot_data = []  # Initialize an empty list for pivoted data
        assessors = []   # List of assessors
        programme_id = None
        term_id = None
        reg_no = None

        if request.method == 'POST':
            # Get filter values from the form
            programme_id = request.form.get('programme_id')
            term_id = request.form.get('term_id')
            reg_no = request.form.get('reg_no')

            # SQL query to fetch assessment data from 'marks' table, joining with 'student_info' and 'terms'
            query = """
                SELECT
                    si.id AS student_id,
                    si.reg_no,
                    si.student_teacher AS student_name,
                    si.subject,
                    t.term,
                    m.term_id AS marks_term_id,  -- Use the term_id from marks table
                    u.username AS assessor,
                    m.marks AS total_marks,
                    CASE
                        WHEN m.marks IS NULL THEN 'Not Assessed'
                        ELSE 'Assessed'
                    END AS status
                FROM
                    student_info si
                INNER JOIN
                    marks m ON si.id = m.student_id AND m.term_id = %s  -- Ensure student has marks for the selected term
                LEFT JOIN
                    users u ON m.assessor_id = u.id
                LEFT JOIN
                    terms t ON m.term_id = t.id  -- Ensure correct term from marks table
                WHERE 1=1
            """

            # Add filters dynamically based on user input
            filters = [term_id]  # The selected term_id is added to filters to be used in the query
            if programme_id:
                query += " AND si.programme_id = %s"
                filters.append(programme_id)
            if reg_no:
                query += " AND si.reg_no LIKE %s"
                filters.append(f"%{reg_no}%")

            # Finalize query with ordering by student registration number
            query += """
                ORDER BY si.reg_no
            """

            # Execute the query with the appropriate filters
            cursor.execute(query, tuple(filters))
            data = cursor.fetchall()

            if data:
                # Data is not empty, proceed with pivoting
                df = pd.DataFrame(data)

                # Extract unique assessors
                assessors = df['assessor'].dropna().unique().tolist()

                # Pivot data: assessors as columns
                pivot_table = df.pivot_table(
                    index=["reg_no", "student_name", "subject", "term", "status", "marks_term_id"],  # Correctly using marks_term_id
                    columns="assessor",
                    values="total_marks",
                    aggfunc="max",
                    fill_value=0
                ).reset_index()

                # Add average score for each student
                score_columns = [
                    col for col in pivot_table.columns
                    if col not in ['reg_no', 'student_name', 'subject', 'term', 'status', 'marks_term_id']
                ]
                pivot_table['average_marks'] = pivot_table[score_columns].replace(0, pd.NA).mean(axis=1)

                # Convert pivot table to dictionary for front-end
                pivot_data = pivot_table.to_dict(orient="records")

                # Flash success message after successful data fetching
                flash('Assessment data fetched successfully!', 'success')

            else:
                # Flash message if no data is found
                flash('No data found for the given filters.', 'warning')

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Render the template with flash messages
    return render_template(
        'assessment_v1/assessment_report.html',
        role=session.get('role'),
        username=session.get('username'),
        programmes=programmes,
        terms=terms,
        data=pivot_data,
        assessors=assessors,
        programme_id=programme_id,
        term_id=term_id,
        reg_no=reg_no
    )





















@d_f_assessment_bp.route('/modulate_assessment_report', methods=['GET', 'POST'])
def modulate_assessment_report():
    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch Programmes and Terms for filters
        cursor.execute("SELECT id, programme_name FROM programmes")
        programmes = cursor.fetchall()

        cursor.execute("SELECT id, term, year FROM terms ORDER BY term")
        terms = cursor.fetchall()

        # Initialize variables
        pivot_data = []  # Initialize an empty list for pivoted data
        assessors = []   # List of assessors
        programme_id = None
        term_id = None
        reg_no = None

        if request.method == 'POST':
            # Get filter values from the form
            programme_id = request.form.get('programme_id')
            term_id = request.form.get('term_id')
            reg_no = request.form.get('reg_no')

            # SQL query to fetch assessment data from 'marks' table, joining with 'student_info' and 'terms'
            query = """
                SELECT
                    si.id AS student_id,
                    si.reg_no,
                    si.student_teacher AS student_name,
                    si.subject,
                    t.term,
                    m.term_id AS marks_term_id,  -- Use the term_id from marks table
                    u.username AS assessor,
                    m.marks AS total_marks,
                    CASE
                        WHEN m.marks IS NULL THEN 'Not Assessed'
                        ELSE 'Assessed'
                    END AS status
                FROM
                    student_info si
                INNER JOIN
                   mudulate_marks m ON si.id = m.student_id AND m.term_id = %s  -- Ensure student has marks for the selected term
                LEFT JOIN
                    users u ON m.assessor_id = u.id
                LEFT JOIN
                    terms t ON m.term_id = t.id  -- Ensure correct term from marks table
                WHERE 1=1
            """

            # Add filters dynamically based on user input
            filters = [term_id]  # The selected term_id is added to filters to be used in the query
            if programme_id:
                query += " AND si.programme_id = %s"
                filters.append(programme_id)
            if reg_no:
                query += " AND si.reg_no LIKE %s"
                filters.append(f"%{reg_no}%")

            # Finalize query with ordering by student registration number
            query += """
                ORDER BY si.reg_no
            """

            # Execute the query with the appropriate filters
            cursor.execute(query, tuple(filters))
            data = cursor.fetchall()

            if data:
                # Data is not empty, proceed with pivoting
                df = pd.DataFrame(data)

                # Extract unique assessors
                assessors = df['assessor'].dropna().unique().tolist()

                # Pivot data: assessors as columns
                pivot_table = df.pivot_table(
                    index=["reg_no", "student_name", "subject", "term", "status", "marks_term_id"],  # Correctly using marks_term_id
                    columns="assessor",
                    values="total_marks",
                    aggfunc="max",
                    fill_value=0
                ).reset_index()

                # Add average score for each student
                score_columns = [
                    col for col in pivot_table.columns
                    if col not in ['reg_no', 'student_name', 'subject', 'term', 'status', 'marks_term_id']
                ]
                pivot_table['average_marks'] = pivot_table[score_columns].replace(0, pd.NA).mean(axis=1)

                # Convert pivot table to dictionary for front-end
                pivot_data = pivot_table.to_dict(orient="records")

                # Flash success message after successful data fetching
                flash('Assessment data fetched successfully!', 'success')

            else:
                # Flash message if no data is found
                flash('No data found for the given filters.', 'warning')

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Render the template with flash messages
    return render_template(
        'assessment_v1/modulate_assessment_report.html',
        role=session.get('role'),
        username=session.get('username'),
        programmes=programmes,
        terms=terms,
        data=pivot_data,
        assessors=assessors,
        programme_id=programme_id,
        term_id=term_id,
        reg_no=reg_no
    )


