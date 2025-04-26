from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

# Initialize blueprint
districts_bp = Blueprint('districts', __name__)





# Route to display the list of districts and manage them
@districts_bp.route('/manage_districts', methods=['GET'])
def manage_districts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM districts")
    districts = cursor.fetchall()  # Fetch all districts from the database
    conn.close()

    role=session.get("role")
    if role == "Research_Assistant":
        return render_template('districts/assessor_manage_district.html', username=session['username'], role=session['role'],districts=districts)
    else:
        return render_template('districts/manage_districts.html', username=session['username'], role=session['role'],districts=districts)







# Route to edit a specific district
@districts_bp.route('/edit_district/<int:district_id>', methods=['GET', 'POST'])
def edit_district(district_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the district by ID
    cursor.execute("SELECT * FROM districts WHERE id = %s", (district_id,))
    district = cursor.fetchone()

    if not district:
        flash("District not found!", 'danger')
        return redirect(url_for('districts.manage_districts'))

    if request.method == 'POST':
        # Get updated data from form
        name = request.form['district_name']
        region = request.form.get('region')
        country = request.form.get('country')

        # Basic validation
        if not name:
            flash("District name is required!", 'danger')
            return redirect(url_for('districts.edit_district', district_id=district_id))

        # Update the district in the database
        try:
            cursor.execute("""
                UPDATE districts 
                SET district_name = %s, region = %s, country = %s 
                WHERE id = %s
            """, (name, region, country, district_id))
            conn.commit()
            flash("District updated successfully!", 'success')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')
        finally:
            conn.close()

        return redirect(url_for('districts.manage_districts'))

    conn.close()
    role=session.get("role")
    if role == "Research_Assistant":
        return render_template('districts/assessor_edit_district.html',
                               username=session['username'],
                               role=session['role'],
                               district=district)
    else:
        return render_template('districts/edit_district.html',
                               username=session['username'],
                               role=session['role'],
                               district=district)





# Route to delete a specific district
@districts_bp.route('/delete_district/<int:district_id>', methods=['GET'])
def delete_district(district_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Delete the district by ID
    cursor.execute("DELETE FROM districts WHERE id = %s", (district_id,))
    conn.commit()
    conn.close()

    flash("district deleted successfully!", 'success')
    return redirect(url_for('districts.manage_districts'))



# Route to add a new district
@districts_bp.route('/add_district', methods=['GET', 'POST'])
def add_district():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('district_name')
        region = request.form.get('region')
        country = request.form.get('country')

        # Validate required fields
        if not name:
            flash("District name is required!", 'danger')
            return redirect(url_for('districts.add_district'))

        # Insert the new district
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                INSERT INTO districts (district_name, region, country)
                VALUES (%s, %s, %s)
            """, (name, region, country))
            conn.commit()
            conn.close()

            flash("District added successfully!", 'success')
            return redirect(url_for('districts.manage_districts'))

        except Exception as e:
            flash(f"An error occurred while adding the district: {str(e)}", 'danger')
            return redirect(url_for('districts.add_district'))

    # GET request — render the form
    role=session.get("role")
    if role == "Research_Assistant":
        return render_template('districts/assessor_add_district.html',
                               username=session['username'],
                               role=session['role'])
    else:
        return render_template('districts/add_district.html',
                               username=session['username'],
                               role=session['role'])

