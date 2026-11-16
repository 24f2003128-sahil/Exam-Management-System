from app import app
from models import db, Admin
from werkzeug.security import generate_password_hash


with app.app_context():
    admin = Admin.query.filter_by(
        username = 'admin@exam.com'
    ).first()

    if not admin:

        admin = Admin(
            username = 'admin@exam.com',
            password = generate_password_hash('Admin@123')
        )
        db.session.add(admin)
        db.session.commit()

        print ('Admin created Successfully')
    else:
        print ('Admin already exist')