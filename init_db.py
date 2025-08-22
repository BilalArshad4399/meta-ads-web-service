"""
Initialize database tables
Run this script to create all database tables
"""

from app import create_app, db
from app.models import User, AdAccount, MCPSession

def init_database():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Optional: Create a test user
        # test_user = User.query.filter_by(email='test@example.com').first()
        # if not test_user:
        #     test_user = User(email='test@example.com', name='Test User')
        #     test_user.set_password('password123')
        #     db.session.add(test_user)
        #     db.session.commit()
        #     print("Test user created: test@example.com / password123")

if __name__ == '__main__':
    init_database()