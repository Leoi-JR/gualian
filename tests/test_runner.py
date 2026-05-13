#!/usr/bin/env python3
"""
测试运行器
Test Runner

统一运行所有单元测试，生成测试报告。

作者：系统重构
日期：2024年
"""

import unittest
import sys
import os
from pathlib import Path
from io import StringIO

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def discover_and_run_tests(verbosity=2, buffer=True):
    """
    发现并运行所有测试
    
    Args:
        verbosity (int): 详细程度 (0=quiet, 1=normal, 2=verbose)
        buffer (bool): 是否缓冲输出
    
    Returns:
        bool: 是否所有测试都通过
    """
    print("=" * 60)
    print("RuleKit - 单元测试")
    print("=" * 60)
    
    # 发现测试
    test_dir = Path(__file__).parent
    loader = unittest.TestLoader()
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    # 统计测试数量
    test_count = suite.countTestCases()
    print(f"发现 {test_count} 个测试用例")
    print("-" * 60)
    
    # 运行测试
    stream = StringIO() if buffer else sys.stderr
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=verbosity,
        buffer=buffer
    )
    
    result = runner.run(suite)
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    
    # 显示失败的测试
    if result.failures:
        print("\n失败的测试:")
        print("-" * 40)
        for test, traceback in result.failures:
            print(f"❌ {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    # 显示错误的测试
    if result.errors:
        print("\n错误的测试:")
        print("-" * 40)
        for test, traceback in result.errors:
            print(f"💥 {test}: {traceback.split('Error:')[-1].strip()}")
    
    # 计算成功率
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n成功率: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
        return True
    else:
        print("❌ 部分测试失败！")
        return False


def run_specific_test(test_module=None, test_class=None, test_method=None):
    """
    运行特定的测试
    
    Args:
        test_module (str): 测试模块名
        test_class (str): 测试类名
        test_method (str): 测试方法名
    
    Returns:
        bool: 测试是否通过
    """
    if test_module:
        try:
            module = __import__(f"tests.{test_module}", fromlist=[test_module])
            suite = unittest.TestLoader().loadTestsFromModule(module)
        except ImportError as e:
            print(f"❌ 无法导入测试模块 {test_module}: {e}")
            return False
    else:
        print("❌ 必须指定测试模块")
        return False
    
    # 如果指定了测试类
    if test_class:
        try:
            test_class_obj = getattr(module, test_class)
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class_obj)
        except AttributeError:
            print(f"❌ 找不到测试类 {test_class}")
            return False
    
    # 如果指定了测试方法
    if test_method:
        if not test_class:
            print("❌ 指定测试方法时必须同时指定测试类")
            return False
        try:
            suite = unittest.TestSuite([test_class_obj(test_method)])
        except:
            print(f"❌ 找不到测试方法 {test_method}")
            return False
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_coverage_test():
    """
    运行代码覆盖率测试
    
    Returns:
        bool: 测试是否成功
    """
    try:
        import coverage
    except ImportError:
        print("❌ 未安装coverage模块，请运行: pip install coverage")
        return False
    
    print("=" * 60)
    print("代码覆盖率测试")
    print("=" * 60)
    
    # 创建coverage对象
    cov = coverage.Coverage()
    cov.start()
    
    # 运行测试
    success = discover_and_run_tests(verbosity=1, buffer=True)
    
    # 停止覆盖率收集
    cov.stop()
    cov.save()
    
    # 生成报告
    print("\n" + "=" * 60)
    print("代码覆盖率报告")
    print("=" * 60)
    
    cov.report()
    
    # 生成HTML报告
    html_dir = project_root / "htmlcov"
    cov.html_report(directory=str(html_dir))
    print(f"\nHTML覆盖率报告已生成到: {html_dir}")
    
    return success


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RuleKit 单元测试运行器")
    parser.add_argument("--module", "-m", help="运行特定模块的测试")
    parser.add_argument("--class", "-c", dest="test_class", help="运行特定类的测试")
    parser.add_argument("--method", "-t", help="运行特定方法的测试")
    parser.add_argument("--coverage", action="store_true", help="运行代码覆盖率测试")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细模式")
    
    args = parser.parse_args()
    
    # 设置详细程度
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 2
    else:
        verbosity = 1
    
    # 运行特定测试
    if args.module:
        success = run_specific_test(args.module, args.test_class, args.method)
    elif args.coverage:
        success = run_coverage_test()
    else:
        success = discover_and_run_tests(verbosity=verbosity)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 