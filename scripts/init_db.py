"""
Script to initialize the database with sample users.
"""
import sys
sys.path.insert(0, ".")

from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.models.models import User


def create_sample_users():
    """Create sample users for testing."""
    init_db()
    
    db = SessionLocal()
    
    try:
        # Check if users already exist
        existing = db.query(User).first()
        if existing:
            print("ℹ️ Users already exist in database. Skipping...")
            return
        
        # Create sample users
        users = [
            User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                email="admin@example.com",
                role="admin",
            ),
            User(
                username="uploader",
                password_hash=get_password_hash("uploader123"),
                email="uploader@example.com",
                role="uploader",
            ),
            User(
                username="user",
                password_hash=get_password_hash("user123"),
                email="user@example.com",
                role="user",
            ),
        ]
        
        for user in users:
            db.add(user)
        
        db.commit()
        
        print("✅ Sample users created successfully!")
        print("\n📋 Users:")
        print("  - admin / admin123 (role: admin)")
        print("  - uploader / uploader123 (role: uploader)")
        print("  - user / user123 (role: user)")
        
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_users()
