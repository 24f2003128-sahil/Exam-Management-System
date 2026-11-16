# Examination Management System

A web-based Examination Management System built using **Python, Flask, Flask-SQLAlchemy, SQLite, HTML, CSS and Bootstrap**.

The application provides a centralized platform for managing examinations, examiners, students, examination slots, bookings and results.

## 🚀 Features

### 👨‍💼 Admin

- Admin dashboard.
- Manage courses and examinations.
- Create and manage examination rubrics.
- Approve and deactivate examiners.
- Manage examination slots.
- Control slot creation and student booking availability.
- View and manage students, examiners and bookings.
- Search examinations, students, examiners and bookings.
- Reschedule bookings and reassign examiners.
- Publish examination results.
- View booking history.

### 👨‍🏫 Examiner

- Examiner registration and login.
- Admin approval system.
- View assigned examinations.
- Create, edit and delete examination slots.
- View students booked into examination slots.
- Evaluate students using examination rubrics.
- Submit marks and feedback.

### 👨‍🎓 Student

- Student registration and login.
- Browse, search and filter examinations.
- View upcoming examinations.
- Book available examination slots.
- View and cancel bookings before the deadline.
- View booking history and upcoming bookings.
- View published results and examiner feedback.
- Update profile information.

## 🛠️ Technologies Used

| Technology       | Purpose             |
| ---------------- | ------------------- |
| Python           | Backend programming |
| Flask            | Web framework       |
| Flask-SQLAlchemy | Database ORM        |
| SQLite           | Database            |
| HTML5            | Page structure      |
| CSS3             | Styling             |
| Bootstrap        | Responsive UI       |
| Jinja2           | Template rendering  |
| Flask-Migrate    | Database migrations |

## 📁 Project Structure

```text
Exam-Management-System/
│
├── app.py
├── models.py
├── insert.py
├── requirements.txt
├── .gitignore
│
├── migrations/
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
└── templates/
    ├── admin/
    ├── examiner/
    ├── student/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register_student.html
    └── register_examiner.html
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/24f2003128-sahil/Exam-Management-System.git
```

### 2. Navigate to the project directory

```bash
cd Exam-Management-System
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows:**

```bash
venv\Scripts\activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Initialize or upgrade the database

```bash
flask --app app db upgrade
```

### 7. Run the application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000/
```

## 🔐 User Roles

The system supports three user roles:

- **Admin:** Controls the overall examination management system.
- **Examiner:** Manages examination slots and evaluates students.
- **Student:** Books examination slots and views results.

## 📌 Important Notes

- This project is designed as a local web application.
- SQLite is used for database management.
- Database schema changes are maintained through Flask-Migrate.
- An administrator account must be initialized before accessing admin functionality.
- Configure application secrets and administrator credentials securely using environment variables before deployment.

## 👨‍💻 Author

**Sahil Sharma**

GitHub: [@24f2003128-sahil](https://github.com/24f2003128-sahil)

## 📄 License

This project is available for educational and learning purposes.
