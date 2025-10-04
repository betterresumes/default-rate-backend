import psycopg2
from datetime import datetime
import getpass
import uuid
from passlib.context import CryptContext

# Use the EXACT same password context as your FastAPI app
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def get_password_hash(password: str) -> str:
    """Hash a password using the same method as FastAPI app."""
    return pwd_context.hash(password)

def create_super_admin():
    # Database connection details
    DB_HOST = "accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com"
    DB_NAME = "postgres"
    DB_USER = "accunode_admin"
    
    # Hardcoded admin details
    admin_email = "admin@accunode.ai"
    admin_password = "AccuNode2024!Admin"
    admin_name = "AccuNode Administrator"
    admin_username = "admin"
    
    print("🎯 Creating Super Admin User (Bcrypt Hashing)")
    print("=" * 50)
    print(f"📧 Email: {admin_email}")
    print(f"👤 Name: {admin_name}")
    print(f"🔑 Username: {admin_username}")
    print("🌟 Super Admin (No tenant/org restrictions)")
    
    # Only ask for database password
    db_password = getpass.getpass("Enter RDS database password: ")
    
    try:
        # Connect to database
        print("\n🔌 Connecting to database...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=db_password,
            port=5432
        )
        
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
        existing_user = cur.fetchone()
        
        if existing_user:
            print(f"\n❌ User with email {admin_email} already exists!")
            # Show existing user details
            cur.execute("SELECT id, email, username, role FROM users WHERE email = %s", (admin_email,))
            user_info = cur.fetchone()
            print(f"   Existing user: ID={user_info[0]}, Email={user_info[1]}, Username={user_info[2]}, Role={user_info[3]}")
            return
        
        # Hash the password using bcrypt (same as FastAPI)
        print("🔐 Hashing password with bcrypt...")
        hashed_password = get_password_hash(admin_password)
        print(f"✅ Password hashed successfully (bcrypt)")
        
        # Generate UUID for user ID only
        user_id = str(uuid.uuid4())
        
        # Insert super admin user with NULL for tenant_id and organization_id
        insert_query = """
        INSERT INTO users (
            id, email, username, hashed_password, full_name, 
            tenant_id, organization_id, role, is_active, 
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id, email
        """
        
        now = datetime.utcnow()
        cur.execute(insert_query, (
            user_id,
            admin_email,
            admin_username,
            hashed_password,
            admin_name,
            None,  # tenant_id = NULL
            None,  # organization_id = NULL
            'super_admin',
            True,
            now,
            now
        ))
        
        created_user_id, email = cur.fetchone()
        conn.commit()
        
        print(f"\n🎉 Super admin created successfully!")
        print(f"   User ID: {created_user_id}")
        print(f"   Email: {email}")
        print(f"   Username: {admin_username}")
        print(f"   Name: {admin_name}")
        print(f"   Password: {admin_password}")
        print(f"   Role: super_admin")
        print(f"   Hashing: bcrypt (matches FastAPI)")
        
        # Verify the user was created and test password
        cur.execute("""
            SELECT id, email, username, full_name, role, is_active, hashed_password
            FROM users WHERE id = %s
        """, (created_user_id,))
        user_data = cur.fetchone()
        
        if user_data:
            print(f"\n✅ Verification successful!")
            print(f"   Login credentials: {user_data[1]} / {admin_password}")
            
            # Test password verification
            stored_hash = user_data[6]
            password_valid = pwd_context.verify(admin_password, stored_hash)
            print(f"   Password verification: {'✅ VALID' if password_valid else '❌ INVALID'}")
            
            if password_valid:
                print(f"\n🚀 Ready to login at your application!")
            else:
                print(f"\n⚠️ Password verification failed - there may be an issue")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    create_super_admin()