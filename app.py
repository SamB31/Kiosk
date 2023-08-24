from flask import Flask, redirect, render_template, request, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import csv


# Create a Flask app instance
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.secret_key = 'fsdjfsldkfjskldjflksdjflksdjf' 
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'sblanton@mrapats.com'
app.config['MAIL_PASSWORD'] = 'nnmvkzfewuffiikp'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)


 
class Students(db.Model):
    studentID = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(120), nullable=False)
    lastname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    borrowings = db.relationship('Borrower', backref='student', lazy=True)

class Borrower(db.Model):
    borrowerID = db.Column(db.Integer, primary_key=True)
    what = db.Column(db.String(120), nullable=False)
    studentID = db.Column(db.Integer, db.ForeignKey('students.studentID'))
    turned_in = db.Column(db.Boolean(), nullable=False )
 
class Historical(db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(120), nullable=False)
    lastname = db.Column(db.String(120), nullable=False)
    what = db.Column(db.String(120), nullable=False)



def send_charge_email():
    with app.app_context():
        # Fetch all borrowers
        borrowers = Borrower.query.all()
        
        if not borrowers:
            return
        
        summary_list = []
        for borrower in borrowers:
            student = Students.query.filter_by(studentID=borrower.studentID).first()

            borrowed_item = borrower.what
            charge = "$5" if borrowed_item == "Charger" else "$10" if borrowed_item == "Computer" else "$0"

            summary_list.append(f"{student.firstname} {student.lastname} - {borrowed_item}: {charge}")
        
        # Convert the list to a string
        summary_str = "\n".join(summary_list)

        # Craft the email message
        msg = Message("Student Charges",
                      sender="sblanton@mrapats.com",
                      recipients=["sblanton@mrapats.org"])
        
        msg.body = f"***This is an automated email***\n\n{summary_str}"
        
        # Send the email
        mail.send(msg)
        
        # Craft the email message
        # List of recipients where turned_in is True
        recipients_turned_in = [borrower.student.email for borrower in borrowers if borrower.turned_in]

        # List of recipients where turned_in is False
        recipients_not_turned_in = [borrower.student.email for borrower in borrowers if not borrower.turned_in]

        if recipients_turned_in:
            msg1 = Message("Borrowed Item was turned in",
                        sender="sblanton@mrapats.com",
                        bcc=recipients_turned_in)
            
            msg1.body = "***This is an automated email***\n\nYour borrowed item was turned into and a charge was added to your MyBackpack."
            mail.send(msg1)

            borrowers_to_delete = Borrower.query.join(Students, Borrower.studentID == Students.studentID).filter(Students.email.in_(recipients_turned_in)).all()
            
            # Delete these students
            for student in borrowers_to_delete:
                db.session.delete(student)

            try:
                db.session.commit()
            except:
                db.session.rollback()

        if recipients_not_turned_in:
            msg2 = Message("Borrowed item not returned",
                        sender="sblanton@mrapats.com",
                        bcc=recipients_not_turned_in)
            
            msg2.body = f"***This is an automated email***\n\nYour borrowed item was not turned in. A charge has been added to your MyBackPack. If the device is not turned in by tomorrow 5pm you will recieve another charge."
            mail.send(msg2)

scheduler = BackgroundScheduler()
scheduler.add_job(func=send_charge_email, trigger="interval", days=1, start_date='2023-08-22 14:26:00') # assuming you want it daily at 5pm
#scheduler.add_job(func=send_charge_email, trigger="interval", days=1, start_date='2023-08-22 17:00:00') # assuming you want it daily at 5pm
scheduler.start()
        

def send_confirmation_email(studentID):
    with app.app_context():

        borrower = Borrower.query.filter_by(studentID=studentID).first()

        # Craft the email message
        recipients = [borrower.student.email]
        
        msg = Message(f"{borrower.what} checkout confirmation",
                      sender="sblanton@mrapats.com",
                      recipients=recipients)
        
        msg.body = f"***This is an automated email***\n\nYou have borrowed a {str.lower(borrower.what)} and a your my backpack account will be charged at 5pm."
        
        # Send the email
        mail.send(msg)


def load_students_from_csv(file_path):
    with app.app_context():  # ensure you're in the app context if this function is run outside of a request context
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                student_id = int(row['studentID'])
                firstname = row['firstname']
                lastname = row['lastname']
                email = row['email']

                # Check if student already exists
                existing_student = Students.query.filter_by(studentID=student_id).first()
                if existing_student:
                    flash(f"Student with ID {student_id} already exists.", 'warning')
                    continue

                new_student = Students(
                    studentID=student_id,
                    firstname=firstname,
                    lastname=lastname,
                    email=email
                )

                db.session.add(new_student)
            try:
                db.session.commit()
                flash('Students loaded successfully!', 'success')
            except:
                db.session.rollback()
                flash('Error occurred while loading students.', 'danger')


@app.route('/startup')
def startup():
    db.create_all()
    load_students_from_csv('students.csv')
    return redirect('/')
 

@app.route('/')
def hello_world():
 
    return render_template('index.html') 

 
@app.route('/add_borrower', methods=['POST'])
def add_borrower():
    if request.method == 'POST':
        email = request.form['email']
        what = request.form['what'] 

        student = Students.query.filter_by(email=email).first()

        borrower = Borrower.query.filter_by(studentID=student.studentID).first()

        if borrower:
            flash(f"You currently have a {str.lower(borrower.what)} checked out. Please return it to borrow something else", 'danger')
            return redirect('/')

        # If student does not exist in Students table
        if not student:
            flash('Student not found. Please ensure you are registered.', 'danger')
            return redirect('/')

        # If student exists
        new_borrower = Borrower(what=what, studentID=student.studentID, turned_in=False)

        try:
            db.session.add(new_borrower)
            db.session.commit()
            send_confirmation_email(student.studentID)
            flash('Item borrowed successfully', 'success')
            return redirect('/')
        except:
            flash('Error occurred. Please try again.', 'danger')
            return redirect('/')
    

@app.route('/return', methods=['POST'])
def returning():

    if request.method == 'POST':
        email = request.form['email']
        student = Students.query.filter_by(email=email).first()

        

        if not student:
            flash('Student not found. Please ensure you are registered.', 'danger')
            return redirect('/')

        borrower_entry = Borrower.query.filter_by(studentID=student.studentID).first()

        if not borrower_entry:
            flash('You have nothing to return', 'danger')
            return redirect('/')
         
        if borrower_entry.turned_in:
            flash('You have already returned everything', 'danger')
            return redirect('/')
            
        
        borrower_entry.turned_in = True

        try:
            db.session.commit()
            flash("You have successfully returned the item", 'success')
            return redirect('/')
            
        except Exception as e:
            flash(f"Error updating student email: {e}", 'danger')
            return redirect('/')




# Run the app when this script is executed
if __name__ == '__main__':
    app.run(debug=True)