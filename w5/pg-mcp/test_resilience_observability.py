"""弹性与可观测性集成测试

测试模块：
1. Circuit Breaker（熔断器）
2. Rate Limiter（速率限制）
3. Metrics（指标收集）
"""
import asyncio
from pg_mcp.resilience.circuit_breaker import CircuitBreaker, CircuitState
from pg_mcp.resilience.rate_limiter import RateLimiter
from pg_mcp.observability.metrics import MetricsCollector


async def test_rate_limiter():
    """测试速率限制器"""
    print("\n" + "=" * 60)
    print("测试 1: 速率限制器")
    print("=" * 60)

    limiter = RateLimiter(max_concurrent=3)

    async def task(task_id: int):
        async with limiter():
            print(f"  任务 {task_id} 开始执行 (活跃: {limiter.active_count}/{limiter.max_concurrent})")
            await asyncio.sleep(0.5)
            print(f"  任务 {task_id} 完成")

    # 启动 6 个并发任务，但只允许 3 个同时执行
    print("\n启动 6 个任务，限制并发数为 3...")
    tasks = [task(i) for i in range(1, 7)]
    await asyncio.gather(*tasks)

    stats = limiter.get_stats()
    print(f"\n统计信息:")
    print(f"  最大并发: {stats['max_concurrent']}")
    print(f"  总请求数: {stats['total_requests']}")
    print(f"  拒绝数: {stats['total_rejections']}")
    print("✅ 速率限制器测试通过")


async def test_circuit_breaker():
    """测试熔断器"""
    print("\n" + "=" * 60)
    print("测试 2: 熔断器")
    print("=" * 60)

    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=2.0)

    # 测试初始状态
    assert breaker.state == CircuitState.CLOSED
    print(f"  初始状态: {breaker.state} ✅")

    # 模拟 3 次失败
    print("\n模拟 3 次失败...")
    for i in range(3):
        breaker.record_failure()
        print(f"  失败 {i+1}: {breaker}")

    # 验证熔断器打开
    assert breaker.state == CircuitState.OPEN
    assert not breaker.allow_request()
    print(f"\n  熔断器状态: {breaker.state} ✅")
    print(f"  阻止请求: {not breaker.allow_request()} ✅")

    # 等待恢复超时
    print(f"\n等待 {breaker._recovery_timeout} 秒进行恢复...")
    await asyncio.sleep(breaker._recovery_timeout + 0.1)

    # 验证进入半开状态
    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.allow_request()
    print(f"  熔断器状态: {breaker.state} ✅")
    print(f"  允许测试请求: {breaker.allow_request()} ✅")

    # 模拟成功请求
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    print(f"\n  成功后状态: {breaker.state} ✅")

    print("✅ 熔断器测试通过")


def test_metrics():
    """测试指标收集"""
    print("\n" + "=" * 60)
    print("测试 3: 指标收集")
    print("=" * 60)

    metrics = MetricsCollector()

    # 记录各种指标
    print("\n记录指标...")
    metrics.increment_query_request("success", "postgres")
    metrics.increment_query_request("success", "postgres")
    metrics.increment_query_request("error", "postgres")
    print("  ✅ 查询请求计数器")

    metrics.increment_llm_call("generate_sql")
    metrics.observe_llm_latency("generate_sql", 1.5)
    metrics.increment_llm_tokens("generate_sql", 150)
    print("  ✅ LLM 调用计数器")

    metrics.increment_sql_rejected("ddl_detected")
    print("  ✅ SQL 拒绝计数器")

    metrics.observe_db_query_duration(0.25)
    print("  ✅ 数据库查询延迟")

    metrics.set_schema_cache_age("postgres", 300.0)
    print("  ✅ Schema 缓存年龄")

    print("\n提示: 访问 http://localhost:9090/metrics 查看完整指标")
    print("✅ 指标收集测试通过")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("弹性与可观测性模块集成测试")
    print("=" * 60)

    try:
        await test_rate_limiter()
        await test_circuit_breaker()
        test_metrics()

        print("\n" + "=" * 60)
        print("所有测试通过！✅")
        print("=" * 60)

        print("\n下一步:")
        print("1. 访问 http://localhost:9090/metrics 查看 Prometheus 指标")
        print("2. 发送实际查询，观察指标变化")
        print("3. 模拟 LLM 失败，测试熔断器")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
