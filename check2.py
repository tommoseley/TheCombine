import asyncio
import sys

try:
    from app.core.database import async_session_factory
    from sqlalchemy import text

    async def check():
        async with async_session_factory() as db:
            result = await db.execute(
                text("SELECT fragment_markup FROM fragment_artifacts WHERE fragment_id = 'epic_stories_card_block_v1'")
            )
            row = result.fetchone()
            if row:
                markup = row[0]
                if 'no-stories-section' in markup:
                    return "SUCCESS"
                else:
                    return "FAIL - no class"
            else:
                return "NOT FOUND"

    result = asyncio.run(check())
    with open('C:/Dev/result.txt', 'w') as f:
        f.write(result)
except Exception as e:
    with open('C:/Dev/error.txt', 'w') as f:
        f.write(str(e))
