"""
System Configuration Routes.

Provides public endpoint for environment display info.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.services.system_config_service import get_environment_display, SystemConfigService

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/environment")
async def get_environment(db: AsyncSession = Depends(get_db)):
    """
    Get environment display info for UI.
    
    Returns:
        {name, version, badge_color}
    """
    return await get_environment_display(db)


@router.get("/{key}")
async def get_config_value(key: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific config value.
    
    Returns:
        {key, value} or 404
    """
    service = SystemConfigService(db)
    value = await service.get(key)
    
    if value is None:
        return {"error": "not_found", "key": key}
    
    return {"key": key, "value": value}