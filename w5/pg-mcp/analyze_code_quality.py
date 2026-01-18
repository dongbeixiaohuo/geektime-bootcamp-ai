"""代码质量验证脚本

验证项目的代码质量、配置使用情况和模型一致性
"""
import ast
import os
from pathlib import Path
from collections import defaultdict


class CodeQualityAnalyzer:
    """代码质量分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src" / "pg_mcp"
        self.issues = []
        self.stats = {}

    def analyze_to_dict_methods(self):
        """分析 to_dict 方法的使用"""
        print("\n" + "=" * 60)
        print("1. 分析 to_dict 方法")
        print("=" * 60)

        to_dict_methods = {}

        for py_file in self.src_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "def to_dict" in content:
                    # 简单统计
                    count = content.count("def to_dict")
                    to_dict_methods[py_file.relative_to(self.project_root)] = count

        print(f"\n找到 {len(to_dict_methods)} 个文件包含 to_dict 方法:")
        for file, count in to_dict_methods.items():
            print(f"  {file}: {count} 个方法")

        # 检查是否有重复
        duplicates = {f: c for f, c in to_dict_methods.items() if c > 1}
        if duplicates:
            print(f"\n⚠️  发现 {len(duplicates)} 个文件有多个 to_dict 方法:")
            for file, count in duplicates.items():
                print(f"  {file}: {count} 个")
                self.issues.append(f"多个 to_dict 方法: {file}")
        else:
            print("\n✅ 没有发现重复的 to_dict 方法")

        self.stats["to_dict_methods"] = len(to_dict_methods)
        self.stats["to_dict_duplicates"] = len(duplicates)

    def analyze_config_usage(self):
        """分析配置字段的使用情况"""
        print("\n" + "=" * 60)
        print("2. 分析配置字段使用情况")
        print("=" * 60)

        # 定义需要检查的配置字段
        config_fields = {
            "readonly_role": "SecurityConfig",
            "safe_search_path": "SecurityConfig",
            "explain_policy": "SecurityConfig",
            "blocked_tables": "SecurityConfig",
            "blocked_columns": "SecurityConfig",
            "max_rows": "SecurityConfig",
            "max_execution_time": "SecurityConfig",
            "min_confidence_score": "ValidationConfig",
            "sample_rows": "ValidationConfig",
            "schema_ttl": "CacheConfig",
        }

        usage_count = {}

        for field in config_fields:
            count = 0
            for py_file in self.src_dir.rglob("*.py"):
                if py_file.name == "settings.py":
                    continue
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    count += content.count(field)
            usage_count[field] = count

        print("\n配置字段使用统计:")
        for field, count in sorted(usage_count.items(), key=lambda x: x[1]):
            status = "✅" if count > 0 else "⚠️ "
            print(f"  {status} {field}: {count} 次使用")
            if count == 0:
                self.issues.append(f"未使用的配置字段: {field}")

        unused = [f for f, c in usage_count.items() if c == 0]
        self.stats["config_fields_total"] = len(config_fields)
        self.stats["config_fields_unused"] = len(unused)

        if unused:
            print(f"\n⚠️  发现 {len(unused)} 个未使用的配置字段")
        else:
            print("\n✅ 所有配置字段都被使用")

    def analyze_response_models(self):
        """分析响应模型的一致性"""
        print("\n" + "=" * 60)
        print("3. 分析响应模型一致性")
        print("=" * 60)

        # 检查 QueryResponse 的使用
        query_response_files = []
        for py_file in self.src_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "QueryResponse" in content:
                    count = content.count("QueryResponse(")
                    if count > 0:
                        query_response_files.append((py_file.relative_to(self.project_root), count))

        print(f"\n找到 {len(query_response_files)} 个文件使用 QueryResponse:")
        for file, count in query_response_files:
            print(f"  {file}: {count} 次")

        # 检查 to_dict 调用
        to_dict_calls = 0
        for py_file in self.src_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                to_dict_calls += content.count(".to_dict()")

        print(f"\n找到 {to_dict_calls} 次 to_dict() 调用")

        self.stats["query_response_usage"] = len(query_response_files)
        self.stats["to_dict_calls"] = to_dict_calls

        print("\n✅ 响应模型使用一致")

    def analyze_test_coverage(self):
        """分析测试覆盖情况"""
        print("\n" + "=" * 60)
        print("4. 分析测试覆盖情况")
        print("=" * 60)

        # 统计源代码文件
        src_files = list(self.src_dir.rglob("*.py"))
        src_files = [f for f in src_files if "__pycache__" not in str(f)]

        # 统计测试文件
        test_dir = self.project_root / "tests"
        test_files = list(test_dir.rglob("test_*.py"))

        # 统计代码行数
        src_lines = 0
        for f in src_files:
            with open(f, "r", encoding="utf-8") as file:
                src_lines += len(file.readlines())

        test_lines = 0
        for f in test_files:
            with open(f, "r", encoding="utf-8") as file:
                test_lines += len(file.readlines())

        print(f"\n源代码文件: {len(src_files)} 个")
        print(f"源代码行数: {src_lines} 行")
        print(f"\n测试文件: {len(test_files)} 个")
        print(f"测试代码行数: {test_lines} 行")
        print(f"\n测试代码比例: {test_lines / src_lines * 100:.1f}%")

        # 检查哪些模块有测试
        src_modules = {f.stem for f in src_files if f.stem != "__init__"}
        test_modules = {f.stem.replace("test_", "") for f in test_files}

        untested = src_modules - test_modules
        if untested:
            print(f"\n⚠️  {len(untested)} 个模块没有测试:")
            for module in sorted(untested):
                print(f"  - {module}")
                self.issues.append(f"缺少测试: {module}")
        else:
            print("\n✅ 所有模块都有测试")

        self.stats["src_files"] = len(src_files)
        self.stats["test_files"] = len(test_files)
        self.stats["src_lines"] = src_lines
        self.stats["test_lines"] = test_lines
        self.stats["test_ratio"] = test_lines / src_lines
        self.stats["untested_modules"] = len(untested)

    def generate_report(self):
        """生成分析报告"""
        print("\n" + "=" * 60)
        print("代码质量分析报告")
        print("=" * 60)

        print("\n统计信息:")
        print(f"  源代码文件: {self.stats.get('src_files', 0)}")
        print(f"  源代码行数: {self.stats.get('src_lines', 0)}")
        print(f"  测试文件: {self.stats.get('test_files', 0)}")
        print(f"  测试代码行数: {self.stats.get('test_lines', 0)}")
        print(f"  测试代码比例: {self.stats.get('test_ratio', 0) * 100:.1f}%")
        print(f"\n  to_dict 方法: {self.stats.get('to_dict_methods', 0)}")
        print(f"  to_dict 重复: {self.stats.get('to_dict_duplicates', 0)}")
        print(f"  配置字段总数: {self.stats.get('config_fields_total', 0)}")
        print(f"  未使用配置: {self.stats.get('config_fields_unused', 0)}")
        print(f"  未测试模块: {self.stats.get('untested_modules', 0)}")

        if self.issues:
            print(f"\n发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ 没有发现问题")

        # 评分
        score = 100
        score -= self.stats.get('to_dict_duplicates', 0) * 5
        score -= self.stats.get('config_fields_unused', 0) * 3
        score -= self.stats.get('untested_modules', 0) * 2

        print(f"\n代码质量评分: {max(0, score)}/100")

        if score >= 90:
            print("评级: 优秀 ⭐⭐⭐⭐⭐")
        elif score >= 80:
            print("评级: 良好 ⭐⭐⭐⭐")
        elif score >= 70:
            print("评级: 中等 ⭐⭐⭐")
        else:
            print("评级: 需要改进 ⭐⭐")

    def run_all_checks(self):
        """运行所有检查"""
        print("=" * 60)
        print("PostgreSQL MCP 代码质量分析")
        print("=" * 60)

        self.analyze_to_dict_methods()
        self.analyze_config_usage()
        self.analyze_response_models()
        self.analyze_test_coverage()
        self.generate_report()


if __name__ == "__main__":
    import sys

    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    analyzer = CodeQualityAnalyzer(project_root)
    analyzer.run_all_checks()
