try:
    import asyncio
    from app.core.database import async_session_factory
    from sqlalchemy import text

    async def check():
        async with async_session_factory() as db:
            r = await db.execute(text("SELECT doc_type_id, required_inputs FROM document_types WHERE doc_type_id = 'epic_backlog'"))
            row = r.fetchone()
            with open('C:/Dev/result.txt', 'w') as f:
                if row:
                    f.write(f'epic_backlog required_inputs: {row[1]}')
                else:
                    f.write('epic_backlog not found')

    asyncio.run(check())
except Exception as e:
    with open('C:/Dev/error.txt', 'w') as f:
        f.write(str(e))
