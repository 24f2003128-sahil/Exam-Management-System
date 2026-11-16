from flask import Flask , render_template , redirect , url_for , session , request , flash 
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash , check_password_hash
from datetime import datetime
from models import db, Admin, Student, Examiner , Courses , Examination , ExamSlot , Rubric , Booking , Evaluation , BookingHistory
app=Flask(__name__)
app.config["SECRET_KEY"] = "examination-secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///examination.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


@app.route('/')
def home():
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))

    if session.get("role") == "examiner":
        return redirect(url_for("examiner_dashboard"))

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    return render_template("index.html")


@app.route('/login' , methods=['GET','POST'])
def login():

    if request.method == 'POST':

        #========Admin Login=====#

        email = request.form["email"]
        password = request.form["password"]

        admin = Admin.query.filter_by(
            username=email
        ).first()

        if admin and check_password_hash(admin.password , password):
            session.clear()

            session["user_id"] = admin.id
            session["role"] = "admin"

            flash(
                "Admin login Successfully!",
                "success"
            )
            return redirect(url_for('admin_dashboard'))

        #=======Student Login==========#
        student = Student.query.filter_by(
            email=email
        ).first()

        if student and check_password_hash(student.password , password):

            if student.blacklisted:
                flash(
                    "Your account is blocked by admin",
                    "danger"
                )

                return redirect(url_for('login'))
            session.clear()

            session["user_id"] = student.id
            session['role'] = "student"

            flash(
                "Student login successfully!",
                "success"
            )
            return redirect(url_for('student_dashboard'))



        #==========Examiner Login====#
        examiner = Examiner.query.filter_by(
            email=email
        ).first()

        if examiner and check_password_hash(examiner.password , password):

            if not examiner.active:
                flash(
                    "Your  examiner accouunt is inactive",
                    "danger"
                )
                return redirect(url_for('login'))
            if not examiner.approved:
                flash(
                    "Your account is waiting for admin Approval  !",
                    "danger"
                )
                return redirect(url_for('login'))
            
            session.clear()

            session["user_id"] = examiner.id
            session["role"] = "examiner"

            flash(
                "Examiner Login Successfully !",
                "success"
            )
            return redirect(url_for('examiner_dashboard'))
        flash(
            "Invalid Credentials",
            "danger"
        )

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    flash(
        "You have been logged out",
        "success"
    )
    return redirect(url_for('home'))

#===============DASHBOARDS=========#
@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("login")
        )
    total_courses = Courses.query.count()
    total_examinations = Examination.query.count()
    total_examiners = Examiner.query.count()
    total_students = Student.query.count()
    total_slots = ExamSlot.query.count()
    total_bookings = Booking.query.count()

    return render_template(
        "admin/dashboard.html",
        total_courses=total_courses,
        total_examinations=total_examinations,
        total_examiners=total_examiners,
        total_students=total_students,
        total_slots=total_slots,
        total_bookings=total_bookings
    )




#=========Student Dashboard=======#

@app.route('/student/dashboard')
def student_dashboard():
    if session.get("role") != "student":
        flash("Access denied. Student login required.", "danger")
        return redirect(url_for("login"))

    student = db.session.get(Student, session.get("user_id"))

    if not student or student.blacklisted:
        session.clear()
        flash("Your student account is unavailable.", "danger")
        return redirect(url_for("login"))

    current_time = datetime.now()
    # Get upcoming exams booked by this student
    upcoming_bookings = Booking.query.join(
        ExamSlot,
        Booking.slot_id == ExamSlot.id
    ).filter(
        Booking.student_id == student.id,
        Booking.status.ilike("Booked"),
        ExamSlot.date >= current_time.date()
    ).order_by(
        ExamSlot.date,
        ExamSlot.start_time
    ).all()


    # Get all published examinations
    all_examinations = Examination.query.filter(
        Examination.status.ilike("published")
    ).order_by(Examination.name).all()

    # Get search and filter values from URL
    search_query = request.args.get("q", "").strip().lower()
    selected_course = request.args.get("course", "")
    selected_type = request.args.get("exam_type", "")

    # Get courses and examination types for dropdowns
    courses = []

    for exam in all_examinations:
        if exam.course not in courses:
            courses.append(exam.course)

    exam_types = []

    for exam in all_examinations:
        if exam.exam_type not in exam_types:
            exam_types.append(exam.exam_type)

    # Search by examination name or course name
    examinations = all_examinations

    # Get upcoming active exam slots
    upcoming_slots = ExamSlot.query.join(
        Examination,
        ExamSlot.examination_id == Examination.id
    ).filter(
        Examination.status.ilike("published"),
        ExamSlot.date >= current_time.date(),
        ExamSlot.status.ilike("active")
    ).order_by(
        ExamSlot.date,
        ExamSlot.start_time
    ).all()

    if search_query:
        examinations = [
            exam for exam in examinations
            if search_query in exam.name.lower()
            or search_query in exam.course.course_name.lower()
        ]

    # Filter by course
    if selected_course:
        examinations = [
            exam for exam in examinations
            if str(exam.course_id) == selected_course
        ]

    # Filter by examination type
    if selected_type:
        examinations = [
            exam for exam in examinations
            if exam.exam_type == selected_type
        ]

    return render_template(
        "student/dashboard.html",
        student=student,
        examinations=examinations,
        now=current_time,
        courses=courses,
        exam_types=exam_types,
        search_query=search_query,
        selected_course=selected_course,
        selected_type=selected_type,
        upcoming_slots=upcoming_slots,
        upcoming_bookings=upcoming_bookings
    )
#======Student  Features======#

@app.route("/student/edit-profile", methods=["GET", "POST"])
def student_edit_profile():

    # Check student login
    if session.get("role") != "student":
        flash("Access denied. Student login required.", "danger")
        return redirect(url_for("login"))

    # Get logged-in student
    student = db.session.get(Student, session.get("user_id"))

    if not student or student.blacklisted:
        session.clear()
        flash("Your student account is unavailable.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":

        # Get form values
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        age_value = request.form.get("age", "").strip()
        department = request.form.get("department", "").strip()

        # Validate name
        if not name:
            flash("Name cannot be empty.", "danger")
            return render_template(
                "student/edit_profile.html",
                student=student
            )

        # Validate age
        age = None

        if age_value:
            try:
                age = int(age_value)
            except ValueError:
                flash("Please enter a valid age.", "danger")
                return render_template(
                    "student/edit_profile.html",
                    student=student
                )

            if age <= 0 or age > 100:
                flash("Age must be between 1 and 100.", "danger")
                return render_template(
                    "student/edit_profile.html",
                    student=student
                )

        # Update student information
        student.name = name
        student.phone = phone
        student.age = age
        student.department = department

        db.session.commit()

        flash("Your profile has been updated successfully!", "success")

        return redirect(url_for("student_dashboard"))

    return render_template(
        "student/edit_profile.html",
        student=student
    )

@app.route("/student/book-slot/<int:slot_id>", methods=["POST"])
def student_book_slot(slot_id):
    if session.get("role") != "student":
        flash("Access denied. Student login required.", "danger")
        return redirect(url_for("login"))

    student = db.session.get(Student, session.get("user_id"))

    if not student or student.blacklisted:
        session.clear()
        flash("Your student account is unavailable.", "danger")
        return redirect(url_for("login"))

    slot = db.get_or_404(ExamSlot, slot_id)
    examination = slot.examination
    current_time = datetime.now()

    # Check that the examination is published.
    if examination.status.lower() != "published":
        flash("This examination is not available for booking.", "danger")
        return redirect(url_for("student_dashboard"))
    # Check Admin's manual booking control.
    if not examination.booking_open:
        flash(
            "Student booking has been manually closed by Admin.",
            "danger"
        )
        return redirect(url_for("student_dashboard"))

    # Check the booking window.
    if not (examination.booking_start <= current_time <= examination.booking_end):
        flash("The booking window is currently closed.", "danger")
        return redirect(url_for("student_dashboard"))

    # Check that the slot is active.
    if slot.status.lower() != "active":
        flash("This slot is not active.", "danger")
        return redirect(url_for("student_dashboard"))

    # Do not allow booking a slot whose time has passed.
    if slot.date < current_time.date() or (
        slot.date == current_time.date()
        and slot.end_time <= current_time.time()
    ):
        flash("You cannot book a slot whose time has passed.", "danger")
        return redirect(url_for("student_dashboard"))

    # Check available seats.
    if slot.available_seats <= 0:
        flash("Sorry, this slot is already full.", "danger")
        return redirect(url_for("student_dashboard"))

    # Prevent the same student from booking this examination twice.
    existing_booking = Booking.query.join(
        ExamSlot, Booking.slot_id == ExamSlot.id
    ).filter(
        Booking.student_id == student.id,
        ExamSlot.examination_id == examination.id,
        Booking.status == "Booked"
    ).first()

    if existing_booking:
        flash("You have already booked this examination.", "warning")
        return redirect(url_for("student_dashboard"))

    # Create the booking and reduce the available seats.
    booking = Booking(
        student_id=student.id,
        slot_id=slot.id,
        status="Booked"
    )

    slot.available_seats -= 1

    if slot.available_seats == 0:
        slot.status = "Full"

    db.session.add(booking)
    db.session.commit()

    flash("Examination slot booked successfully!", "success")
    return redirect(url_for("student_dashboard"))


@app.route("/student/my-bookings")
def student_my_bookings():
    if session.get("role") != "student":
        flash("Access denied. Student login required.", "danger")
        return redirect(url_for("login"))

    student = db.session.get(Student, session.get("user_id"))

    if not student or student.blacklisted:
        session.clear()
        flash("Your student account is unavailable.", "danger")
        return redirect(url_for("login"))

    bookings = Booking.query.filter_by(
        student_id=student.id
    ).order_by(
        Booking.booking_date.desc()
    ).all()

    return render_template(
        "student/my_bookings.html",
        student=student,
        bookings=bookings,
        now=datetime.now()
    )

@app.route("/student/cancel-booking/<int:booking_id>", methods=["POST"])
def student_cancel_booking(booking_id):
    if session.get("role") != "student":
        flash("Access denied. Student login required.", "danger")
        return redirect(url_for("login"))

    student = db.session.get(Student, session.get("user_id"))

    if not student or student.blacklisted:
        session.clear()
        flash("Your student account is unavailable.", "danger")
        return redirect(url_for("login"))

    booking = db.session.get(Booking, booking_id)

    if not booking or booking.student_id != student.id:
        flash("Booking not found.", "danger")
        return redirect(url_for("student_my_bookings"))

    if booking.status != "Booked":
        flash("This booking cannot be cancelled.", "warning")
        return redirect(url_for("student_my_bookings"))

    current_time = datetime.now()
    examination = booking.slot.examination

    if current_time >= examination.booking_end:
        flash("The cancellation deadline has passed.", "danger")
        return redirect(url_for("student_my_bookings"))

    if booking.result_published:
        flash("A booking with a published result cannot be cancelled.", "danger")
        return redirect(url_for("student_my_bookings"))

    slot = booking.slot
    
    slot_start = datetime.combine(slot.date, slot.start_time)

    if current_time >= slot_start:
        flash("This slot has already started. Cancellation is not allowed.", "danger")
        return redirect(url_for("student_my_bookings"))

    
    booking.status = "Cancelled"

    if slot.available_seats < slot.capacity:
        slot.available_seats += 1

    if slot.available_seats > 0 and slot.status == "Full":
        slot.status = "Active"

    db.session.commit()

    flash("Booking cancelled successfully.", "success")
    return redirect(url_for("student_my_bookings"))

@app.route("/student/my-results")
def student_my_results():

    if session.get("role") != "student":
        flash("Access denied. Student login required.", "danger")
        return redirect(url_for("login"))

    student = db.session.get(Student, session.get("user_id"))

    if not student or student.blacklisted:
        session.clear()
        flash("Your student account is unavailable.", "danger")
        return redirect(url_for("login"))

    bookings = Booking.query.filter_by(
        student_id=student.id
    ).order_by(
        Booking.booking_date.desc()
    ).all()

    result_data = {}

    for booking in bookings:

        # Cancelled bookings do not have a student result.
        if booking.status != "Booked":
            continue

        examination = booking.slot.examination

        rubrics = Rubric.query.filter_by(
            examination_id=examination.id
        ).all()

        evaluations = Evaluation.query.join(
            Rubric,
            Evaluation.rubric_id == Rubric.id
        ).filter(
            Evaluation.booking_id == booking.id,
            Rubric.examination_id == examination.id
        ).all()

        total_max_marks = sum(
            rubric.max_marks for rubric in rubrics
        )

        obtained_marks = sum(
            evaluation.marks for evaluation in evaluations
        )

        completed = (
            len(rubrics) > 0
            and len(evaluations) == len(rubrics)
        )

        percentage = 0

        if completed and total_max_marks > 0:
            percentage = (
                obtained_marks / total_max_marks
            ) * 100

        result_data[booking.id] = {
            "rubrics": rubrics,
            "evaluations": evaluations,
            "total_max_marks": total_max_marks,
            "obtained_marks": obtained_marks,
            "percentage": percentage,
            "completed": completed
        }

    return render_template(
        "student/my_results.html",
        student=student,
        bookings=bookings,
        result_data=result_data
    )




@app.route('/examiner/dashboard')
def examiner_dashboard():

    # Check whether the logged-in user is an examiner
    if session.get("role") != "examiner":
        flash("Access denied. Examiner login required.", "danger")
        return redirect(url_for("login"))

    # Get the examiner's ID from session
    examiner_id = session.get("user_id")

    examiner = db.session.get(Examiner, examiner_id)

    # Check whether examiner exists, is active and approved
    if not examiner or not examiner.active or not examiner.approved:
        session.clear()
        flash("Your account is inactive or not approved.", "danger")
        return redirect(url_for("login"))

    # Get all examination slots created by this examiner
    exam_slots = ExamSlot.query.filter_by(
        examiner_id=examiner.id
    ).order_by(
        ExamSlot.date.asc(),
        ExamSlot.start_time.asc()
    ).all()

    # Total number of slots
    total_slots = len(exam_slots)

    # Total number of students booked in examiner's slots
    total_booked_students = Booking.query.join(
        ExamSlot,
        Booking.slot_id == ExamSlot.id
    ).filter(
        ExamSlot.examiner_id == examiner.id,
        Booking.status == "Booked"
    ).count()

    # Get all booked students assigned to this examiner
    booked_students = Booking.query.join(
        ExamSlot,
        Booking.slot_id == ExamSlot.id
    ).filter(
        ExamSlot.examiner_id == examiner.id,
        Booking.status == "Booked"
    ).all()

    # Calculate pending evaluations
    pending_evaluations = 0

    for booking in booked_students:

        # Get all rubrics for this examination
        rubrics = Rubric.query.filter_by(
            examination_id=booking.slot.examination_id
        ).all()

        # Count completed rubric evaluations
        completed_evaluations = len(booking.evaluations)

        # Check whether all rubrics have been evaluated
        if len(rubrics) > 0 and completed_evaluations < len(rubrics):
            pending_evaluations += 1

    # Display examiner dashboard
    return render_template(
        "examiner/dashboard.html",
        now=datetime.now(),
        examiner=examiner,
        exam_slots=exam_slots,
        total_slots=total_slots,
        total_booked_students=total_booked_students,
        pending_evaluations=pending_evaluations
    )


#==========Student Registration=========#

@app.route('/register/student' , methods = ['GET' , 'POST' ])
def register_student():
    if request.method == 'POST':
        name = request.form["name"]
        age = request.form["age"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        department = request.form["department"]

        existing_student = Student.query.filter_by(
            email=email
        ).first()
        existing_examiner = Examiner.query.filter_by(
            email=email
        ).first()

        if existing_student or existing_examiner:
            flash(
                "An account with this email already existed",
                "dnager"
            )
            return redirect(url_for("register_student"))
        student = Student(
            name=name,
            email=email,
            password=generate_password_hash(password),
            age=int(age),
            phone=phone,
            department=department
        )
        db.session.add(student)
        db.session.commit()

        flash(
            "Student registration successfull ! Please login.",
            "success"
        )
        return redirect(url_for("login"))
    return render_template("register_student.html")



# ============ EXAMINER REGISTRATION ============

@app.route("/register/examiner", methods=["GET", "POST"])
def register_examiner():

    if request.method == "POST":

        # 1. Get data from the registration form
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        department = request.form.get("department", "").strip()

        # 2. Validate that fields are not empty
        if not all([name, email, phone, password, department]):
            flash(
                "Please fill in all the fields.",
                "danger"
            )
            return redirect(url_for("register_examiner"))

        # 3. Check whether the email already belongs to a student
        existing_student = Student.query.filter_by(
            email=email
        ).first()

        # 4. Check whether the email already belongs to an examiner
        existing_examiner = Examiner.query.filter_by(
            email=email
        ).first()

        # 5. Prevent duplicate accounts
        if existing_student or existing_examiner:
            flash(
                "An account with this email already exists. Please use another email.",
                "danger"
            )
            return redirect(url_for("register_examiner"))

        # 6. Create the examiner account
        examiner = Examiner(
            name=name,
            email=email,
            phone=phone,
            department=department,
            password=generate_password_hash(password),
            active=True,
            approved=False
        )

        # 7. Save the examiner to the database
        db.session.add(examiner)
        db.session.commit()

        # 8. Show success message
        flash(
            "Registration successful! Please wait for admin approval.",
            "success"
        )

        # 9. Redirect to login
        return redirect(url_for("login"))

    # GET request: display the registration form
    return render_template("register_examiner.html")



#=========ADMIN FEATURES=======#

@app.route("/admin/examiner")
def admin_examiners():

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('login'))

    # Get search and filter values
    search_query = request.args.get("q", "").strip().lower()
    approval_status = request.args.get("approval", "")
    active_status = request.args.get("active", "")

    # Get all examiners
    examiners = Examiner.query.order_by(
        Examiner.created_at.desc()
    ).all()

    # Search by examiner name or email
    if search_query:
        examiners = [
            examiner for examiner in examiners
            if search_query in examiner.name.lower()
            or search_query in examiner.email.lower()
        ]

    # Filter by approval status
    if approval_status == "approved":
        examiners = [
            examiner for examiner in examiners
            if examiner.approved == True
        ]

    elif approval_status == "pending":
        examiners = [
            examiner for examiner in examiners
            if examiner.approved == False
        ]

    # Filter by active status
    if active_status == "active":
        examiners = [
            examiner for examiner in examiners
            if examiner.active == True
        ]

    elif active_status == "inactive":
        examiners = [
            examiner for examiner in examiners
            if examiner.active == False
        ]

    return render_template(
        "admin/examiner.html",
        examiners=examiners,
        search_query=search_query,
        approval_status=approval_status,
        active_status=active_status
    )

    
@app.route("/admin/examiner/approve/<int:examiner_id>" , methods=["POST"])
def approve_examiner(examiner_id):

    if session.get('role') != 'admin':

        flash(
            "Acess Denied",
            "danger"
        )

        return redirect(url_for('login'))

    examiner = Examiner.query.get_or_404(examiner_id)

    examiner.approved = True
    examiner.active = True

    db.session.commit()

    flash(
        "Examiner approved succcessfully",
        "success"
    )
    return redirect(url_for("admin_examiners"))

@app.route("/admin/examiner/deactivate/<int:examiner_id>" , methods=['POST'])
def deactivate_examiner(examiner_id):
    if session.get('role') != 'admin':
        flash(
            "Acesss Denied" ,
            "danger"
        )
        return redirect(url_for('login'))
    examiner = Examiner.query.get_or_404(examiner_id)

    examiner.active = False

    db.session.commit()

    flash(
        "Examiner deactivate successfully",
        "warning"
    )

    return redirect(url_for("admin_examiners"))

@app.route(
    "/admin/examiner/activate/<int:examiner_id>",
    methods=["POST"]
)
def activate_examiner(examiner_id):

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    examiner = Examiner.query.get_or_404(examiner_id)

    examiner.active = True

    db.session.commit()

    flash(
        "Examiner activated successfully!",
        "success"
    )

    return redirect(url_for("admin_examiners"))

@app.route('/admin/courses')
def admin_courses():

    if session.get('role') != 'admin':

        flash("Acces Denied" , "danger")
        return redirect(url_for('login'))

    courses = Courses.query.order_by(Courses.id.desc()).all()

    return render_template(
        "admin/courses.html",
        courses=courses
    )
@app.route("/admin/courses/create" , methods=["GET" , "POST"])
def create_course():

    if session.get('role') != 'admin':
        flash("Access Denied" , "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':

        course_code = request.form.get(
            "course_code" , ""
        ).strip().upper()

        course_name = request.form.get(
            "course_name" , ""
        ).strip()

        description = request.form.get(
            "description"  ,  ""
        ).strip()

        if not course_code or not course_name:
            flash(
                "Course code and Course name are required",
                "danger"
            )
            return redirect(url_for('create_course'))

        existing_course = Courses.query.filter_by(
            course_code = course_code
        ).first()

        if existing_course:
            flash(
                "This Course are already exist",
                "danger"
            )
            return redirect(url_for("create_course"))

        course = Courses(
            course_code=course_code,
            course_name=course_name,
            description=description,
            status="Active"
        )
        db.session.add(course)
        db.session.commit()

        flash("Course ceated  successfully" , "success")
        return redirect(url_for("admin_courses"))
    return render_template("admin/create_course.html")

# ============ ADMIN: EDIT COURSE ============

@app.route(
    "/admin/courses/edit/<int:course_id>",
    methods=["GET", "POST"]
)
def edit_course(course_id):

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    course = Courses.query.get_or_404(course_id)

    if request.method == "POST":

        course_code = request.form.get(
            "course_code", ""
        ).strip().upper()

        course_name = request.form.get(
            "course_name", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        if not course_code or not course_name:
            flash(
                "Course code and course name are required.",
                "danger"
            )
            return redirect(
                url_for("edit_course", course_id=course.id)
            )

        duplicate = Courses.query.filter(
            Courses.course_code == course_code,
            Courses.id != course.id
        ).first()

        if duplicate:
            flash(
                "Another course already uses this code.",
                "danger"
            )
            return redirect(
                url_for("edit_course", course_id=course.id)
            )

        course.course_code = course_code
        course.course_name = course_name
        course.description = description

        db.session.commit()

        flash("Course updated successfully!", "success")
        return redirect(url_for("admin_courses"))

    return render_template(
        "admin/edit_course.html",
        course=course
    )
# ============ ADMIN: TOGGLE COURSE STATUS ============

@app.route("/admin/courses/toggle-status/<int:course_id>",methods=["POST"])
def toggle_course_status(course_id):

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    course = Courses.query.get_or_404(course_id)

    if course.status == "Active":
        course.status = "Inactive"
        message = "Course deactivated successfully!"
    else:
        course.status = "Active"
        message = "Course activated successfully!"

    db.session.commit()

    flash(message, "success")
    return redirect(url_for("admin_courses"))

@app.route("/admin/examinations")
def admin_examinations():
    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('login'))

    # Get filter values from URL
    search_query = request.args.get("q", "").strip().lower()
    selected_type = request.args.get("exam_type", "")
    selected_status = request.args.get("status", "")

    # Get all examinations
    all_examinations = Examination.query.order_by(
        Examination.id.desc()
    ).all()

    # Get available examination types
    exam_types = []

    for exam in all_examinations:
        if exam.exam_type and exam.exam_type not in exam_types:
            exam_types.append(exam.exam_type)

    examinations = all_examinations

    # Search by examination name or course details
    if search_query:
        examinations = [
            exam for exam in examinations
            if search_query in (exam.name or "").lower()
            or search_query in (exam.course.course_code or "").lower()
            or search_query in (exam.course.course_name or "").lower()
        ]

    # Filter by examination type
    if selected_type:
        examinations = [
            exam for exam in examinations
            if exam.exam_type == selected_type
        ]

    # Filter by examination status
    if selected_status:
        examinations = [
            exam for exam in examinations
            if exam.status.lower() == selected_status.lower()
        ]

    return render_template(
        "admin/examinations.html",
        examinations=examinations,
        exam_types=exam_types,
        search_query=search_query,
        selected_type=selected_type,
        selected_status=selected_status
    )
@app.route("/admin/examinations/<int:exam_id>/toggle-control/<string:control>", methods=["POST"])
def toggle_exam_control(exam_id, control):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('login'))

    examination = Examination.query.get_or_404(exam_id)

    if control == "slot_creation":
        examination.slot_creation_open = not examination.slot_creation_open

        if examination.slot_creation_open:
            flash("Slot creation has been opened.", "success")
        else:
            flash("Slot creation has been closed.", "warning")

    elif control == "booking":
        examination.booking_open = not examination.booking_open

        if examination.booking_open:
            flash("Student booking has been opened.", "success")
        else:
            flash("Student booking has been closed.", "warning")

    else:
        flash("Invalid control selected.", "danger")
        return redirect(url_for('admin_examinations'))

    db.session.commit()

    return redirect(url_for('admin_examinations'))

@app.route("/admin/examinations/create", methods=["GET", "POST"])
def create_examination():
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    courses = Courses.query.filter_by(status="Active").order_by(
        Courses.course_name
    ).all()

    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        name = request.form.get("name", "").strip()
        exam_type = request.form.get("exam_type", "").strip()

        duration = request.form.get("duration", type=int)
        max_marks = request.form.get("max_marks", type=float)

        slot_creation_start = datetime.fromisoformat(
            request.form.get("slot_creation_start", "")
        )
        slot_creation_end = datetime.fromisoformat(
            request.form.get("slot_creation_end", "")
        )
        booking_start = datetime.fromisoformat(
            request.form.get("booking_start", "")
        )
        booking_end = datetime.fromisoformat(
            request.form.get("booking_end", "")
        )

        course = db.session.get(Courses, course_id) if course_id else None

        if not all([name, exam_type, duration, max_marks, course]):
            flash("Please enter all required fields correctly.", "danger")
            return redirect(url_for("create_examination"))

        if course.status != "Active":
            flash("Please select an active course.", "danger")
            return redirect(url_for("create_examination"))

        if duration <= 0 or max_marks <= 0:
            flash("Duration and maximum marks must be positive.", "danger")
            return redirect(url_for("create_examination"))

        if slot_creation_start >= slot_creation_end:
            flash("Slot creation end must be after its start.", "danger")
            return redirect(url_for("create_examination"))

        if booking_start >= booking_end:
            flash("Booking end must be after its start.", "danger")
            return redirect(url_for("create_examination"))

        examination = Examination(
            course_id=course_id,
            name=name,
            exam_type=exam_type,
            duration=duration,
            max_marks=max_marks,
            slot_creation_start=slot_creation_start,
            slot_creation_end=slot_creation_end,
            booking_start=booking_start,
            booking_end=booking_end,
            status="draft"
        )

        db.session.add(examination)
        db.session.commit()

        flash("Examination created successfully!", "success")
        return redirect(url_for("admin_examinations"))

    return render_template(
        "admin/create_examination.html",
        courses=courses
    )

@app.route("/admin/examinations/edit/<int:examination_id>",methods=["GET", "POST"])
def edit_examination(examination_id):
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    examination = db.get_or_404(Examination, examination_id)
    courses = Courses.query.order_by(Courses.course_name).all()

    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        name = request.form.get("name", "").strip()
        exam_type = request.form.get("exam_type", "").strip()

        duration = request.form.get("duration", type=int)
        max_marks = request.form.get("max_marks", type=float)

        slot_creation_start = datetime.fromisoformat(
            request.form.get("slot_creation_start", "")
        )
        slot_creation_end = datetime.fromisoformat(
            request.form.get("slot_creation_end", "")
        )
        booking_start = datetime.fromisoformat(
            request.form.get("booking_start", "")
        )
        booking_end = datetime.fromisoformat(
            request.form.get("booking_end", "")
        )

        course = db.session.get(Courses, course_id) if course_id else None

        if not all([name, exam_type, duration, max_marks, course]):
            flash("Please enter all required fields correctly.", "danger")
            return redirect(
                url_for("edit_examination", examination_id=examination.id)
            )

        if course.status != "Active":
            flash("Please select an active course.", "danger")
            return redirect(
                url_for("edit_examination", examination_id=examination.id)
            )

        if duration <= 0 or max_marks <= 0:
            flash("Duration and maximum marks must be positive.", "danger")
            return redirect(
                url_for("edit_examination", examination_id=examination.id)
            )

        if slot_creation_start >= slot_creation_end:
            flash("Slot creation end must be after its start.", "danger")
            return redirect(
                url_for("edit_examination", examination_id=examination.id)
            )

        if booking_start >= booking_end:
            flash("Booking end must be after its start.", "danger")
            return redirect(
                url_for("edit_examination", examination_id=examination.id)
            )

        examination.course_id = course_id
        examination.name = name
        examination.exam_type = exam_type
        examination.duration = duration
        examination.max_marks = max_marks
        examination.slot_creation_start = slot_creation_start
        examination.slot_creation_end = slot_creation_end
        examination.booking_start = booking_start
        examination.booking_end = booking_end

        db.session.commit()

        flash("Examination updated successfully!", "success")
        return redirect(url_for("admin_examinations"))

    return render_template(
        "admin/edit_examination.html",
        examination=examination,
        courses=courses
    )

@app.route(
    "/admin/examinations/status/<int:examination_id>",
    methods=["POST"]
)
def update_examination_status(examination_id):
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    examination = db.get_or_404(Examination, examination_id)
    new_status = request.form.get("status", "").strip().lower()

    if new_status not in ["draft", "published", "completed", "cancelled"]:
        flash("Invalid examination status.", "danger")
        return redirect(url_for("admin_examinations"))

    examination.status = new_status
    db.session.commit()

    flash("Examination status updated successfully!", "success")
    return redirect(url_for("admin_examinations"))


@app.route("/admin/rubrics")
def admin_rubrics():
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    rubrics = Rubric.query.order_by(Rubric.id.desc()).all()

    return render_template(
        "admin/rubrics.html",
        rubrics=rubrics
    )


@app.route("/admin/rubrics/create", methods=["GET", "POST"])
def create_rubric():
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    examinations = Examination.query.order_by(
        Examination.name
    ).all()

    if request.method == "POST":
        examination_id = request.form.get("examination_id", type=int)
        criteria_name = request.form.get("criteria_name", "").strip()
        description = request.form.get("description", "").strip()
        max_marks = request.form.get("max_marks", type=float)
        weightage = request.form.get("weightage", type=float)

        examination = (
            db.session.get(Examination, examination_id)
            if examination_id else None
        )

        if not all([examination, criteria_name, max_marks, weightage]):
            flash("Please fill in all required fields correctly.", "danger")
            return redirect(url_for("create_rubric"))

        if max_marks <= 0:
            flash("Maximum marks must be greater than zero.", "danger")
            return redirect(url_for("create_rubric"))

        if weightage <= 0 or weightage > 100:
            flash("Weightage must be greater than 0 and at most 100.", "danger")
            return redirect(url_for("create_rubric"))

        rubric = Rubric(
            examination_id=examination_id,
            criteria_name=criteria_name,
            max_marks=max_marks,
            weightage=weightage,
            description=description
        )

        db.session.add(rubric)
        db.session.commit()

        flash("Rubric created successfully!", "success")
        return redirect(url_for("admin_rubrics"))

    return render_template(
        "admin/create_rubric.html",
        examinations=examinations
    )

@app.route("/admin/rubrics/edit/<int:rubric_id>", methods=["GET", "POST"])
def edit_rubric(rubric_id):
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    rubric = db.get_or_404(Rubric, rubric_id)
    examinations = Examination.query.order_by(Examination.name).all()

    if request.method == "POST":
        examination_id = request.form.get("examination_id", type=int)
        criteria_name = request.form.get("criteria_name", "").strip()
        description = request.form.get("description", "").strip()
        max_marks = request.form.get("max_marks", type=float)
        weightage = request.form.get("weightage", type=float)

        examination = (
            db.session.get(Examination, examination_id)
            if examination_id else None
        )

        if not all([examination, criteria_name, max_marks, weightage]):
            flash("Please fill in all required fields correctly.", "danger")
            return redirect(url_for("edit_rubric", rubric_id=rubric.id))

        if max_marks <= 0:
            flash("Maximum marks must be greater than zero.", "danger")
            return redirect(url_for("edit_rubric", rubric_id=rubric.id))

        if weightage <= 0 or weightage > 100:
            flash("Weightage must be greater than 0 and at most 100.", "danger")
            return redirect(url_for("edit_rubric", rubric_id=rubric.id))

        rubric.examination_id = examination_id
        rubric.criteria_name = criteria_name
        rubric.max_marks = max_marks
        rubric.weightage = weightage
        rubric.description = description

        db.session.commit()

        flash("Rubric updated successfully!", "success")
        return redirect(url_for("admin_rubrics"))

    return render_template(
        "admin/edit_rubric.html",
        rubric=rubric,
        examinations=examinations
    )

@app.route("/admin/rubrics/delete/<int:rubric_id>", methods=["POST"])
def delete_rubric(rubric_id):
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    rubric = db.get_or_404(Rubric, rubric_id)

    if rubric.evaluations:
        flash(
            "Cannot delete this rubric because evaluations are associated with it.",
            "danger"
        )
        return redirect(url_for("admin_rubrics"))

    db.session.delete(rubric)
    db.session.commit()

    flash("Rubric deleted successfully!", "success")
    return redirect(url_for("admin_rubrics"))



@app.route("/admin/exam-slots")
def admin_exam_slots():
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    exam_slots = ExamSlot.query.order_by(
        ExamSlot.date.desc(),
        ExamSlot.start_time
    ).all()

    return render_template(
        "admin/exam_slots.html",
        exam_slots=exam_slots
    )


@app.route("/admin/exam-slots/create", methods=["GET", "POST"])
def create_exam_slot():
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    examinations = Examination.query.filter_by(
        status="published"
    ).order_by(Examination.name).all()

    examiners = Examiner.query.filter_by(
        active=True,
        approved=True
    ).order_by(Examiner.name).all()

    if request.method == "POST":
        examination_id = request.form.get("examination_id", type=int)
        examiner_id = request.form.get("examiner_id", type=int)
        date_value = request.form.get("date", "")
        start_value = request.form.get("start_time", "")
        end_value = request.form.get("end_time", "")
        capacity = request.form.get("capacity", type=int)

        examination = (
            db.session.get(Examination, examination_id)
            if examination_id else None
        )

        examiner = (
            db.session.get(Examiner, examiner_id)
            if examiner_id else None
        )

        if not all([
            examination, examiner, date_value,
            start_value, end_value, capacity
        ]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("create_exam_slot"))

        if examination.status.lower() != "published":
            flash("Select a published examination.", "danger")
            return redirect(url_for("create_exam_slot"))

        if not examiner.active or not examiner.approved:
            flash("Select an active and approved examiner.", "danger")
            return redirect(url_for("create_exam_slot"))

        slot_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_value, "%H:%M").time()
        end_time = datetime.strptime(end_value, "%H:%M").time()

        if start_time >= end_time:
            flash("End time must be after start time.", "danger")
            return redirect(url_for("create_exam_slot"))

        if capacity <= 0:
            flash("Capacity must be greater than zero.", "danger")
            return redirect(url_for("create_exam_slot"))

        if start_time.minute or start_time.second or end_time.minute or end_time.second:
            # No restriction on minute values; this block intentionally does nothing.
            pass

        current_time = datetime.now()

        if current_time < examination.slot_creation_start:
            flash("Slot creation has not started yet for this examination.", "danger")
            return redirect(url_for("create_exam_slot"))

        if current_time > examination.slot_creation_end:
            flash("The slot-creation window has closed for this examination.", "danger")
            return redirect(url_for("create_exam_slot"))

        if ExamSlot.query.filter_by(
            examiner_id=examiner_id,
            date=slot_date
        ).filter(
            ExamSlot.start_time < end_time,
            ExamSlot.end_time > start_time
        ).first():
            flash("This examiner already has an overlapping slot.", "danger")
            return redirect(url_for("create_exam_slot"))

        exam_slot = ExamSlot(
            examination_id=examination_id,
            examiner_id=examiner_id,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            available_seats=capacity,
            status="Active"
        )

        db.session.add(exam_slot)
        db.session.commit()

        flash("Exam slot created successfully!", "success")
        return redirect(url_for("admin_exam_slots"))

    return render_template(
        "admin/create_exam_slot.html",
        examinations=examinations,
        examiners=examiners
    )


@app.route("/admin/exam-slots/edit/<int:slot_id>", methods=["GET", "POST"])
def edit_exam_slot(slot_id):
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    slot = db.get_or_404(ExamSlot, slot_id)

    examinations = Examination.query.filter_by(
        status="published"
    ).order_by(Examination.name).all()

    examiners = Examiner.query.filter_by(
        active=True,
        approved=True
    ).order_by(Examiner.name).all()

    if request.method == "POST":
        examination_id = request.form.get("examination_id", type=int)
        examiner_id = request.form.get("examiner_id", type=int)
        date_value = request.form.get("date", "")
        start_value = request.form.get("start_time", "")
        end_value = request.form.get("end_time", "")
        capacity = request.form.get("capacity", type=int)

        examination = (
            db.session.get(Examination, examination_id)
            if examination_id else None
        )
        examiner = (
            db.session.get(Examiner, examiner_id)
            if examiner_id else None
        )

        if not all([
            examination, examiner, date_value,
            start_value, end_value, capacity
        ]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        if examination.status.lower() != "published":
            flash("Select a published examination.", "danger")
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        if not examiner.active or not examiner.approved:
            flash("Select an active and approved examiner.", "danger")
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        slot_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_value, "%H:%M").time()
        end_time = datetime.strptime(end_value, "%H:%M").time()

        if start_time >= end_time:
            flash("End time must be after start time.", "danger")
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        if capacity <= 0:
            flash("Capacity must be greater than zero.", "danger")
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        booked_count = Booking.query.filter_by(
            slot_id=slot.id,
            status="Booked"
        ).count()

        if capacity < booked_count:
            flash(
                "Capacity cannot be less than the number of booked students.",
                "danger"
            )
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        

        overlapping_slot = ExamSlot.query.filter(
            ExamSlot.id != slot.id,
            ExamSlot.examiner_id == examiner_id,
            ExamSlot.date == slot_date,
            ExamSlot.start_time < end_time,
            ExamSlot.end_time > start_time
        ).first()

        if overlapping_slot:
            flash("This examiner already has an overlapping slot.", "danger")
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        # Avoid changing the examination or time of a slot with bookings.
        if booked_count > 0 and (
            slot.examination_id != examination_id
            or slot.date != slot_date
            or slot.start_time != start_time
            or slot.end_time != end_time
        ):
            flash(
                "Cannot change the examination or timing of a slot with booked students.",
                "danger"
            )
            return redirect(url_for("edit_exam_slot", slot_id=slot.id))

        slot.examination_id = examination_id
        slot.examiner_id = examiner_id
        slot.date = slot_date
        slot.start_time = start_time
        slot.end_time = end_time
        slot.capacity = capacity
        slot.available_seats = capacity - booked_count

        db.session.commit()

        flash("Exam slot updated successfully!", "success")
        return redirect(url_for("admin_exam_slots"))

    return render_template(
        "admin/edit_exam_slot.html",
        slot=slot,
        examinations=examinations,
        examiners=examiners
    )

@app.route("/admin/exam-slots/toggle-status/<int:slot_id>", methods=["POST"])
def toggle_exam_slot_status(slot_id):
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    slot = db.get_or_404(ExamSlot, slot_id)

    if slot.status == "Active":
        booked_count = Booking.query.filter_by(
            slot_id=slot.id,
            status="Booked"
        ).count()

        if booked_count > 0:
            flash(
                "Cannot deactivate this slot because students have booked it.",
                "danger"
            )
            return redirect(url_for("admin_exam_slots"))

        slot.status = "Inactive"
        flash("Exam slot deactivated successfully!", "success")

    else:
        slot.status = "Active"
        flash("Exam slot activated successfully!", "success")

    db.session.commit()
    return redirect(url_for("admin_exam_slots"))


@app.route('/admin/students')
def admin_students():
    if session.get('role') != 'admin':
        flash("Access Denied" , "danger")
        return redirect(url_for('login'))
    search = request.args.get("search" , "").strip()

    if search:
        students = Student.query.filter(
            db.or_(
                Student.name.ilike(f"%{search}%"),
                Student.email.ilike(f"%{search}%")
            )
        ).order_by(Student.name.asc()).all()
    else:
        students = Student.query.order_by(Student.name.asc()).all()

    return render_template(
        "admin/students.html",
        students=students,
        search=search   
    )

@app.route("/admin/students/toggle-status/<int:student_id>", methods=["POST"])
def admin_toggle_student_status(student_id):

    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    student = db.session.get(Student, student_id)

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("admin_students"))

    # Toggle student status
    student.blacklisted = not student.blacklisted

    db.session.commit()

    if student.blacklisted:
        flash(
            f"{student.name} has been blocked successfully.",
            "success"
        )
    else:
        flash(
            f"{student.name} has been activated successfully.",
            "success"
        )

    return redirect(url_for("admin_students"))


@app.route("/admin/results")
def admin_results():

    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    admin = db.session.get(Admin, session.get("user_id"))

    if not admin:
        session.clear()
        flash("Admin account not found.", "danger")
        return redirect(url_for("login"))

    bookings = Booking.query.filter_by(
        status="Booked"
    ).order_by(Booking.booking_date.desc()).all()

    result_data = {}

    for booking in bookings:

        examination = booking.slot.examination

        rubrics = Rubric.query.filter_by(
            examination_id=examination.id
        ).all()

        evaluations = Evaluation.query.join(
            Rubric,
            Evaluation.rubric_id == Rubric.id
        ).filter(
            Evaluation.booking_id == booking.id,
            Rubric.examination_id == examination.id
        ).all()

        total_max_marks = sum(
            rubric.max_marks for rubric in rubrics
        )

        obtained_marks = sum(
            evaluation.marks for evaluation in evaluations
        )

        completed = (
            len(rubrics) > 0
            and len(evaluations) == len(rubrics)
        )

        percentage = 0

        if completed and total_max_marks > 0:
            percentage = (obtained_marks / total_max_marks) * 100

        result_data[booking.id] = {
            "rubrics": rubrics,
            "evaluations": evaluations,
            "total_max_marks": total_max_marks,
            "obtained_marks": obtained_marks,
            "percentage": percentage,
            "completed": completed
        }

    return render_template(
        "admin/results.html",
        bookings=bookings,
        result_data=result_data
    )


@app.route("/admin/publish-result/<int:booking_id>", methods=["POST"])
def admin_publish_result(booking_id):

    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    admin = db.session.get(Admin, session.get("user_id"))

    if not admin:
        session.clear()
        flash("Admin account not found.", "danger")
        return redirect(url_for("login"))

    booking = db.session.get(Booking, booking_id)

    if not booking or booking.status != "Booked":
        flash("Valid booking not found.", "danger")
        return redirect(url_for("admin_results"))

    if booking.result_published:
        flash("This result has already been published.", "warning")
        return redirect(url_for("admin_results"))

    examination = booking.slot.examination

    rubrics = Rubric.query.filter_by(
        examination_id=examination.id
    ).all()

    evaluations = Evaluation.query.join(
        Rubric,
        Evaluation.rubric_id == Rubric.id
    ).filter(
        Evaluation.booking_id == booking.id,
        Rubric.examination_id == examination.id
    ).all()

    if not rubrics or len(evaluations) != len(rubrics):
        flash("This student has not completed all evaluations.", "danger")
        return redirect(url_for("admin_results"))

    booking.result_published = True

    db.session.commit()

    flash("Student result published successfully!", "success")

    return redirect(url_for("admin_results"))


@app.route("/admin/bookings")
def admin_view_bookings():
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    search_query = request.args.get("q", "").strip().lower()
    selected_status = request.args.get("status", "")

    bookings = Booking.query.order_by(
        Booking.booking_date.desc()
    ).all()

    # Search by student name, email or examination name
    if search_query:
        bookings = [
            booking for booking in bookings
            if search_query in booking.student.name.lower()
            or search_query in booking.student.email.lower()
            or search_query in booking.slot.examination.name.lower()
        ]

    # Filter by booking status
    if selected_status:
        bookings = [
            booking for booking in bookings
            if booking.status == selected_status
        ]

    return render_template(
        "admin/bookings.html",
        bookings=bookings,
        search_query=search_query,
        selected_status=selected_status
    )

@app.route("/admin/edit-booking/<int:booking_id>", methods=["GET", "POST"])
def admin_edit_booking(booking_id):

    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    admin = db.session.get(Admin, session.get("user_id"))

    if not admin:
        session.clear()
        flash("Admin account not found.", "danger")
        return redirect(url_for("login"))

    booking = db.session.get(Booking, booking_id)

    if not booking or booking.status != "Booked":
        flash("Active booking not found.", "danger")
        return redirect(url_for("admin_view_bookings"))

    if booking.result_published:
        flash("Published results cannot be rescheduled.", "warning")
        return redirect(url_for("admin_view_bookings"))

    current_time = datetime.now()
    examination = booking.slot.examination

    available_slots = ExamSlot.query.filter(
        ExamSlot.examination_id == examination.id,
        ExamSlot.status.in_(["Active", "Full"]),
        ExamSlot.available_seats > 0
    ).order_by(
        ExamSlot.date,
        ExamSlot.start_time
    ).all()

    available_slots = [
        slot for slot in available_slots
        if (
            slot.date > current_time.date()
            or (
                slot.date == current_time.date()
                and slot.start_time > current_time.time()
            )
        )
    ]

    if request.method == "POST":

        try:
            new_slot_id = int(request.form.get("slot_id"))
        except (TypeError, ValueError):
            flash("Please select a valid slot.", "danger")
            return redirect(url_for(
                "admin_edit_booking",
                booking_id=booking.id
            ))

        new_slot = db.session.get(ExamSlot, new_slot_id)

        if not new_slot or new_slot.examination_id != examination.id:
            flash("Invalid examination slot selected.", "danger")
            return redirect(url_for(
                "admin_edit_booking",
                booking_id=booking.id
            ))

        if new_slot.id == booking.slot_id:
            flash("This student is already assigned to this slot.", "warning")
            return redirect(url_for(
                "admin_edit_booking",
                booking_id=booking.id
            ))

        if new_slot.status not in ["Active", "Full"]:
            flash("Selected slot is not active.", "danger")
            return redirect(url_for(
                "admin_edit_booking",
                booking_id=booking.id
            ))

        if new_slot.available_seats <= 0:
            flash("Selected slot is full.", "danger")
            return redirect(url_for(
                "admin_edit_booking",
                booking_id=booking.id
            ))

        if (
            new_slot.date < current_time.date()
            or (
                new_slot.date == current_time.date()
                and new_slot.start_time <= current_time.time()
            )
        ):
            flash("You cannot assign a past slot.", "danger")
            return redirect(url_for(
                "admin_edit_booking",
                booking_id=booking.id
            ))

        old_slot = booking.slot

        history = BookingHistory(
            
            booking_id=booking.id,
            old_slot_id=old_slot.id,
            new_slot_id=new_slot.id,
            changed_by=admin.id,
            reason=request.form.get("reason", "").strip()
            )
        db.session.add(history)

        old_slot.available_seats += 1

        if old_slot.status == "Full":
            old_slot.status = "Active"

        new_slot.available_seats -= 1

        if new_slot.available_seats == 0:
            new_slot.status = "Full"

        booking.slot_id = new_slot.id

        db.session.commit()

        flash("Booking rescheduled successfully!", "success")

        return redirect(url_for("admin_view_bookings"))

    return render_template(
        "admin/edit_booking.html",
        booking=booking,
        available_slots=available_slots
    )

@app.route("/admin/booking-history")
def admin_booking_history():
    if session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("login"))

    search_query = request.args.get("q", "").strip().lower()

    history = BookingHistory.query.order_by(
        BookingHistory.changed_at.desc()
    ).all()

    if search_query:
        history = [
            item for item in history
            if (
                item.booking
                and item.booking.student
                and (
                    search_query in item.booking.student.name.lower()
                    or search_query in item.booking.student.email.lower()
                )
            )
            or (
                item.booking
                and item.booking.slot
                and item.booking.slot.examination
                and search_query in item.booking.slot.examination.name.lower()
            )
            or (
                item.admin
                and search_query in item.admin.username.lower()
            )
            or (
                item.old_slot
                and item.old_slot.examiner
                and search_query in item.old_slot.examiner.name.lower()
            )
            or (
                item.new_slot
                and item.new_slot.examiner
                and search_query in item.new_slot.examiner.name.lower()
            )
        ]

    return render_template(
        "admin/booking_history.html",
        history=history,
        search_query=search_query
    )








#============Eaxminer Features=====#


@app.route("/examiner/exam-slots/create", methods=["GET", "POST"])
def examiner_create_exam_slot():
    if session.get("role") != "examiner":
        flash("Access denied. Examiner login required.", "danger")
        return redirect(url_for("login"))

    examiner_id = session.get("user_id")
    examiner = db.session.get(Examiner, examiner_id)

    if not examiner or not examiner.active or not examiner.approved:
        session.clear()
        flash("Your examiner account is inactive or not approved.", "danger")
        return redirect(url_for("login"))

    current_time = datetime.now()

    # Show only examinations where slot creation is manually open
    # and the configured time window is active.
    examinations = Examination.query.filter(
        Examination.status.ilike("published"),
        Examination.slot_creation_open == True,
        Examination.slot_creation_start <= current_time,
        Examination.slot_creation_end >= current_time
    ).order_by(Examination.name).all()

    if request.method == "POST":
        examination_id = request.form.get("examination_id", type=int)
        date_value = request.form.get("date", "")
        start_value = request.form.get("start_time", "")
        end_value = request.form.get("end_time", "")
        capacity = request.form.get("capacity", type=int)

        examination = (
            db.session.get(Examination, examination_id)
            if examination_id else None
        )

        if not all([
            examination, date_value, start_value,
            end_value, capacity
        ]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("examiner_create_exam_slot"))

        if examination.status.lower() != "published":
            flash("Select a published examination.", "danger")
            return redirect(url_for("examiner_create_exam_slot"))

        # NEW: Check Admin's manual slot creation control
        if not examination.slot_creation_open:
            flash(
                "Slot creation has been manually closed by Admin.",
                "danger"
            )
            return redirect(url_for("examiner_create_exam_slot"))

        current_time = datetime.now()

        if current_time < examination.slot_creation_start:
            flash("Slot creation has not started yet.", "danger")
            return redirect(url_for("examiner_create_exam_slot"))

        if current_time > examination.slot_creation_end:
            flash("The slot-creation window has closed.", "danger")
            return redirect(url_for("examiner_create_exam_slot"))

        slot_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_value, "%H:%M").time()
        end_time = datetime.strptime(end_value, "%H:%M").time()

        if start_time >= end_time:
            flash("End time must be after start time.", "danger")
            return redirect(url_for("examiner_create_exam_slot"))

        if capacity <= 0:
            flash("Capacity must be greater than zero.", "danger")
            return redirect(url_for("examiner_create_exam_slot"))

        overlapping_slot = ExamSlot.query.filter(
            ExamSlot.examiner_id == examiner.id,
            ExamSlot.date == slot_date,
            ExamSlot.start_time < end_time,
            ExamSlot.end_time > start_time
        ).first()

        if overlapping_slot:
            flash(
                "You already have an overlapping slot on this date.",
                "danger"
            )
            return redirect(url_for("examiner_create_exam_slot"))

        exam_slot = ExamSlot(
            examination_id=examination.id,
            examiner_id=examiner.id,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            available_seats=capacity,
            status="Active"
        )

        db.session.add(exam_slot)
        db.session.commit()

        flash("Exam slot created successfully!", "success")
        return redirect(url_for("examiner_dashboard"))

    return render_template(
        "examiner/create_exam_slot.html",
        examiner=examiner,
        examinations=examinations
    )


@app.route("/examiner/exam-slots/edit/<int:slot_id>", methods=["GET", "POST"])
def examiner_edit_exam_slot(slot_id):
    if session.get("role") != "examiner":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    examiner = db.session.get(Examiner, session.get("user_id"))

    if not examiner or not examiner.active or not examiner.approved:
        flash("Your examiner account is inactive or not approved.", "danger")
        return redirect(url_for("login"))

    slot = db.get_or_404(ExamSlot, slot_id)

    # Examiners can edit only their own slots.
    if slot.examiner_id != examiner.id:
        flash("You cannot edit another examiner's slot.", "danger")
        return redirect(url_for("examiner_dashboard"))

    if datetime.now() >= slot.examination.booking_start:
        flash("Slots can only be edited before booking starts.", "danger")
        return redirect(url_for("examiner_dashboard"))

    if request.method == "POST":
        date_value = request.form.get("date", "")
        start_value = request.form.get("start_time", "")
        end_value = request.form.get("end_time", "")
        capacity = request.form.get("capacity", type=int)

        if not all([date_value, start_value, end_value]) or capacity is None:
            flash("Please fill in all required fields.", "danger")
            return redirect(
                url_for("examiner_edit_exam_slot", slot_id=slot.id)
            )

        slot_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_value, "%H:%M").time()
        end_time = datetime.strptime(end_value, "%H:%M").time()

        if start_time >= end_time:
            flash("End time must be after start time.", "danger")
            return redirect(
                url_for("examiner_edit_exam_slot", slot_id=slot.id)
            )

        if capacity <= 0:
            flash("Capacity must be greater than zero.", "danger")
            return redirect(
                url_for("examiner_edit_exam_slot", slot_id=slot.id)
            )

        bookings = Booking.query.filter_by(slot_id=slot.id).all()
        booked_count = sum(1 for booking in bookings if booking.status == "Booked")

        if capacity < booked_count:
            flash(
                "Capacity cannot be less than the number of booked students.",
                "danger"
            )
            return redirect(
                url_for("examiner_edit_exam_slot", slot_id=slot.id)
            )

        # Preserve the schedule if any booking history exists.
        if bookings and (
            slot.date != slot_date
            or slot.start_time != start_time
            or slot.end_time != end_time
        ):
            flash(
                "The schedule cannot be changed because this slot has booking records.",
                "danger"
            )
            return redirect(
                url_for("examiner_edit_exam_slot", slot_id=slot.id)
            )

        overlapping_slot = ExamSlot.query.filter(
            ExamSlot.id != slot.id,
            ExamSlot.examiner_id == examiner.id,
            ExamSlot.date == slot_date,
            ExamSlot.start_time < end_time,
            ExamSlot.end_time > start_time
        ).first()

        if overlapping_slot:
            flash("You already have an overlapping slot.", "danger")
            return redirect(
                url_for("examiner_edit_exam_slot", slot_id=slot.id)
            )

        slot.date = slot_date
        slot.start_time = start_time
        slot.end_time = end_time
        slot.capacity = capacity
        slot.available_seats = capacity - booked_count

        db.session.commit()

        flash("Exam slot updated successfully!", "success")
        return redirect(url_for("examiner_dashboard"))

    return render_template(
        "examiner/edit_exam_slot.html",
        slot=slot
    )

@app.route("/examiner/exam-slots/delete/<int:slot_id>", methods=["POST"])
def examiner_delete_exam_slot(slot_id):
    if session.get("role") != "examiner":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    examiner = db.session.get(Examiner, session.get("user_id"))

    if not examiner or not examiner.active or not examiner.approved:
        flash("Your examiner account is inactive or not approved.", "danger")
        return redirect(url_for("login"))

    slot = db.get_or_404(ExamSlot, slot_id)

    if slot.examiner_id != examiner.id:
        flash("You cannot delete another examiner's slot.", "danger")
        return redirect(url_for("examiner_dashboard"))

    if datetime.now() >= slot.examination.booking_start:
        flash("Slots can only be removed before booking starts.", "danger")
        return redirect(url_for("examiner_dashboard"))

    if Booking.query.filter_by(slot_id=slot.id).first():
        flash(
            "This slot has booking records and cannot be deleted.",
            "danger"
        )
        return redirect(url_for("examiner_dashboard"))

    db.session.delete(slot)
    db.session.commit()

    flash("Exam slot removed successfully!", "success")
    return redirect(url_for("examiner_dashboard"))

@app.route("/examiner/exam-slots/<int:slot_id>/students")
def examiner_slot_students(slot_id):

    if session.get("role") != "examiner":
        flash("Access denied. Examiner login required.", "danger")
        return redirect(url_for("login"))

    examiner = db.session.get(Examiner, session.get("user_id"))

    if not examiner or not examiner.active or not examiner.approved:
        session.clear()
        flash("Your examiner account is unavailable or not approved.", "danger")
        return redirect(url_for("login"))

    slot = db.get_or_404(ExamSlot, slot_id)

    # Examiner can view students only in their own slot
    if slot.examiner_id != examiner.id:
        flash("You are not allowed to view this slot.", "danger")
        return redirect(url_for("examiner_dashboard"))

    bookings = Booking.query.filter_by(
        slot_id=slot.id,
        status="Booked"
    ).order_by(Booking.booking_date.desc()).all()

    
    rubrics = Rubric.query.filter_by(
        examination_id=slot.examination_id
    ).all()

    total_max_marks = sum(rubric.max_marks for rubric in rubrics)

    student_results = {}

    for booking in bookings:

        evaluations = booking.evaluations

        obtained_marks = sum(
            evaluation.marks for evaluation in evaluations
        )

        evaluation_count = len(evaluations)

        if evaluation_count == len(rubrics) and len(rubrics) > 0:
            evaluation_status = "Completed"
        else:
            evaluation_status = "Pending"

        percentage = 0

        if total_max_marks > 0 and evaluation_status == "Completed":
            percentage = (obtained_marks / total_max_marks) * 100

        student_results[booking.id] = {
            "obtained_marks": obtained_marks,
            "total_max_marks": total_max_marks,
            "percentage": percentage,
            "status": evaluation_status
        }

    return render_template(
        "examiner/slot_students.html",
        examiner=examiner,
        slot=slot,
        bookings=bookings,
        student_results=student_results
    )


@app.route("/examiner/evaluate/<int:booking_id>", methods=['GET', 'POST'])
def examiner_evaluate_student(booking_id):
    if session.get("role") != "examiner":
        flash("Access denied. Examiner login required.", "danger")
        return redirect(url_for("login"))

    examiner = db.session.get(Examiner, session.get("user_id"))

    if not examiner or not examiner.active or not examiner.approved:
        session.clear()
        flash("Your examiner account is unavailable or not approved.", "danger")
        return redirect(url_for("login"))

    booking = db.get_or_404(Booking, booking_id)

    if booking.slot.examiner_id != examiner.id:
        flash("You are not allowed to evaluate this student.", "danger")
        return redirect(url_for("examiner_dashboard"))

    if booking.status != "Booked":
        flash("This booking is not available for evaluation.", "danger")
        return redirect(url_for("examiner_slot_students", slot_id=booking.slot_id))

    rubrics = Rubric.query.filter_by(
        examination_id=booking.slot.examination_id
    ).all()

    if not rubrics:
        flash("No rubrics found for this examination. Please contact admin.", "danger")
        return redirect(url_for("examiner_slot_students", slot_id=booking.slot_id))

    if request.method == "POST":
        submitted_evaluation = []

        for rubric in rubrics:
            marks_value = request.form.get(f"marks_{rubric.id}", "").strip()
            remarks = request.form.get(f"remarks_{rubric.id}", "").strip()

            try:
                marks = float(marks_value)
            except (ValueError, TypeError):
                flash(f"Please enter valid marks for {rubric.criteria_name}.", "danger")
                return render_template(
                    "examiner/evaluate_student.html",
                    booking=booking,
                    rubrics=rubrics
                )

            if marks < 0 or marks > rubric.max_marks:
                flash(
                    f"Marks for '{rubric.criteria_name}' must be between 0 and {rubric.max_marks}.",
                    "danger"
                )
                return render_template(
                    "examiner/evaluate_student.html",
                    booking=booking,
                    rubrics=rubrics
                )

            existing = Evaluation.query.filter_by(
                booking_id=booking.id,
                rubric_id=rubric.id
            ).first()

            if existing:
                existing.marks = marks
                existing.remarks = remarks
            else:
                submitted_evaluation.append(
                    Evaluation(
                        booking_id=booking.id,
                        rubric_id=rubric.id,
                        marks=marks,
                        remarks=remarks
                    )
                )

        if submitted_evaluation:
            db.session.add_all(submitted_evaluation)

        db.session.commit()

        flash("Evaluation submitted successfully.", "success")
        return redirect(
            url_for("examiner_slot_students", slot_id=booking.slot_id)
        )

    return render_template(
        "examiner/evaluate_student.html",
        booking=booking,
        rubrics=rubrics
    )

            






if __name__ == '__main__':
    app.run(debug=True)