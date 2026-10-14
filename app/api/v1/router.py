from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    containers,
    dashboard,
    inventory,
    items,
    notifications,
    properties,
    reference,
    reminders,
    system,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(properties.router)
api_router.include_router(properties.invitation_router)
api_router.include_router(reference.router)
api_router.include_router(containers.router)
api_router.include_router(items.router)
api_router.include_router(inventory.router)
api_router.include_router(reminders.router)
api_router.include_router(notifications.router)
api_router.include_router(system.router)
api_router.include_router(dashboard.router)
