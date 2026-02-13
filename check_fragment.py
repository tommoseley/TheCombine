import asyncio
from app.core.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as db:
        result = await db.execute(
            text("SELECT fragment_markup FROM fragment_artifacts WHERE fragment_id = 'epic_stories_card_block_v1'")
        )
        row = result.fetchone()
        with open('C:/Dev/fragment_check.txt', 'w') as f:
            if row:
                markup = row[0]
                if 'no-stories-section' in markup:
                    f.write("SUCCESS: Fragment contains no-stories-section class")
                else:
                    f.write("FAIL: Fragment does NOT contain no-stories-section class")
            else:
                f.write("Fragment not found")

asyncio.run(check())
