"""
Migration script to add email verification and password reset columns to existing database.
Run this if you have an existing database and want to add the new features.
"""
from sqlalchemy import text
from app.core.database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add email verification and password reset columns to users table"""
    db = SessionLocal()
    
    try:
        # Check database type
        database_url = str(engine.url)
        is_sqlite = "sqlite" in database_url.lower()
        is_postgres = "postgresql" in database_url.lower()
        
        logger.info(f"Database type: {'SQLite' if is_sqlite else 'PostgreSQL' if is_postgres else 'Unknown'}")
        
        if is_sqlite:
            # SQLite migration
            columns_to_add = [
                ("is_verified", "BOOLEAN DEFAULT 0"),
                ("verification_token", "TEXT"),
                ("verification_token_expires", "DATETIME"),
                ("reset_token", "TEXT"),
                ("reset_token_expires", "DATETIME"),
            ]
            
            for column_name, column_def in columns_to_add:
                try:
                    # SQLite doesn't support IF NOT EXISTS in ALTER TABLE
                    # So we'll try to add and catch error if exists
                    db.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}"))
                    db.commit()
                    logger.info(f"✓ Added column: {column_name}")
                except Exception as e:
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        logger.warning(f"  Column {column_name} already exists, skipping")
                    else:
                        logger.error(f"  Error adding {column_name}: {e}")
                        db.rollback()
            
            # Set existing users as verified (for backward compatibility)
            try:
                db.execute(text("UPDATE users SET is_verified = 1 WHERE is_verified IS NULL"))
                db.commit()
                logger.info("✓ Set existing users as verified")
            except Exception as e:
                logger.warning(f"  Could not update existing users: {e}")
                db.rollback()
        
        elif is_postgres:
            # PostgreSQL migration
            columns_to_add = [
                ("is_verified", "BOOLEAN DEFAULT FALSE"),
                ("verification_token", "VARCHAR"),
                ("verification_token_expires", "TIMESTAMP"),
                ("reset_token", "VARCHAR"),
                ("reset_token_expires", "TIMESTAMP"),
            ]
            
            for column_name, column_def in columns_to_add:
                try:
                    db.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column_name} {column_def}"))
                    db.commit()
                    logger.info(f"✓ Added column: {column_name}")
                except Exception as e:
                    logger.error(f"  Error adding {column_name}: {e}")
                    db.rollback()
            
            # Set existing users as verified
            try:
                db.execute(text("UPDATE users SET is_verified = TRUE WHERE is_verified IS NULL"))
                db.commit()
                logger.info("✓ Set existing users as verified")
            except Exception as e:
                logger.warning(f"  Could not update existing users: {e}")
                db.rollback()
        
        else:
            logger.error("Unsupported database type. Please migrate manually.")
            return False
        
        logger.info("=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Email Verification & Password Reset Migration")
    print("=" * 60)
    print("")
    print("This script will add the following columns to the users table:")
    print("  - is_verified (BOOLEAN)")
    print("  - verification_token (TEXT/VARCHAR)")
    print("  - verification_token_expires (DATETIME/TIMESTAMP)")
    print("  - reset_token (TEXT/VARCHAR)")
    print("  - reset_token_expires (DATETIME/TIMESTAMP)")
    print("")
    print("Existing users will be marked as verified (is_verified = true)")
    print("")
    
    response = input("Continue with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        success = migrate_database()
        if success:
            print("\n✓ Migration completed! You can now use email verification and password reset.")
        else:
            print("\n✗ Migration failed. Please check the logs above.")
    else:
        print("Migration cancelled.")


