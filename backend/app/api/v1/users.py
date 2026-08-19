"""Kullanıcı ve rol yönetimi uçları / User and role management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    client_ip,
    db_session,
    get_current_user,
    get_language,
    pagination,
    require_permissions,
)
from app.core import bootstrap
from app.core.exceptions import ConflictError, PermissionDeniedError, ValidationError
from app.core.i18n import t
from app.core.permissions import ALL_PERMISSIONS, Perm, ROLE_LABELS
from app.core.security import hash_password, password_strength_issues
from app.models.user import Role, User
from app.schemas.auth import (
    PasswordReset,
    RoleOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.schemas.common import Message, Page, PaginationParams
from app.services import audit
from app.services.crud import apply_search, apply_sort, get_or_404, paginate

router = APIRouter(prefix="/users", tags=["Kullanıcılar"])


def _assign_roles(db: Session, user: User, role_codes: list[str]) -> None:
    roles = db.scalars(select(Role).where(Role.code.in_(role_codes))).all()
    found = {r.code for r in roles}
    missing = set(role_codes) - found
    if missing:
        raise ValidationError(details={"unknown_roles": sorted(missing)})
    user.roles = list(roles)


@router.get("", response_model=Page[UserOut], summary="Kullanıcıları listele")
def list_users(
    q: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.USER_READ)),
) -> Page[UserOut]:
    stmt = select(User)
    stmt = apply_search(stmt, User, q, ["email", "full_name", "phone"])
    if role:
        stmt = stmt.join(User.roles).where(Role.code == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    stmt = apply_sort(stmt, User, params, "full_name")
    rows, total = paginate(db, stmt, params)
    return Page[UserOut](
        items=[UserOut.model_validate(u) for u in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=UserOut, status_code=201, summary="Kullanıcı oluştur")
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.USER_WRITE)),
) -> UserOut:
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise ConflictError("common.already_exists", details={"field": "email"})

    issues = password_strength_issues(payload.password)
    if issues:
        raise ValidationError("auth.password_weak", details={"issues": issues})

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        language=payload.language,
        is_active=payload.is_active,
        must_change_password=payload.must_change_password,
    )
    if payload.role_codes:
        _assign_roles(db, user, payload.role_codes)
    db.add(user)
    db.flush()
    audit.record(
        db,
        action="create",
        entity_type="user",
        entity_id=user.id,
        user=current,
        summary=f"Kullanıcı oluşturuldu: {user.email}",
        changes={"email": user.email, "roles": payload.role_codes},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/permissions", summary="Tüm izin kodları")
def list_permissions(
    _: User = Depends(require_permissions(Perm.ROLE_MANAGE)),
) -> dict:
    grouped: dict[str, list[str]] = {}
    for perm in ALL_PERMISSIONS:
        resource = perm.split(":")[0]
        grouped.setdefault(resource, []).append(perm)
    return {"permissions": ALL_PERMISSIONS, "grouped": grouped}


@router.get("/roles", response_model=list[RoleOut], summary="Rolleri listele")
def list_roles(
    db: Session = Depends(db_session),
    _: User = Depends(get_current_user),
) -> list[RoleOut]:
    roles = db.scalars(select(Role).order_by(Role.code)).all()
    return [RoleOut.model_validate(r) for r in roles]


@router.get("/roles/catalog", summary="Rol kataloğu (etiketlerle)")
def role_catalog(lang: str = Depends(get_language)) -> dict:
    groups = {
        "management": [
            "system_admin",
            "school_director",
            "operations_manager",
            "finance",
            "hr",
            "reception",
            "sales_marketing",
        ],
        "education": [
            "head_coach",
            "swim_coach",
            "swim_instructor",
            "kids_instructor",
            "baby_instructor",
            "private_instructor",
            "adaptive_instructor",
            "conditioning_coach",
        ],
        "other": [
            "lifeguard",
            "pool_technician",
            "medical_staff",
            "athlete",
            "student",
            "parent",
        ],
    }
    return {
        "groups": {
            key: [
                {"code": code, "label": ROLE_LABELS.get(code, {}).get(lang, code)}
                for code in codes
            ]
            for key, codes in groups.items()
        }
    }


@router.get("/{user_id}", response_model=UserOut, summary="Kullanıcı detayı")
def get_user(
    user_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.USER_READ)),
) -> UserOut:
    return UserOut.model_validate(get_or_404(db, User, user_id))


@router.patch("/{user_id}", response_model=UserOut, summary="Kullanıcı güncelle")
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.USER_WRITE)),
) -> UserOut:
    user = get_or_404(db, User, user_id)
    data = payload.model_dump(exclude_unset=True)
    role_codes = data.pop("role_codes", None)

    changes: dict = {}
    for key, value in data.items():
        if getattr(user, key, None) != value:
            changes[key] = {"from": getattr(user, key, None), "to": value}
            setattr(user, key, value)

    if role_codes is not None:
        if not current.is_superuser and not current.has_permission(Perm.ROLE_MANAGE):
            raise PermissionDeniedError(details={"required": [Perm.ROLE_MANAGE.value]})
        changes["roles"] = {"from": user.role_codes, "to": role_codes}
        _assign_roles(db, user, role_codes)

    audit.record(
        db,
        action="update",
        entity_type="user",
        entity_id=user.id,
        user=current,
        summary=f"Kullanıcı güncellendi: {user.email}",
        changes=changes,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post(
    "/reset-password", response_model=Message, summary="Parola sıfırla (yönetici)"
)
def reset_password(
    payload: PasswordReset,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.USER_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    # Kurulum parolası ASLA geri getirilemez: politika `admin` değerini
    # reddeder, burada ayrıca açıkça da engellenir.
    if payload.new_password.strip().lower() == bootstrap.BOOTSTRAP_PASSWORD:
        raise ValidationError("auth.password_weak", details={"issues": ["too_common"]})

    issues = password_strength_issues(payload.new_password)
    if issues:
        raise ValidationError("auth.password_weak", details={"issues": issues})

    user = get_or_404(db, User, payload.user_id)
    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = payload.must_change_password
    user.failed_login_count = 0
    user.locked_until = None
    audit.record(
        db,
        action="reset_password",
        entity_type="user",
        entity_id=user.id,
        user=current,
        summary=f"Parola sıfırlandı: {user.email}",
        ip_address=client_ip(request),
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


@router.delete(
    "/{user_id}", response_model=Message, summary="Kullanıcıyı devre dışı bırak"
)
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.USER_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    """Kullanıcı silinmez, devre dışı bırakılır (denetim izini korunur)."""
    user = get_or_404(db, User, user_id)
    if user.id == current.id:
        raise ValidationError(details={"reason": "self_deactivation_not_allowed"})
    user.is_active = False
    audit.record(
        db,
        action="deactivate",
        entity_type="user",
        entity_id=user.id,
        user=current,
        summary=f"Kullanıcı devre dışı bırakıldı: {user.email}",
        ip_address=client_ip(request),
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))
