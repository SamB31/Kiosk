from flask import Flask, redirect, render_template, request, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import psycopg2
import csv
import threading
import os

# Create a Flask app instance
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:2107@localhost:5433/postgres'
app.secret_key = 'fsdjfsldkfjskldjflksdjflksdjf' 
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'sblanton@mrapats.com'
app.config['MAIL_PASSWORD'] = 'nnmvkzfewuffiikp'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

time = datetime.now().strftime("%B %d, %Y %I:%M %p")

class Students(db.Model):
    studentID = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(120), nullable=False)
    lastname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    borrowings = db.relationship('Borrower', backref='student', lazy=True)
    card = db.relationship('Card', backref='student', lazy=True)

class Borrower(db.Model):
    borrowerID = db.Column(db.Integer, primary_key=True)
    what = db.Column(db.String(120), nullable=False)
    studentID = db.Column(db.Integer, db.ForeignKey('students.studentID'))
    turned_in = db.Column(db.Boolean(), nullable=False )
 
class Card(db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    what = db.Column(db.String(120), nullable=False)
    studentID = db.Column(db.Integer, db.ForeignKey('students.studentID'))

class Historical(db.Model): 
    ID = db.Column(db.Integer, primary_key=True)
    studentID = db.Column(db.Integer, db.ForeignKey('students.studentID'))
    what = db.Column(db.String(120), nullable=False)
    when = db.Column(db.DateTime)


def write_to_log(message, category):
    # Directory to store log files
    log_dir = 'logs'
    
    # Create directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Define the path of the log file based on the category
    log_file_path = os.path.join(log_dir, f"{category}.log")

    # Write the message to the log file
    with open(log_file_path, 'a') as file:
        file.write(f"{message}\n")


def send_charge_email():
    with app.app_context():
        # Fetch all borrowers
        borrowers = Borrower.query.all()
        cards = Card.query.all()
        
        if not borrowers and cards:
            print('Nothing to send')
            return
        
        summary_list = []
        if borrowers:
            for borrower in borrowers:
                student = Students.query.filter_by(studentID=borrower.studentID).first()

                borrowed_item = borrower.what
                charge = "$5" if borrowed_item == "Charger" else "$10" if borrowed_item == "Computer" else "$0"

                summary_list.append(f"{student.firstname} {student.lastname} - {borrowed_item}: {charge}")

        if cards:
            for card in cards:
                student = Students.query.filter_by(studentID=card.studentID).first()

                replace_id = card.what
                charge = "$10"

                summary_list.append(f"{student.firstname} {student.lastname} - {replace_id}: {charge}")

                db.session.delete(card)

            try:
                db.session.commit()
            except Exception as e:
                write_to_log(f"{time}-{str(e)}", "error")
                db.session.rollback()
        
        
        summary_str = "\n".join(summary_list)

        # Craft the email message
        msg = Message("Student Charges",
                      sender="sblanton@mrapats.com",
                      recipients=["sblanton@mrapats.org"])
        
        msg.body = f"***This is an automated email***\n\n{summary_str}"
        
        try:
            mail.send(msg)
        except Exception as e:
            write_to_log(f"{time}-{str(e)}", "error")

        
        recipients_turned_in = [borrower.student.email for borrower in borrowers if borrower.turned_in]

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
            except Exception as e:
                write_to_log(f"{time}-{str(e)}", "error")
                db.session.rollback()

        if recipients_not_turned_in:
            msg2 = Message("Borrowed item not returned",
                        sender="sblanton@mrapats.com",
                        bcc=recipients_not_turned_in)
            
            msg2.body = f"***This is an automated email***\n\nYour borrowed item was not turned in. A charge has been added to your MyBackPack. Please turn in your item to stop future charges" 
            
            try:
                mail.send(msg2) 
            except Exception as e:
                write_to_log(f"{time}-{str(e)}", "error")



scheduler = BackgroundScheduler()
scheduler.add_job(func=send_charge_email, trigger="interval", days=1, start_date='2023-08-22 17:00:00', weekdays="0-4") # assuming you want it daily at 5pm 
#scheduler.add_job(func=send_charge_email, trigger="interval", days=1, start_date='2023-08-22 17:00:00') # assuming you want it daily at 5pm
scheduler.start()
        

def send_confirmation_email(studentID):
    with app.app_context():
        try:
            borrower = Borrower.query.filter_by(studentID=studentID).first()

            # Craft the email message
            recipients = [borrower.student.email]
            
            msg = Message(f"{borrower.what} checkout confirmation",
                        sender="sblanton@mrapats.com",
                        recipients=recipients)
            
            msg.body = f"***This is an automated email***\n\nYou have borrowed a {str.lower(borrower.what)} and a your my backpack account will be charged at 5pm. If the {str.lower(borrower.what)} is not returned before 5pm you will be charged for another day."
            
            # Send the email
            mail.send(msg)
        except Exception as e:
            # Log the error message
            write_to_log(f"{time}-{str(e)}", "error")


def send_email_in_background(studentID):
    email_thread = threading.Thread(target=send_confirmation_email, args=(studentID,))
    email_thread.start()


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
            except Exception as e:
                write_to_log(f"{time}-{str(e)}", "error")
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

@app.route('/cards')
def show_cards():
    all_cards = Card.query.all()
    return render_template('cards.html', cards=all_cards)

 
@app.route('/add_borrower', methods=['POST'])
def add_borrower():
    if request.method == 'POST':
        email = request.form['email']
        what = request.form['what'] 

        student = Students.query.filter_by(email=email).first()

        if not student:
            flash('Student not found. Please use an MRA provided email address.', 'danger')
            return redirect('/')
        

        

        borrower = Borrower.query.filter_by(studentID=student.studentID).first()

        if borrower:
            flash(f"You currently have a {str.lower(borrower.what)} checked out. Please return it to borrow something else", 'danger')
            return redirect('/')

        # If student does not exist in Students table


        # If student exists
        new_borrower = Borrower(what=what, studentID=student.studentID, turned_in=False)
        historical = Historical(what=what, studentID=student.studentID, when=datetime.now())
        
        try:
            db.session.add(new_borrower)
            db.session.add(historical)
            db.session.commit()
            send_email_in_background(student.studentID)
            flash('Item borrowed successfully', 'success')
            return redirect('/')
        except Exception as e:
            write_to_log(f"{time}-{str(e)}", "error")
            flash('Error occurred. Please try again.', 'danger')
            return redirect('/')
    

@app.route('/borrower', methods=['POST','GET'])
def borrower():
    borrowers = Borrower.query.all()
    if request.method == 'POST':
        borrowerID = request.form['borrowerID'] 
        borrower = db.session.get(Borrower, borrowerID)
        db.session.delete(borrower)
        try:
            db.session.commit()
            flash('Student absolved', 'success')
            return redirect('/borrower')
        except Exception as e:
            write_to_log(f"{time}-{str(e)}", "error")
            flash('Error occurred. Please try again.', 'danger')
            return redirect('/borrower')
    
    return render_template('borrower.html', borrowers=borrowers)

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
            write_to_log(f"{time}-{str(e)}", "error")
            flash(f"Error updating student email: {e}", 'danger')
            return redirect('/')

@app.route('/replace_id', methods=['POST'])
def replace_id():

    if request.method == 'POST':
        email = request.form['email']
        student = Students.query.filter_by(email=email).first()

        

        if not student:
            flash('Student not found. Please ensure you are registered.', 'danger')
            return redirect('/')

        card_entry = Card.query.filter_by(studentID=student.studentID).first()

        if card_entry:
            flash('You have already ordered an ID today', 'danger')
            return redirect('/')
        
        new_card = Card(what="ID", studentID=student.studentID)
        historical = Historical(what="ID", studentID=student.studentID, when=datetime.now())
        db.session.add(historical)
        db.session.add(new_card)

        try:
            db.session.commit()
            flash("Your ID has been ordered. Come pick it up later today.", 'success')
            return redirect('/')
            
        except Exception as e:
            write_to_log(f"{time}-{str(e)}", "error")
            flash(f"Error ordering ID: {e}", 'danger')
            return redirect('/')
        
@app.route('/historical', methods=['GET', 'POST'])
def historical(): 
    
    if request.method == 'POST':
        search = request.form.get('search')
        students = Students.query.filter(Students.lastname.ilike(f"%{search}%")).all()
        return render_template('history.html', students=students)
    else:
        students = Students.query.all()  # Fetch all Students records
        return render_template('history.html', active_page='Students', students=students)
    
@app.route('/student/<int:studentID>/', methods=['GET'])
def student_details(studentID):
    student = Students.query.get_or_404(studentID)
    history = Historical.query.filter_by(studentID=studentID).all()
    

    return render_template('student_details.html', student=student, history=history)


# Run the app when this script is executed
if __name__ == '__main__':
    app.run()