from flask import Flask
from config import Config
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# ✅ Secret key for session signing
app.config['SECRET_KEY'] = 'your_secret_key_here'

# ✅ Ensure session is permanent and has a defined lifetime
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=3000)

# CSRF protection
csrf = CSRFProtect(app)

# Uploads path
UPLOAD_FOLDER = 'app/static/uploads/imgs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Import blueprints
from app.modulate.modulate import modulate_bp

from app.auth.auth import users_bp
from app.main.main import main_bp
from app.students.students import student_bp
from app.aspects.aspects import aspects_bp
from app.aspect_questions.aspect_questions import aspect_qns_bp
from app.assessment.assessment import assessment_bp
from app.scores.scores import scores_bp


from app.school_category.school_category import school_category_bp
from app.schools.schools import schools_bp
from app.moderate.moderate import moderate_bp
from app.ratings.ratings import ratings_bp

from app.districts.districts import districts_bp
from app.demo_data.demo_data import demo_data_bp
from app.assign_ra.assign_ra import assign_ra_bp

# Register blueprints
app.register_blueprint(assign_ra_bp, url_prefix='/assign_ra')
app.register_blueprint(demo_data_bp, url_prefix='/demo_data')
app.register_blueprint(districts_bp, url_prefix='/districts')



app.register_blueprint(modulate_bp, url_prefix='/modulate')


app.register_blueprint(ratings_bp, url_prefix='/ratings')
app.register_blueprint(moderate_bp, url_prefix='/moderate')
app.register_blueprint(schools_bp, url_prefix='/schools')
app.register_blueprint(school_category_bp, url_prefix='/school_category')


app.register_blueprint(scores_bp, url_prefix='/scores')
app.register_blueprint(assessment_bp, url_prefix='/assessment')
app.register_blueprint(aspect_qns_bp, url_prefix='/aspect_qns')
app.register_blueprint(aspects_bp, url_prefix='/aspects')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(main_bp, url_prefix='/')
