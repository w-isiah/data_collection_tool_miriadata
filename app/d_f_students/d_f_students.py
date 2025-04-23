from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session,jsonify
from app.db import get_db_connection
import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from io import BytesIO
from app import app
import mysql.connector  # Import mysql.connector at the top of your file
from mysql.connector import Error  # Import the Error class from mysql.connector
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
# Initialize blueprint

d_f_students_bp = Blueprint('d_f_students', __name__)








@d_f_students_bp.route('/i_a_students', methods=['GET', 'POST'])
def i_a_students():
    # Check if the user is logged in
    if 'id' not in session:
        flash('You must be logged in to access this page', 'danger')
        return redirect(url_for('auth.login'))

    # Initialize database connection
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch filter data (programmes, terms, schools, and assessors)
        cursor.execute("SELECT id, programme_name FROM programmes")
        programmes = cursor.fetchall()

        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()

        cursor.execute("SELECT id, name FROM schools")
        schools = cursor.fetchall()

        cursor.execute("SELECT id, username FROM users WHERE role NOT IN ('admin', 'Head of Department')")
        assessors = cursor.fetchall()

        # Retrieve form filter values
        programme_id = request.form.get('programme')
        term_id = request.form.get('term')
        school_id = request.form.get('School')
        reg_no = request.form.get('reg_no')

        # Updated query to include term_id, student_id, assessor_id from d_f_scores and status logic
        query = """ 
            SELECT
                s.name as school_name,
                si.id AS student_id,
                si.reg_no,
                si.student_teacher AS student_name,
                dfs.term_id,
                dfs.student_id AS score_student_id,
                dfs.assessor_id,
                CASE
                    WHEN si.id = dfs.student_id 
                         AND si.term_id = dfs.term_id
                         AND %s = dfs.assessor_id THEN 'assessed'
                    ELSE 'not assessed'
                END AS status
            FROM student_info si
            JOIN schools s ON si.school_id = s.id
            JOIN d_internal_assign_assessor di ON si.school_id = di.school_id
            JOIN users u ON di.assessor_id = u.id
            LEFT JOIN d_f_scores dfs ON si.id = dfs.student_id AND si.term_id = dfs.term_id
            WHERE di.assessor_id = %s
        """

        # Add filters to the query if they are provided
        query_params = [session['id'], session['id']]  # Session ID for status check and WHERE clause

        if programme_id:
            query += " or si.programme_id = %s"
            query_params.append(programme_id)

        if term_id:
            query += " or si.term_id = %s"
            query_params.append(term_id)

        if school_id:
            query += " OR si.school_id = %s"
            query_params.append(school_id)

        if reg_no:
            query += " OR si.reg_no LIKE %s"
            query_params.append(f"%{reg_no}%")  # Use LIKE for partial matching

        # Execute the query with the filtered parameters
        cursor.execute(query, tuple(query_params))
        student_info = cursor.fetchall()

        # Render the template with the filtered data
        return render_template(
            'd_f_student/i_a_student.html',
            username=session['username'],
            role=session['role'],
            student_info=student_info,
            programmes=programmes,
            terms=terms,
            schools=schools,
            assessors=assessors
        )

    except mysql.connector.Error as err:
        # Handle MySQL specific errors
        print(f"Database error: {err}")
        flash(f"A database error occurred: {err}", 'danger')
        return redirect(url_for('main.index'))

    except Exception as e:
        # Catch any other exceptions
        print(f"Error occurred: {e}")
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('main.index'))

    finally:
        # Ensure that the cursor and connection are properly closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()



