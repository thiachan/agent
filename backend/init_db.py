from app.core.database import Base, engine, SessionLocal
from app.models import user, document, chat, knowledge_base
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def init_db():
    """Initialize the database with tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")
    
    # Create default admin user if it doesn't exist
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "thiachan@pseudo-ai.com").first()
        if not admin:
            admin = User(
                email="thiachan@pseudo-ai.com",
                hashed_password=get_password_hash("password123"),
                full_name="Admin User",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True  # Admin created programmatically, no need to verify
            )
            db.add(admin)
            db.commit()
            print("Default admin user created!")
            print("   Email: thiachan@pseudo-ai.com")
            print("   Password: password123")
        else:
            print("Admin user already exists")
    except Exception as e:
        db.rollback()
        print(f"Could not create admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()

