from flask import Flask
from config import Config
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta

# In config.py or directly in your app's configuration
# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=3000)
csrf = CSRFProtect(app)



# Allowed file extensions


# Path to save uploaded files (you can change this as needed)
#UPLOAD_FOLDER = 'uploads/'
UPLOAD_FOLDER = 'app/static/uploads/imgs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Import blueprints
from app.modulate.modulate import modulate_bp
from app.results_upload.results_upload import results_upload_bp
from app.auth.auth import users_bp
from app.main.main import main_bp
from app.students.students  import student_bp
from app.aspects.aspects  import aspects_bp
from app.aspect_questions.aspect_questions import aspect_qns_bp
from app.assessment_v1.assessment_v1 import assessment_bp
from app.scores.scores import scores_bp
from app.programmes.programmes import programmes_bp
from app.terms.terms  import term_bp
from app.school_category.school_category import school_category_bp
from app.schools.schools  import schools_bp
from app.moderate.moderate import moderate_bp
from app.ratings.ratings import ratings_bp
from app.assign_assessor.assign_assessor import assign_assessor_bp
from app.d_f_assign_assessor.d_f_assign_assessor import d_f_assign_assessor_bp
from app.d_f_students.d_f_students import d_f_students_bp
from app.d_f_assessment_v1.d_f_assessment_v1 import d_f_assessment_bp
from app.d_f_scores.d_f_scores import d_f_scores_bp
from app.academic_year.academic_year import academic_year_bp
from app.study_year.study_year import study_year_bp
from app.db_bk.db_bk import db_bk_bp
from app.districts.districts import districts_bp



# Register blueprints
app.register_blueprint(districts_bp,url_prefix='/districts')
app.register_blueprint(db_bk_bp,url_prefix='/db_bk')
app.register_blueprint(study_year_bp,url_prefix='/study_year')
app.register_blueprint(academic_year_bp,url_prefix='/academic_year')
app.register_blueprint(d_f_scores_bp,url_prefix='/d_f_scores')
app.register_blueprint(d_f_assessment_bp,url_prefix='/d_f_assessment')
app.register_blueprint(d_f_students_bp,url_prefix='/d_f_students')
app.register_blueprint(d_f_assign_assessor_bp,url_prefix='/d_f_assign_assessor')
app.register_blueprint(modulate_bp,url_prefix='/modulate')
app.register_blueprint(results_upload_bp,url_prefix='/results_upload')
app.register_blueprint(assign_assessor_bp,url_prefix='/assign_assessor')
app.register_blueprint(ratings_bp,url_prefix='/ratings')
app.register_blueprint(moderate_bp,url_prefix='/moderate')
app.register_blueprint(schools_bp,url_prefix='/schools')
app.register_blueprint(school_category_bp,url_prefix='/school_category')
app.register_blueprint(term_bp,url_prefix='/terms')
app.register_blueprint(programmes_bp,url_prefix='/programmes')
app.register_blueprint(scores_bp,url_prefix='/scores')
app.register_blueprint(assessment_bp,url_prefix='/assessment')
app.register_blueprint(aspect_qns_bp,url_prefix='/aspect_qns')
app.register_blueprint(aspects_bp, url_prefix='/aspects')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(main_bp, url_prefix='/') 
