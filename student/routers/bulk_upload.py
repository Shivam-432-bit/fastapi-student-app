from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
from datetime import datetime

from student.core.database import get_db, Student
from student.core.models import StudentResponse

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])

@router.post("/upload-students", response_model=dict)
async def bulk_upload_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Bulk upload students from CSV or Excel file.
    
    Expected columns: first_name, last_name, email, age, grade
    Optional: Any missing columns will use defaults
    """
    
    # Validate file type
    if file.content_type not in [
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload CSV or Excel file."
        )
    
    try:
        content = await file.read()
        
        # Read file based on type
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=400,
                detail="File must be .csv, .xlsx, or .xls"
            )
        
        # Validate required columns
        required_columns = ['first_name', 'last_name', 'email']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Process each row
        created = 0
        skipped = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Check if email already exists
                existing = db.query(Student).filter(
                    Student.email == row['email']
                ).first()
                
                if existing:
                    skipped += 1
                    errors.append({
                        "row": index + 2,  # +2 for 1-based index and header
                        "email": row['email'],
                        "error": "Email already exists"
                    })
                    continue
                
                # Create student with defaults for missing fields
                student = Student(
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    email=row['email'],
                    age=int(row.get('age', 20)),  # Default age 20
                    grade=row.get('grade', 'B')   # Default grade B
                )
                
                db.add(student)
                created += 1
                
            except Exception as e:
                errors.append({
                    "row": index + 2,
                    "email": row.get('email', 'N/A'),
                    "error": str(e)
                })
                skipped += 1
        
        db.commit()
        
        return {
            "message": "Bulk upload completed",
            "total_rows": len(df),
            "created": created,
            "skipped": skipped,
            "errors": errors[:10]  # Limit to first 10 errors
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="File is empty")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/template/students")
def download_student_template():
    """
    Download a CSV template for bulk student upload.
    """
    from fastapi.responses import StreamingResponse
    
    template = "first_name,last_name,email,age,grade\n"
    template += "John,Doe,john.doe@example.com,20,A\n"
    template += "Jane,Smith,jane.smith@example.com,22,B+\n"
    template += "Bob,Johnson,bob.johnson@example.com,21,A-\n"
    
    return StreamingResponse(
        io.StringIO(template),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=student_upload_template.csv"
        }
    )

@router.post("/export-students")
def export_students(
    db: Session = Depends(get_db),
    format: str = "csv"
):
    """
    Export all students to CSV or Excel format.
    
    Query param: format=csv or format=excel
    """
    from fastapi.responses import StreamingResponse
    
    students = db.query(Student).all()
    
    if not students:
        raise HTTPException(status_code=404, detail="No students found to export")
    
    # Convert to DataFrame
    data = [{
        "id": s.id,
        "first_name": s.first_name,
        "last_name": s.last_name,
        "email": s.email,
        "age": s.age,
        "grade": s.grade
    } for s in students]
    
    df = pd.DataFrame(data)
    
    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    elif format == "excel":
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')
        stream.seek(0)
        
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'csv' or 'excel'"
        )
