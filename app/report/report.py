from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
import random
import string
import logging

import pandas as pd
from io import BytesIO
from flask import send_file

report_bp = Blueprint('report', __name__)



@report_bp.route('/report', methods=['GET'])
def ra_report():
    try:
        # Get session information
        username = session.get('username', 'Guest')
        role = session.get('role', 'User')
        role0 = role

        # Fetch demo data for all users
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT 
                        demo_data.*, 
                        scores.marks_scores_sku,
                        users.username,
                        CASE 
                            WHEN scores.demo_data_id IS NOT NULL THEN 'Assessed'
                            ELSE 'Unassessed'
                        END AS assessment_status
                    FROM demo_data
                    LEFT JOIN users ON demo_data.user_id = users.id
                    LEFT JOIN scores ON demo_data.id = scores.demo_data_id
                    GROUP BY demo_data.id
                    ORDER BY demo_data.created_at
                """)
                demo_data = cursor.fetchall()

        # Render report page for authorized roles
        if role0 in ["Principal_Investigator", " Research_Assistant"]:
            return render_template(
                'report/ra_report.html',
                username=username,
                role=role,
                demo_data=demo_data
            )

    except Exception as e:
        logging.error(f"Error in ra_report: {str(e)}")
        flash(f"An error occurred while fetching respondent data: {str(e)}", 'danger')
        return redirect(url_for('main.index'))







@report_bp.route('/export_report', methods=['GET'])
def export_report():
    try:
        # Fetch demo data for all users
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT 
                        demo_data.*, 
                        scores.marks_scores_sku,
                        users.username,
                        CASE 
                            WHEN scores.demo_data_id IS NOT NULL THEN 'Assessed'
                            ELSE 'Unassessed'
                        END AS assessment_status
                    FROM demo_data
                    LEFT JOIN users ON demo_data.user_id = users.id
                    LEFT JOIN scores ON demo_data.id = scores.demo_data_id
                    GROUP BY demo_data.id
                    ORDER BY demo_data.created_at
                """)
                demo_data = cursor.fetchall()

        # Convert data to a Pandas DataFrame
        df = pd.DataFrame(demo_data)

        # Save the DataFrame to an in-memory Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Respondents")

        # Rewind the in-memory file
        output.seek(0)

        # Send the Excel file as a response
        return send_file(output, as_attachment=True, download_name="respondents_report.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    except Exception as e:
        logging.error(f"Error in export_report: {str(e)}")
        flash(f"An error occurred while exporting the report: {str(e)}", 'danger')
        return redirect(url_for('main.index'))
