from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint
programmes_bp = Blueprint('programmes', __name__)





# Route to display the list of programmes and manage them
@programmes_bp.route('/manage_programmes', methods=['GET'])
def manage_programmes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM programmes")
    programmes = cursor.fetchall()  # Fetch all programmes from the database
    conn.close()
    
    return render_template('programmes/manage_programmes.html', username=session['username'], role=session['role'],programmes=programmes)

# Route to edit a specific programme
@programmes_bp.route('/edit_programme/<int:programme_id>', methods=['GET', 'POST'])
def edit_programme(programme_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the programme by ID
    cursor.execute("SELECT * FROM programmes WHERE id = %s", (programme_id,))
    programme = cursor.fetchone()

    if not programme:
        flash("Programme not found!", 'danger')
        return redirect(url_for('programmes.manage_programmes'))

    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        description = request.form['description']

        # Update the programme details in the database
        cursor.execute("UPDATE programmes SET programme_name = %s, description = %s WHERE id = %s", 
                       (name, description, programme_id))
        conn.commit()
        conn.close()

        flash("Programme updated successfully!", 'success')
        return redirect(url_for('programmes.manage_programmes'))

    conn.close()
    return render_template('programmes/edit_programmes.html',username=session['username'], role=session['role'], programme=programme)

# Route to delete a specific programme
@programmes_bp.route('/delete_programme/<int:programme_id>', methods=['GET'])
def delete_programme(programme_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Delete the programme by ID
    cursor.execute("DELETE FROM programmes WHERE id = %s", (programme_id,))
    conn.commit()
    conn.close()

    flash("Programme deleted successfully!", 'success')
    return redirect(url_for('programmes.manage_programmes'))



# Route to add a new programme
@programmes_bp.route('/add_programme', methods=['GET', 'POST'])
def add_programme():
    if request.method == 'POST':
        # Get the form data from the POST request
        name = request.form.get('name')
        description = request.form.get('description')

        # Validate form fields (make sure both fields are provided)
        if not name or not description:
            flash("Both Programme Name and Description are required!", 'danger')
            return redirect(url_for('programmes.add_programme'))

        # Insert the new programme into the database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("INSERT INTO programmes (programme_name, description) VALUES (%s, %s)", (name, description))
            conn.commit()  # Commit the changes to the database
            conn.close()

            flash("Programme added successfully!", 'success')
            return redirect(url_for('programmes.manage_programmes'))  # Redirect to manage programmes page after successful addition
        except Exception as e:
            flash(f"An error occurred while adding the programme: {str(e)}", 'danger')
            return redirect(url_for('programmes.add_programme'))

    # If it's a GET request, render the add programme form
    return render_template('programmes/add_programme.html',username=session['username'], role=session['role'])
