# Environment & Files Overview

## 🐍 Python Environment
- **Version**: Python 3.14.0
- **Virtual Environment**: `.venv/` (local to project)
- **Activation**: `source .venv/bin/activate`

## 📋 CSV/Excel Files

### Production Templates
- **`student_template.csv`** (154B)
  - Template showing correct format for bulk student uploads
  - Fields: `first_name, last_name, email, age, grade`
  - Use this as reference when creating bulk upload files

### Sample/Export Data
- **`students_export.csv`** (6.5KB)
- **`students_export.xlsx`** (11KB)
  - Sample exported student data
  - Generated from API export endpoint
  - Can be used for testing import functionality

### Test Data
- **`test_upload.csv`** (258B)
- **`test_upload.xlsx`** (5KB)
  - Small test datasets for automated testing
  - Used by `test_bulk_upload.py`

## 🧪 Test Files

### API Tests
- **`test_auth_students.py`** - JWT authentication & student CRUD tests
- **`test_bulk_upload.py`** - CSV/Excel bulk upload tests
- **`test_complete_api.py`** - Full API integration tests
- **`test_health.py`** - Health check endpoint tests

### Service Tests  
- **`test_ollama.py`** - Ollama AI service integration tests
- **`test_search_id.py`** - Document search functionality tests
- **`test_services.sh`** - Comprehensive service health check script

## 📂 Files to Keep vs Remove

### ✅ Keep (Essential)
- `student_template.csv` - Users need this template
- Test files (`test_*.py`, `test_services.sh`) - Development/QA
- `reprocess_documents.py` - Utility script for ChromaDB maintenance
- `requirements.txt` - Python dependencies

### ⚠️ Optional (Can Remove if Not Needed)
- `students_export.csv/xlsx` - Sample data (regenerate via API)
- `test_upload.csv/xlsx` - Test data (can recreate)
- `API_OVERVIEW.md` - Documentation (keep if helpful)

### ❌ Already Removed
- Old virtual environment (`.venv310`)
- Log files (`*.log`)
- Cache files (`__pycache__`, `*.pyc`)
- Backup files (`.env.backup`)
- Empty folders (`student/rag/`, `student/vector_db/`)

## 🚀 Running Tests

```bash
# Activate environment
source .venv/bin/activate

# Run all tests
pytest test_*.py

# Run specific test
python test_auth_students.py
python test_bulk_upload.py

# Run service health check
./test_services.sh
```

## 📦 Environment Setup

```bash
# Create virtual environment
python3.14 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (needed for FastAPI)
export MYSQL_USER=root
export MYSQL_PASSWORD='Shivam@12345'
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=school
export SECRET_KEY='your-secret-key'
export ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 🎯 Recommendation

**Keep current setup as-is** because:
1. Test files are essential for development
2. CSV templates are needed by users
3. Sample data helps with testing
4. Python 3.14 environment is working correctly

If disk space is a concern, you can remove `students_export.*` and `test_upload.*` files (they can be regenerated).
