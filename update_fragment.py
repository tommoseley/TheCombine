import asyncio
from app.core.database import async_session_factory
from app.api.services.fragment_registry_service import FragmentRegistryService
from seed.registry.fragment_artifacts import EPIC_STORIES_CARD_BLOCK_V1_FRAGMENT

async def update_fragment():
    async with async_session_factory() as db:
        registry = FragmentRegistryService(db)
        
        # Get existing fragment
        existing = await registry.get_fragment("epic_stories_card_block_v1", 1)
        
        if existing:
            # Update the markup directly
            from sqlalchemy import text
            await db.execute(
                text("UPDATE fragment_artifacts SET fragment_markup = :markup WHERE fragment_id = :fid AND version = :v"),
                {"markup": EPIC_STORIES_CARD_BLOCK_V1_FRAGMENT, "fid": "epic_stories_card_block_v1", "v": 1}
            )
            await db.commit()
            print("Fragment updated!")
        else:
            print("Fragment not found")

asyncio.run(update_fragment())
