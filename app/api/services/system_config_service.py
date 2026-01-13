"""
System Configuration Service.

Simple service for reading/writing system config values.
Includes in-memory caching since these values rarely change.
"""

from typing import Dict, Optional
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


class SystemConfigService:
    """Service for system configuration key-value store."""
    
    # Simple in-memory cache (cleared on write)
    _cache: Dict[str, str] = {}
    _cache_loaded: bool = False
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a config value by key.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Config value or default
        """
        # Check cache first
        if self._cache_loaded and key in self._cache:
            return self._cache[key]
        
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if config:
            self._cache[key] = config.value
            return config.value
        
        return default
    
    async def get_all(self) -> Dict[str, str]:
        """
        Get all config values as a dict.
        
        Returns:
            Dict of key -> value
        """
        if self._cache_loaded:
            return self._cache.copy()
        
        stmt = select(SystemConfig)
        result = await self.db.execute(stmt)
        configs = result.scalars().all()
        
        self._cache = {c.key: c.value for c in configs}
        self._cache_loaded = True
        
        return self._cache.copy()
    
    async def set(self, key: str, value: str, description: Optional[str] = None) -> None:
        """
        Set a config value (upsert).
        
        Args:
            key: Configuration key
            value: Value to set
            description: Optional description
        """
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if config:
            config.value = value
            if description:
                config.description = description
        else:
            config = SystemConfig(key=key, value=value, description=description)
            self.db.add(config)
        
        await self.db.commit()
        
        # Update cache
        self._cache[key] = value
        
        logger.info(f"Set system config: {key}={value}")
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the config cache (call after direct DB updates)."""
        cls._cache = {}
        cls._cache_loaded = False


async def get_environment_display(db: AsyncSession) -> Dict[str, str]:
    """
    Convenience function to get environment display info.
    
    Returns:
        Dict with 'name', 'version', 'badge_color'
    """
    service = SystemConfigService(db)
    
    return {
        "name": await service.get("environment_name", "Unknown"),
        "version": await service.get("version", "v0.0"),
        "badge_color": await service.get("environment_badge_color", "gray"),
    }