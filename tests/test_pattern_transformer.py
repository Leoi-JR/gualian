#!/usr/bin/env python3
"""
PatternTransformer 单元测试
Pattern Transformer Unit Tests

测试模式转换器的各项功能，确保转换结果的正确性。

作者：系统重构
日期：2024年
"""

import unittest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.pattern_transformer import PatternTransformer
from core.data_models import TransformResult, PatternType


class TestPatternTransformer(unittest.TestCase):
    """PatternTransformer 测试类"""
    
    def setUp(self):
        """测试前设置"""
        self.transformer = PatternTransformer(default_max_chars=200)
    
    def test_single_keyword_pattern(self):
        """测试单个关键词模式"""
        test_cases = [
            "汽车",
            "新能源",
            "人工智能",
            "区块链技术"
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                result = self.transformer.transform_pattern(case)
                self.assertEqual(result[0], 0)  # 模式类型应该是0
                self.assertEqual(result[1], case)  # 关键词应该匹配
    
    def test_and_pattern(self):
        """测试&模式"""
        test_cases = [
            ("汽车&保险", [1, ["汽车"], ["保险"], 0, 200]),
            ("新能源&电池", [1, ["新能源"], ["电池"], 0, 200]),
            ("人工智能&机器学习", [1, ["人工智能"], ["机器学习"], 0, 200])
        ]
        
        for pattern, expected in test_cases:
            with self.subTest(pattern=pattern):
                result = self.transformer.transform_pattern(pattern)
                self.assertEqual(result, expected)
    
    def test_and_and_pattern(self):
        """测试&&模式"""
        test_cases = [
            ("汽车&&保险", [2, ["汽车"], ["保险"], 0, 200]),
            ("新能源&&电池", [2, ["新能源"], ["电池"], 0, 200]),
            ("人工智能&&机器学习", [2, ["人工智能"], ["机器学习"], 0, 200])
        ]
        
        for pattern, expected in test_cases:
            with self.subTest(pattern=pattern):
                result = self.transformer.transform_pattern(pattern)
                self.assertEqual(result, expected)
    
    def test_range_pattern(self):
        """测试范围模式"""
        test_cases = [
            ("车载.{0,5}充电机", [1, ["车载"], ["充电机"], 0, 5]),
            ("新能源.{1,10}汽车", [1, ["新能源"], ["汽车"], 1, 10]),
            ("人工智能.{0,20}应用", [1, ["人工智能"], ["应用"], 0, 20])
        ]
        
        for pattern, expected in test_cases:
            with self.subTest(pattern=pattern):
                result = self.transformer.transform_pattern(pattern)
                self.assertEqual(result, expected)
    
    def test_bracket_and_pattern(self):
        """测试括号&模式"""
        test_cases = [
            ("光刻机&(研发,制造,销售)", [1, ["光刻机"], ["研发", "制造", "销售"], 0, 200]),
            ("(研发,制造,销售)&光刻机", [1, ["研发", "制造", "销售"], ["光刻机"], 0, 200]),
            ("(新能源,氢能源)&(汽车,载具)", [1, ["新能源", "氢能源"], ["汽车", "载具"], 0, 200])
        ]
        
        for pattern, expected in test_cases:
            with self.subTest(pattern=pattern):
                result = self.transformer.transform_pattern(pattern)
                self.assertEqual(result, expected)
    
    def test_bracket_and_and_pattern(self):
        """测试括号&&模式"""
        test_cases = [
            ("光刻机&&(研发,制造,销售)", [2, ["光刻机"], ["研发", "制造", "销售"], 0, 200]),
            ("(研发,制造,销售)&&光刻机", [2, ["研发", "制造", "销售"], ["光刻机"], 0, 200]),
            ("(新能源,氢能源)&&(汽车,载具)", [2, ["新能源", "氢能源"], ["汽车", "载具"], 0, 200])
        ]
        
        for pattern, expected in test_cases:
            with self.subTest(pattern=pattern):
                result = self.transformer.transform_pattern(pattern)
                self.assertEqual(result, expected)
    
    def test_extract_bracket_items(self):
        """测试括号项目提取"""
        test_cases = [
            ("(研发,制造,销售)", ["研发", "制造", "销售"]),
            ("(新能源,氢能源)", ["新能源", "氢能源"]),
            ("(单项)", None),  # 单项应该返回None
            ("", None),       # 空字符串应该返回None
            ("无括号", None),  # 无括号应该返回None
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.transformer._extract_bracket_items(text)
                self.assertEqual(result, expected)
    
    def test_validate_range_values(self):
        """测试范围值验证"""
        # 有效范围值
        valid_cases = [
            ("0", "5", (0, 5)),
            ("1", "10", (1, 10)),
            ("10", "100", (10, 100))
        ]
        
        for num1, num2, expected in valid_cases:
            with self.subTest(num1=num1, num2=num2):
                result = self.transformer._validate_range_values(num1, num2)
                self.assertEqual(result, expected)
        
        # 无效范围值
        invalid_cases = [
            ("-1", "5"),    # 负数
            ("10", "5"),    # 最小值大于最大值
            ("0", "10001")  # 超过上限
        ]
        
        for num1, num2 in invalid_cases:
            with self.subTest(num1=num1, num2=num2):
                with self.assertRaises(ValueError):
                    self.transformer._validate_range_values(num1, num2)
    
    def test_transform_multiple_patterns(self):
        """测试多模式转换"""
        text = "新能源|汽车&保险|车载.{0,5}充电机"
        results = self.transformer.transform(text)
        
        expected = [
            [0, "新能源"],
            [1, ["汽车"], ["保险"], 0, 200],
            [1, ["车载"], ["充电机"], 0, 5]
        ]
        
        self.assertEqual(results, expected)
    
    def test_empty_and_invalid_inputs(self):
        """测试空值和无效输入"""
        # 空字符串
        result = self.transformer.transform_pattern("")
        self.assertEqual(result, [0, ""])
        
        # None值
        result = self.transformer.transform_pattern(None)
        self.assertEqual(result, [0, ""])
        
        # 空白字符串
        result = self.transformer.transform_pattern("   ")
        self.assertEqual(result, [0, ""])
        
        # 空列表测试
        result = self.transformer.transform("")
        self.assertEqual(result, [])
    
    def test_pattern_description(self):
        """测试模式描述功能"""
        test_cases = [
            ([0, "汽车"], "单个关键词: 汽车"),
            ([1, ["新能源"], ["汽车"], 0, 200], "有序匹配: ['新能源'] -> ['汽车'], 间隔: 0-200"),
            ([2, ["新能源"], ["汽车"], 0, 200], "无序匹配: ['新能源'] <-> ['汽车'], 间隔: 0-200")
        ]
        
        for result, expected_desc in test_cases:
            with self.subTest(result=result):
                description = self.transformer.get_pattern_description(result)
                self.assertEqual(description, expected_desc)
    
    def test_chinese_symbols_handling(self):
        """测试中文符号处理（如果实现了的话）"""
        # 注意：当前的PatternTransformer没有中文符号处理功能
        # 这个测试为未来的功能预留
        pass


class TestPatternTransformerEdgeCases(unittest.TestCase):
    """PatternTransformer 边缘情况测试"""
    
    def setUp(self):
        """测试前设置"""
        self.transformer = PatternTransformer(default_max_chars=100)
    
    def test_complex_patterns(self):
        """测试复杂模式"""
        # 测试嵌套括号（应该被当作普通字符处理）
        result = self.transformer.transform_pattern("((test))")
        self.assertEqual(result[0], 0)  # 应该被当作单个关键词
    
    def test_special_characters(self):
        """测试特殊字符"""
        special_patterns = [
            "关键词@符号",
            "测试#标签",
            "项目$成本"
        ]
        
        for pattern in special_patterns:
            with self.subTest(pattern=pattern):
                result = self.transformer.transform_pattern(pattern)
                self.assertEqual(result[0], 0)  # 应该被当作单个关键词
                self.assertEqual(result[1], pattern)
    
    def test_very_long_patterns(self):
        """测试很长的模式"""
        long_keyword = "很长的关键词" * 50  # 创建一个很长的关键词
        result = self.transformer.transform_pattern(long_keyword)
        self.assertEqual(result[0], 0)
        self.assertEqual(result[1], long_keyword)
    
    def test_whitespace_handling(self):
        """测试空白字符处理"""
        patterns_with_whitespace = [
            "  汽车  ",
            "\t新能源\t",
            "\n电池\n"
        ]
        
        for pattern in patterns_with_whitespace:
            with self.subTest(pattern=repr(pattern)):
                result = self.transformer.transform_pattern(pattern)
                self.assertEqual(result[0], 0)
                self.assertEqual(result[1], pattern.strip())


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTest(unittest.makeSuite(TestPatternTransformer))
    suite.addTest(unittest.makeSuite(TestPatternTransformerEdgeCases))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    if run_all_tests():
        print("\n✓ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败！")
        sys.exit(1) 