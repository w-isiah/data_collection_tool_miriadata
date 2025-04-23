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
# Initialize blueprint
d_f_assign_assessor_bp = Blueprint('d_f_assign_assessor', __name__)


    

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


















@d_f_assign_assessor_bp.route('/manage_students', methods=['GET', 'POST'])
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
        return render_template('d_f_assign_assessor/manage_student.html', 
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














@d_f_assign_assessor_bp.route('/assign_assessor', methods=['GET', 'POST'])
def assign_assessor():
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
                SELECT * FROM assign_assessor 
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
                    INSERT INTO assign_assessor (assessor_id, student_id, assigned_by, term_id)
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
        return redirect(url_for('assign_assessor.manage_student'))













@d_f_assign_assessor_bp.route('/m_manage_students', methods=['GET', 'POST'])
def m_manage_student():
    try:
        # Database connection and fetching terms and schools
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()  # Fetching only terms now

        # Fetch assessors
        assessors_query = "SELECT id, username FROM users WHERE role != 'admin' AND role != 'Head of Department'"
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        cursor.execute("SELECT id, name FROM schools")
        schools = cursor.fetchall()

        # Base query without filters
        query = """
        SELECT 
            t.term AS term,
            IF(d.school_id IS NOT NULL, TRUE, FALSE) AS assigned,  -- If the school_id exists in d_assign_assessor, it's assigned, otherwise not assigned
            u.username AS assessor_name,  -- Assessor's name (null if no assignment)
            s.name AS school_name,  -- School name from schools table
            s.id AS school_id,  -- School id from schools table
            IF(d.school_id IS NULL, 'Not Assessed', 'Assigned') AS assessment_status  -- 'Not Assessed' if no record in d_assign_assessor, else 'Assigned'
        FROM schools s
        LEFT JOIN d_assign_assessor d ON s.id = d.school_id  -- Left join to include all schools, even those not assigned
        LEFT JOIN terms t ON d.term_id = t.id  -- Join with terms based on term_id, note some schools may not have a term assigned
        LEFT JOIN users u ON d.assessor_id = u.id  -- Join with users to get assessor name, null if not assigned
        """
        
        params = []
        result_list = []

        # Handle dynamic filtering based on POST request
        if request.method == 'POST':
            conditions = []

            # Get the form values
            term = request.form.get('term')
            school = request.form.get('school')

            # Validation: Ensure both term and school are selected
            if not term or not school:
                flash("Please select both a term and a school to filter.", 'danger')
                return redirect(url_for('d_f_assign_assessor.m_manage_student'))  # Redirect back to the same page with the message

            # Apply filtering based on selected term and school
            if term:
                conditions.append("d.term_id = %s")  # Adjusted to d_assign_assessor's term_id
                params.append(term)

            if school:
                conditions.append("d.school_id = %s")  # Adjusted to d_assign_assessor's school_id
                params.append(school)

            # If both conditions are selected, apply them to the query using AND
            if conditions:
                query += " WHERE " + " AND ".join(conditions)  # Ensure both filters are applied

        # Execute the query with both filters
        cursor.execute(query, params)
        result_list = cursor.fetchall()

        # Always close the connection after the query is executed
        cursor.close()
        conn.close()

        # Pass the filtered data (or all data if no filters) to the template
        return render_template('d_f_assign_assessor/m_assessor_manage_student.html', 
                               username=session['username'], 
                               role=session['role'],
                               result_list=result_list,  # Renamed to result_list since student info is removed
                               terms=terms,
                               schools=schools,
                               assessors=assessors)

    except Exception as e:
        # Log the error and provide feedback to the user
        print(f"Error occurred: {str(e)}")  # For debugging
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))














 














@d_f_assign_assessor_bp.route('/m_assign_assessor', methods=['GET', 'POST'])
def m_assign_assessor():
    if request.method == 'POST':
        # Get form data
        assessor_id = request.form.get('assessor')
        school_ids = request.form.getlist('school_ids')
        assigned_by = session['id']
        term_id = request.form.get('term_id')  # Assuming term_id is passed in the form
        
        # Validate form data
        if not assessor_id or not school_ids or not term_id:
            flash('Please select an assessor, at least one school, and a term.', 'warning')
            return redirect(url_for('d_f_assign_assessor.m_manage_student'))

        # Establish a connection to the database
        connection = get_db_connection()

        # Flag to check if any assignment was successful
        any_assignment_successful = False

        try:
            with connection.cursor() as cursor:
                for school_id in school_ids:
                    # Check if the assessor is already assigned to this school and term
                    cursor.execute("""
                        SELECT * FROM d_assign_assessor 
                        WHERE school_id = %s AND term_id = %s AND assessor_id = %s
                    """, (school_id, term_id, assessor_id))
                    existing_assignment = cursor.fetchone()

                    if existing_assignment:
                        # If the assignment already exists, flash a warning message and skip this school
                        flash(f'Assessor {assessor_id} is already assigned to school {school_id} for this term.', 'warning')
                        continue  # Skip this school if the assessor is already assigned

                    # Proceed with assignment if no existing assignment
                    cursor.execute("""
                        INSERT INTO d_assign_assessor (assessor_id, assigned_by, term_id, school_id)
                        VALUES (%s, %s, %s, %s)
                    """, (assessor_id, assigned_by, term_id, school_id))
                    any_assignment_successful = True  # Mark that we did an assignment

            # Commit the transaction only if there was at least one successful assignment
            if any_assignment_successful:
                connection.commit()
                flash('Assessors successfully assigned!', 'success')
            else:
                # No assignments were successful, so no success message
                flash('No new assignments were made. Please check the existing assignments.', 'info')

        except mysql.connector.Error as e:
            # Rollback in case of error
            connection.rollback()
            flash(f'Error assigning assessors: {str(e)}', 'danger')

        finally:
            # Close connection
            connection.close()

        return redirect(url_for('d_f_assign_assessor.m_manage_student'))














@d_f_assign_assessor_bp.route('/internal_m_manage_students', methods=['GET', 'POST'])
def internal_m_manage_student():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()

        assessors_query = "SELECT id, a_internal_role, username FROM users WHERE role != 'admin' AND role != 'Head of Department' AND  a_internal_role = 1 "
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        cursor.execute("SELECT id, name FROM schools")
        schools = cursor.fetchall()

        query = """
        SELECT 
            t.term AS term,
            IF(d.school_id IS NOT NULL, TRUE, FALSE) AS assigned,
            u.username AS assessor_name,
            s.name AS school_name,
            s.id AS school_id,
            IF(d.school_id IS NULL, 'Not Assessed', 'Assigned') AS assessment_status
        FROM schools s
        LEFT JOIN d_internal_assign_assessor  d ON s.id = d.school_id
        LEFT JOIN terms t ON d.term_id = t.id
        LEFT JOIN users u ON d.assessor_id = u.id
        """

        params = []
        conditions = []

        if request.method == 'POST':
            term = request.form.get('term')
            school = request.form.get('school')

            if term:
                conditions.append("d.term_id = %s")
                params.append(term)

            if school:
                conditions.append("d.school_id = %s")
                params.append(school)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        cursor.execute(query, params)
        result_list = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('d_f_assign_assessor/i_m_assessor_manage_student.html',
                               username=session['username'],
                               role=session['role'],
                               result_list=result_list,
                               terms=terms,
                               schools=schools,
                               assessors=assessors)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))






@d_f_assign_assessor_bp.route('/internal_m_assign_assessor', methods=['GET', 'POST'])
def internal_m_assign_assessor():
    if request.method == 'POST':
        # Get form data
        assessor_id = request.form.get('assessor')
        school_ids = request.form.getlist('school_ids')
        assigned_by = session['id']
        term_id = request.form.get('term_id')  # Assuming term_id is passed in the form
        
        # Validate form data
        if not assessor_id or not school_ids or not term_id:
            flash('Please select an assessor, at least one school, and a term.', 'warning')
            return redirect(url_for('d_f_assign_assessor.internal_m_manage_students'))
        
        if not school_ids:
            flash('Please select at least one school.', 'warning')
            return redirect(url_for('d_f_assign_assessor.internal_m_manage_students'))

        # Establish a connection to the database
        connection = get_db_connection()

        # Flag to check if any assignment was successful
        any_assignment_successful = False

        try:
            with connection.cursor() as cursor:
                for school_id in school_ids:
                    # Check if the assessor is already assigned to this school and term
                    cursor.execute("""
                        SELECT * FROM d_internal_assign_assessor 
                        WHERE school_id = %s AND term_id = %s AND assessor_id = %s
                    """, (school_id, term_id, assessor_id))
                    existing_assignment = cursor.fetchone()

                    if existing_assignment:
                        # If the assignment already exists, flash a warning message and skip this school
                        flash(f'Assessor {assessor_id} is already assigned to school {school_id} for this term.', 'warning')
                        continue  # Skip this school if the assessor is already assigned

                    # Proceed with assignment if no existing assignment
                    cursor.execute("""
                        INSERT INTO d_internal_assign_assessor (assessor_id, assigned_by, term_id, school_id)
                        VALUES (%s, %s, %s, %s)
                    """, (assessor_id, assigned_by, term_id, school_id))
                    any_assignment_successful = True  # Mark that we did an assignment

            # Commit the transaction only if there was at least one successful assignment
            if any_assignment_successful:
                connection.commit()
                flash('Assessors successfully assigned!', 'success')
            else:
                # No assignments were successful, so no success message
                flash('No new assignments were made. Please check the existing assignments.', 'info')

        except mysql.connector.Error as e:
            # Rollback in case of error
            connection.rollback()
            flash(f'Error assigning assessors: {str(e)}', 'danger')


        finally:
            # Close connection
            connection.close()

        # Always return a redirect after POST request
        return redirect(url_for('main.index'))
    
    # Handle GET request by rendering the page (if needed)
    #return render_template('your_template_name.html')  # Ensure you have a template to render
    return redirect(url_for('main.index'))
    #return redirect(url_for('d_f_assign_assessor.internal_m_manage_students'))














@d_f_assign_assessor_bp.route('/external_m_manage_students', methods=['GET', 'POST'])
def external_m_manage_student():
    try:
        # Database connection and fetching terms and schools
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()  # Fetching only terms now

        # Fetch assessors
        assessors_query = "SELECT id, a_external_role, username FROM users WHERE role != 'admin' AND role != 'Head of Department' AND  a_external_role = 1 "
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()


        cursor.execute("SELECT id, name FROM schools")
        schools = cursor.fetchall()

        # Base query without filters
        query = """
        SELECT 
            t.term AS term,
            IF(d.school_id IS NOT NULL, TRUE, FALSE) AS assigned,  -- If the school_id exists in d_assign_assessor, it's assigned, otherwise not assigned
            u.username AS assessor_name,  -- Assessor's name (null if no assignment)
            s.name AS school_name,  -- School name from schools table
            s.id AS school_id,  -- School id from schools table
            IF(d.school_id IS NULL, 'Not Assessed', 'Assigned') AS assessment_status  -- 'Not Assessed' if no record in d_assign_assessor, else 'Assigned'
        FROM schools s
        LEFT JOIN d_external_assign_assessor d ON s.id = d.school_id  -- Left join to include all schools, even those not assigned
        LEFT JOIN terms t ON d.term_id = t.id  -- Join with terms based on term_id, note some schools may not have a term assigned
        LEFT JOIN users u ON d.assessor_id = u.id  -- Join with users to get assessor name, null if not assigned
        """
        
        params = []
        result_list = []

        # Handle dynamic filtering based on POST request
        if request.method == 'POST':
            conditions = []

            # Get the form values
            term = request.form.get('term')
            school = request.form.get('school')

            # Validation: Ensure both term and school are selected
            if not term or not school:
                flash("Please select both a term and a school to filter.", 'danger')
                return redirect(url_for('d_f_assign_assessor.external_m_manage_students'))  # Redirect back to the same page with the message

            # Apply filtering based on selected term and school
            if term:
                conditions.append("d.term_id = %s")  # Adjusted to d_assign_assessor's term_id
                params.append(term)

            if school:
                conditions.append("d.school_id = %s")  # Adjusted to d_assign_assessor's school_id
                params.append(school)

            # If both conditions are selected, apply them to the query using AND
            if conditions:
                query += " WHERE " + " AND ".join(conditions)  # Ensure both filters are applied

        # Execute the query with both filters
        cursor.execute(query, params)
        result_list = cursor.fetchall()

        # Always close the connection after the query is executed
        cursor.close()
        conn.close()

        # Pass the filtered data (or all data if no filters) to the template
        return render_template('d_f_assign_assessor/e_m_assessor_manage_student.html', 
                               username=session['username'], 
                               role=session['role'],
                               result_list=result_list,  # Renamed to result_list since student info is removed
                               terms=terms,
                               schools=schools,
                               assessors=assessors)

    except Exception as e:
        # Log the error and provide feedback to the user
        print(f"Error occurred: {str(e)}")  # For debugging
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))







@d_f_assign_assessor_bp.route('/external_m_assign_assessor', methods=['GET', 'POST'])
def external_m_assign_assessor():
    if request.method == 'POST':
        # Get form data
        assessor_id = request.form.get('assessor')
        school_ids = request.form.getlist('school_ids')
        assigned_by = session['id']
        term_id = request.form.get('term_id')  # Assuming term_id is passed in the form
        
        # Validate form data
        if not assessor_id or not school_ids or not term_id:
            flash('Please select an assessor, at least one school, and a term.', 'warning')
            return redirect(url_for('d_f_assign_assessor.external_m_manage_students'))

        # Establish a connection to the database
        connection = get_db_connection()

        # Flag to check if any assignment was successful
        any_assignment_successful = False

        try:
            with connection.cursor() as cursor:
                for school_id in school_ids:
                    # Check if the assessor is already assigned to this school and term
                    cursor.execute("""
                        SELECT * FROM  d_external_assign_assessor  
                        WHERE school_id = %s AND term_id = %s AND assessor_id = %s
                    """, (school_id, term_id, assessor_id))
                    existing_assignment = cursor.fetchone()

                    if existing_assignment:
                        # If the assignment already exists, flash a warning message and skip this school
                        flash(f'Assessor {assessor_id} is already assigned to school {school_id} for this term.', 'warning')
                        continue  # Skip this school if the assessor is already assigned

                    # Proceed with assignment if no existing assignment
                    cursor.execute("""
                        INSERT INTO  d_external_assign_assessor  (assessor_id, assigned_by, term_id, school_id)
                        VALUES (%s, %s, %s, %s)
                    """, (assessor_id, assigned_by, term_id, school_id))
                    any_assignment_successful = True  # Mark that we did an assignment

            # Commit the transaction only if there was at least one successful assignment
            if any_assignment_successful:
                connection.commit()
                flash('Assessors successfully assigned!', 'success')
            else:
                # No assignments were successful, so no success message
                flash('No new assignments were made. Please check the existing assignments.', 'info')

        except mysql.connector.Error as e:
            # Rollback in case of error
            connection.rollback()
            flash(f'Error assigning assessors: {str(e)}', 'danger')

        finally:
            # Close connection
            connection.close()

        return redirect(url_for('main.index'))