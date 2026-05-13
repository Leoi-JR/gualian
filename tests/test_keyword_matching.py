#!/usr/bin/env python3
"""
关键词匹配功能单元测试
Keyword Matching Unit Tests

该模块包含智能关键词匹配功能的完整单元测试，
覆盖所有核心模块和功能组件。

测试覆盖：
1. 关键词编译器测试
2. 筛选逻辑测试
3. 匹配引擎测试
4. 结果处理器测试
5. 主控制器测试

作者：系统开发
日期：2024年
"""

import unittest
import pandas as pd
import tempfile
import json
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.keyword_compiler import KeywordCompiler, CompiledPattern
from core.filter_logic import FilterLogic, FilterResult
from core.matching_engine import MatchingEngine, MatchResult
from core.result_processor import ResultProcessor
from core.keyword_matcher import KeywordMatcher


class TestKeywordCompiler(unittest.TestCase):
    """关键词编译器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.compiler = KeywordCompiler()
    
    def test_compile_direct_match(self):
        """测试直接匹配模式编译"""
        pattern_data = [0, "新能源汽车"]
        result = self.compiler.compile_keyword_pattern(pattern_data)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.pattern_type, 0)
        self.assertIsNotNone(result.regex_pattern)
        self.assertEqual(result.keywords, ["新能源汽车"])
    
    def test_compile_ordered_match(self):
        """测试有序匹配模式编译"""
        pattern_data = [1, ["新能源"], ["汽车"], 0, 10]
        result = self.compiler.compile_keyword_pattern(pattern_data)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.pattern_type, 1)
        self.assertIsNotNone(result.regex_pattern)
        self.assertEqual(result.keywords, ["新能源", "汽车"])
    
    def test_compile_unordered_match(self):
        """测试无序匹配模式编译"""
        pattern_data = [2, ["电动", "混动"], ["汽车", "车辆"], 0, 20]
        result = self.compiler.compile_keyword_pattern(pattern_data)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.pattern_type, 2)
        self.assertIsNotNone(result.regex_pattern)
        self.assertEqual(result.keywords, ["电动", "混动", "汽车", "车辆"])
    
    def test_compile_invalid_pattern(self):
        """测试无效模式编译"""
        pattern_data = [99, "invalid"]
        result = self.compiler.compile_keyword_pattern(pattern_data)
        
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.error_message)
    
    def test_compile_string_pattern(self):
        """测试字符串格式模式编译"""
        pattern_data = "[0, '测试关键词']"
        result = self.compiler.compile_keyword_pattern(pattern_data)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.pattern_type, 0)
    
    def test_compile_zero_pattern(self):
        """测试零值模式"""
        pattern_data = "0"
        result = self.compiler.compile_keyword_pattern(pattern_data)
        
        self.assertFalse(result.is_valid)
    
    def test_batch_compile(self):
        """测试批量编译"""
        patterns = [
            [0, "关键词1"],
            [0, "关键词2"],
            "0"
        ]
        results = self.compiler.batch_compile(patterns)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].is_valid)
        self.assertTrue(results[1].is_valid)
        self.assertFalse(results[2].is_valid)


class TestFilterLogic(unittest.TestCase):
    """筛选逻辑测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.filter_logic = FilterLogic()
    
    def test_industry_filter_default(self):
        """测试行业筛选默认值"""
        result = self.filter_logic.apply_industry_filter("default", "123")
        self.assertTrue(result.passed)
        self.assertIn("默认", result.reason)
    
    def test_industry_filter_match(self):
        """测试行业筛选匹配"""
        result = self.filter_logic.apply_industry_filter("123、456、789", "456")
        self.assertTrue(result.passed)
        self.assertIn("匹配", result.reason)
    
    def test_industry_filter_no_match(self):
        """测试行业筛选不匹配"""
        result = self.filter_logic.apply_industry_filter("123、456", "999")
        self.assertFalse(result.passed)
        self.assertIn("不匹配", result.reason)
    
    def test_source_scope_filter_default(self):
        """测试字段范围筛选默认值"""
        result = self.filter_logic.apply_source_scope_filter("default")
        self.assertTrue(result.passed)
        self.assertIsNotNone(result.filtered_columns)

    def test_source_scope_filter_scope_a(self):
        """测试字段范围筛选排除范围A"""
        result = self.filter_logic.apply_source_scope_filter("scope_a")
        self.assertTrue(result.passed)
        self.assertNotIn("software_full_name", result.filtered_columns)

    def test_source_scope_filter_scope_b(self):
        """测试字段范围筛选排除范围B"""
        result = self.filter_logic.apply_source_scope_filter("scope_b")
        self.assertTrue(result.passed)
        self.assertNotIn("patent_title", result.filtered_columns)
        self.assertNotIn("patent_abs", result.filtered_columns)
        self.assertIn("company_profile", result.filtered_columns)

    def test_combined_filter(self):
        """测试组合筛选"""
        keyword_row = {
            'type_filter': '123、456',
            'field_scope': 'scope_a'
        }
        input_row = {
            'category_code': '456'
        }
        
        result = self.filter_logic.apply_combined_filter(keyword_row, input_row)
        self.assertTrue(result.passed)
        self.assertIsNotNone(result.filtered_columns)


class TestMatchingEngine(unittest.TestCase):
    """匹配引擎测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = MatchingEngine()
    
    def test_match_like_keywords_default(self):
        """测试Like关键词默认值匹配"""
        keyword_row = {
            'converted_like_keyword': '0',
            'like_keyword': ''
        }
        input_row = {'company_profile': ['测试文本']}
        text_columns = ['company_profile']
        
        result = self.engine._match_like_keywords(keyword_row, input_row, text_columns)
        self.assertTrue(result.success)
    
    def test_match_like_keywords_success(self):
        """测试Like关键词成功匹配"""
        keyword_row = {
            'converted_like_keyword': '[0, "新能源"]',
            'like_keyword': '新能源'
        }
        input_row = {'company_profile': ['我们是新能源汽车公司']}
        text_columns = ['company_profile']
        
        result = self.engine._match_like_keywords(keyword_row, input_row, text_columns)
        self.assertTrue(result.success)
        self.assertTrue(any(result.matched_texts.values()))
    
    def test_match_unlike_keywords_fail(self):
        """测试Unlike关键词匹配失败"""
        keyword_row = {
            'converted_unlike_keyword': '[0, "传统"]',
            'unlike_keyword': '传统'
        }
        input_row = {'company_profile': ['传统燃油车制造']}
        text_columns = ['company_profile']
        
        result = self.engine._match_unlike_keywords(keyword_row, input_row, text_columns)
        self.assertFalse(result.success)
        self.assertIn("Unlike", result.failure_reason)
    
    def test_full_keyword_matching(self):
        """测试完整关键词匹配流程"""
        keyword_row = {
            'converted_like_keyword': '[0, "新能源"]',
            'like_keyword': '新能源',
            'converted_must_keyword': '[0, "汽车"]',
            'must_keyword': '汽车',
            'converted_unlike_keyword': '0',
            'unlike_keyword': ''
        }
        input_row = {
            'company_profile': ['新能源汽车制造企业'],
            'main_product': ['电动汽车']
        }
        text_columns = ['company_profile', 'main_product']
        
        result = self.engine.match_keywords(keyword_row, input_row, text_columns)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.matched_texts)


class TestResultProcessor(unittest.TestCase):
    """结果处理器测试类"""

    def setUp(self):
        """测试前准备"""
        patcher = patch('core.result_processor.config_manager')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

        # 配置 mock 返回值，解耦真实 config
        self.mock_config.get_list.side_effect = lambda key, default=None: {
            'keyword_matching.input_table_columns.identifier_columns': ['record_id', 'record_name'],
            'keyword_matching.input_table_columns.text_content_columns': ['company_profile', 'main_product'],
        }.get(key, default or [])
        self.mock_config.get_str.return_value = 'matching_results.csv'

        self.processor = ResultProcessor()
    
    def test_format_matched_texts_list(self):
        """测试匹配文本列表格式化"""
        matched_texts = ["文本1_like_关键词", "文本2_must_关键词"]
        result = self.processor._format_matched_texts_list(matched_texts)
        
        self.assertIsInstance(result, str)
        self.assertIn("文本1", result)
        self.assertIn("文本2", result)
    
    def test_format_single_result_success(self):
        """测试单个成功结果格式化"""
        result_data = {
            'keyword_index': 0,
            'record_id': 'C001',
            'record_name': '测试记录',
            'match_success': True,
            'matched_texts': {
                'company_profile': ['匹配文本1'],
                'main_product': ['匹配文本2']
            }
        }

        formatted = self.processor._format_single_result(result_data)
        self.assertIsNotNone(formatted)
        self.assertEqual(formatted['keyword_index'], 0)
        self.assertEqual(formatted['record_id'], 'C001')
    
    def test_format_single_result_failure(self):
        """测试单个失败结果格式化"""
        result_data = {
            'keyword_index': 0,
            'record_id': 'C001',
            'match_success': False
        }
        formatted = self.processor._format_single_result(result_data)
        self.assertIsNone(formatted)
    
    def test_generate_summary_report(self):
        """测试摘要报告生成"""
        matching_results = [
            {'match_success': True, 'matched_texts': {'company_profile': ['文本1']}},
            {'match_success': False, 'failure_reason': '测试失败'},
            {'match_success': True, 'matched_texts': {'main_product': ['文本2']}}
        ]
        
        report = self.processor.generate_summary_report(matching_results)
        
        self.assertEqual(report['total_processed'], 3)
        self.assertEqual(report['successful_matches'], 2)
        self.assertEqual(report['failed_matches'], 1)
        self.assertAlmostEqual(report['match_rate'], 2/3, places=2)


class TestKeywordMatcher(unittest.TestCase):
    """关键词匹配器测试类"""

    def setUp(self):
        """测试前准备：mock parquet 配置避免 ValueError"""
        # KeywordMatcher.__init__ 调用 _validate_parquet_config()，
        # 若 folder_path_1/2 为空会抛 ValueError，必须 mock 掉
        parquet_config = {
            'folder_path_1': '/mock/path1',
            'folder_path_2': '/mock/path2',
            'file_extension': '.parquet',
            'merge_on_columns': ['record_id', 'record_name'],
            'batch_processing': {
                'enable_full_batch': True,
                'enable_random_test': False,
                'progress_report_interval': 10,
                'enable_skip_processed': False,
                'error_handling': {'continue_on_error': True, 'max_errors': 50, 'log_errors': True}
            }
        }
        with patch('pathlib.Path.exists', return_value=True):
            with patch('core.keyword_matcher.config_manager') as mock_cfg:
                mock_cfg.get_str.side_effect = lambda key, default='': {
                    'keyword_matching.keyword_file_path': 'auto_detect',
                    'keyword_matching.keyword_sheet_name': '转换后规则',
                    'keyword_matching.input_file_path': '',
                    'keyword_matching.input_sheet_name': 'Sheet1',
                    'keyword_matching.output_file_path': 'matching_results.csv',
                    'keyword_matching.result_fields.keyword_identifier.field_name': 'keyword_index',
                    'keyword_matching.result_fields.company_identifier.field_name': 'record_id',
                }.get(key, default)
                mock_cfg.get_dict.side_effect = lambda key, default=None: {
                    'keyword_matching.parquet_data_source': parquet_config,
                }.get(key, default or {})
                mock_cfg.get_bool.return_value = False
                mock_cfg.get_int.return_value = 4
                self.matcher = KeywordMatcher()

    @patch('pandas.read_excel')
    def test_load_keyword_data(self, mock_read_excel):
        """测试关键词数据加载"""
        mock_df = pd.DataFrame({
            'label_name': ['分类1'],
            'converted_like_keyword': ['[0, "关键词"]']
        })
        mock_read_excel.return_value = mock_df

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = self.matcher.load_keyword_data(tmp_path)
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch('pandas.read_excel')
    def test_load_input_data_excel(self, mock_read_excel):
        """测试输入数据加载（Excel）"""
        mock_df = pd.DataFrame({
            'record_id': ['C001'],
            'record_name': ['测试记录'],
            'company_profile': [['公司简介']]
        })
        mock_read_excel.return_value = mock_df

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = self.matcher.load_input_data(tmp_path)
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch('pandas.read_csv')
    def test_load_input_data_csv(self, mock_read_csv):
        """测试输入数据加载（CSV）"""
        mock_df = pd.DataFrame({
            'record_id': ['C001'],
            'record_name': ['测试记录']
        })
        mock_read_csv.return_value = mock_df

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = self.matcher.load_input_data(tmp_path)
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_auto_detect_keyword_file(self):
        """测试自动检测关键词文件"""
        test_file = Path('converted_keyword_rules_test.xlsx')
        test_file.touch()

        try:
            result = self.matcher._auto_detect_keyword_file()
            self.assertIsNotNone(result)
            self.assertIn('converted_keyword_rules', result)
        finally:
            test_file.unlink(missing_ok=True)


class TestCoreMatchingPipeline(unittest.TestCase):
    """
    核心执行链路集成测试：FilterLogic + MatchingEngine 端到端
    覆盖字段名重命名后的真实运行时行为
    """

    def setUp(self):
        """准备测试用的关键词规则和输入数据"""
        self.filter_logic = FilterLogic()
        self.matching_engine = MatchingEngine()

        # 模拟关键词规则行（使用新字段名）
        self.kw_match = {
            'converted_like_keyword': '[0, "新能源"]',
            'like_keyword': '新能源',
            'converted_must_keyword': '[0, "汽车"]',
            'must_keyword': '汽车',
            'converted_unlike_keyword': '0',
            'unlike_keyword': '',
            'type_filter': 'default',
            'field_scope': 'default',
        }
        self.kw_no_match = {
            'converted_like_keyword': '[0, "量子计算"]',
            'like_keyword': '量子计算',
            'converted_must_keyword': '0',
            'must_keyword': '',
            'converted_unlike_keyword': '0',
            'unlike_keyword': '',
            'type_filter': 'default',
            'field_scope': 'default',
        }
        self.kw_unlike_block = {
            'converted_like_keyword': '[0, "新能源"]',
            'like_keyword': '新能源',
            'converted_must_keyword': '0',
            'must_keyword': '',
            'converted_unlike_keyword': '[0, "传统燃油"]',
            'unlike_keyword': '传统燃油',
            'type_filter': 'default',
            'field_scope': 'default',
        }

        # 模拟输入数据行（使用新字段名）
        self.input_match = {
            'record_id': 'R001',
            'record_name': '示例新能源公司',
            'category_code': 'M',
            'company_profile': ['专注于新能源汽车研发制造'],
            'text_field_1': ['电动汽车整车'],
        }
        self.input_no_match = {
            'record_id': 'R002',
            'record_name': '示例传统企业',
            'category_code': 'M',
            'company_profile': ['传统机械制造企业'],
            'text_field_1': ['工程机械'],
        }
        self.input_unlike_hit = {
            'record_id': 'R003',
            'record_name': '示例传统燃油公司',
            'category_code': 'M',
            'company_profile': ['新能源与传统燃油混动技术'],
            'text_field_1': ['混合动力'],
        }

        self.text_columns = ['company_profile', 'text_field_1']

    def test_pipeline_like_and_must_both_match(self):
        """Like + Must 均命中 → 匹配成功，record_id 等新字段正确传递"""
        filter_result = self.filter_logic.apply_combined_filter(self.kw_match, self.input_match)
        self.assertTrue(filter_result.passed)

        match_result = self.matching_engine.match_keywords(
            self.kw_match, self.input_match, self.text_columns
        )
        self.assertTrue(match_result.success)
        # 验证命中的文本列确实存在
        matched_cols = [c for c, texts in match_result.matched_texts.items() if texts]
        self.assertGreater(len(matched_cols), 0)

    def test_pipeline_like_no_match(self):
        """Like 未命中 → 短路，匹配失败"""
        filter_result = self.filter_logic.apply_combined_filter(self.kw_no_match, self.input_no_match)
        self.assertTrue(filter_result.passed)

        match_result = self.matching_engine.match_keywords(
            self.kw_no_match, self.input_no_match, self.text_columns
        )
        self.assertFalse(match_result.success)

    def test_pipeline_unlike_blocks_single_text(self):
        """
        unlike 是文本粒度排除：同时含 like 词和 unlike 词的单条文本被拦截，
        但整行其他文本若通过则整行仍可成功。
        验证：文本列只有一条且该文本含 unlike 词时，整行匹配失败。
        """
        input_only_unlike = {
            'record_id': 'R003',
            'record_name': '示例传统燃油公司',
            'category_code': 'M',
            # 只有一条文本，且同时含 like 词（新能源）和 unlike 词（传统燃油）
            'company_profile': ['传统燃油动力系统，无新能源成分'],
            # text_field_1 无内容
            'text_field_1': [],
        }
        # like 词换一个不出现在 unlike 文本里的，确保 unlike 命中是唯一问题
        kw_strict = {
            'converted_like_keyword': '[0, "燃油"]',
            'like_keyword': '燃油',
            'converted_must_keyword': '0',
            'must_keyword': '',
            'converted_unlike_keyword': '[0, "传统燃油"]',
            'unlike_keyword': '传统燃油',
            'type_filter': 'default',
            'field_scope': 'default',
        }
        filter_result = self.filter_logic.apply_combined_filter(kw_strict, input_only_unlike)
        self.assertTrue(filter_result.passed)

        match_result = self.matching_engine.match_keywords(
            kw_strict, input_only_unlike, self.text_columns
        )
        # 唯一文本被 unlike 拦截，整行失败
        self.assertFalse(match_result.success)

    def test_pipeline_type_filter_blocks(self):
        """type_filter 与 category_code 不匹配 → filter 不通过，不进入匹配"""
        kw_with_filter = {**self.kw_match, 'type_filter': 'A、B'}
        input_wrong_type = {**self.input_match, 'category_code': 'Z'}

        filter_result = self.filter_logic.apply_combined_filter(kw_with_filter, input_wrong_type)
        self.assertFalse(filter_result.passed)

    def test_pipeline_type_filter_passes(self):
        """type_filter 与 category_code 匹配 → filter 通过"""
        kw_with_filter = {**self.kw_match, 'type_filter': 'A、M、Z'}
        input_right_type = {**self.input_match, 'category_code': 'M'}

        filter_result = self.filter_logic.apply_combined_filter(kw_with_filter, input_right_type)
        self.assertTrue(filter_result.passed)

    def test_pipeline_field_scope_excludes_columns(self):
        """field_scope=scope_b → patent_title/patent_abs 被排除出匹配列"""
        kw_scope = {**self.kw_match, 'field_scope': 'scope_b'}
        filter_result = self.filter_logic.apply_combined_filter(kw_scope, self.input_match)

        self.assertTrue(filter_result.passed)
        self.assertNotIn('patent_title', filter_result.filtered_columns)
        self.assertNotIn('patent_abs', filter_result.filtered_columns)

    def test_record_id_field_name_in_result(self):
        """验证匹配结果字典中使用新字段名 record_id"""
        filter_result = self.filter_logic.apply_combined_filter(self.kw_match, self.input_match)
        match_result = self.matching_engine.match_keywords(
            self.kw_match, self.input_match, self.text_columns
        )
        self.assertTrue(match_result.success)
        # matched_texts 应以列名为 key，与 text_columns 对应
        for col in match_result.matched_texts:
            self.assertIn(col, self.text_columns)

    def test_multi_rule_like_keyword(self):
        """多规则 | 拼接的 converted_like_keyword 能正确匹配"""
        kw_multi = {
            'converted_like_keyword': '[0, "光伏"]|[0, "太阳能"]',
            'like_keyword': '光伏|太阳能',
            'converted_must_keyword': '0',
            'must_keyword': '',
            'converted_unlike_keyword': '0',
            'unlike_keyword': '',
            'type_filter': 'default',
            'field_scope': 'default',
        }
        input_solar = {
            'record_id': 'R004',
            'record_name': '示例太阳能公司',
            'category_code': 'M',
            'company_profile': ['专注于太阳能光伏板生产'],
            'text_field_1': [],
        }
        filter_result = self.filter_logic.apply_combined_filter(kw_multi, input_solar)
        match_result = self.matching_engine.match_keywords(
            kw_multi, input_solar, self.text_columns
        )
        self.assertTrue(match_result.success)


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("关键词匹配功能单元测试")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestKeywordCompiler,
        TestFilterLogic,
        TestMatchingEngine,
        TestResultProcessor,
        TestKeywordMatcher,
        TestCoreMatchingPipeline,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    print(f"运行测试数: {result.testsRun}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    print(f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
