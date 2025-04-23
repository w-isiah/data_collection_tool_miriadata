from datetime import timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.db import get_db_connection  # Assuming you have a custom db module to manage DB connections
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from flask import session, flash, redirect, url_for, render_template, request
import logging

# Initialize the blueprint
d_f_scores_bp = Blueprint('d_f_scores', __name__)



















@d_f_scores_bp.route("/save_scores", methods=["POST"])
def save_scores():
    # Check if the user is logged in
    if "id" not in session:
        flash("You must be logged in to submit scores.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        assessor_id = session["id"]
        print(f'assessor_id: {assessor_id}')  # Print assessor_id for debugging
        
        student_id = request.form.get("student_id")
        print(f'student_id: {student_id}')  # Print student_id to check its value
        
        term_id = request.form.get("term_id")
        print(f'term_id: {term_id}')  # Print term_id to check its value
        
        score_type = request.form.get("score_type")  # e.g. 'im' or 'ee'
        print(f'score_type: {score_type}')  # Print score_type
        
        comment = request.form.get("comment")  # Get the comment text from the form
        print(f'comment: {comment}')  # Print comment value to check it

        # Ensure required fields are provided
        if not all([student_id, term_id, score_type, comment]):
            flash("Missing required fields. Please check your input.", "danger")
            return redirect(url_for("main.index"))

        # Define score fields to be collected
        score_fields = [
            "coverage", "quality", "quantity", "attractiveness", "accuracy", 
            "grading", "relevance", "printing", "durability", "originality", 
            "explanation", "storage"
        ]

        # Collect score values from the form
        scores = {field: request.form.get(field) for field in score_fields}
        print(f'scores: {scores}')  # Print the scores to check if any field is missing or empty
        
        # Ensure all score fields are provided
        if not all(scores.values()):
            flash("All score fields are required.", "danger")
            return redirect(url_for("main.index"))

        # Convert score values to float and insert them into the d_f_scores table
        data_to_insert = {
            "student_id": student_id,
            "assessor_id": assessor_id,
            "term_id": term_id,
            "score_type": score_type,
            "comment": comment
        }

        # Adding scores dynamically to the dictionary
        for field in score_fields:
            data_to_insert[field] = float(scores[field])

        # Insert the data into the d_f_scores table
        cursor.execute("""
            INSERT INTO d_f_scores (
                student_id, coverage, quality, quantity, attractiveness, accuracy, grading, relevance, 
                printing, durability, originality, explanation, storage, assessor_id, score_type, term_id, comment
            )
            VALUES (%(student_id)s, %(coverage)s, %(quality)s, %(quantity)s, %(attractiveness)s, %(accuracy)s, 
                    %(grading)s, %(relevance)s, %(printing)s, %(durability)s, %(originality)s, %(explanation)s, 
                    %(storage)s, %(assessor_id)s, %(score_type)s, %(term_id)s, %(comment)s)
        """, data_to_insert)

        conn.commit()
        flash("Scores and comments saved successfully!", "success")

        # Redirect based on the user's role
        role = session.get("role")
        if role == "Head of Department":
            return render_template("scores/evaluation_summary.html", username=session['username'], role=session['role'], student_id=student_id, term_id=term_id)
        elif role == "School Practice Supervisor":
            return render_template("scores/assessor/evaluation_summary.html", username=session['username'], role=session['role'], student_id=student_id, term_id=term_id)
        else:
            flash("Unauthorized role. Cannot view the summary.", "danger")
            return redirect(url_for("main.index"))

    except Exception as e:
        flash(f"An error occurred while saving scores: {str(e)}", "danger")
        return redirect(url_for("main.index"))

    finally:
        conn.close()















@d_f_scores_bp.route("/edit_score/<int:score_id>", methods=["GET", "POST"])
def edit_score(score_id):
    conn = get_db_connection()
    try:
        if request.method == "POST":
            # Handle form submission
            score = request.form.get("score")
            comment = request.form.get("comment")

            # Validate input
            try:
                score = float(score)
            except ValueError:
                flash("Invalid score. Please enter a numeric value.", "danger")
                return redirect(url_for("edit_score", score_id=score_id))

            if len(comment) > 255:
                flash("Comment is too long. Maximum 255 characters allowed.", "danger")
                return redirect(url_for("scores.edit_score", score_id=score_id))

            # Update the database
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE scores
                    SET score = %s, comment = %s
                    WHERE id = %s
                    """,
                    (score, comment, score_id),
                )
                conn.commit()
                flash("Score updated successfully.", "success")
                return redirect(url_for("student_data", student_id=request.form.get("student_id")))

        # Fetch the record for pre-filling the form
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT scores.*, aspect.aspect_name as aspect_name, assessment_criteria.criteria_name as criteria_name
                FROM scores
                INNER JOIN aspect ON scores.aspect_id = aspect.aspect_id
                INNER JOIN assessment_criteria ON scores.criteria_id = assessment_criteria.criteria_id
                WHERE scores.id = %s
                """,
                (score_id,),
            )
            record = cursor.fetchone()
            if not record:
                flash("Record not found.", "danger")
                return redirect(url_for("main.index"))

        return render_template("scores/edit_score.html", username=session['username'], role=session['role'],record=record)

    except Exception as e:
        flash(f"Error editing score: {str(e)}", "danger")
        return redirect(url_for("main.index"))

    finally:
        conn.close()

