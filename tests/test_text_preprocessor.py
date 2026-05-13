#!/usr/bin/env python3
"""
文本预处理器单元测试
Text Preprocessor Unit Tests

测试文本预处理模块中的5个纯函数。
"""

import unittest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.text_preprocessor import (
    smart_parse_text_data,
    remove_html_tags,
    normalize_special_characters,
    normalize_whitespace,
    remove_control_characters,
)


class TestTextPreprocessor(unittest.TestCase):
    """文本预处理器测试类"""

    def test_smart_parse_text_data_list(self):
        """测试列表输入"""
        result = smart_parse_text_data(["文本1", "文本2", "文本3"])
        self.assertEqual(result, ["文本1", "文本2", "文本3"])

    def test_smart_parse_text_data_none(self):
        """测试None输入"""
        result = smart_parse_text_data(None)
        self.assertEqual(result, [])

    def test_smart_parse_text_data_empty(self):
        """测试空列表"""
        result = smart_parse_text_data([])
        self.assertEqual(result, [])

    def test_smart_parse_text_data_with_none_values(self):
        """测试包含None值的列表"""
        result = smart_parse_text_data(["文本1", None, "文本2", None])
        self.assertEqual(result, ["文本1", "文本2"])

    def test_smart_parse_text_data_numpy_array(self):
        """测试numpy数组输入"""
        try:
            import numpy as np
            arr = np.array(["文本1", "文本2"])
            result = smart_parse_text_data(arr)
            self.assertEqual(result, ["文本1", "文本2"])
        except ImportError:
            self.skipTest("numpy未安装")

    def test_smart_parse_text_data_strips_whitespace(self):
        """测试自动去除空白"""
        result = smart_parse_text_data(["  文本1  ", "", "   "])
        self.assertEqual(result, ["文本1"])

    def test_remove_html_tags_basic(self):
        """测试基本HTML标签移除"""
        result = remove_html_tags("<p>Hello</p>")
        self.assertEqual(result, "Hello")

    def test_remove_html_tags_nested(self):
        """测试嵌套HTML标签"""
        result = remove_html_tags("<div><p>嵌套<b>内容</b></p></div>")
        self.assertEqual(result, "嵌套内容")

    def test_remove_html_tags_entities(self):
        """测试HTML实体解码"""
        result = remove_html_tags("Hello&nbsp;World &amp; More")
        self.assertEqual(result, "Hello World & More")

    def test_remove_html_tags_plain_text(self):
        """测试无HTML标签的文本"""
        text = "纯文本内容"
        result = remove_html_tags(text)
        self.assertEqual(result, text)

    def test_remove_html_tags_empty(self):
        """测试空字符串"""
        result = remove_html_tags("")
        self.assertEqual(result, "")

    def test_normalize_special_characters_fullwidth_comma(self):
        """测试全角逗号转半角"""
        result = normalize_special_characters("测试，内容")
        self.assertEqual(result, "测试,内容")

    def test_normalize_special_characters_fullwidth_punctuation(self):
        """测试全角括号转半角"""
        result = normalize_special_characters("（测试内容）")
        self.assertEqual(result, "(测试内容)")

    def test_normalize_special_characters_mixed(self):
        """测试混合全半角标点"""
        result = normalize_special_characters("测试：A（公司）简介；B、C")
        self.assertEqual(result, "测试:A(公司)简介;B、C")

    def test_normalize_special_characters_no_change(self):
        """测试无需变更的文本"""
        text = "abcABC123"
        result = normalize_special_characters(text)
        self.assertEqual(result, text)

    def test_normalize_whitespace_multiple_spaces(self):
        """测试多空格合并"""
        result = normalize_whitespace("测试   内容")
        self.assertEqual(result, "测试 内容")

    def test_normalize_whitespace_tabs_and_newlines(self):
        """测试tab和换行转为空格"""
        result = normalize_whitespace("测试\t内容\n第二行")
        self.assertEqual(result, "测试 内容 第二行")

    def test_normalize_whitespace_trim(self):
        """测试首尾空格去除"""
        result = normalize_whitespace("  测试内容  ")
        self.assertEqual(result, "测试内容")

    def test_normalize_whitespace_empty(self):
        """测试空字符串"""
        result = normalize_whitespace("")
        self.assertEqual(result, "")

    def test_remove_control_characters_removes_low_chars(self):
        """测试控制字符移除"""
        result = remove_control_characters("test\x00\x01\x02content")
        self.assertEqual(result, "testcontent")

    def test_remove_control_characters_preserves_newline_tab(self):
        """测试保留换行和tab"""
        result = remove_control_characters("line1\n\tline2")
        self.assertEqual(result, "line1\n\tline2")

    def test_remove_control_characters_normal_text(self):
        """测试正常文本不变"""
        text = "Hello 世界！"
        result = remove_control_characters(text)
        self.assertEqual(result, text)

    def test_remove_control_characters_empty(self):
        """测试空字符串"""
        result = remove_control_characters("")
        self.assertEqual(result, "")


def run_all_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTextPreprocessor)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite).wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
