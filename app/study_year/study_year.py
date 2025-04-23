from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint
study_year_bp = Blueprint('study_year', __name__)

# Route to display the list of study_year and manage them
@study_year_bp.route('/manage_study_year', methods=['GET'])
def manage_study_year():
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Execute query to fetch all study_year
        cursor.execute("SELECT * FROM study_year")
        study_years = cursor.fetchall()  # Fetch all study_year from the database

        # Close the connection
        conn.close()

        return render_template('study_year/manage_study_year.html', username=session['username'], role=session['role'], study_years=study_years)

    except Exception as e:
        flash(f"Error retrieving study_year: {str(e)}", 'danger')
        return redirect(url_for('main.index'))  # Redirect to home if error occurs


@study_year_bp.route('/edit_study_year/<int:study_year_id>', methods=['GET', 'POST'])
def edit_study_year(study_year_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get the study year by ID
        cursor.execute("SELECT * FROM study_year WHERE id = %s", (study_year_id,))
        study_year = cursor.fetchone()

        if not study_year:
            flash("Study Year not found!", 'danger')
            return redirect(url_for('study_year.manage_study_year'))

        if request.method == 'POST':
            # Get form data
            updated_study_year = request.form['study_year'].strip()

            # Validate study year
            if not updated_study_year:
                flash("Study Year cannot be empty!", 'danger')
                return render_template('study_year/edit_study_year.html', username=session['username'], role=session['role'], study_year=study_year)

            # Check if the updated study year already exists in the database (excluding the current one)
            cursor.execute("SELECT * FROM study_year WHERE study_year = %s AND id != %s", (updated_study_year, study_year_id))
            existing_study_year = cursor.fetchone()

            # If the study year already exists, show a flash message and do not update
            if existing_study_year:
                flash("This Study Year already exists!", 'danger')
                return render_template('study_year/edit_study_year.html', username=session['username'], role=session['role'], study_year=study_year)

            # Update the study year details in the database
            cursor.execute("""
                UPDATE study_year
                SET study_year = %s
                WHERE id = %s
            """, (updated_study_year, study_year_id))
            conn.commit()

            flash("Study Year updated successfully!", 'success')
            return redirect(url_for('study_year.manage_study_year'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'danger')
    finally:
        conn.close()

    return render_template('study_year/edit_study_year.html', username=session['username'], role=session['role'], study_year=study_year)


# Route to delete a specific study year
@study_year_bp.route('/delete_study_year/<int:study_year_id>', methods=['GET'])
def delete_study_year(study_year_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Delete the study year by ID
        cursor.execute("DELETE FROM study_year WHERE id = %s", (study_year_id,))
        conn.commit()

        flash("Study Year deleted successfully!", 'success')
    except Exception as e:
        flash(f"An error occurred while deleting the study year: {str(e)}", 'danger')
    finally:
        conn.close()

    return redirect(url_for('study_year.manage_study_year'))


# Route to add a new study year
@study_year_bp.route('/add_study_year', methods=['GET', 'POST'])
def add_study_year():
    if request.method == 'POST':
        # Get the form data from the POST request
        study_year = request.form.get('study_year').strip()

        # Validate the form field (make sure the study year is provided)
        if not study_year:
            flash("Study Year is required!", 'danger')
            return redirect(url_for('study_year.add_study_year'))

        # Check if the study year already exists in the database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM study_year WHERE study_year = %s", (study_year,))
            existing_study_year = cursor.fetchone()

            # If the study year already exists, show a flash message and do not insert
            if existing_study_year:
                flash("This Study Year already exists!", 'danger')
                conn.close()
                return redirect(url_for('study_year.add_study_year'))

            # Insert the new study year into the database
            cursor.execute("""
                INSERT INTO study_year (study_year)
                VALUES (%s)
            """, (study_year,))
            conn.commit()  # Commit the changes to the database
            conn.close()

            flash("Study Year added successfully!", 'success')
            return redirect(url_for('study_year.manage_study_year'))  # Redirect to manage study years page after successful addition
        except Exception as e:
            flash(f"An error occurred while adding the study year: {str(e)}", 'danger')
            return redirect(url_for('study_year.add_study_year'))

    # If it's a GET request, render the add study year form
    return render_template('study_year/add_study_year.html', username=session['username'], role=session['role'])
