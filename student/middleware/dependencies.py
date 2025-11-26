from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from student.core.database import get_db, User
from student.routers.auth_utils import verify_token

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Extract and validate user from JWT token."""
    token = credentials.credentials
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin_or_teacher(current_user: User = Depends(get_current_user)):
    """Require admin or teacher role for access."""
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Required role: admin/teacher. Your role: {current_user.role}"
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin role for access."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Required role: admin. Your role: {current_user.role}"
        )
    return current_user
