from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'


    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(100),nullable=False,unique=True)
    password = db.Column(db.String(80) , nullable=False)

    def __repr__(self):
        return f"Admin {self.username}"


    
class Student(db.Model):
    __tablename__ = 'students'


    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100),nullable=False)
    email = db.Column(db.String(100),nullable=False , unique=True)
    password = db.Column(db.String(80),nullable=False)
    phone = db.Column(db.String(30))
    age = db.Column(db.Integer)
    department = db.Column(db.String(140))
    blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    bookings = db.relationship(
        'Booking',
        backref='student'
    )

    def __repr__(self):
        return f"Student {self.name}"

class Examiner(db.Model):
    __tablename__ = 'examiners'

    id = db.Column(db.Integer , primary_key=True)
    name = db.Column(db.String(100),nullable=False)
    email = db.Column(db.String(100) , nullable=False , unique=True)
    password = db.Column(db.String(80) , nullable=False)
    phone = db.Column(db.String(50))
    department = db.Column(db.String(150))
    approved = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean , default=True)
    created_at = db.Column(db.DateTime , default=datetime.now)
    exam_slots = db.relationship(
        'ExamSlot',
        backref="examiner"
    )

    def __repr__(self):
        return f"Examiner {self.name}"

class Courses(db.Model):
    __tablename__ =  'courses'
    id = db.Column(db.Integer , primary_key=True)
    course_code = db.Column(db.String(50) , nullable=False , unique=True)
    course_name = db.Column(db.String(80) , nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(30) , default='Active')
    

    examinations = db.relationship(
        'Examination',
        backref='course',
        cascade='all, delete-orphan',
        lazy=True
    )

    def __repr__(self):
        return f" Course {self.course_name}"

class Examination(db.Model):
    __tablename__ = 'examinations'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer , db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(40) , nullable=False)
    duration = db.Column(db.Integer , nullable=False)
    max_marks = db.Column(db.Float , nullable=False)
    slot_creation_start = db.Column(db.DateTime , nullable=False)
    slot_creation_end = db.Column(db.DateTime , nullable=False)
    booking_start = db.Column(db.DateTime , nullable=False)
    booking_end = db.Column(db.DateTime , nullable=False) 
    status = db.Column(db.String(30) , default='draft')
    slot_creation_open = db.Column(db.Boolean, default=True,nullable=False)
    
    booking_open = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )
   
    rubrics = db.relationship(
        'Rubric',
        backref='examination',
        cascade='all, delete-orphan',
    )
    exam_slots = db.relationship(
        'ExamSlot',
        backref="examination"
    )
    def __repr__(self):
        return f"Examination {self.name}"

class Rubric(db.Model):
    __tablename__ ='rubrics'

    id = db.Column(db.Integer , primary_key=True)
    examination_id = db.Column(db.Integer , db.ForeignKey('examinations.id') , nullable=False )
    criteria_name = db.Column(db.String(120) , nullable=False)
    max_marks = db.Column(db.Float , nullable=False)
    weightage =  db.Column(db.Float , nullable=False)
    description = db.Column(db.Text)
    
    evaluations = db.relationship(
        'Evaluation',
        backref='rubric'
    )

    def __repr__(self):
        return f"Rubric {self.criteria_name}"

class ExamSlot(db.Model):
    __tablename__ = 'exam_slots'

    id = db.Column(db.Integer , primary_key=True)
    examination_id = db.Column(db.Integer , db.ForeignKey('examinations.id') , nullable=False)
    examiner_id = db.Column(db.Integer , db.ForeignKey('examiners.id') , nullable=False)
    date = db.Column(db.Date , nullable=False) 
    start_time = db.Column(db.Time , nullable=False)
    end_time = db.Column(db.Time , nullable=False)
    capacity = db.Column(db.Integer , nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30) , default='Active')
    
    
    bookings = db.relationship(
        'Booking',
        backref="slot"
    )

    def __repr__(self):
        return f"Exam Slot {self.id}"

class Booking(db.Model):
    __tablename__= 'bookings'
    id = db.Column(db.Integer , primary_key=True)
    student_id = db.Column(db.Integer , db.ForeignKey('students.id') , nullable=False)
    slot_id = db.Column(db.Integer , db.ForeignKey('exam_slots.id') , nullable=False)
    booking_date = db.Column("boking_date" , db.DateTime , default=datetime.now)
    status = db.Column(db.String(30) , default='Booked')
    result_published = db.Column(db.Boolean , default=False)

    evaluations = db.relationship(
        "Evaluation",
        backref="booking"
    )
    
   

    def __repr__(self):
        return f"Booking {self.id}"
    
class Evaluation(db.Model):
    __tablename__ = "evaluations"

    __table_args__ = (
        db.UniqueConstraint(
            "booking_id",
            "rubric_id",
            name="unique_booking_rubric"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id"),
        nullable=False
    )

    rubric_id = db.Column(
        db.Integer,
        db.ForeignKey("rubrics.id"),
        nullable=False
    )

    marks = db.Column(
        db.Float,
        nullable=False
    )

    remarks = db.Column(db.Text)

    evaluated_at = db.Column(
        db.DateTime,
        default=datetime.now
    )
    def __repr__(self):
        return f"<Evaluation {self.id}>"


class BookingHistory(db.Model):
    __tablename__ = "booking_history"

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id"),
        nullable=False
    )

    old_slot_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_slots.id"),
        nullable=False
    )

    new_slot_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_slots.id"),
        nullable=False
    )

    changed_by = db.Column(
        db.Integer,
        db.ForeignKey("admins.id"),
        nullable=False
    )

    changed_at = db.Column(
        db.DateTime,
        default=datetime.now
    )

    reason = db.Column(db.Text)

    old_slot = db.relationship(
        "ExamSlot",
        foreign_keys=[old_slot_id]
    )

    new_slot = db.relationship(
        "ExamSlot",
        foreign_keys=[new_slot_id]
    )

    booking = db.relationship(
        "Booking",
        backref="history"
    )

    admin = db.relationship("Admin")

    def __repr__(self):
        return f"<BookingHistory {self.id}>"

        





    