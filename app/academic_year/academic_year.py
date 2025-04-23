from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint
academic_year_bp = Blueprint('academic_year', __name__)


#Route to display the list of academic_year and manage them
@academic_year_bp.route('/manage_academic_year', methods=['GET'])
def manage_academic_year():
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Execute query to fetch all academic_year
        cursor.execute("SELECT * FROM academic_year")
        academic_years = cursor.fetchall()  # Fetch all academic_year from the database
        
        # Close the connection
        conn.close()
        
        return render_template('academic_year/manage_academic_year.html', username=session['username'], role=session['role'],academic_years=academic_years)
    
    except Exception as e:
        flash(f"Error retrieving academic_year: {str(e)}", 'danger')
        return redirect(url_for('main.index'))  # Redirect to home if error occurs









@academic_year_bp.route('/edit_academic_year/<int:academic_year_id>', methods=['GET', 'POST'])
def edit_academic_year(academic_year_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get the academic year by ID
        cursor.execute("SELECT * FROM academic_year WHERE id = %s", (academic_year_id,))
        academic_year = cursor.fetchone()

        if not academic_year:
            flash("Academic Year not found!", 'danger')
            return redirect(url_for('academic_year.manage_academic_year'))

        if request.method == 'POST':
            # Get form data
            updated_academic_year = request.form['academic_year'].strip()

            # Validate academic year
            if not updated_academic_year:
                flash("Academic Year cannot be empty!", 'danger')
                return render_template('academic_year/edit_academic_year.html', username=session['username'], role=session['role'], academic_year=academic_year)

            # Check if the updated academic year already exists in the database (excluding the current one)
            cursor.execute("SELECT * FROM academic_year WHERE academic_year = %s AND id != %s", (updated_academic_year, academic_year_id))
            existing_academic_year = cursor.fetchone()

            # If the academic year already exists, show a flash message and do not update
            if existing_academic_year:
                flash("This Academic Year already exists!", 'danger')
                return render_template('academic_year/edit_academic_year.html', username=session['username'], role=session['role'], academic_year=academic_year)

            # Update the academic year details in the database
            cursor.execute("""
                UPDATE academic_year
                SET academic_year = %s
                WHERE id = %s
            """, (updated_academic_year, academic_year_id))
            conn.commit()

            flash("Academic Year updated successfully!", 'success')
            return redirect(url_for('academic_year.manage_academic_year'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'danger')
    finally:
        conn.close()

    return render_template('academic_year/edit_academic_year.html', username=session['username'], role=session['role'], academic_year=academic_year)









# Route to delete a specific academic year
@academic_year_bp.route('/delete_academic_year/<int:academic_year_id>', methods=['GET'])
def delete_academic_year(academic_year_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Delete the academic year by ID
        cursor.execute("DELETE FROM academic_year WHERE id = %s", (academic_year_id,))
        conn.commit()

        flash("Academic Year deleted successfully!", 'success')
    except Exception as e:
        flash(f"An error occurred while deleting the academic year: {str(e)}", 'danger')
    finally:
        conn.close()

    return redirect(url_for('academic_year.manage_academic_year'))




# Route to add a new academic year
@academic_year_bp.route('/add_academic_year', methods=['GET', 'POST'])
def add_academic_year():
    if request.method == 'POST':
        # Get the form data from the POST request
        academic_year = request.form.get('academic_year').strip()

        # Validate the form field (make sure the academic year is provided)
        if not academic_year:
            flash("Academic Year is required!", 'danger')
            return redirect(url_for('academic_year.add_academic_year'))

        # Check if the academic year already exists in the database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM academic_year WHERE academic_year = %s", (academic_year,))
            existing_academic_year = cursor.fetchone()

            # If the academic year already exists, show a flash message and do not insert
            if existing_academic_year:
                flash("This Academic Year already exists!", 'danger')
                conn.close()
                return redirect(url_for('academic_year.add_academic_year'))

            # Insert the new academic year into the database
            cursor.execute("""
                INSERT INTO academic_year (academic_year)
                VALUES (%s)
            """, (academic_year,))
            conn.commit()  # Commit the changes to the database
            conn.close()

            flash("Academic Year added successfully!", 'success')
            return redirect(url_for('academic_year.manage_academic_year'))  # Redirect to manage academic years page after successful addition
        except Exception as e:
            flash(f"An error occurred while adding the academic year: {str(e)}", 'danger')
            return redirect(url_for('academic_year.add_academic_year'))

    # If it's a GET request, render the add academic year form
    return render_template('academic_year/add_academic_year.html', username=session['username'], role=session['role'])

