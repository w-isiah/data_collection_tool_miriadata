import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
import mysql.connector

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user="root",
            password='',
            database='teaching_practice'
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None


# Fetch data from the database
conn = get_db_connection()
if not conn:
    print("Failed to connect to the database.")
    exit()

cursor = conn.cursor(dictionary=True)

# Fetch programmes, terms, and schools from the database
cursor.execute("SELECT id, programme_name FROM programmes ORDER BY programme_name")  # Removed ASC
programmes = [row['programme_name'] for row in cursor.fetchall()]

cursor.execute("SELECT id, term FROM terms ORDER BY term")  # Removed ASC
terms = [row['term'] for row in cursor.fetchall()]

cursor.execute("SELECT id, name FROM schools ORDER BY name")  # Removed ASC
schools = [row['name'] for row in cursor.fetchall()]

cursor.execute("SELECT id, academic_year FROM academic_year ORDER BY academic_year")
academic_year = [row['academic_year'] for row in cursor.fetchall()]

cursor.execute("SELECT id, study_year FROM study_year ORDER BY study_year")  # Removed ASC
study_year = [row['study_year'] for row in cursor.fetchall()]


cursor.close()
conn.close()

# Create a new workbook and select the active worksheet
wb = openpyxl.Workbook()
ws1 = wb.active
ws1.title = "Students Template"

# Add headers to the first sheet
ws1.append(["student_teacher", "reg no", "Semester", "School", "programmes", "Academic Year", "Study Year"])

# Create a second sheet for drop-down data (optional)
ws2 = wb.create_sheet("drop_down data")

# Add drop-down lists to the second sheet (optional)
ws2.append(["Terms", "programmes", "Schools", "academic_year", "study_year"])
ws2.append([", ".join(terms), ", ".join(programmes), ", ".join(schools), ", ".join(academic_year), ", ".join(study_year)])

# Create data validation for Term
dv_term = DataValidation(type="list", formula1=f'"{",".join(terms)}"', allow_blank=True)
ws1.add_data_validation(dv_term)
dv_term.add("C2:C100")  # Apply to rows 2 to 100 in the Term column

# Create data validation for Programmes
dv_programmes = DataValidation(type="list", formula1=f'"{",".join(programmes)}"', allow_blank=True)
ws1.add_data_validation(dv_programmes)
dv_programmes.add("E2:E100")  # Apply to rows 2 to 100 in the Programmes column

# Create data validation for School
dv_school = DataValidation(type="list", formula1=f'"{",".join(schools)}"', allow_blank=True)
ws1.add_data_validation(dv_school)
dv_school.add("D2:D100")  # Apply to rows 2 to 100 in the School column

# Create data validation for Academic Year
dv_academic_year = DataValidation(type="list", formula1=f'"{",".join(academic_year)}"', allow_blank=True)
ws1.add_data_validation(dv_academic_year)
dv_academic_year.add("F2:F100")  # Apply to rows 2 to 100 in the Academic Year column

# Create data validation for Study Year
dv_study_year = DataValidation(type="list", formula1=f'"{",".join(study_year)}"', allow_blank=True)
ws1.add_data_validation(dv_study_year)
dv_study_year.add("G2:G100")  # Apply to rows 2 to 100 in the Study Year column

# Save the workbook
try:
    wb.save("Students_template.xlsx")
    print("Workbook saved successfully.")
except Exception as e:
    print(f"Error saving workbook: {e}")
