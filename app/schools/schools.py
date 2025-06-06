from datetime import timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.db import get_db_connection  # Now importing from the db module
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from psycopg2 import Error
# Initialize blueprint
schools_bp = Blueprint('schools', __name__)
# Route to display the list of school_category and manage them
@schools_bp.route('/add_schools', methods=['GET', 'POST'])
def add_schools():
    if request.method == 'POST':
        category_id = request.form['category_id']
        district_id = request.form['district_id']  # fixed typo
        name = request.form['name']
        address = request.form['address']
        description = request.form['description']
        contact = request.form['contact']

        # Insert school data
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO schools (category_id, name, address, description, contact, district_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (category_id, name, address, description, contact, district_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('School added successfully!', 'success')
        return redirect(url_for('schools.add_schools'))

    # Fetch dropdown data
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM school_category')
    categories = cursor.fetchall()
    cursor.execute('SELECT * FROM districts')
    districts = cursor.fetchall()
    cursor.close()
    conn.close()

    role=session.get("role")
    if role == "School Practice Supervisor":

        return render_template(
            'schools/assessor_add_schools.html',
            username=session['username'],
            role=session['role'],
            categories=categories,
            districts=districts
        )
    else:
        return render_template(
            'schools/add_schools.html',
            username=session['username'],
            role=session['role'],
            categories=categories,
            districts=districts
        )




@schools_bp.route('/edit_schools/<int:school_id>', methods=['GET', 'POST'])
def edit_schools(school_id):
    # Fetch the current details of the school to be edited
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT * FROM schools WHERE id = %s
    ''', (school_id,))
    school = cursor.fetchone()

    # Fetch categories for the category dropdown
    cursor.execute('SELECT * FROM school_category')
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    if school is None:
        flash('School not found!', 'danger')
        return redirect(url_for('manage_schools'))

    if request.method == 'POST':
        category_id = request.form['category_id']
        name = request.form['name']
        address = request.form['address']
        description = request.form['description']
        contact = request.form['contact']

        # Update school data
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE schools
            SET category_id = %s, name = %s, address = %s, description = %s, contact = %s
            WHERE id = %s
        ''', (category_id, name, address, description, contact, school_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('School updated successfully!', 'success')
        return redirect(url_for('schools.manage_schools'))
    role=session.get("role")
    if role == "School Practice Supervisor":
        return render_template('schools/assessor_edit_schools.html',username=session['username'],role=session['role'], school=school, categories=categories)
    else:
        return render_template('schools/edit_schools.html',username=session['username'],role=session['role'], school=school, categories=categories)








@schools_bp.route('/manage_schools', methods=['GET'])
def manage_schools():
    # Fetch all schools with their category and district info
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT 
            schools.id,
            schools.name,
            schools.address,
            schools.description,
            schools.contact,
            school_category.category_name,
            districts.district_name,
            districts.region,
            districts.country
        FROM schools
        JOIN school_category ON schools.category_id = school_category.id
        JOIN districts ON schools.district_id = districts.id
    ''')
    schools = cursor.fetchall()
    cursor.close()
    conn.close()

    role=session.get("role")
    if role == "School Practice Supervisor":

        return render_template(
            'schools/assessor_manage_schools.html',
            username=session['username'],
            role=session['role'],
            schools=schools
        )
    else:
        return render_template(
            'schools/manage_schools.html',
            username=session['username'],
            role=session['role'],
            schools=schools
        )












@schools_bp.route('/delete_schools/<int:school_id>', methods=['GET', 'POST'])
def delete_schools(school_id):
    # Establish a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete the school by id
    cursor.execute('''DELETE FROM schools WHERE id = %s''', (school_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash('School deleted successfully!', 'success')

    # Redirect back to the manage_schools route
    return redirect(url_for('schools.manage_schools'))
