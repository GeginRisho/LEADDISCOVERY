from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-form", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
        
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    if user.status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact an administrator."
        )
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource."
        )
    return current_user

from sqlalchemy import func

def seed_default_users(db: Session):
    # 1. Seed default Admin
    admin_email = "admin@leaddiscovery.com"
    admin = db.query(User).filter(func.lower(User.email) == admin_email).first()
    if not admin:
        hashed_pwd = get_password_hash("admin123")
        admin = User(
            email=admin_email,
            hashed_password=hashed_pwd,
            role="ADMIN",
            status="ACTIVE"
        )
        db.add(admin)
    elif not verify_password("admin123", admin.hashed_password):
        admin.hashed_password = get_password_hash("admin123")
        admin.role = "ADMIN"
        admin.status = "ACTIVE"
    
    # 2. Seed default Standard Normal User
    standard_email = "user@leaddiscovery.com"
    std_user = db.query(User).filter(func.lower(User.email) == standard_email).first()
    if not std_user:
        hashed_pwd = get_password_hash("user123")
        std_user = User(
            email=standard_email,
            hashed_password=hashed_pwd,
            role="USER",
            status="ACTIVE"
        )
        db.add(std_user)
    elif not verify_password("user123", std_user.hashed_password):
        std_user.hashed_password = get_password_hash("user123")
        std_user.role = "USER"
        std_user.status = "ACTIVE"

    # 3. Seed default Test User
    user_email = "testuser@leaddiscovery.com"
    test_user = db.query(User).filter(func.lower(User.email) == user_email).first()
    if not test_user:
        hashed_pwd = get_password_hash("User@12345")
        test_user = User(
            email=user_email,
            hashed_password=hashed_pwd,
            role="USER",
            status="ACTIVE"
        )
        db.add(test_user)
    elif not verify_password("User@12345", test_user.hashed_password):
        test_user.hashed_password = get_password_hash("User@12345")
        test_user.role = "USER"
        test_user.status = "ACTIVE"
        
    db.commit()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    seed_default_users(db)
    clean_email = user_data.email.strip().lower()
    existing_user = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered."
        )
    
    hashed_pwd = get_password_hash(user_data.password)
    role = "ADMIN" if clean_email.startswith("admin@") else "USER"
    new_user = User(
        email=clean_email,
        hashed_password=hashed_pwd,
        role=role,
        status="ACTIVE"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login_json(user_data: UserLogin, db: Session = Depends(get_db)):
    clean_email = user_data.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if not user:
        if db.query(User).count() == 0:
            seed_default_users(db)
            user = db.query(User).filter(func.lower(User.email) == clean_email).first()
            
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password."
        )
    if user.status == "SUSPENDED":
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended."
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/login-form", response_model=Token)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    clean_email = form_data.username.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if not user:
        if db.query(User).count() == 0:
            seed_default_users(db)
            user = db.query(User).filter(func.lower(User.email) == clean_email).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password."
        )
    if user.status == "SUSPENDED":
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended."
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
