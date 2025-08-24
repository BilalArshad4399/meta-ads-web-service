"""
Main application entry point
"""

from app import create_app
import os

app = create_app()

# Note: Database tables are managed in Supabase
# Run supabase_setup.sql in Supabase SQL Editor to create tables

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)