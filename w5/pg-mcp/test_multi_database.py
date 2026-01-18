"""测试多数据库支持的脚本

这个脚本演示如何配置和测试多数据库支持。

使用方法：
1. 确保你有多个数据库可用（可以是同一个 PostgreSQL 实例中的不同数据库）
2. 修改下面的配置，添加你的数据库连接信息
3. 运行: python test_multi_database.py
"""

import asyncio
import os
from pg_mcp.config.settings import DatabaseConfig, Settings
from pg_mcp.db.pool import create_pool, close_pools


async def test_multi_database():
    """测试多数据库配置"""

    # 方式 1: 通过代码直接创建多个数据库配置
    db1_config = DatabaseConfig(
        host="aws-0-us-west-2.pooler.supabase.com",
        port=6543,
        name="postgres",  # 主数据库
        user="postgres.rpzmbxmfvsgulwrqxvsb",
        password="Linemore@2030!",
    )

    # 如果你有第二个数据库，可以这样配置
    # 注意：这里假设你在同一个 Supabase 实例中创建了 test_db
    db2_config = DatabaseConfig(
        host="aws-0-us-west-2.pooler.supabase.com",
        port=6543,
        name="test_db",  # 测试数据库
        user="postgres.rpzmbxmfvsgulwrqxvsb",
        password="Linemore@2030!",
    )

    # 创建连接池
    pools = {}

    try:
        print("正在连接数据库...")

        # 连接第一个数据库
        try:
            pool1 = await create_pool(db1_config)
            pools[db1_config.name] = pool1
            print(f"✓ 成功连接到数据库: {db1_config.name}")

            # 测试查询
            async with pool1.acquire() as conn:
                result = await conn.fetchval("SELECT current_database()")
                print(f"  当前数据库: {result}")

                # 列出所有表
                tables = await conn.fetch("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)
                print(f"  表数量: {len(tables)}")
                if tables:
                    print(f"  表列表: {', '.join([t['tablename'] for t in tables[:5]])}")
        except Exception as e:
            print(f"✗ 连接数据库 {db1_config.name} 失败: {e}")

        # 连接第二个数据库
        try:
            pool2 = await create_pool(db2_config)
            pools[db2_config.name] = pool2
            print(f"✓ 成功连接到数据库: {db2_config.name}")

            # 测试查询
            async with pool2.acquire() as conn:
                result = await conn.fetchval("SELECT current_database()")
                print(f"  当前数据库: {result}")

                # 列出所有表
                tables = await conn.fetch("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)
                print(f"  表数量: {len(tables)}")
                if tables:
                    print(f"  表列表: {', '.join([t['tablename'] for t in tables[:5]])}")
        except Exception as e:
            print(f"✗ 连接数据库 {db2_config.name} 失败: {e}")
            print(f"  提示: 请确保数据库 '{db2_config.name}' 已创建")
            print(f"  你可以使用以下 SQL 创建: CREATE DATABASE {db2_config.name};")

        print(f"\n总共配置了 {len(pools)} 个数据库")
        print(f"可用数据库: {list(pools.keys())}")

    finally:
        # 清理连接池
        if pools:
            print("\n正在关闭连接池...")
            await close_pools(pools)
            print("✓ 连接池已关闭")


async def test_settings_multi_database():
    """测试通过 Settings 配置多数据库"""

    print("\n" + "="*60)
    print("测试通过 Settings 配置多数据库")
    print("="*60)

    # 创建多个数据库配置
    db_configs = [
        DatabaseConfig(
            host="aws-0-us-west-2.pooler.supabase.com",
            port=6543,
            name="postgres",
            user="postgres.rpzmbxmfvsgulwrqxvsb",
            password="Linemore@2030!",
        ),
        # 如果有第二个数据库，取消注释
        # DatabaseConfig(
        #     host="aws-0-us-west-2.pooler.supabase.com",
        #     port=6543,
        #     name="test_db",
        #     user="postgres.rpzmbxmfvsgulwrqxvsb",
        #     password="Linemore@2030!",
        # ),
    ]

    # 创建 Settings 实例
    settings = Settings(databases=db_configs)

    print(f"配置的数据库数量: {len(settings.databases)}")
    for db in settings.databases:
        print(f"  - {db.name} ({db.safe_dsn})")

    print(f"默认数据库: {settings.default_database}")


if __name__ == "__main__":
    print("="*60)
    print("PostgreSQL MCP 多数据库支持测试")
    print("="*60)
    print()

    # 测试直接连接
    asyncio.run(test_multi_database())

    # 测试 Settings 配置
    asyncio.run(test_settings_multi_database())

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
