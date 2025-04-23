from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint
school_category_bp = Blueprint('school_category', __name__)

# Route to display the list of school_category and manage them
@school_category_bp.route('/manage_category', methods=['GET'])
def manage_category():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM school_category")
    school_category = cursor.fetchall()  # Fetch all school_category from the database
    conn.close()
    
    return render_template('school_category/manage_school_category.html', username=session['username'], role=session['role'],school_categories=school_category)

# Route to edit a specific school_category
@school_category_bp.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the school_category by ID
    cursor.execute("SELECT * FROM school_category WHERE id = %s", (category_id,))
    school_category = cursor.fetchone()

    if not school_category:
        flash("school_category not found!", 'danger')
        return redirect(url_for('school_category.manage_category'))

    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        description = request.form['description']

        # Update the school_category details in the database
        cursor.execute("UPDATE school_category SET category_name = %s, description = %s WHERE id = %s", 
                       (name, description, category_id))
        conn.commit()
        conn.close()

        flash("school_category updated successfully!", 'success')
        return redirect(url_for('school_category.manage_category'))

    conn.close()
    return render_template('school_category/edit_school_category.html',username=session['username'], role=session['role'], category=school_category)

# Route to delete a specific school_category
@school_category_bp.route('/delete_category/<int:category_id>', methods=['GET'])
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Delete the school_category by ID
    cursor.execute("DELETE FROM school_category WHERE id = %s", (category_id,))
    conn.commit()
    conn.close()

    flash("school_category deleted successfully!", 'success')
    return redirect(url_for('school_category.manage_category'))



# Route to add a new school_category
@school_category_bp.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        # Get the form data from the POST request
        name = request.form.get('name')
        description = request.form.get('description')

        # Validate form fields (make sure both fields are provided)
        if not name or not description:
            flash("Both school_category Name and Description are required!", 'danger')
            return redirect(url_for('school_category.add_category'))

        # Insert the new school_category into the database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("INSERT INTO school_category (category_name, description) VALUES (%s, %s)", (name, description))
            conn.commit()  # Commit the changes to the database
            conn.close()

            flash("school_category added successfully!", 'success')
            return redirect(url_for('school_category.manage_category'))  # Redirect to manage school_category page after successful addition
        except Exception as e:
            flash(f"An error occurred while adding the school_category: {str(e)}", 'danger')
            return redirect(url_for('school_category.add_category'))

    # If it's a GET request, render the add school_category form
    return render_template('school_category/add_school_category.html',username=session['username'], role=session['role'])
