import asyncio
import os
import asyncpg
from pg_mcp.config.settings import Settings

async def test_supabase_connection():
    # 强制加载 .env (虽然 Settings 会自动做，但我们想直接验证)
    settings = Settings()
    
    print(f"Connecting to Supabase:")
    print(f"  Host: {settings.database.host}")
    print(f"  Port: {settings.database.port}")
    print(f"  User: {settings.database.user}")
    print(f"  DB:   {settings.database.name}")
    print(f"  Pwd:  {'*' * len(settings.database.password)}")
    
    try:
        # 关键测试点：禁用 statement_cache_size (Transaction Mode 必须)
        conn = await asyncpg.connect(
            host=settings.database.host,
            port=settings.database.port,
            user=settings.database.user,
            password=settings.database.password,
            database=settings.database.name,
            statement_cache_size=0,
            timeout=10
        )
        print("\n✅ Connection successful!")
        
        # 简单查询验证
        version = await conn.fetchval("SELECT version()")
        print(f"Server version: {version}")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        # 如果是认证错误，提示可能的原因
        if "password authentication failed" in str(e):
            print("Tip: Please double check your DATABASE_PASSWORD in .env")

if __name__ == "__main__":
    asyncio.run(test_supabase_connection())
