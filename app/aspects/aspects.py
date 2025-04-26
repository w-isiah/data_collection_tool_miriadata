from datetime import timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.db import get_db_connection  # Now importing from the db module
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from psycopg2 import Error

# Initialize blueprint
aspects_bp = Blueprint('aspects', __name__)
# Initialize the blueprint
@aspects_bp.route('/manage_aspects')
def manage_aspects():
    if 'role' not in session:
        return redirect(url_for('auth.login'))  # Redirect to login if no role is found in session

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM aspect")
    aspects = cursor.fetchall()
    cursor.close()
    conn.close()

    if session['role'] == "Principal_Investigator":
        return render_template('aspects/moderator_manage_aspect.html',username=session['username'],role=session['role'], aspects=aspects)
    else:
        return render_template('aspects/manage_aspect.html',username=session['username'],role=session['role'], aspects=aspects)




@aspects_bp.route('/add_aspects', methods=['GET', 'POST'])
def add_aspects():
    if request.method == 'POST':
        # Retrieve form data
        aspect_name = request.form['aspect_name']
        description = request.form['description']
        competence = request.form['competence']

        try:
            # Establish connection to the database
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if the aspect name already exists in the database
            cursor.execute("SELECT COUNT(*) FROM aspect WHERE aspect_name = %s", (aspect_name,))
            aspect_exists = cursor.fetchone()[0]

            if aspect_exists > 0:
                flash('An aspect with this name already exists. Please choose a different name.', 'danger')
                return redirect(url_for('aspects.add_aspects'))  # Redirect back to the form

            # Insert the new aspect into the database
            cursor.execute("""
                INSERT INTO aspect (aspect_name, description, competence)
                VALUES (%s, %s, %s)
            """, (aspect_name, description, competence))

            # Commit the transaction
            conn.commit()
            flash('Aspect added successfully!', 'success')

        except mysql.connector.Error as err:
            # Handle MySQL error
            flash(f'Error: {err}', 'danger')

        finally:
            # Ensure the connection is closed
            cursor.close()
            conn.close()

        # Redirect to manage aspects page after successful insertion
        return redirect(url_for('aspects.manage_aspects'))

    # Render the add aspects form on GET request
    return render_template('aspects/add_aspects.html',username=session['username'],role=session['role'])





@aspects_bp.route('/update_aspect/<int:id>', methods=['GET', 'POST'])
def update_aspect(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        aspect_name = request.form['aspect_name']
        description = request.form['description']
        competence = request.form['competence']  # Added handling for the 'competence' field

        # Check if the new aspect name already exists in the database, excluding the current aspect
        cursor.execute("""
            SELECT COUNT(*) FROM aspect
            WHERE aspect_name = %s AND aspect_id != %s
        """, (aspect_name, id))
        count = cursor.fetchone()['COUNT(*)']

        if count > 0:
            # Aspect name already exists, flash a message and return to the form
            flash('The aspect name is already taken. Please choose a different name.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('aspects.update_aspect', id=id))

        # Update query for the 'aspect' table
        cursor.execute("""
            UPDATE aspect
            SET aspect_name=%s, description=%s, competence=%s
            WHERE aspect_id=%s
        """, (aspect_name, description, competence, id))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Aspect updated successfully', 'success')
        return redirect(url_for('aspects.manage_aspects'))

    # Fetching the current data for the aspect to populate the form
    cursor.execute("SELECT * FROM aspect WHERE aspect_id=%s", [id])
    aspect = cursor.fetchone()  # Fetch the single aspect by ID
    cursor.close()

    return render_template('aspects/edit_aspect.html',username=session['username'],role=session['role'], aspect=aspect)  # Updated variable names for clarity



@aspects_bp.route('/delete_aspects/<int:id>', methods=['GET', 'POST'])
def delete_aspects(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Prepare the SQL query to delete the aspect
        delete_query = "DELETE FROM aspect WHERE aspect_id = %s"
        cursor.execute(delete_query, (id,))

        # Commit the transaction
        conn.commit()

        if cursor.rowcount > 0:
            flash(f"Aspect with ID {id} has been deleted successfully.", 'success')
        else:
            flash(f"No aspect found with ID {id}.", 'warning')

        # Close the cursor and connection
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        # Handle MySQL errors
        flash(f"Error: {err}", 'danger')
        if conn:
            conn.rollback()  # Rollback the transaction in case of error
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Redirect back to the aspects list or dashboard
    return redirect(url_for('aspects.manage_aspects'))  # Or wherever the list of aspects is