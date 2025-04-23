import os
from flask import Blueprint, render_template, flash, session, redirect, url_for, request
from app import app
from app.db import get_db_connection,get_db_data
import datetime
import subprocess
from werkzeug.utils import secure_filename
import logging
from contextlib import contextmanager

# Initialize the Blueprint
db_bk_bp = Blueprint('db_bk', __name__)

# Configuration Constants
ALLOWED_EXTENSIONS = {'sql'}
UPLOAD_FOLDER = app.config.get('UPLOAD_FOLDER')
DB_BK_FOLDER = os.path.join(UPLOAD_FOLDER, 'db_bk')

# Ensure the backup folder exists
os.makedirs(DB_BK_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@db_bk_bp.route('/manage_backups')
def manage_backups():
    try:
        # Ensure the user has the 'admin' role
        if session.get('role') == 'admin':
            with get_db_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT * FROM database_backups")
                    backups = cursor.fetchall()  # Fetch all backup records
                    num_backups = len(backups)  # Number of backups
                    
                    # Get a list of .sql files from the db_bk folder
                    sql_files = [f for f in os.listdir(DB_BK_FOLDER) if f.endswith('.sql')]

                    return render_template('db_bk/manage_backups.html', 
                                           username=session['username'], 
                                           role=session['role'], 
                                           backups=backups, 
                                           num_backups=num_backups,
                                           sql_files=sql_files)
        else:
            flash("Unauthorized access", 'danger')
            return redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"Error fetching backups: {str(e)}")
        flash(f"Error fetching data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))










# Set up logger
logger = logging.getLogger(__name__)

@db_bk_bp.route('/create_backup', methods=['GET', 'POST'])
def create_backup():
    try:
        # Ensure the user has the 'admin' role
        if session.get('role') != 'admin':
            flash("Unauthorized access", 'danger')
            return redirect(url_for('main.index'))

        # Get the description from the form, or use None if no description is provided
        description = request.form.get('description', None)

        # Generate a backup filename based on the current timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file_name = f"backup_{timestamp}.sql"
        backup_file_path = os.path.join(DB_BK_FOLDER, backup_file_name).replace("\\", "/")  # Ensure forward slashes

        # Get DB credentials
        host, user, password, database = get_db_data()
        db_user = user
        db_password = password
        db_name = database

        # Run the mysqldump command to create a backup
        dump_command = f"mysqldump -u {db_user} -p{db_password} {db_name} > {backup_file_path}"

        # Run the subprocess command to create the dump
        try:
            result = subprocess.run(dump_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            # Log the error and display a flash message
            error_message = e.stderr.decode()
            logger.error(f"Error creating backup: {error_message}")
            flash(f"Error creating backup: {error_message}", 'danger')
            return redirect(url_for('db_bk.manage_backups'))

        # Store backup information in the database
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO database_backups (backup_file_name, backup_file_path, backup_date, file_size, created_by, backup_status, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (backup_file_name, backup_file_path, datetime.datetime.now(), os.path.getsize(backup_file_path), session['username'], 'success', description))
                connection.commit()

        flash(f"Backup created successfully: {backup_file_name}", 'success')
        return redirect(url_for('db_bk.manage_backups'))

    except Exception as e:
        logger.error(f"Unexpected error creating backup: {e}")
        flash(f"Error creating backup: {e}", 'danger')
        return redirect(url_for('db_bk.manage_backups'))

