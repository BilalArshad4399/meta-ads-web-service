"""
Main application entry point
"""

from app import create_app, db
import os

app = create_app()

# Create tables on startup (for production)
with app.app_context():
    try:
        db.create_all()
        print("Database tables initialized")
    except Exception as e:
        print(f"Database tables already exist or error: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)