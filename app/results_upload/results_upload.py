from datetime import datetime
import os
import pandas as pd
import zipfile
import tempfile
import logging
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, send_file
)
from werkzeug.utils import secure_filename
from app.db import get_db_connection
from app import app
import warnings

warnings.simplefilter("ignore", UserWarning)

# Initialize blueprint
results_upload_bp = Blueprint('results_upload', __name__)

# Constants
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



















# Helper functions
def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



from datetime import datetime

def validate_marks_data(df):
    """Validate and process the marks data from the uploaded Excel file."""
    processed_data = []
    errors = []

    # Retrieve assessor_id from session
    assessor_id = session.get('id')  
    if not assessor_id:
        errors.append("Assessor ID is missing from the session.")
        return [], errors

    with get_db_connection() as connection:
        cursor = connection.cursor()

        for index, row in df.iterrows():
            reg_no = row.get('reg no')
            term = row.get('Term')
            school = row.get('School')
            marks = row.get('Marks')
            assessment_type = row.get('Assessment Type')
            date_awarded = row.get('Date Awarded')  # New field for date awarded

            # Check for missing required fields
            if pd.isna(reg_no) or pd.isna(term) or pd.isna(school) or pd.isna(marks) or pd.isna(assessment_type):
                errors.append(f"Missing required fields in row {index + 1}.")
                continue

            # If date_awarded is missing, set it to current date
            if pd.isna(date_awarded):
                date_awarded = datetime.now().date()
            else:
                try:
                    # Ensure the date format is correct if provided
                    date_awarded = datetime.strptime(str(date_awarded), '%Y-%m-%d').date()
                except ValueError:
                    errors.append(f"Invalid date format for 'Date Awarded' in row {index + 1}. Expected format: YYYY-MM-DD.")
                    continue

            # Validate reg_no
            cursor.execute("SELECT id FROM student_info WHERE reg_no = %s", (reg_no,))
            student = cursor.fetchone()

            # Validate term
            cursor.execute("SELECT id FROM terms WHERE term = %s", (term,))
            term_id = cursor.fetchone()

            # Validate school
            cursor.execute("SELECT id FROM schools WHERE name = %s", (school,))
            school_id = cursor.fetchone()

            # Check if entries exist in the database
            if not student:
                errors.append(f"Student with reg no '{reg_no}' does not exist in row {index + 1}.")
            if not term_id:
                errors.append(f"Term '{term}' does not exist in row {index + 1}.")
            if not school_id:
                errors.append(f"School '{school}' does not exist in row {index + 1}.")

            # Add data to the list if no errors
            if student and term_id and school_id:
                processed_data.append({
                    'student_id': student[0],
                    'term_id': term_id[0],
                    'school_id': school_id[0],
                    'assessor_id': assessor_id,  # Taken from session
                    'marks': int(marks),
                    'assessment_type': assessment_type,
                    'date_awarded': date_awarded
                })

    return processed_data, errors




















def insert_marks_into_database(data):
    """Insert processed marks data into the database."""
    with get_db_connection() as connection:
        cursor = connection.cursor()
        sql = """
        INSERT INTO  mudulate_marks (student_id, term_id, assessor_id, school_id, marks, assessment_type, date_awarded)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        for row in data:
            cursor.execute(sql, (
                row['student_id'], row['term_id'], row['assessor_id'],
                row['school_id'], row['marks'], row['assessment_type'], row['date_awarded']
            ))
        connection.commit()








# Routes
@results_upload_bp.route('/results_upload', methods=['GET', 'POST'])
def results_upload():
    """Handle Excel file upload for marks."""
    if request.method == 'POST':
        file = request.files.get('file')
        
        if not file or file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('Invalid file format. Please upload an Excel file.', 'danger')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        try:
            df = pd.read_excel(file_path)
            processed_data, errors = validate_marks_data(df)
            
            if errors:
                flash('Errors encountered:\n' + '\n'.join(errors), 'danger')
                return redirect(request.url)
            
            insert_marks_into_database(processed_data)
            flash(f'{len(processed_data)} records uploaded successfully!', 'success')
            return redirect(url_for('results_upload.results_upload')) 
        
        except pd.errors.EmptyDataError:
            flash('Uploaded file is empty.', 'danger')
        except Exception as e:
            flash(f'Error processing the file: {str(e)}', 'danger')
        
        return redirect(url_for('results_upload.results_upload'))
    
    return render_template('results_upload/h_results_upload.html')











@results_upload_bp.route('/download_marks_template_2', methods=['GET'])
def download_marks_template_1():
    """Provide the marks template file for download."""
    target_file = "marks_template.xlsx"
    file_path = os.path.join(UPLOAD_FOLDER, target_file)

    if not os.path.isfile(file_path):
        flash(f"Error: File '{target_file}' not found in the upload folder.", "warning")
        return redirect(url_for('main.index'))

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
            zip_path = temp_zip.name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, target_file)

        return send_file(zip_path, as_attachment=True, download_name=f"{target_file}.zip", mimetype="application/zip")
    except Exception as e:
        logger.error(f"Error creating ZIP file: {e}")
        flash("Error creating template file for download.", "danger")
        return redirect(url_for('main.index'))












@results_upload_bp.route('/download_marks_template', methods=['GET'])
def download_marks_template():
    # Get the upload folder path from Flask config
    upload_folder = app.config['UPLOAD_FOLDER']

    # Ensure the folder exists
    if not os.path.exists(upload_folder):
        flash("Error: Upload folder does not exist.", "danger")
        return redirect(url_for('main.index'))  # Replace with an actual route

    # Define the specific file name to download
    target_file = "marks_tempalate.xlsx"

    # Construct the full path to the target file
    file_path = os.path.join(upload_folder, target_file)

    # Check if the target file exists
    if not os.path.isfile(file_path):
        flash(f"Error: File '{target_file}' not found in the upload folder.", "warning")
        return redirect(url_for('main.index'))  # Replace with an actual route

    # Create a temporary ZIP file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
        zip_path = temp_zip.name
    
    # Add only the target file to the ZIP archive
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_path, target_file)

    # Send the ZIP file for download
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"{target_file}.zip",
        mimetype="application/zip"
    )

