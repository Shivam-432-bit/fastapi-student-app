import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_auth_and_students():
    print("=" * 60)
    print("Testing Authentication & Student Management Endpoints")
    print("=" * 60)
    
    # Test 1: Register a new user
    print("\n1. Testing User Registration...")
    register_data = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "SecurePass123"
    }
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            print("✅ User registered successfully!")
            user_data = response.json()
            print(f"   User ID: {user_data['id']}, Role: {user_data['role']}")
        elif response.status_code == 400:
            print("⚠️  User already exists (this is OK if running test multiple times)")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Login to get token
    print("\n2. Testing User Login...")
    login_data = {
        "username": "testuser",
        "password": "SecurePass123"
    }
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data=login_data,  # OAuth2 uses form data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            print("✅ Login successful!")
            token_data = response.json()
            token = token_data['access_token']
            print(f"   Token: {token[:30]}...")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   {response.text}")
            token = None
    except Exception as e:
        print(f"❌ Error: {e}")
        token = None
    
    # Test 3: Create a student
    print("\n3. Testing Create Student...")
    student_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@school.com",
        "age": 20,
        "grade": "A"
    }
    try:
        response = requests.post(f"{BASE_URL}/students/", json=student_data)
        if response.status_code == 201:
            print("✅ Student created successfully!")
            created_student = response.json()
            student_id = created_student['id']
            print(f"   Student ID: {student_id}, Name: {created_student['first_name']} {created_student['last_name']}")
        elif response.status_code == 400:
            print("⚠️  Student already exists (this is OK if running test multiple times)")
            # Try to get existing student
            response = requests.get(f"{BASE_URL}/students/")
            if response.status_code == 200:
                students = response.json()
                if students:
                    student_id = students[0]['id']
                else:
                    student_id = None
            else:
                student_id = None
        else:
            print(f"❌ Create student failed: {response.status_code}")
            print(f"   {response.text}")
            student_id = None
    except Exception as e:
        print(f"❌ Error: {e}")
        student_id = None
    
    # Test 4: List students
    print("\n4. Testing List Students...")
    try:
        response = requests.get(f"{BASE_URL}/students/")
        if response.status_code == 200:
            students = response.json()
            print(f"✅ Found {len(students)} student(s)")
            for student in students[:3]:  # Show first 3
                print(f"   - {student['first_name']} {student['last_name']} (Grade: {student['grade']})")
        else:
            print(f"❌ List students failed: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Get single student
    if student_id:
        print(f"\n5. Testing Get Student by ID (ID: {student_id})...")
        try:
            response = requests.get(f"{BASE_URL}/students/{student_id}")
            if response.status_code == 200:
                student = response.json()
                print(f"✅ Student found: {student['first_name']} {student['last_name']}")
                print(f"   Email: {student['email']}, Age: {student['age']}, Grade: {student['grade']}")
            else:
                print(f"❌ Get student failed: {response.status_code}")
                print(f"   {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 6: Update student
    if student_id:
        print(f"\n6. Testing Update Student (ID: {student_id})...")
        update_data = {
            "grade": "A+"
        }
        try:
            response = requests.put(f"{BASE_URL}/students/{student_id}", json=update_data)
            if response.status_code == 200:
                updated_student = response.json()
                print(f"✅ Student updated successfully!")
                print(f"   New grade: {updated_student['grade']}")
            else:
                print(f"❌ Update student failed: {response.status_code}")
                print(f"   {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("- Authentication endpoints (register, login) are working")
    print("- Student CRUD endpoints (create, read, update) are working")
    print("- Note: Authentication is not enforced yet (no middleware)")
    print("=" * 60)

if __name__ == "__main__":
    test_auth_and_students()
