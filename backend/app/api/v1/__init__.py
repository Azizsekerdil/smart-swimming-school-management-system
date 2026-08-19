"""API v1 yönlendirici birleştirmesi / API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    ai_developer,
    attendance,
    auth,
    backup,
    caio,
    competitions,
    finance,
    guardians,
    instructors,
    lessons,
    memberships,
    performance,
    pools,
    reports,
    search,
    statistics,
    students,
    system,
    training,
    users,
)

api_router = APIRouter()

# --- Kimlik & kullanıcılar ---
api_router.include_router(auth.router)
api_router.include_router(users.router)

# --- Kişiler ---
api_router.include_router(students.router)
api_router.include_router(guardians.router)
api_router.include_router(instructors.router)
api_router.include_router(instructors.groups_router)

# --- Tesis & program ---
api_router.include_router(pools.router)
api_router.include_router(lessons.router)
api_router.include_router(attendance.router)

# --- Ticari ---
api_router.include_router(memberships.router)
api_router.include_router(memberships.packages_router)
api_router.include_router(finance.router)

# --- Spor ---
api_router.include_router(performance.router)
api_router.include_router(competitions.router)

# --- Analitik ---
api_router.include_router(statistics.router)
api_router.include_router(reports.router)

# --- Yapay zekâ ---
api_router.include_router(ai.router)
api_router.include_router(ai_developer.router)
api_router.include_router(caio.router)

# --- Sistem ---
api_router.include_router(backup.router)
api_router.include_router(search.router)
api_router.include_router(training.router)
api_router.include_router(system.router)

__all__ = ["api_router"]
