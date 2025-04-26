from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint
moderate_bp = Blueprint('moderate', __name__)

@moderate_bp.route('/manage_students', methods=['GET', 'POST'])
def manage_students():
    try:
        # Database connection and fetching programmes and terms
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, programme_name FROM programmes")
        programmes = cursor.fetchall()

        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()

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
                LEFT JOIN programmes p ON si.programme_id = p.id
                LEFT JOIN terms t ON si.term_id = t.id
            """

        params = []

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

            cursor.execute(query, params)
            student_info = cursor.fetchall()

        else:
            student_info = []

        cursor.close()
        conn.close()

        # Ensure that student_info is being passed correctly to the template
        print("Student Info for Rendering:", student_info)

        # Selecting the correct template based on user role
        template = 'student/manage_student.html' if session.get('role') == "Principal_Investigator" else 'student/assessor_manage_student.html'
        return render_template(template, username=session.get('username'), role=session.get('role'),
                               student_info=student_info, programmes=programmes, terms=terms)
    
    except Exception as e:
        # Log the error for debugging and provide feedback to the user
        print(f"Error occurred: {str(e)}")  # Debug: Log error
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))






@moderate_bp.route('/add_marks', methods=['GET', 'POST'])
def add_marks():
    try:
        # Database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the list of students for dropdown (this can be filtered by assessor_id)
        cursor.execute("""
            SELECT si.id AS student_id, si.student_teacher 
            FROM student_info si 
            WHERE si.assessor_id = %s
        """, [session["id"]])
        students = cursor.fetchall()

        # Fetch the list of terms for dropdown
        cursor.execute("SELECT id, term FROM terms")
        terms = cursor.fetchall()

        # Fetch the list of schools for dropdown
        cursor.execute("SELECT id, name FROM schools")
        schools = cursor.fetchall()

        if request.method == 'POST':
            # Get form data
            student_id = request.form.get('student_id')
            term_id = request.form.get('term_id')
            school_id = request.form.get('school_id')
            marks = request.form.get('marks')
            assessment_type = request.form.get('assessment_type')
            date_awarded = request.form.get('date_awarded')

            # Validation (you can add more validations if necessary)
            if not student_id or not term_id or not marks or not assessment_type or not date_awarded:
                flash("All fields are required", 'danger')
                return redirect(url_for('marks.add_marks'))

            # Insert the marks into the 'marks' table
            cursor.execute("""
                INSERT INTO marks (student_id, term_id, assessor_id, school_id, marks, assessment_type, date_awarded)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [student_id, term_id, session["id"], school_id, marks, assessment_type, date_awarded])

            # Commit the transaction
            conn.commit()

            flash("Marks have been successfully added", 'success')
            return redirect(url_for('marks.add_marks'))  # Redirect to the same page after successful insertion

        cursor.close()
        conn.close()

        # Render the template with the data for students, terms, and schools
        return render_template('marks/add_marks.html', 
                               students=students, terms=terms, schools=schools)

    except Exception as e:
        # Log the error for debugging and provide feedback to the user
        print(f"Error occurred: {str(e)}")  # Debug: Log error
        flash(f"An error occurred while submitting the marks: {str(e)}", 'danger')
        return redirect(url_for('main.index'))




















@moderate_bp.route('/check_student', methods=['GET', 'POST'])
def check_student():
    role = session.get('role')  # Get the logged-in user's role
    role = role.strip()
    user_id = session.get('id')  # Get the logged-in user's ID
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if not user_id:
        return redirect(url_for('login'))  # Redirect if the user is not logged in

    try:
        if request.method == 'POST':
            reg_no = request.form.get('reg_no')  # Get registration number from form input

            # Fetch student details from the student_info table
            cursor.execute("SELECT * FROM student_info WHERE reg_no = %s", (reg_no,))
            student = cursor.fetchone()

            if not student:
                if role == "Principal_Investigator":
                    return render_template('moderate/check_student_2.html', role=role, message="No student found with the given registration number.")
                else:
                    return render_template('moderate/assessor/check_student_2.html', role=role, message="No student found with the given registration number.")

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
                if role == "Principal_Investigator":
                    return render_template('moderate/check_student_2.html', username=session['username'], role=role, student=student, message="Student has not been assessed yet. Please assess them.")
                else:
                    return render_template('moderate/assessor/check_student_2.html', username=session['username'], role=role, student=student, message="Student has not been assessed yet. Please assess them.")

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

            # Return the template with results
            if role == "Principal_Investigator":
                return render_template('moderate/check_student_2.html', username=session['username'], role=role, student=student, results=results)
            else:
                return render_template('moderate/assessor/check_student_2.html', username=session['username'], role=role, student=student, results=results)

        # Handle GET requests (show the initial form)
        if role == "Principal_Investigator":
            return render_template('moderate/check_student_2.html', username=session['username'], role=role)
        else:
            return render_template('moderate/assessor/check_student_2.html', username=session['username'], role=role)

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        flash("An error occurred while processing the request.", "danger")
        if role == "Principal_Investigator":
            return render_template('moderate/check_student_2.html', username=session['username'], role=role)
        else:
            return render_template('moderate/assessor/check_student_2.html', username=session['username'], role=role)
    finally:
        cursor.close()
        connection.close()












@moderate_bp.route('/assess_v1/<int:student_id>', methods=['GET', 'POST'])
def assess_v1(student_id):
    role = session.get('role')
    
    # Establish database connection
    conn = get_db_connection()

    try:
        # Fetch student data by ID
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM student_info WHERE id = %s", (student_id,))
            student = cursor.fetchone()

            cursor.execute("SELECT * FROM schools")
            schools = cursor.fetchall()

        # Check if student is found
        if not student:
            return "Student not found", 404  # Return 404 if no student is found

    finally:
        conn.close()  # Close the database connection

    # Based on user role, render appropriate template
    if role == 'Principal_Investigator':
        return render_template(
            'moderate/add_assessment.html', 
            schools=schools,
            username=session['username'],
            role=session['role'], 
            student_id=student_id, 
            student=student
        )
    elif role == 'Research_Assistant':
        return render_template(
            'assessment_v1/assessor/add_assessment.html', 
            schools=schools, 
            username=session['username'],
            role=session['role'],
            student_id=student_id,
            student=student
        )
    else:
        return redirect(url_for('main.index'))  # Redirect to home page if role is unrecognized




@moderate_bp.route("/save_scores", methods=["POST"])
def save_scores():
    role0 = session.get('role')
    
    # Ensure the user is logged in by checking the session
    if "id" not in session:
        flash("You must be logged in to submit scores.", "danger")
        return redirect(url_for("auth.login"))

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get form data
        assessor_id = session["id"]
        student_id = request.form.get("student_teacher_id")
        term_id = request.form.get("term_id")
        school_id = request.form.get("school_id")

        print(f"Received data: student_id={student_id}, term_id={term_id}, school_id={school_id}")

        # Validate form inputs
        if not all([student_id, term_id, school_id]):
            flash("Missing required fields. Please check your input.", "danger")
            return redirect(url_for("main.index"))

        # Prepare marks data (assuming 'marks' input from form)
        marks = request.form.get("marks")

        # Validate the marks input (ensure it is a number)
        try:
            marks = float(marks)
        except ValueError:
            flash("Invalid marks. Please enter a valid number.", "danger")
            return redirect(url_for("main.index"))

        # Insert into marks table (insert only one record)
        cursor.execute("""
            INSERT INTO marks (student_id, assessor_id, term_id, school_id, marks, assessment_type, date_awarded)
            VALUES (%s, %s, %s, %s, %s, %s, CURDATE())
            ON DUPLICATE KEY UPDATE marks = %s, date_awarded = CURDATE()
        """, (student_id, assessor_id, term_id, school_id, marks, "manual", marks))

        # Commit the transaction
        conn.commit()
        print(f"Inserted into marks table: student_id={student_id}, assessor_id={assessor_id}, marks={marks}")

        flash("Marks saved successfully!", "success")

        # Render a summary page with the saved data based on the role
        if role0 == "Principal_Investigator":
            return render_template("moderate/evaluation_summary.html", username=session['username'], role=session['role'], student_id=student_id, term_id=term_id)
        elif role0 == "Research_Assistant":
            return render_template("scores/assessor/evaluation_summary.html", username=session['username'], role=session['role'], student_id=student_id, term_id=term_id)
        else:
            flash("Unauthorized role. Cannot view the summary.", "danger")
            return redirect(url_for("main.index"))

    except Exception as e:
        logging.error(f"An error occurred while saving scores: {str(e)}")
        flash(f"An error occurred while saving scores: {str(e)}", "danger")
        return redirect(url_for("main.index"))

    finally:
        conn.close()  # Always close the connection
