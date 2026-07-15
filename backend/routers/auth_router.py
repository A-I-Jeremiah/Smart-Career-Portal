# backend/routers/auth_router.py
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.schemas import RegisterRequest, LoginRequest, TokenResponse
from backend import database as db
from backend.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201)
def register(req: RegisterRequest):
    """Create a new student account."""
    # Validate department for SS classes
    ss_classes = {"SSS 1", "SSS 2", "SSS 3", "SS1", "SS2", "SS3"}
    if req.class_level in ss_classes and not req.department:
        raise HTTPException(
            status_code=422,
            detail="Department is required for SSS students."
        )

    dept = req.department if req.class_level in ss_classes else None
    created = db.create_user(
        full_name=req.full_name,
        dob=req.dob,
        class_level=req.class_level,
        department=dept,
        email=req.email,
        hashed_password=hash_password(req.password),
    )
    if not created:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        )
    return {"message": "Account created successfully. Please log in."}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Authenticate and return a JWT access token."""
    user = db.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token({"sub": str(user["id"])})
    return TokenResponse(
        access_token=token,
        user={
            "id":          user["id"],
            "full_name":   user["full_name"],
            "email":       user["email"],
            "class_level": user["class_level"],
            "department":  user["department"],
            "dob":         user["dob"],
        },
    )


@router.post('/user/change-password')
def change_password(payload: dict, current_user: dict = Depends(get_current_user)):
    """Change the logged-in user's password.

    Expected JSON body: { "old_password": "...", "new_password": "..." }
    """
    old = payload.get('old_password')
    new = payload.get('new_password')
    if not old or not new:
        raise HTTPException(status_code=400, detail='Old and new passwords are required.')

    # Verify current password
    user = db.get_user_by_id(current_user['id'])
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    # For verification we need the hashed password — fetch by email
    stored = db.get_user_by_email(user['email'])
    if not stored or not verify_password(old, stored['password']):
        raise HTTPException(status_code=401, detail='Current password is incorrect')

    # Update
    hashed = hash_password(new)
    db.update_user_password(current_user['id'], hashed)
    return {'message': 'Password updated successfully.'}
