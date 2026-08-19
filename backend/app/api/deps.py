"""FastAPI bağımlılıkları / FastAPI dependencies: oturum, kullanıcı, RBAC."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import bootstrap
from app.core.exceptions import (
    AuthenticationError,
    PasswordChangeRequiredError,
    PermissionDeniedError,
)
from app.core.i18n import normalize_language
from app.core.permissions import (
    INSTRUCTOR_SCOPED_ROLES,
    SELF_SCOPED_ROLES,
    Perm,
    RoleCode,
)
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginationParams

bearer_scheme = HTTPBearer(auto_error=False)


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_language(
    lang: str | None = None,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> str:
    """İstek dilini belirler: ?lang= > Accept-Language > varsayılan."""
    return normalize_language(lang or accept_language)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(db_session),
) -> User:
    """Geçerli JWT'den kullanıcıyı çözer.

    Ayrıca **zorunlu parola değişimi kapısı** buradan geçer: bu, kimlik
    doğrulaması gerektiren her ucun tek ortak noktasıdır, dolayısıyla tek bir
    denetimle bütün korumalı yüzey kapanır (bkz. `app/core/bootstrap.py`).
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("auth.not_authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise AuthenticationError("auth.invalid_token")

    try:
        user_id = int(payload.get("sub", 0))
    except (TypeError, ValueError):
        raise AuthenticationError("auth.invalid_token") from None

    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("auth.invalid_token")
    if not user.is_active:
        raise AuthenticationError("auth.inactive_user")

    # Parola değiştirilmeden yalnızca parola değiştirme akışı çalışır.
    if user.must_change_password and not bootstrap.path_allows_password_change_only(
        request.url.path
    ):
        raise PasswordChangeRequiredError(
            details={"must_change_password": True, "next": "/auth/change-password"}
        )
    return user


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(db_session),
) -> User | None:
    """Kimlik doğrulama zorunlu olmayan uçlar için."""
    if credentials is None:
        return None
    try:
        return get_current_user(request, credentials, db)
    except (AuthenticationError, PasswordChangeRequiredError):
        return None


def require_permissions(*permissions: str, require_all: bool = True) -> Callable:
    """Belirtilen izinleri isteyen bağımlılık üreticisi.

    Kullanım:
        @router.get("/", dependencies=[Depends(require_permissions(Perm.STUDENT_READ))])
    """

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user
        owned = user.permissions
        needed = {str(p) for p in permissions}
        ok = needed.issubset(owned) if require_all else bool(needed & owned)
        if not ok:
            raise PermissionDeniedError(
                details={"required": sorted(needed), "missing": sorted(needed - owned)}
            )
        return user

    return _checker


def require_any_permission(*permissions: str) -> Callable:
    return require_permissions(*permissions, require_all=False)


def require_roles(*role_codes: str) -> Callable:
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user
        if not user.has_any_role({str(r) for r in role_codes}):
            raise PermissionDeniedError(details={"required_roles": list(role_codes)})
        return user

    return _checker


def pagination(
    page: int = 1,
    page_size: int = 25,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> PaginationParams:
    return PaginationParams(
        page=max(1, page),
        page_size=min(max(1, page_size), 200),
        sort_by=sort_by,
        sort_dir="desc" if sort_dir.lower() == "desc" else "asc",
    )


class AccessScope:
    """Satır bazlı erişim kapsamı.

    Öğrenci/veli/sporcu rolleri yalnızca kendi (veya çocuklarının) verisini,
    eğitmen rolleri öncelikle kendi derslerini görür.
    """

    def __init__(self, user: User, db: Session) -> None:
        self.user = user
        self.db = db
        self.is_admin = user.is_superuser or user.has_any_role(
            {
                RoleCode.SYSTEM_ADMIN,
                RoleCode.SCHOOL_DIRECTOR,
                RoleCode.OPERATIONS_MANAGER,
            }
        )
        self.is_self_scoped = (
            not self.is_admin
            and user.has_any_role(SELF_SCOPED_ROLES)
            and not user.has_permission(Perm.STUDENT_WRITE)
        )
        self.is_instructor_scoped = (
            not self.is_admin
            and not self.is_self_scoped
            and user.has_any_role(INSTRUCTOR_SCOPED_ROLES)
        )

    @property
    def instructor_id(self) -> int | None:
        return self.user.instructor.id if self.user.instructor else None

    @property
    def student_id(self) -> int | None:
        return self.user.student.id if self.user.student else None

    def allowed_student_ids(self) -> list[int] | None:
        """None => kısıt yok. Liste => yalnızca bu öğrenciler görülebilir."""
        if not self.is_self_scoped:
            return None
        ids: list[int] = []
        if self.user.student:
            ids.append(self.user.student.id)
        if self.user.guardian:
            ids.extend(sg.student_id for sg in self.user.guardian.students)
        return ids or [-1]  # eşleşme yoksa hiçbir kaydı döndürme

    def can_read_sensitive(self) -> bool:
        return self.user.has_permission(Perm.STUDENT_READ_SENSITIVE)

    def can_read_salary(self) -> bool:
        return (
            self.user.has_any_role(
                {
                    RoleCode.SYSTEM_ADMIN,
                    RoleCode.SCHOOL_DIRECTOR,
                    RoleCode.FINANCE,
                    RoleCode.HR,
                }
            )
            or self.user.is_superuser
        )

    # ------------------------------------------------------------------
    # Ortak satır/nesne bazlı yetkilendirme mekanizması
    # Shared row / object level authorisation mechanism
    #
    # Kendi verisiyle sınırlı roller (ATHLETE / STUDENT / PARENT) için tek
    # noktadan uygulanır. Her uç ya `scope_students(...)` ile sorguyu daraltır,
    # ya `assert_student_allowed(...)` ile tekil nesneyi doğrular, ya da
    # `assert_org_wide()` ile kohort ötesi toplulaştırmayı reddeder.
    # ------------------------------------------------------------------

    def assert_org_wide(self) -> None:
        """Kurum geneli veriye erişimi kendi verisiyle sınırlı rollere kapatır.

        Toplulaştırılmış/kurum geneli uçlar satır bazlı filtrelenemez; bu
        yüzden self-scoped roller için tamamen reddedilir.
        """
        if self.is_self_scoped:
            raise PermissionDeniedError(details={"reason": "scope.org_wide_only"})

    def assert_student_allowed(self, student_id: int | None) -> None:
        """Tekil öğrenci nesnesine erişimi doğrular (IDOR koruması)."""
        allowed = self.allowed_student_ids()
        if allowed is None:
            return
        if student_id is None or int(student_id) not in allowed:
            raise PermissionDeniedError(details={"reason": "scope.student_forbidden"})

    def assert_students_allowed(self, student_ids: Iterable[int | None]) -> None:
        allowed = self.allowed_student_ids()
        if allowed is None:
            return
        for student_id in student_ids:
            if student_id is None or int(student_id) not in allowed:
                raise PermissionDeniedError(
                    details={"reason": "scope.student_forbidden"}
                )

    def scope_students(self, stmt, column):  # noqa: ANN001, ANN202
        """Bir sorguyu öğrenci kimliği sütunu üzerinden daraltır."""
        allowed = self.allowed_student_ids()
        if allowed is None:
            return stmt
        return stmt.where(column.in_(allowed))

    def limit_student_ids(self, requested: Iterable[int] | None) -> list[int] | None:
        """İstenen öğrenci kimliklerini izin verilen kümeyle kesiştirir."""
        allowed = self.allowed_student_ids()
        if allowed is None:
            return list(requested) if requested is not None else None
        if requested is None:
            return list(allowed)
        allowed_set = set(allowed)
        return [int(s) for s in requested if int(s) in allowed_set]

    def filter_student_payloads(
        self, items: Iterable[dict], key: str = "student_id"
    ) -> list[dict]:
        """Sözlük listelerini (toplulaştırılmış çıktı) satır bazlı süzer."""
        allowed = self.allowed_student_ids()
        if allowed is None:
            return list(items)
        allowed_set = set(allowed)
        return [item for item in items if item.get(key) in allowed_set]

    def assert_lesson_allowed(self, lesson_id: int) -> None:
        """Ders nesnesine erişimi doğrular.

        Self-scoped rol yalnızca kendisinin/çocuğunun kayıtlı olduğu dersi görür.
        """
        allowed = self.allowed_student_ids()
        if allowed is None:
            return
        from app.models.lesson import LessonEnrollment  # yerelde: döngüsel import yok

        found = self.db.scalar(
            select(LessonEnrollment.id)
            .where(
                LessonEnrollment.lesson_id == lesson_id,
                LessonEnrollment.student_id.in_(allowed),
            )
            .limit(1)
        )
        if found is None:
            raise PermissionDeniedError(details={"reason": "scope.lesson_forbidden"})


def get_scope(
    user: User = Depends(get_current_user), db: Session = Depends(db_session)
) -> AccessScope:
    return AccessScope(user, db)


def require_org_wide_scope(scope: AccessScope = Depends(get_scope)) -> AccessScope:
    """Kurum geneli uçlar için bağımlılık: self-scoped rolleri reddeder."""
    scope.assert_org_wide()
    return scope


def client_ip(request: Request) -> str | None:
    """İstemci IP'si (proxy başlığı varsa ilk değeri)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
