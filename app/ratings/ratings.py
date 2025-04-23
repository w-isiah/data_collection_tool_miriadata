from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint for ratings
ratings_bp = Blueprint('ratings', __name__)


@ratings_bp.route('/manage_ratings', methods=['GET'])
def manage_ratings():
    try:
        # Use a context manager for database connection
        with get_db_connection() as conn:
            # Create a cursor to execute queries
            cursor = conn.cursor(dictionary=True)
            # Execute the query to fetch all ratings, ordered by 'mark' ascending
            cursor.execute("SELECT * FROM ratings ORDER BY mark ASC")
            ratings = cursor.fetchall()  # Fetch all ratings from the database
        
        # Render the template with ratings and session data
        return render_template('ratings/manage_ratings.html', 
                               username=session.get('username'), 
                               role=session.get('role'), 
                               ratings=ratings)
    
    except Exception as e:
        # Handle any exceptions that occur during the database operation
        return f"An error occurred: {e}", 500








@ratings_bp.route('/add_rating', methods=['GET', 'POST'])
def add_rating():
    # Fetching assessment criteria from the database
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM assessment_criteria")
        assessment_criteria = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching assessment criteria: {e}", 'danger')
        return redirect(url_for('ratings.manage_ratings'))

    if request.method == 'POST':
        # Get the form data
        rating_name = request.form['rating_name']
        description = request.form['description']
        mark = request.form['mark']
        assessment_criteria_id = request.form['assessment_criteria_id']

        # Simple input validation
        if not rating_name or not description or not mark or not assessment_criteria_id:
            flash('All fields are required. Please fill them out.', 'danger')
            return redirect(url_for('ratings.add_rating'))

        try:
            # Inserting the new rating into the database
            cursor.execute("""
                INSERT INTO ratings (rating, description, mark, assessment_criteria_id)
                VALUES (%s, %s, %s, %s)
            """, (rating_name, description, mark, assessment_criteria_id))
            conn.commit()
        except Exception as e:
            flash(f"Error adding rating: {e}", 'danger')
            return redirect(url_for('ratings.add_rating'))
        finally:
            conn.close()

        flash('Rating added successfully!', 'success')
        return redirect(url_for('ratings.manage_ratings'))

    # If GET request, render the form with assessment criteria
    return render_template('ratings/add_rating.html', assessment_criteria=assessment_criteria)














# Route to edit an existing rating
@ratings_bp.route('/edit_rating/<int:rating_id>', methods=['GET', 'POST'])
def edit_rating(rating_id): 
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the rating based on the rating_id
    cursor.execute("SELECT * FROM ratings WHERE id = %s", (rating_id,))
    rating = cursor.fetchone()

    # If rating is not found, redirect with an error
    if not rating:
        flash('Rating not found!', 'danger')
        return redirect(url_for('ratings.manage_ratings'))

    # If the form is submitted (POST request)
    if request.method == 'POST':
        rating_name = request.form['rating_name']
        description = request.form['description']
        mark = request.form['mark']

        # Update the rating in the database
        cursor.execute("""
            UPDATE ratings
            SET rating = %s, description = %s, mark = %s
            WHERE id = %s
        """, (rating_name, description, mark, rating_id))  # Pass values, not dict
        conn.commit()

        # Close the connection
        conn.close()

        # Flash success message and redirect
        flash('Rating updated successfully!', 'success')
        return redirect(url_for('ratings.manage_ratings'))

    # Close the connection and render the edit page
    conn.close()
    return render_template('ratings/edit_ratings.html', rating=rating)


# Route to delete a rating
@ratings_bp.route('/delete_rating/<int:rating_id>',  methods=['GET', 'POST'])
def delete_rating(rating_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ratings WHERE id = %s", (rating_id,))
    conn.commit()
    conn.close()

    flash('Rating deleted successfully!', 'danger')
    return redirect(url_for('ratings.manage_ratings'))





@ratings_bp.route('/moderator_view_ratings/<criteria_id>', methods=['GET', 'POST'])
def moderator_view_ratings(criteria_id):
    # Get the database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all records for the given aspect_id
    cursor.execute("SELECT * FROM ratings WHERE assessment_criteria_id = %s", (criteria_id,))
    ratings = cursor.fetchall()  # This will fetch all the records

    # Close the connection
    conn.close()

    # Pass the questions list to the template
    return render_template('ratings/manage_ratings.html',username=session['username'],role=session['role'], ratings=ratings)




    