from datetime import timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.db import get_db_connection  # Assuming you have a custom db module to manage DB connections
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from flask import session, flash, redirect, url_for, render_template, request
import logging
logging.basicConfig(level=logging.INFO)

import random

# Initialize the blueprint
scores_bp = Blueprint('scores', __name__)







@scores_bp.route("/save_scores", methods=["POST"])
def save_scores():
    role0 = session.get('role')

    if "id" not in session:
        flash("You must be logged in to submit scores.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        assessor_id = session["id"]
        demo_data_id = request.form.get("demo_data_id")
        school_id = request.form.get("school_id")

        aspect_ids = request.form.getlist("aspect_id[]")
        scores = request.form.getlist("score[]")
        criteria_ids = request.form.getlist("criteria_id[]")
        comment = request.form.get("comment")

        if not all([demo_data_id, aspect_ids, scores, criteria_ids, school_id, comment]):
            flash("Missing required fields. Please check your input.", "danger")
            return redirect(url_for("main.index"))

        if len(aspect_ids) != len(scores) or len(scores) != len(criteria_ids):
            flash("Data mismatch error. Please ensure all inputs align.", "danger")
            return redirect(url_for("main.index"))

        try:
            scores_float = [float(score) for score in scores]
            total_score = sum(scores_float)
        except ValueError as e:
            flash(f"Error converting scores: {str(e)}", "danger")
            return redirect(url_for("main.index"))

        max_score = 5 * len(criteria_ids)
        if max_score > 0:
            total_percentage = (total_score / max_score) * 100
            total_percentage = round(min(total_percentage, 100), 0)

            marks_scores_sku = str(random.randint(1000000000, 9999999999))

            # Insert into marks
            cursor.execute("""
                INSERT INTO marks (demo_data_id, assessor_id, school_id, marks, assessment_type, date_awarded, marks_scores_sku)
                VALUES (%s, %s, %s, %s, %s, CURDATE(), %s)
                ON DUPLICATE KEY UPDATE marks = %s, date_awarded = CURDATE(), marks_scores_sku = %s
            """, (demo_data_id, assessor_id, school_id, total_percentage, "system", marks_scores_sku, total_percentage, marks_scores_sku))
            conn.commit()

        else:
            flash("Invalid max score calculated. No data inserted into marks.", "danger")
            return redirect(url_for("main.index"))

        # Insert general comment
        cursor.execute("""
            INSERT INTO general_comments (demo_data_id, assessor_id, comment, marks_scores_sku)
            VALUES (%s, %s, %s, %s)
        """, (demo_data_id, assessor_id, comment, marks_scores_sku))
        conn.commit()

        # Insert detailed scores
        data_to_insert_scores = []
        for idx, criteria_id in enumerate(criteria_ids):
            score = scores_float[idx]
            aspect_id = aspect_ids[idx]

            data_to_insert_scores.append(
                (school_id, demo_data_id, aspect_id, criteria_id, assessor_id, score, marks_scores_sku)
            )

        cursor.executemany("""
            INSERT INTO scores (school_id, demo_data_id, aspect_id, criteria_id, assessor_id, score, marks_scores_sku)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, data_to_insert_scores)
        conn.commit()

        flash("Scores and comments saved successfully!", "success")
        return redirect(url_for("demo_data.manage_demo_data"))

    except Exception as e:
        logging.error(f"An error occurred while saving scores: {str(e)}")
        flash(f"An error occurred while saving scores: {str(e)}", "danger")
        return redirect(url_for("main.index"))

    finally:
        conn.close()









@scores_bp.route("/view_scores/<string:marks_scores_sku>", methods=["GET", "POST"])
def view_scores(marks_scores_sku):
    role0 = session.get('role')

    if "id" not in session:
        flash("You must be logged in to submit scores.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        assessor_id = session["id"]

        # Fetch data using marks_scores_sku from both `marks` and `scores` tables
        cursor.execute("""
            SELECT m.assessor_id, m.school_id, m.marks, m.assessment_type, m.date_awarded, m.marks_scores_sku, 
                   s.aspect_id, a.aspect_name, c.criteria_name, s.score
            FROM marks m
            JOIN scores s ON m.marks_scores_sku = s.marks_scores_sku
            JOIN aspect a ON s.aspect_id = a.aspect_id
            JOIN assessment_criteria c ON s.criteria_id = c.criteria_id
            WHERE m.marks_scores_sku = %s
        """, (marks_scores_sku,))
        saved_data = cursor.fetchall()

        # Get general comment if available
        cursor.execute('SELECT comment FROM general_comments WHERE marks_scores_sku = %s', (marks_scores_sku,))
        comment = cursor.fetchone()
        print(f'comment is : {comment}')

        # Get mark score from marks table
        cursor.execute("SELECT marks FROM marks WHERE marks_scores_sku = %s", (marks_scores_sku,))
        mark_score = cursor.fetchone()

        if not saved_data:
            flash("No data found for this marks_scores_sku.", "warning")
            return redirect(url_for("main.index"))

        flash("Scores fetched successfully!", "success")

        # Render based on user role
        if role0 == "Head of Department":
            return render_template("scores/evaluation_summary.html", 
                                   username=session['username'], 
                                   role=session['role'],
                                   mark_score=mark_score,
                                   comment=comment, 
                                   saved_data=saved_data, 
                                   marks_scores_sku=marks_scores_sku)
        elif role0 == "School Practice Supervisor":
            return render_template("scores/assessor/evaluation_summary.html", 
                                   username=session['username'], 
                                   role=session['role'],
                                   mark_score=mark_score, 
                                   comment=comment, 
                                   saved_data=saved_data, 
                                   marks_scores_sku=marks_scores_sku)
        else:
            flash("Unauthorized role. Cannot view the summary.", "danger")
            return redirect(url_for("main.index"))

    except Exception as e:
        logging.error(f"An error occurred while viewing scores: {str(e)}")
        flash(f"An error occurred while viewing scores: {str(e)}", "danger")
        return redirect(url_for("main.index"))

    finally:
        conn.close()














@scores_bp.route("/edit_score/<string:marks_scores_sku>", methods=["GET", "POST"])
def edit_score(marks_scores_sku):
    """Handles editing a score and comment."""
    
    # Check if the user is logged in
    if "id" not in session:
        return jsonify({"error": "You must be logged in to view score data."}), 401

    conn = None  # Initialize conn to None
    cursor = None  # Initialize cursor to None
    try:
        # Establish DB connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Log the received SKU value
        logging.info(f'Received marks_scores_sku: {marks_scores_sku}')

        # Handle the GET request: Fetch the existing score data
        if request.method == "GET":
            cursor.execute("""
                SELECT
                    s.score AS score_mark,
                    a.aspect_name,
                    ac.criteria_name,
                    ac.criteria_id AS criteria_id,
                    a.description AS aspect_description
                FROM
                    scores s
                JOIN
                    aspect a ON s.aspect_id = a.aspect_id
                JOIN
                    assessment_criteria ac ON s.criteria_id = ac.criteria_id
                WHERE
                    s.marks_scores_sku = %s;
            """, (marks_scores_sku,))

            # Fetch all matching records
            records = cursor.fetchall()

            # Fetch existing comment
            cursor.execute("SELECT comment FROM  general_comments WHERE marks_scores_sku = %s", (marks_scores_sku,))
            comment = cursor.fetchone()


            cursor.execute("SELECT marks FROM  marks WHERE marks_scores_sku = %s", (marks_scores_sku,))
            mark_score = cursor.fetchone()

            # Check if records were found
            if records:
                # Pass all records to the template
                role=session.get("role")
                if role == "School Practice Supervisor":
                    return render_template(
                        "scores/assessor/edit_score.html",
                        username=session.get("username"),
                        comment=comment,
                        marks_scores_sku=marks_scores_sku,
                        role=session.get("role"),
                        record=records,  # Send the records to the form
                        mark_score=mark_score,
                        related_records=records  # Send the related records for loops in HTML
                        )
                else:
                    return render_template(
                        "scores/edit_score.html",
                        username=session.get("username"),
                        comment=comment,
                        marks_scores_sku=marks_scores_sku,
                        role=session.get("role"),
                        record=records,  # Send the records to the form
                        mark_score=mark_score,
                        related_records=records  # Sen
                )
            else:
                # Handle the case where the record does not exist
                logging.warning(f"No records found for marks_scores_sku: {marks_scores_sku}")
                return "Record not found", 404

        # Handle the POST request: Update the score in the database
        elif request.method == "POST":
            # Get the list of criteria_ids and the new scores from the form
            criteria_ids = request.form.getlist("criteria_id[]")
            scores = request.form.getlist("score[]")
            comment = request.form.get('comment')

            # Ensure there is a match between criteria and scores
            if len(criteria_ids) != len(scores):
                return jsonify({"error": "Mismatch between criteria IDs and scores."}), 400

            # Convert scores to float and calculate the total score
            try:
                scores_float = [float(score) for score in scores]
                total_score = sum(scores_float)
            except ValueError:
                return jsonify({"error": "Invalid score format."}), 400

            # Calculate the maximum score (5 * number of criteria)
            max_score = 5 * len(criteria_ids)

            # Calculate the total percentage
            if max_score > 0:
                total_percentage = (total_score / max_score) * 100
                total_percentage = round(min(total_percentage, 100), 2)  # Ensure max is 100%
            else:
                total_percentage = 0

            # Update scores in the database for each criteria
            for criteria_id, score in zip(criteria_ids, scores):
                cursor.execute("""
                    UPDATE scores
                    SET score = %s
                    WHERE marks_scores_sku = %s AND criteria_id = %s;
                """, (score, marks_scores_sku, criteria_id))

            # Update the marks table with the total percentage
            cursor.execute("""
                UPDATE marks
                SET marks = %s
                WHERE marks_scores_sku = %s;
            """, (total_percentage, marks_scores_sku))

            # Update the comment in the general_comments table
            cursor.execute("UPDATE general_comments SET comment = %s WHERE marks_scores_sku = %s", (comment, marks_scores_sku))

            # Commit the changes to the database
            conn.commit()

            # Provide feedback to the user
            flash("Scores and total percentage updated successfully!", "success")

            # Redirect to a page where the user can view the updated score
            return redirect(url_for('scores.view_scores', marks_scores_sku=marks_scores_sku))

    except mysql.connector.Error as err:
        # Handle MySQL-specific errors and log them
        logging.error(f"MySQL error: {err}")
        return jsonify({"error": f"MySQL error: {err}"}), 500

    except Exception as e:
        # Handle any other unexpected errors and log them with full exception details
        logging.exception(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

    finally:
        # Ensure the cursor and connection are closed properly
        if cursor:  # Add a check to make sure the cursor exists.
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            logging.info("Database connection closed.")
















@scores_bp.route("/delete_scores/<string:marks_scores_sku>", methods=["GET", "POST"])
def delete_scores(marks_scores_sku):
    if "id" not in session:
        flash("You must be logged in to delete scores.", "danger")
        return redirect(url_for("auth.login"))

    try:
        # Establish database connection using 'with' to ensure proper closure
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            

            # Delete from scores table
            cursor.execute("DELETE FROM scores WHERE marks_scores_sku = %s", (marks_scores_sku,))

            # Delete from general_comments table
            cursor.execute("DELETE FROM general_comments WHERE marks_scores_sku = %s", (marks_scores_sku,))

            # Delete from marks table
            cursor.execute("DELETE FROM marks WHERE marks_scores_sku = %s", (marks_scores_sku,))

            # Commit the transaction
            conn.commit()

        flash("Scores and related data successfully deleted.", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        # Log the error with detailed message
        logging.error(f"An error occurred while deleting scores for {marks_scores_sku}: {str(e)}")
        flash(f"An error occurred while deleting scores: {str(e)}", "danger")
        return redirect(url_for("main.index"))
