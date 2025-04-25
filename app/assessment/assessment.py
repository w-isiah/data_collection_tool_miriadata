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
assessment_bp = Blueprint('assessment', __name__)




@assessment_bp.route('/assess/<int:student_id>', methods=['GET', 'POST'])
def assess(student_id):
    role0 = session.get('role')
    
    # Establish a database connection
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Fetch student data
        cursor.execute("SELECT * FROM student_info WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        cursor.execute("SELECT * FROM schools")
        schools = cursor.fetchall()

        cursor.execute("SELECT * FROM ratings")
        ratings = cursor.fetchall()

        # Check if the student exists
        if not student:
            return "Student not found", 404  # Return a 404 error if the student does not exist

        # Fetch assessment criteria data with aspect_id included
        cursor.execute("""
            SELECT s.aspect_id, s.aspect_name, ac.criteria_id, ac.criteria_name, s.description, s.competence
            FROM aspect s
            JOIN assessment_criteria ac ON s.aspect_id = ac.aspect_id
        """)
        data = cursor.fetchall()

        # Fetch ratings by assessment_criteria_id
        ratings_by_criteria = {}
        for row in data:
            cursor.execute("SELECT * FROM ratings WHERE assessment_criteria_id = %s", (row['criteria_id'],))
            ratings_by_criteria[row['criteria_id']] = cursor.fetchall()

    finally:
        # Close the cursor and connection to free up resources
        cursor.close()
        connection.close()

    # Render the template with the fetched data
    if session['role'] == 'Head of Department':
        return render_template('assessment/add_assessment.html',
                               ratings_by_criteria=ratings_by_criteria, 
                               schools=schools,
                               username=session['username'], 
                               role=session['role'], 
                               student_id=student_id, 
                               data=data, 
                               student=student)
    else:
        return render_template('assessment/assessor/add_assessment.html',
                               ratings_by_criteria=ratings_by_criteria, 
                               schools=schools,
                               username=session['username'], 
                               role=session['role'],
                               student_id=student_id, 
                               data=data, 
                               student=student)





















































