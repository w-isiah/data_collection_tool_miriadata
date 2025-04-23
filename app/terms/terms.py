from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint
term_bp = Blueprint('terms', __name__)


#Route to display the list of terms and manage them
@term_bp.route('/manage_term', methods=['GET'])
def manage_term():
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Execute query to fetch all terms
        cursor.execute("SELECT * FROM terms")
        terms = cursor.fetchall()  # Fetch all terms from the database
        
        # Close the connection
        conn.close()
        
        return render_template('terms/manage_term.html', username=session['username'], role=session['role'],terms=terms)
    
    except Exception as e:
        flash(f"Error retrieving terms: {str(e)}", 'danger')
        return redirect(url_for('main.index'))  # Redirect to home if error occurs















@term_bp.route('/edit_term/<int:term_id>', methods=['GET', 'POST'])
def edit_term(term_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get the term by ID
        cursor.execute("SELECT * FROM terms WHERE id = %s", (term_id,))
        term = cursor.fetchone()

        if not term:
            flash("Semester not found!", 'danger')
            return redirect(url_for('terms.manage_term'))

        if request.method == 'POST':
            # Get form data
            new_term = request.form['term'].strip()

            # Validate term name
            if not new_term:
                flash("Semester cannot be empty!", 'danger')
                return render_template('terms/edit_term.html', username=session['username'], role=session['role'], term=term)

            # Check if the new term already exists in the database
            cursor.execute("SELECT * FROM terms WHERE term = %s AND id != %s", (new_term, term_id))
            existing_term = cursor.fetchone()

            if existing_term:
                flash("This semester already exists!", 'danger')
                return render_template('terms/edit_term.html', username=session['username'], role=session['role'], term=term)

            # Update the term details in the database
            cursor.execute("""
                UPDATE terms
                SET term = %s
                WHERE id = %s
            """, (new_term, term_id))
            conn.commit()

            flash("Semester updated successfully!", 'success')
            return redirect(url_for('terms.manage_term'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'danger')
    finally:
        conn.close()

    return render_template('terms/edit_term.html', username=session['username'], role=session['role'], term=term)



















# Route to delete a specific term
@term_bp.route('/delete_term/<int:term_id>', methods=['GET'])
def delete_term(term_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Delete the term by ID
    cursor.execute("DELETE FROM terms WHERE id = %s", (term_id,))
    conn.commit()
    conn.close()

    flash("Semester deleted successfully!", 'success')
    return redirect(url_for('terms.manage_term'))





@term_bp.route('/add_term', methods=['GET', 'POST'])
def add_term():
    if request.method == 'POST':
        # Get the form data from the POST request
        term_name = request.form.get('term').strip()

        # Validate form fields (make sure the term name is provided)
        if not term_name:
            flash("Semester is required!", 'danger')
            return redirect(url_for('terms.add_term'))

        # Check if the term already exists in the database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Query to check if the term already exists
            cursor.execute("SELECT * FROM terms WHERE term = %s", (term_name,))
            existing_term = cursor.fetchone()

            if existing_term:
                flash("This semester already exists!", 'danger')
                return redirect(url_for('terms.add_term'))  # Don't insert, just return to the form

            # Insert the new term into the database since it doesn't exist
            cursor.execute("""
                INSERT INTO terms (term)
                VALUES (%s)
            """, (term_name,))  # Pass as a tuple

            conn.commit()  # Commit the changes to the database

        except Exception as e:
            flash(f"An error occurred while adding the term: {str(e)}", 'danger')
            return redirect(url_for('terms.add_term'))

        finally:
            conn.close()  # Ensure the connection is closed

        flash("Semester added successfully!", 'success')
        return redirect(url_for('terms.manage_term'))  # Redirect to manage term page after successful addition

    # If it's a GET request, render the add term form
    return render_template('terms/add_term.html', username=session.get('username'), role=session.get('role'))

