"""
Faker script to populate database with realistic test data
"""
from faker import Faker
from sqlalchemy.orm import Session
import random
from datetime import datetime

from student.core.database import SessionLocal, Student, User
from student.routers.auth_utils import get_password_hash

fake = Faker()

def create_fake_students(db: Session, count: int = 50):
    """Generate fake student records."""
    print(f"📝 Creating {count} fake students...")
    
    students_created = 0
    students_skipped = 0
    
    for i in range(count):
        email = fake.unique.email()
        
        # Check if email exists
        existing = db.query(Student).filter(Student.email == email).first()
        if existing:
            students_skipped += 1
            continue
        
        student = Student(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            age=random.randint(18, 30),
            grade=random.choice(['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F'])
        )
        
        db.add(student)
        students_created += 1
        
        if (i + 1) % 10 == 0:
            db.commit()
            print(f"  ✅ Created {students_created} students...")
    
    db.commit()
    print(f"✅ Total created: {students_created}")
    print(f"⚠️  Skipped (duplicates): {students_skipped}")
    return students_created

def create_fake_users(db: Session, count: int = 20):
    """Generate fake user accounts."""
    print(f"\n👥 Creating {count} fake users...")
    
    users_created = 0
    users_skipped = 0
    
    roles = ['student', 'teacher', 'admin']
    role_weights = [0.7, 0.25, 0.05]  # 70% students, 25% teachers, 5% admins
    
    for i in range(count):
        username = fake.unique.user_name()
        email = fake.unique.email()
        
        # Check if username or email exists
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            users_skipped += 1
            continue
        
        role = random.choices(roles, weights=role_weights)[0]
        
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash("password123"),  # Default password
            role=role,
            is_active=1
        )
        
        db.add(user)
        users_created += 1
        
        if (i + 1) % 5 == 0:
            db.commit()
            print(f"  ✅ Created {users_created} users...")
    
    db.commit()
    print(f"✅ Total created: {users_created}")
    print(f"⚠️  Skipped (duplicates): {users_skipped}")
    print(f"\n🔑 Default password for all users: password123")
    return users_created

def clear_all_data(db: Session):
    """⚠️  WARNING: Delete all students and users."""
    print("\n⚠️  WARNING: Clearing all data...")
    
    students_count = db.query(Student).count()
    users_count = db.query(User).count()
    
    response = input(f"Delete {students_count} students and {users_count} users? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    db.query(Student).delete()
    db.query(User).delete()
    db.commit()
    
    print(f"✅ Deleted {students_count} students")
    print(f"✅ Deleted {users_count} users")

def show_statistics(db: Session):
    """Display current database statistics."""
    from sqlalchemy import text, func
    
    print("\n📊 Database Statistics")
    print("=" * 50)
    
    # Students
    total_students = db.query(Student).count()
    print(f"👨‍🎓 Total Students: {total_students}")
    
    if total_students > 0:
        grade_distribution = db.query(
            Student.grade, 
            func.count(Student.id).label('count')
        ).filter(Student.grade.isnot(None)).group_by(Student.grade).order_by(func.count(Student.id).desc()).all()
        
        print("\n  Grade Distribution:")
        for grade, count in grade_distribution[:5]:
            print(f"    {grade}: {count}")
    
    # Users
    total_users = db.query(User).count()
    print(f"\n👥 Total Users: {total_users}")
    
    if total_users > 0:
        role_distribution = db.query(
            User.role,
            func.count(User.id).label('count')
        ).group_by(User.role).all()
        
        print("\n  Role Distribution:")
        for role, count in role_distribution:
            print(f"    {role}: {count}")
    
    print("=" * 50)

def main():
    """Main menu for faker operations."""
    print("\n" + "=" * 50)
    print("  🎭 FAKER DATA POPULATION SCRIPT")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        while True:
            print("\nOptions:")
            print("  1. Create fake students (default: 50)")
            print("  2. Create fake users (default: 20)")
            print("  3. Create both students and users")
            print("  4. Show statistics")
            print("  5. Clear all data (⚠️  DANGEROUS)")
            print("  6. Exit")
            
            choice = input("\nEnter choice (1-6): ").strip()
            
            if choice == '1':
                count = input("How many students? (default 50): ").strip()
                count = int(count) if count.isdigit() else 50
                create_fake_students(db, count)
                show_statistics(db)
                
            elif choice == '2':
                count = input("How many users? (default 20): ").strip()
                count = int(count) if count.isdigit() else 20
                create_fake_users(db, count)
                show_statistics(db)
                
            elif choice == '3':
                students = input("How many students? (default 50): ").strip()
                students = int(students) if students.isdigit() else 50
                users = input("How many users? (default 20): ").strip()
                users = int(users) if users.isdigit() else 20
                create_fake_students(db, students)
                create_fake_users(db, users)
                show_statistics(db)
                
            elif choice == '4':
                show_statistics(db)
                
            elif choice == '5':
                clear_all_data(db)
                show_statistics(db)
                
            elif choice == '6':
                print("\n👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please try again.")
                
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    finally:
        db.close()

if __name__ == "__main__":
    main()
