"""Quick script to list all tables in the PostgreSQL database."""
import asyncio
import asyncpg


async def list_tables():
    """Connect to database and list all tables."""
    conn = await asyncpg.connect(
        host="aws-0-us-west-2.pooler.supabase.com",
        port=6543,
        database="postgres",
        user="postgres.rpzmbxmfvsgulwrqxvsb",
        password="Linemore@2030!",
    )

    try:
        # Query to get all tables in public schema
        query = """
        SELECT
            schemaname,
            tablename,
            tableowner
        FROM pg_catalog.pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schemaname, tablename;
        """

        rows = await conn.fetch(query)

        print(f"\n找到 {len(rows)} 个表:\n")
        print(f"{'Schema':<20} {'Table Name':<40} {'Owner':<30}")
        print("-" * 90)

        for row in rows:
            print(f"{row['schemaname']:<20} {row['tablename']:<40} {row['tableowner']:<30}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(list_tables())
