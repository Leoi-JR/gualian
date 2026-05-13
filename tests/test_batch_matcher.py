#!/usr/bin/env python3
"""
批量匹配器单元测试
Batch Matcher Unit Tests

测试批量匹配策略选择和执行功能。
"""

import unittest
import unittest.mock
import re
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.keyword_compiler import CompiledPattern
from core.batch_matcher import BatchMatcher


class TestBatchMatcher(unittest.TestCase):
    """BatchMatcher 测试类"""

    def setUp(self):
        """测试前准备"""
        self.match_tags = []

        def generate_tag(text, keyword, match_type):
            tag = f"{text}_{match_type}_{keyword}"
            self.match_tags.append(tag)
            return tag

        self.matcher = BatchMatcher(generate_tag)

        # 编译好的测试模式
        self.pattern_new_energy = CompiledPattern(
            pattern_type=0,
            regex_pattern=re.compile(r'新能源'),
            keywords=['新能源'],
            is_valid=True,
        )
        self.pattern_electric = CompiledPattern(
            pattern_type=1,
            regex_pattern=re.compile(r'电动'),
            keywords=['电动'],
            is_valid=True,
        )

    def tearDown(self):
        """测试后清理"""
        self.match_tags.clear()

    def test_empty_texts(self):
        """测试空文本列表"""
        result = self.matcher.batch_match_texts_optimized([], [self.pattern_new_energy], 'like', 'test')
        self.assertEqual(result, [])

    def test_empty_patterns(self):
        """测试空模式列表"""
        result = self.matcher.batch_match_texts_optimized(["新能源"], [], 'like', 'test')
        self.assertEqual(result, [])

    def test_traditional_strategy_small(self):
        """测试小数据量使用传统策略（<5000次操作）"""
        texts = ["我们是新能源汽车公司", "传统燃油车制造", "新能源电池研发"]
        patterns = [self.pattern_new_energy]
        result = self.matcher.batch_match_texts_optimized(texts, patterns, 'like', '新能源')
        self.assertEqual(len(result), 2)  # text[0]和text[2]匹配
        self.assertIn("我们是新能源汽车公司_like_新能源", result)

    def test_vectorized_strategy_medium(self):
        """测试中等数据量使用向量化策略（>=5000, <50000次操作）"""
        # 100文本 × 50模式 = 5000操作 → 向量化路径
        texts = [f"文本{i} 新能源" for i in range(100)]
        patterns = [self.pattern_new_energy] * 50

        with unittest.mock.patch.object(self.matcher, '_vectorized_batch_match',
                                         wraps=self.matcher._vectorized_batch_match) as mock_vec:
            result = self.matcher.batch_match_texts_optimized(texts, patterns, 'like', '新能源')
            mock_vec.assert_called_once()
            self.assertGreater(len(result), 0)

    def test_chunked_strategy_large(self):
        """测试大数据量使用分块策略（>=50000次操作）"""
        # 500文本 × 101模式 = 50500操作 → 分块路径
        texts = [f"文本{i} 新能源" for i in range(500)]
        patterns = [self.pattern_new_energy] * 101

        with unittest.mock.patch.object(self.matcher, '_chunked_vectorized_match',
                                         wraps=self.matcher._chunked_vectorized_match) as mock_chunk:
            result = self.matcher.batch_match_texts_optimized(
                texts, patterns, 'like', '新能源'
            )
            mock_chunk.assert_called_once()
            self.assertTrue(len(result) > 0)

    def test_match_type_like(self):
        """测试like匹配类型标记"""
        texts = ["新能源公司"]
        result = self.matcher.batch_match_texts_optimized(
            texts, [self.pattern_new_energy], 'like', '新能源'
        )
        self.assertIn("新能源公司_like_新能源", result)

    def test_match_type_must(self):
        """测试must匹配类型标记"""
        texts = ["新能源公司"]
        result = self.matcher.batch_match_texts_optimized(
            texts, [self.pattern_new_energy], 'must', '新能源'
        )
        self.assertIn("新能源公司_must_新能源", result)

    def test_match_type_unlike(self):
        """测试unlike匹配类型标记"""
        texts = ["新能源公司"]
        result = self.matcher.batch_match_texts_optimized(
            texts, [self.pattern_new_energy], 'unlike', '新能源'
        )
        self.assertIn("新能源公司_unlike_新能源", result)

    def test_early_exit(self):
        """测试early_exit功能"""
        # early_exit应尽早返回结果
        texts = ["新能源A", "无匹配", "新能源B", "无匹配", "新能源C"]
        patterns = [self.pattern_new_energy]

        result = self.matcher.batch_match_texts_optimized(
            texts, patterns, 'like', '新能源', early_exit=True
        )
        self.assertEqual(len(result), 1)  # early_exit在第一个匹配后就退出

    def test_no_match(self):
        """测试无匹配情况"""
        texts = ["传统燃油车", "机械制造"]
        result = self.matcher.batch_match_texts_optimized(
            texts, [self.pattern_new_energy], 'like', '新能源'
        )
        self.assertEqual(result, [])

    def test_multi_pattern_match(self):
        """测试多模式匹配"""
        texts = ["新能源汽车", "电动车"]
        patterns = [self.pattern_new_energy, self.pattern_electric]
        result = self.matcher.batch_match_texts_optimized(
            texts, patterns, 'like', '新能源|电动'
        )
        self.assertEqual(len(result), 2)

    def test_fallback_on_error(self):
        """测试向量化路径异常时回退到传统方法"""
        # 100文本 × 51模式 = 5100操作 → >=5000 触发向量化路径
        # 向量化抛出异常后应回退到传统路径
        texts = [f"新能源文本{i}" for i in range(100)]
        patterns = [self.pattern_new_energy] * 51

        with unittest.mock.patch.object(self.matcher, '_traditional_batch_match',
                                         wraps=self.matcher._traditional_batch_match) as mock_trad:
            with unittest.mock.patch.object(self.matcher, '_vectorized_batch_match',
                                             side_effect=Exception("模拟向量化失败")):
                result = self.matcher.batch_match_texts_optimized(texts, patterns, 'like', '新能源')
                # 向量化失败后应回退到传统方法并仍然返回结果
                mock_trad.assert_called_once()
                self.assertGreater(len(result), 0)


def run_all_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBatchMatcher)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite).wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
