from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, or_, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import httpx
from datetime import datetime, timezone

from schemas import (
    TodoCreate,
    TodoUpdate,
    TodoReturn,
    TodoPatch,
    UserCreate,
    UserReturn,
    LoginRequest,
    TokenResponse,
    Priority,
    EmailVerificationRequest,
    ResendOTPRequest,
    ForgotPasswordRequest,
    VerifyResetOTPRequest,
    ResetPasswordRequest,
)
from database import get_db, Todo, User
from security import hash_password, verify_password
from auth import create_access_token, get_current_user
from otp_verification import verify_user_email, OTPVerificationError
from otp_service import generate_otp
from otp_repository import create_otp
from email_service import send_otp_email, send_password_reset_email
from otp_resend_service import prepare_resend_otp, OTPResendError
from password_reset_request_service import (
    prepare_password_reset_otp,
    PasswordResetRequestError,
)
from password_reset_service import (
    verify_reset_otp,
    reset_password,
    PasswordResetError,
)




router = APIRouter()


@router.get("/todos", response_model=list[TodoReturn])
def get_todos(
    completed: bool | None = None,
    priority: Priority | None = None,
    sort_by: str = "id",
    order: str = "asc",
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Todo).where(Todo.user_id == current_user.id)

    if completed is not None:
        query = query.where(Todo.completed == completed)

    if priority is not None:
        query = query.where(Todo.priority == priority)

    if sort_by not in {"id", "priority"}:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    if order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid sort order")

    if search is not None:
        query = query.where(Todo.task.ilike(f"%{search}%"))

    if sort_by == "priority":
        sort_column = case(
            (Todo.priority == "urgent", 1),
            (Todo.priority == "important", 2),
            (Todo.priority == "normal", 3),
        )
    else:
        sort_column = Todo.id

    query = query.order_by(
        sort_column.asc() if order == "asc" else sort_column.desc()
    )

    query = query.offset(skip).limit(limit)

    return db.scalars(query).all()


@router.get("/todo/{todo_id}", response_model=TodoReturn)
def get_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
        )
    )

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    return todo


@router.post("/todo", response_model=TodoReturn, status_code=201)
def post_todo(
    todo: TodoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_todo = Todo(
        task=todo.task,
        completed=False,
        priority=todo.priority,
        description=todo.description,
        due_date=todo.due_date,
        user_id=current_user.id,
    )

    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)

    return new_todo


@router.put("/todo/{todo_id}", response_model=TodoReturn)
def update_todo(
    todo_id: int,
    todo_data: TodoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
        )
    )

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.task = todo_data.task
    todo.completed = todo_data.completed
    todo.priority = todo_data.priority
    todo.description = todo_data.description
    todo.due_date = todo_data.due_date

    db.commit()
    db.refresh(todo)

    return todo


@router.patch("/todo/{todo_id}", response_model=TodoReturn)
def patch_todo(
    todo_id: int,
    todo_data: TodoPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
        )
    )

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    update_data = todo_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(todo, field, value)

    db.commit()
    db.refresh(todo)

    return todo


@router.delete("/todo/{todo_id}", status_code=204)
def del_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
        )
    )

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.delete(todo)
    db.commit()



@router.post("/auth/register", response_model=UserReturn, status_code=201)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        is_verified=False,
    )

    try:
        db.add(user)
        db.flush()

        otp = generate_otp()
        create_otp(db, user.id, otp)

        now = datetime.now(timezone.utc)
        user.otp_last_sent_at = now
        user.otp_window_started_at = now
        user.otp_request_count = 1

        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists",
        )

    try:
        send_otp_email(user.email, otp)
    except (httpx.HTTPError, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail=(
                "Account created, but verification email could not be sent. "
                "Please try requesting a new verification code."
            ),
        )

    return user



@router.post("/auth/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            or_(
                User.username == data.identifier,
                User.email == data.identifier,
            )
        )
    )

    if user is None or not verify_password(
        data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/auth/verify-email")
def verify_email(
    data: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == data.email)
    )

    if user is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Email is already verified",
        )

    try:
        verify_user_email(db, user, data.otp)
    except OTPVerificationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {"message": "Email verified successfully"}


@router.post("/auth/resend-otp")
def resend_otp(data: ResendOTPRequest, db: Session = Depends(get_db)):
    generic_response = {
        "message": (
            "If the account is eligible, "
            "a verification email will be sent."
        )
    }

    user = db.scalar(select(User).where(User.email == data.email))

    if user is None or user.is_verified:
        return generic_response

    try:
        otp = prepare_resend_otp(db, user.id)
    except OTPResendError:
        # Keep account eligibility and rate-limit state out of the response.
        return generic_response

    try:
        send_otp_email(user.email, otp)
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Verification email could not be sent. Please try again later.",
        ) from exc

    return generic_response


@router.get("/auth/me", response_model=UserReturn)
def get_user(
    current_user: User = Depends(get_current_user),
) -> User:
    
    return current_user


@router.post("/auth/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    response = {
        "message": (
            "If an eligible account exists, "
            "a password-reset email will be sent."
        )
    }

    user = db.scalar(
        select(User).where(User.email == data.email)
    )

    if user is None:
        return response

    try:
        otp = prepare_password_reset_otp(db, user.id)
    except PasswordResetRequestError:
        return response

    try:
        send_password_reset_email(user.email, otp)
    except (httpx.HTTPError, RuntimeError):
        return response

    return response


@router.post("/auth/verify-reset-otp")
def verify_password_reset_otp(
    data: VerifyResetOTPRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == data.email)
    )

    if user is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP",
        )

    try:
        reset_token = verify_reset_otp(db, user.id, data.otp)
    except PasswordResetError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP",
        ) from exc

    return {"reset_token": reset_token}


@router.post("/auth/reset-password")
def reset_user_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        reset_password(
            db,
            data.reset_token,
            data.new_password,
        )
    except PasswordResetError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token",
        ) from exc

    return {"message": "Password reset successfully"}
