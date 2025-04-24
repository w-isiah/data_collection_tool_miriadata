import os
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', '1234')  # For session management
    MYSQL_HOST = 'localhost'  # Change to your MySQL server details
    MYSQL_USER = 'root'
    MYSQL_PASSWORD =''
    MYSQL_DB = 'miriadata'



