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
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from io import BytesIO
import mysql.connector
from flask import send_file


ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
# Initialize blueprint
student_bp = Blueprint('student', __name__)


    

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










student_bp = Blueprint('student', __name__)

def fetch_programmes_and_terms():
    """Fetches programmes and terms from the database."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, programme_name, description FROM programmes")
    programmes = cursor.fetchall()

    cursor.execute("SELECT id, term FROM terms")
    terms = cursor.fetchall()

    cursor.close()
    conn.close()
    return programmes, terms







@student_bp.route('/manage_student', methods=['GET', 'POST'])
def manage_student():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch Programmes and Terms
        programmes, terms = fetch_programmes_and_terms()

        # Fetch academic years and study years
        cursor.execute("SELECT id, academic_year FROM academic_year")
        academic_years = cursor.fetchall()

        cursor.execute("SELECT id, study_year FROM study_year")
        study_years = cursor.fetchall()

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
                t.term AS term_name,
                sy.study_year AS study_year,
                ay.academic_year AS academic_year,
                s.name AS school_name
            FROM student_info si
            LEFT JOIN programmes p ON si.programme_id = p.id
            LEFT JOIN terms t ON si.term_id = t.id
            LEFT JOIN schools s ON si.school_id = s.id
            LEFT JOIN academic_year ay ON si.academic_year_id = ay.id
            LEFT JOIN study_year sy ON si.study_year_id = sy.id
        """

        params = []

        if request.method == 'POST':
            conditions = []

            # Apply filters if values are provided
            if programme := request.form.get('programme'):
                conditions.append("si.programme_id = %s")
                params.append(int(programme))

            if term := request.form.get('term'):
                conditions.append("si.term_id = %s")
                params.append(int(term))

            if reg_no := request.form.get('reg_no'):
                conditions.append("si.reg_no LIKE %s")
                params.append(f"%{reg_no}%")

            if academic_year := request.form.get('academic_year'):
                conditions.append("ay.academic_year = %s")
                params.append(academic_year)

            if study_year := request.form.get('study_year'):
                conditions.append("sy.study_year = %s")
                params.append(study_year)

            # If any filters are applied, add them to the query
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            print(f"Executing SQL query: {query}")
            print(f"With parameters: {params}")

            cursor.execute(query, params)
            student_info = cursor.fetchall()

        else:
            # If it's a GET request, return 0 students
            
            student_info = []

        cursor.close()
        conn.close()

        template = 'student/manage_student.html' if session['role'] == "Head of Department" else 'student/assessor_manage_student.html'
        return render_template(template, username=session['username'], role=session['role'],
                               student_info=student_info, programmes=programmes, terms=terms,
                               academic_years=academic_years, study_years=study_years)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))









@student_bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    # Establish a database connection
    connection = get_db_connection()
    
    if not connection:
        flash('Failed to connect to the database.', 'danger')
        return render_template('student/add_student.html')

    cursor = connection.cursor(dictionary=True)

    # Fetch dropdown data for programmes, terms, and schools
    cursor.execute('SELECT id, programme_name FROM programmes')
    programmes = cursor.fetchall()
    
    cursor.execute('SELECT id, term FROM terms')
    terms = cursor.fetchall()

    cursor.execute('SELECT id, academic_year FROM academic_year')
    academic_years = cursor.fetchall()

    cursor.execute('SELECT id, name FROM schools')
    schools = cursor.fetchall()

    cursor.execute('SELECT id, study_year FROM study_year')
    study_years = cursor.fetchall()

    if request.method == 'POST':
        # Retrieve form data
        student_teacher = request.form['student_teacher']
        programme_id = request.form['programme_id']
        reg_no = request.form['reg_no']
        term_id = request.form['term_id']
        school_id = request.form['school_id']
        subject = request.form['subject']
        class_name = request.form['class']
        teaching_time = request.form['teaching_time']
        topic = request.form['topic']
        subtopic = request.form['subtopic']
        academic_year_id = request.form['academic_year_id']
        study_year_id = request.form['study_year_id']

        try:
            # Check if the registration number already exists
            cursor.execute("SELECT COUNT(*) FROM student_info WHERE reg_no = %s", (reg_no,))
            result = cursor.fetchone()

            if result['COUNT(*)'] > 0:
                flash('This registration number already exists. Please use a different one.', 'danger')
                return render_template('student/add_student.html', study_years=study_years, academic_years=academic_years, schools=schools, programmes=programmes, terms=terms)

            # Insert data into the student_info table
            query = """
                INSERT INTO student_info (
                    student_teacher, programme_id, reg_no, term_id, school_id, subject, 
                    class_name, teaching_time, topic, subtopic, academic_year_id, study_year_id
                ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (student_teacher, programme_id, reg_no, term_id, school_id, subject, 
                      class_name, teaching_time, topic, subtopic, academic_year_id, study_year_id)

            cursor.execute(query, values)
            connection.commit()  # Commit the transaction

            flash('Student Teacher added successfully!', 'success')
            return redirect(url_for('student.add_student'))

        except mysql.connector.Error as e:
            connection.rollback()  # Rollback on error
            flash(f'Error: {e}', 'danger')
            return render_template('student/add_student.html', study_years=study_years, academic_years=academic_years, schools=schools, programmes=programmes, terms=terms)

        finally:
            cursor.close()  # Always close the cursor after the operation

    # Return the page with dropdown data on GET request
    return render_template('student/add_student.html',  study_years=study_years, academic_years=academic_years, schools=schools, programmes=programmes, terms=terms)

 
 
  




@student_bp.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch student details from the database
        cursor.execute("SELECT * FROM student_info WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        # Fetch dropdown data for programmes, terms, schools, academic_years, and study_years
        cursor.execute('SELECT id, programme_name FROM programmes')
        programmes = cursor.fetchall()
        
        cursor.execute('SELECT id, term FROM terms')
        terms = cursor.fetchall()

        cursor.execute('SELECT id, name FROM schools')
        schools = cursor.fetchall()

        cursor.execute('SELECT id, academic_year FROM academic_year')
        academic_years = cursor.fetchall()

        cursor.execute('SELECT id, study_year FROM study_year')
        study_years = cursor.fetchall()

        # If student doesn't exist, flash a message and redirect
        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for('student.manage_student'))

        if request.method == 'POST':
            # Collect form data, including academic_year_id and study_year_id
            form_data = {key: request.form[key] for key in ('student_teacher', 'programme_id', 'reg_no', 'term_id', 
                                                            'subject', 'class', 'topic', 'subtopic', 'teaching_time', 
                                                            'school_id', 'academic_year_id', 'study_year_id')}

            # Check if all required fields are filled
            if not all(form_data.values()):
                flash("All fields are required!", "danger")
            else:
                try:
                    # Extract the form values explicitly
                    student_teacher = form_data['student_teacher']
                    programme_id = form_data['programme_id']
                    reg_no = form_data['reg_no']
                    term_id = form_data['term_id']
                    subject = form_data['subject']
                    class_name = form_data['class']
                    topic = form_data['topic']
                    subtopic = form_data['subtopic']
                    teaching_time = form_data['teaching_time']
                    school_id = form_data['school_id']
                    academic_year_id = form_data['academic_year_id']
                    study_year_id = form_data['study_year_id']

                    # Update the student information in the database
                    query = """
                        UPDATE student_info
                        SET student_teacher = %s, programme_id = %s, reg_no = %s, term_id = %s,
                            subject = %s, class_name = %s, topic = %s, subtopic = %s, teaching_time = %s,
                            school_id = %s, academic_year_id = %s, study_year_id = %s
                        WHERE id = %s
                    """
                    # Values must match the placeholders in the SQL query
                    values = (student_teacher, programme_id, reg_no, term_id, subject, class_name, topic, subtopic, 
                              teaching_time, school_id, academic_year_id, study_year_id, student_id)

                    cursor.execute(query, values)
                    connection.commit()

                    flash("Student updated successfully!", "success")
                    return redirect(url_for('main.index'))  # Redirect after successful update

                except Exception as e:
                    flash(f"An error occurred: {str(e)}", "danger")

        cursor.close()
        connection.close()

        # Render the template with student details, programmes, terms, schools, academic_years, and study_years
        return render_template('student/edit_student.html', username=session['username'], student=student, 
                               programmes=programmes, terms=terms, schools=schools, academic_years=academic_years,
                               study_years=study_years)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('main.index'))










@student_bp.route('/a_edit_student/<int:student_id>', methods=['GET', 'POST'])
def a_edit_student(student_id):
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch student details from the database
        cursor.execute("SELECT * FROM student_info WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        # If student doesn't exist, flash a message and redirect
        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for('student.manage_student'))

        if request.method == 'POST':
            # Collect form data
            form_data = {
                'subject': request.form.get('subject'),
                'class': request.form.get('class'),
                'topic': request.form.get('topic'),
                'subtopic': request.form.get('subtopic'),
                'teaching_time': request.form.get('teaching_time'),
            }

            # Check if all required fields are filled
            if not all(form_data.values()):
                flash("All fields are required!", "danger")
            else:
                try:
                    # Extract form values explicitly
                    subject = form_data['subject']
                    class_name = form_data['class']
                    topic = form_data['topic']
                    subtopic = form_data['subtopic']
                    teaching_time = form_data['teaching_time']

                    # Update the student information in the database
                    query = """
                        UPDATE student_info
                        SET subject = %s, class_name = %s, topic = %s, subtopic = %s, teaching_time = %s
                        WHERE id = %s
                    """
                    # Values must match the placeholders in the SQL query
                    values = (subject, class_name, topic, subtopic, teaching_time, student_id)

                    cursor.execute(query, values)
                    connection.commit()

                    flash("Student updated successfully!", "success")
                    return redirect(url_for('main.index'))  # Redirect after successful update

                except Exception as e:
                    flash(f"An error occurred: {str(e)}", "danger")

        cursor.close()
        connection.close()

        # Render the template with student details
        return render_template('student/assessor_edit_student.html', username=session['username'], student=student)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('main.index'))












@student_bp.route('/delete_student/<string:get_id>')
def delete_student(get_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("DELETE FROM student_info WHERE id = %s", (get_id,))
        conn.commit()
        flash('Student deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()






@student_bp.route('/manage_students_api', methods=['GET'])
def manage_student_api():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Base query for student information
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
                    t.term
                FROM student_info si
                JOIN programmes p ON si.programme_id = p.id
                JOIN terms t ON si.term_id = t.id
            """

            # Execute the query to fetch all students
            cursor.execute(query)
            students = cursor.fetchall()

            return jsonify({'students': students}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
















@student_bp.route('/register_student/<int:student_id>', methods=['GET', 'POST'])
def register_student(student_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the student's current details
        cursor.execute("SELECT * FROM student_info WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        # Fetch terms for the dropdown
        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()

        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for('student.manage_student'))

        if request.method == 'POST':
            term_id = request.form.get('term_id')
            if not term_id:
                flash("Term is required!", "danger")
            else:
                # Update the term for the student
                cursor.execute(
                    "UPDATE student_info SET term_id = %s WHERE id = %s",
                    (term_id, student_id)
                )
                conn.commit()
                flash("Student's term updated successfully!", "success")
                return redirect(url_for('student.manage_student'))

        cursor.close()
        conn.close()

        return render_template('student/register_student.html',username=session['username'], student=student, terms=terms)

    except Exception as e:
        flash(f"An error occurred while fetching data: {str(e)}", "danger")
        return redirect(url_for('student.manage_student'))


    return redirect(url_for('student.manage_student'))







@student_bp.route('/register_selected_students', methods=['POST'])
def register_selected_students():
    try:
        # Get the list of selected students' IDs
        selected_students = request.form.getlist('students[]')
        if not selected_students:
            flash("No students selected!", "danger")
            return redirect(url_for('student.manage_student'))

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the terms for the dropdown
        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()

        # Check if a term is provided in the form
        term_id = request.form.get('term_id')
        if not term_id:
            flash("Term is required!", "danger")
            return redirect(url_for('student.manage_student'))

        # Loop through the selected students and update their term_id
        for student_id in selected_students:
            cursor.execute(
                "UPDATE student_info SET term_id = %s WHERE id = %s",
                (term_id, student_id)
            )

        # Commit the changes to the database
        conn.commit()
        flash(f"Successfully registered {len(selected_students)} students.", "success")
        return redirect(url_for('student.manage_student'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('student.manage_student'))

    finally:
        cursor.close()
        conn.close()








def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS





@student_bp.route('/download_template', methods=['GET'])
def download_template():
    # Fetch data from the database
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return "Database connection failed", 500

    cursor = conn.cursor(dictionary=True)

    # Fetch programmes, terms, and schools from the database
    cursor.execute("SELECT id, programme_name FROM programmes ORDER BY programme_name")
    programmes = [row['programme_name'] for row in cursor.fetchall()]

    cursor.execute("SELECT id, term FROM terms ORDER BY term")
    terms = [row['term'] for row in cursor.fetchall()]

    cursor.execute("SELECT id, name FROM schools ORDER BY name")
    schools = [row['name'] for row in cursor.fetchall()]

    cursor.execute("SELECT id, academic_year FROM academic_year ORDER BY academic_year")
    academic_year = [row['academic_year'] for row in cursor.fetchall()]

    cursor.execute("SELECT id, study_year FROM study_year ORDER BY study_year")
    study_year = [row['study_year'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    # Create a new workbook and select the active worksheet
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Students Template"

    # Add headers to the first sheet
    ws1.append(["reg no", "student_teacher", "Semester", "School", "programmes", "Academic Year", "Study Year"])

    # Create a second sheet for drop-down data
    ws2 = wb.create_sheet("drop_down data")
    ws2.append(["terms", "programmes", "Schools", "academic_year", "study_year"])
    ws2.append([", ".join(terms), ", ".join(programmes), ", ".join(schools), ", ".join(academic_year), ", ".join(study_year)])

    # Create data validation for Term
    dv_term = DataValidation(type="list", formula1=f'"{",".join(terms)}"', allow_blank=True)
    ws1.add_data_validation(dv_term)
    dv_term.add("C2:C100")  # Apply to rows 2 to 100 in the Term column

    # Create data validation for Programmes
    dv_programmes = DataValidation(type="list", formula1=f'"{",".join(programmes)}"', allow_blank=True)
    ws1.add_data_validation(dv_programmes)
    dv_programmes.add("E2:E100")  # Apply to rows 2 to 100 in the Programmes column

    # Create data validation for School
    dv_school = DataValidation(type="list", formula1=f'"{",".join(schools)}"', allow_blank=True)
    ws1.add_data_validation(dv_school)
    dv_school.add("D2:D100")  # Apply to rows 2 to 100 in the School column

    # Create data validation for Academic Year
    dv_academic_year = DataValidation(type="list", formula1=f'"{",".join(academic_year)}"', allow_blank=True)
    ws1.add_data_validation(dv_academic_year)
    dv_academic_year.add("F2:F100")  # Apply to rows 2 to 100 in the Academic Year column

    # Create data validation for Study Year
    dv_study_year = DataValidation(type="list", formula1=f'"{",".join(study_year)}"', allow_blank=True)
    ws1.add_data_validation(dv_study_year)
    dv_study_year.add("G2:G100")  # Apply to rows 2 to 100 in the Study Year column

    # Save the workbook to memory
    output = BytesIO()
    try:
        wb.save(output)
        output.seek(0)
    except Exception as e:
        print(f"Error saving workbook: {e}")
        return "Error saving workbook", 500

    # Return the file as an attachment
    return send_file(output, as_attachment=True, download_name="student_teacher_template.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")









# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@student_bp.route('/upload_excel', methods=['GET', 'POST'])
def upload_excel():
    if request.method == 'POST':
        file = request.files.get('file')

        if not file or file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Invalid file format. Please upload an Excel file.', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            df = pd.read_excel(file_path)
            processed_data, errors, existing_reg_nos, duplicate_reg_nos = validate_excel_data(df)

            if duplicate_reg_nos:
                flash(f"Duplicate registration numbers found in file: {', '.join(map(str, duplicate_reg_nos))}. Remove duplicates and try again.", 'danger')
                return redirect(request.url)

            if errors:
                flash('Errors encountered:\n' + '\n'.join(errors), 'danger')
                return redirect(request.url)

            if existing_reg_nos:
                flash(f"Registration numbers already exist: {', '.join(existing_reg_nos)}. These entries were skipped.", 'warning')

            insert_into_database(processed_data)

            flash(f'{len(processed_data)} new record(s) uploaded successfully!', 'success')
            return redirect(url_for('student.upload_excel'))
        
        except pd.errors.EmptyDataError:
            flash('Uploaded file is empty.', 'danger')
        except Exception as e:
            flash(f'Error processing the file: {str(e)}', 'danger')

        return redirect(url_for('student.upload_excel'))

    return render_template('student/upload_excel.html', username=session['username'], role=session['role'])




def validate_excel_data(df):
    processed_data = []
    errors = []
    existing_reg_nos = []
    duplicate_reg_nos = []
    seen_reg_nos = set()

    with get_db_connection() as connection:
        cursor = connection.cursor()

        for index, row in df.iterrows():
            student_teacher = row.get('student_teacher')
            reg_no = row.get('reg no')
            programmes = row.get('programmes')
            term = row.get('Semester')  # 'Semester' maps to 'term'
            school = row.get('School')
            academic_year = row.get('Academic Year')
            study_year = row.get('Study Year')

            # ✅ Essential fields check
            if pd.isna(reg_no) or pd.isna(student_teacher)  or pd.isna(programmes) or pd.isna(term) or pd.isna(school) or pd.isna(academic_year) or pd.isna(study_year):
                errors.append(f"Missing required fields in row {index + 1}.")
                
                continue


            reg_no = str(reg_no).strip()  # Ensure it's a string

            # Check for duplicates in the current batch
            if reg_no in seen_reg_nos:
                duplicate_reg_nos.append(reg_no)
                continue
            seen_reg_nos.add(reg_no)

            # Check if the reg_no already exists in the database
            cursor.execute("SELECT COUNT(*) FROM student_info WHERE reg_no = %s", (reg_no,))
            if cursor.fetchone()[0] > 0:
                existing_reg_nos.append(reg_no)
                continue

            # Check if the programme exists in the database
            cursor.execute("SELECT id FROM programmes WHERE programme_name = %s", (programmes,))
            programme_id = cursor.fetchone()

            # Check if the school exists in the database
            cursor.execute("SELECT id FROM schools WHERE name = %s", (school,))
            school_id = cursor.fetchone()

            # Check if the term (semester) exists in the database
            cursor.execute("SELECT id FROM terms WHERE term = %s", (term,))
            term_id = cursor.fetchone()

            # Check if the academic year exists in the database
            cursor.execute("SELECT id FROM academic_year WHERE academic_year = %s", (academic_year,))
            academic_year_id = cursor.fetchone()

            # Check if the study year exists in the database
            cursor.execute("SELECT id FROM study_year WHERE study_year = %s", (study_year,))
            study_year_id = cursor.fetchone()

            # Add errors for missing program, school, term, academic year, or study year
            if not programme_id:
                errors.append(f"Programme '{programmes}' does not exist in row {index + 1}.")
            if not school_id:
                errors.append(f"School '{school}' does not exist in row {index + 1}.")
            if not term_id:
                errors.append(f"Term '{term}' does not exist in row {index + 1}.")
            if not academic_year_id:
                errors.append(f"Academic Year '{academic_year}' does not exist in row {index + 1}.")
            if not study_year_id:
                errors.append(f"Study Year '{study_year}' does not exist in row {index + 1}.")

            # If all necessary IDs are found, prepare data for insertion
            if programme_id and term_id and school_id and academic_year_id and study_year_id:
                print(f"{row.get('student_teaher')}")
                processed_data.append({
                    'student_teacher': row.get('student_teacher', ''),
                    'programme_id': programme_id[0],
                    'reg_no': reg_no,
                    'term_id': term_id[0],
                    'school_id': school_id[0],
                    'academic_year_id': academic_year_id[0],
                    'study_year_id': study_year_id[0],
                })

    return processed_data, errors, existing_reg_nos, duplicate_reg_nos









# Function to insert valid data into the database
def insert_into_database(data):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        sql = """
        INSERT INTO student_info (student_teacher, programme_id, reg_no, term_id, school_id, academic_year_id, study_year_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        for row in data:
            cursor.execute(sql, (
                row['student_teacher'], row['programme_id'], row['reg_no'],
                row['term_id'], row['school_id'], row['academic_year_id'], row['study_year_id']
            ))
        connection.commit()










@student_bp.route('/manage_assigned_students', methods=['GET', 'POST'])
def manage_assigned_student():
    try:
        # Database connection and fetching programmes and terms
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        programmes, terms = fetch_programmes_and_terms()

        # Fetch assessors with corrected query
        assessors_query = "SELECT id, username FROM users WHERE role != 'admin' AND role != 'Head of Department'"
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        # Base query for student information, including checking if the assessor is the current session user
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
            a.assessor_id IS NOT NULL AS assigned,
            u.username AS assessor_name,  -- Added to fetch assessor's name
            CASE 
                WHEN a.assessor_id = %s THEN 'Yes' 
                ELSE 'No' 
            END AS is_assessor_match  -- Determine if the session user is the assigned assessor
        FROM student_info si
        LEFT JOIN programmes p ON si.programme_id = p.id
        LEFT JOIN terms t ON si.term_id = t.id
        LEFT JOIN assign_assessor a ON si.id = a.student_id
        LEFT JOIN users u ON a.assessor_id = u.id  -- Join with users to get assessor name
        """

        params = [session['id']]  # Pass the session's user id to check for matches

        if request.method == 'POST':
            conditions = []

            # Handle dynamic filtering
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
                query += " WHERE " + " AND ".join(conditions)

            # Execute query to fetch students based on filtering
            cursor.execute(query, params)
            student_info = cursor.fetchall()

        else:
            cursor.execute(query, params)
            student_info = cursor.fetchall()

        cursor.close()
        conn.close()

        # Pass the information to the template
        return render_template('student/manage_assigned_student.html', 
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









@student_bp.route('/manage_assess_students', methods=['GET', 'POST'])
def manage_assess_students():
    try:
        # Ensure that the session has a valid assessor id
        if 'id' not in session:
            flash('You must be logged in to access this page', 'danger')
            return redirect(url_for('auth.login'))

        # Database connection and fetching programmes and terms
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        programmes, terms = fetch_programmes_and_terms()

        # Fetch assessors with corrected query
        assessors_query = """
            SELECT id, username FROM users WHERE role != 'admin' AND role != 'Head of Department'
        """
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        # Base query for student information, modified to only include students assigned to the current assessor
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
                a.assessor_id IS NOT NULL AS assigned,
                u.username AS assessor_name,
                si.term_id AS term_id
            FROM student_info si
            LEFT JOIN programmes p ON si.programme_id = p.id
            LEFT JOIN terms t ON si.term_id = t.id
            LEFT JOIN assign_assessor a ON si.id = a.student_id
            LEFT JOIN users u ON a.assessor_id = u.id
            WHERE a.assessor_id = %s
        """

        # Prepare params for filtering
        params = [session['id']]

        # If it's a POST request, add filters to the query
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
                query += " AND " + " AND ".join(conditions)

        # Execute query to fetch students based on filtering
        cursor.execute(query, params)
        student_info = cursor.fetchall()

        # For each student, check if a mark exists for the same term_id in the marks table
        for student in student_info:
            term_id = student['term_id']
            student_id = student['student_id']

            # Query to check if the student has a mark for the same term_id by this specific assessor
            mark_query = """
                SELECT marks, marks_scores_sku
                FROM marks 
                WHERE student_id = %s AND term_id = %s AND assessor_id = %s
                LIMIT 1
            """
            cursor.execute(mark_query, (student_id, term_id, session['id']))
            mark_result = cursor.fetchone()

            if mark_result:
                student['status'] = 'Assessed'
                student['mark'] = mark_result['marks']  # Store the mark if available
                student['marks_scores_sku'] = mark_result['marks_scores_sku']
            else:
                # Check if there is any missing data in the student's information
                required_fields = ['term', 'programme_name', 'class_name', 'reg_no', 'subject', 'topic', 'subtopic', 'teaching_time']
                missing_fields = [field for field in required_fields if not student.get(field)]

                if missing_fields:
                    student['status'] = 'Update Student Data'
                    student['mark'] = None
                else:
                    student['status'] = 'Unassessed'
                    student['mark'] = None

        cursor.close()
        conn.close()

        # Pass the information to the template
        return render_template('student/manage_assess_student.html', 
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











@student_bp.route('/moderator_manage_assess_students', methods=['GET', 'POST'])
def moderator_manage_assess_students():
    try:
        # Ensure the session has a valid assessor id
        if 'id' not in session:
            flash('You must be logged in to access this page', 'danger')
            return redirect(url_for('auth.login'))

        # Database connection and fetching programmes and terms
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch programmes and terms
        programmes, terms = fetch_programmes_and_terms()

        # Fetch assessors
        assessors_query = """
            SELECT id, username FROM users WHERE role NOT IN ('admin', 'Head of Department')
        """
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        # Base query for student information
        query = """
            SELECT DISTINCT
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
                COALESCE(a.assessor_id, 0) IS NOT NULL AS assigned,
                u.username AS assessor_name,
                si.term_id AS term_id
            FROM student_info si
            LEFT JOIN programmes p ON si.programme_id = p.id
            LEFT JOIN terms t ON si.term_id = t.id
            LEFT JOIN assign_assessor a ON si.id = a.student_id
            LEFT JOIN users u ON a.assessor_id = u.id
        """

        # Prepare params for filtering
        params = []

        # Default to an empty list if no filters are applied
        student_info = []

        # If it's a POST request, add filters to the query
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
            
            if assessor := request.form.get('assessor'):
                conditions.append("a.assessor_id = %s")
                params.append(assessor)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

                # Execute query to fetch students based on filtering
                cursor.execute(query, params)
                student_info = cursor.fetchall()

                # For each student, check if a mark exists for the same term_id in the marks table
                for student in student_info:
                    term_id = student['term_id']
                    student_id = student['student_id']

                    # Query to check if the student has a mark for the same term_id by this specific assessor
                    mark_query = """
                        SELECT marks, marks_scores_sku
                        FROM marks 
                        WHERE student_id = %s AND term_id = %s 
                        LIMIT 1
                    """
                    cursor.execute(mark_query, (student_id, term_id))
                    mark_result = cursor.fetchone()

                    if mark_result:
                        student['status'] = 'Assessed'
                        student['mark'] = mark_result['marks']
                        student['marks_scores_sku'] = mark_result['marks_scores_sku']
                    else:
                        required_fields = ['term', 'programme_name', 'class_name', 'reg_no', 'subject', 'topic', 'subtopic', 'teaching_time']
                        missing_fields = [field for field in required_fields if not student.get(field)]

                        if missing_fields:
                            student['status'] = 'Update Student Data'
                            student['mark'] = None
                        else:
                            student['status'] = 'Unassessed'
                            student['mark'] = None
                            student['marks_scores_sku'] = None

        cursor.close()
        conn.close()

        return render_template('student/moderator_manage_assess_student.html', 
                               username=session['username'], 
                               role=session['role'],
                               student_info=student_info, 
                               programmes=programmes, 
                               terms=terms,
                               assessors=assessors)

    except Exception as e:
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))

























@student_bp.route('/m_manage_assess_students', methods=['GET', 'POST'])
def m_manage_assess_student():
    try:
        # Ensure that the session has a valid assessor id
        if 'id' not in session:
            flash('You must be logged in to access this page', 'danger')
            return redirect(url_for('auth.login'))

        # Database connection and fetching programmes and terms
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        programmes, terms = fetch_programmes_and_terms()

        # Fetch assessors with corrected query
        assessors_query = "SELECT id, username FROM users WHERE role != 'admin' AND role != 'Head of Department'"
        cursor.execute(assessors_query)
        assessors = cursor.fetchall()

        # Base query for student information, modified to only include students assigned to the current assessor
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
            a.assessor_id IS NOT NULL AS assigned,
            u.username AS assessor_name,  -- Added to fetch assessor's name
            si.term_id AS term_id
        FROM student_info si
        LEFT JOIN programmes p ON si.programme_id = p.id
        LEFT JOIN terms t ON si.term_id = t.id
        LEFT JOIN m_assign_assessor a ON si.id = a.student_id
        LEFT JOIN users u ON a.assessor_id = u.id
        WHERE a.assessor_id = %s
        """

        # Prepare params for filtering
        params = [session['id']]

        # If it's a POST request, add filters to the query
        if request.method == 'POST':
            conditions = []

            # Handle dynamic filtering
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
                query += " AND " + " AND ".join(conditions)

        # Execute query to fetch students based on filtering
        cursor.execute(query, params)
        student_info = cursor.fetchall()

        # For each student, check if a mark exists for the same term_id in the marks table
        for student in student_info:
            term_id = student['term_id']
            student_id = student['student_id']

            # Query to check if the student has a mark for the same term_id by this specific assessor
            mark_query = """
            SELECT marks 
            FROM  mudulate_marks 
            WHERE student_id = %s AND term_id = %s AND assessor_id = %s
            LIMIT 1
            """
            cursor.execute(mark_query, (student_id, term_id, session['id']))
            mark_result = cursor.fetchone()

            if mark_result:
                student['status'] = 'Assessed'
                student['mark'] = mark_result['marks']  # Store the mark if available
            else:
                student['status'] = 'Unassessed'
                student['mark'] = None

        cursor.close()
        conn.close()

        # Pass the information to the template
        return render_template('student/m_manage_assess_student.html', 
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
