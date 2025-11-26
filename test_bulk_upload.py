#!/usr/bin/env python3
"""
Test script for bulk upload functionality
"""
import requests
import pandas as pd
import io

BASE_URL = "http://localhost:8000/api"

def test_download_template():
    """Test downloading the CSV template."""
    print("=" * 70)
    print("1. Testing Template Download")
    print("=" * 70)
    
    try:
        response = requests.get(f"{BASE_URL}/bulk/template/students")
        if response.status_code == 200:
            print("✅ Template downloaded successfully")
            print("\nTemplate content:")
            print(response.text)
            
            # Save to file
            with open("student_template.csv", "w") as f:
                f.write(response.text)
            print("\n📝 Saved as: student_template.csv")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_bulk_upload():
    """Test bulk upload with CSV file."""
    print("\n" + "=" * 70)
    print("2. Testing Bulk Upload (CSV)")
    print("=" * 70)
    
    # Create sample CSV data
    csv_data = """first_name,last_name,email,age,grade
Michael,Brown,michael.brown@example.com,23,A
Sarah,Davis,sarah.davis@example.com,21,B+
David,Wilson,david.wilson@example.com,22,A-
Emily,Taylor,emily.taylor@example.com,20,B
James,Anderson,james.anderson@example.com,24,A+"""
    
    try:
        # Save to temporary file
        with open("test_upload.csv", "w") as f:
            f.write(csv_data)
        
        # Upload
        with open("test_upload.csv", "rb") as f:
            files = {"file": ("test_upload.csv", f, "text/csv")}
            response = requests.post(f"{BASE_URL}/bulk/upload-students", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Bulk upload successful!")
            print(f"\n📊 Results:")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Created: {result['created']}")
            print(f"   Skipped: {result['skipped']}")
            
            if result['errors']:
                print(f"\n⚠️  Errors ({len(result['errors'])}):")
                for error in result['errors'][:3]:
                    print(f"   Row {error['row']}: {error['error']}")
            
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_bulk_upload_excel():
    """Test bulk upload with Excel file."""
    print("\n" + "=" * 70)
    print("3. Testing Bulk Upload (Excel)")
    print("=" * 70)
    
    try:
        # Create sample Excel data
        data = {
            'first_name': ['Robert', 'Linda', 'William'],
            'last_name': ['Martinez', 'Garcia', 'Rodriguez'],
            'email': ['robert.m@example.com', 'linda.g@example.com', 'william.r@example.com'],
            'age': [21, 22, 23],
            'grade': ['A', 'B+', 'A-']
        }
        df = pd.DataFrame(data)
        
        # Save to Excel
        df.to_excel("test_upload.xlsx", index=False)
        
        # Upload
        with open("test_upload.xlsx", "rb") as f:
            files = {"file": ("test_upload.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            response = requests.post(f"{BASE_URL}/bulk/upload-students", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Excel upload successful!")
            print(f"\n📊 Results:")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Created: {result['created']}")
            print(f"   Skipped: {result['skipped']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_export_csv():
    """Test exporting students to CSV."""
    print("\n" + "=" * 70)
    print("4. Testing Export to CSV")
    print("=" * 70)
    
    try:
        response = requests.post(f"{BASE_URL}/bulk/export-students?format=csv")
        if response.status_code == 200:
            print("✅ Export successful!")
            
            # Save exported file
            with open("students_export.csv", "wb") as f:
                f.write(response.content)
            
            # Show preview
            df = pd.read_csv(io.StringIO(response.text))
            print(f"\n📊 Exported {len(df)} students")
            print("\nFirst 3 rows:")
            print(df.head(3).to_string(index=False))
            print("\n📝 Saved as: students_export.csv")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_export_excel():
    """Test exporting students to Excel."""
    print("\n" + "=" * 70)
    print("5. Testing Export to Excel")
    print("=" * 70)
    
    try:
        response = requests.post(f"{BASE_URL}/bulk/export-students?format=excel")
        if response.status_code == 200:
            print("✅ Export successful!")
            
            # Save exported file
            with open("students_export.xlsx", "wb") as f:
                f.write(response.content)
            
            # Show preview
            df = pd.read_excel(io.BytesIO(response.content))
            print(f"\n📊 Exported {len(df)} students")
            print("\nFirst 3 rows:")
            print(df.head(3).to_string(index=False))
            print("\n📝 Saved as: students_export.xlsx")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "=" * 70)
    print("  📦 BULK UPLOAD & EXPORT TEST SUITE")
    print("=" * 70)
    
    results = []
    
    results.append(("Template Download", test_download_template()))
    results.append(("Bulk Upload CSV", test_bulk_upload()))
    results.append(("Bulk Upload Excel", test_bulk_upload_excel()))
    results.append(("Export CSV", test_export_csv()))
    results.append(("Export Excel", test_export_excel()))
    
    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {passed_count}/{len(results)} tests passed")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
