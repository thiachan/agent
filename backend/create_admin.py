"""Script to create a default admin user"""
from app.core.database import SessionLocal, Base, engine
from app.models import user, document, chat  # Import all models to register relationships
from app.models.user import User, UserRole
from app.core.security import get_password_hash

# Ensure all models are registered
Base.metadata.create_all(bind=engine)

def create_admin_user():
    """Create default admin user if it doesn't exist"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.email == "thiachan@pseudo-ai.com").first()
        if admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(
            email="thiachan@pseudo-ai.com",
            hashed_password=get_password_hash("password123"),
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("Admin user created successfully!")
        print("   Email: thiachan@pseudo-ai.com")
        print("   Password: password123")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()

