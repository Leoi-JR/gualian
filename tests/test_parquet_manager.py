#!/usr/bin/env python3
"""
Parquet管理器单元测试
Parquet Manager Unit Tests

测试Parquet文件发现、数据加载、已处理文件追踪等功能。
通过mock文件操作测试逻辑层，避免依赖真实parquet文件。
"""

import unittest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.parquet_manager import ParquetManager


class TestParquetManager(unittest.TestCase):
    """ParquetManager 测试类"""

    def setUp(self):
        """测试前准备"""
        self.mock_config = {
            'folder_path_1': '/mock/path1',
            'folder_path_2': '/mock/path2',
            'file_extension': '.parquet',
            'batch_processing': {
                'enable_full_batch': True,
                'enable_random_test': True,
                'progress_report_interval': 10,
                'enable_skip_processed': True,
                'error_handling': {
                    'continue_on_error': True,
                    'max_errors': 50,
                    'log_errors': True
                }
            },
            'merge_on_columns': ['record_id', 'record_name']
        }

    def test_init_stores_config(self):
        """测试初始化正确存储配置"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        self.assertEqual(manager.folder_path_1, '/mock/path1')
        self.assertEqual(manager.folder_path_2, '/mock/path2')
        self.assertEqual(manager.file_extension, '.parquet')
        self.assertEqual(manager.merge_columns, ['record_id', 'record_name'])

    def test_init_default_merge_columns(self):
        """测试默认合并列"""
        config = {'folder_path_1': '/p1', 'folder_path_2': '/p2'}
        manager = ParquetManager(config, '/mock/processed.json')
        self.assertEqual(manager.merge_columns, ['record_id', 'record_name'])

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
        'files': ['file1.parquet', 'file2.parquet'],
        'last_updated': '2025-01-01'
    }))
    @patch('pathlib.Path.exists', return_value=True)
    def test_initialize_loads_processed_files(self, mock_path_exists, mock_file, mock_os_exists):
        """测试初始化加载已处理文件"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.initialize()
        processed = manager.get_processed_files()
        self.assertEqual(processed, ['file1.parquet', 'file2.parquet'])

    @patch('os.path.exists', return_value=False)
    def test_initialize_no_processed_file(self, mock_exists):
        """测试无已处理文件时初始化为空"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        with patch('pathlib.Path.exists', return_value=True):
            manager.initialize()
        # 不调用initialize中的_validate_parquet_config，先测试无文件的情况
        manager._load_processed_files()
        self.assertEqual(manager.get_processed_files(), [])

    def test_is_file_processed(self):
        """测试已处理文件判断"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.processed_files_data = {
            'files': ['file1.parquet', 'path/to/file2.parquet']
        }
        self.assertTrue(manager.is_file_processed('file1.parquet'))
        self.assertTrue(manager.is_file_processed('file2.parquet'))
        self.assertFalse(manager.is_file_processed('file3.parquet'))

    def test_is_file_processed_disabled(self):
        """测试禁用跳过时返回False"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.enable_skip_processed = False
        manager.processed_files_data = {'files': ['file1.parquet']}
        self.assertFalse(manager.is_file_processed('file1.parquet'))

    def test_add_processed_file(self):
        """测试添加已处理文件"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.processed_files_data = {'files': []}

        with patch.object(manager, '_save_processed_files') as mock_save:
            manager.add_processed_file('new_file.parquet')
            self.assertIn('new_file.parquet', manager.get_processed_files())
            mock_save.assert_called_once()

    def test_add_processed_file_no_duplicate(self):
        """测试重复添加不产生重复条目（文件列表长度不变）"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.processed_files_data = {'files': ['file1.parquet']}

        with patch.object(manager, '_save_processed_files') as mock_save:
            manager.add_processed_file('file1.parquet')
            # 文件已存在，列表长度不变
            self.assertEqual(len(manager.get_processed_files()), 1)
            # 注意：源码无论是否重复都会调用 _save_processed_files
            mock_save.assert_called_once()

    def test_remove_processed_file(self):
        """测试移除已处理文件"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.processed_files_data = {'files': ['file1.parquet', 'file2.parquet']}

        with patch.object(manager, '_save_processed_files') as mock_save:
            manager.remove_processed_file('file1.parquet')
            self.assertNotIn('file1.parquet', manager.get_processed_files())
            self.assertIn('file2.parquet', manager.get_processed_files())
            mock_save.assert_called_once()

    def test_clear_processed_files(self):
        """测试清空已处理文件"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.processed_files_data = {'files': ['file1.parquet', 'file2.parquet']}

        with patch.object(manager, '_save_processed_files') as mock_save:
            manager.clear_processed_files()
            self.assertEqual(manager.get_processed_files(), [])
            mock_save.assert_called_once()

    @patch('pathlib.Path.glob')
    @patch('pathlib.Path.exists', return_value=True)
    def test_get_available_parquet_files(self, mock_exists, mock_glob):
        """测试获取可用parquet文件列表"""
        mock_glob.side_effect = [
            [Path('file1.parquet'), Path('file2.parquet')],
            [Path('file1.parquet'), Path('file2.parquet')],
        ]

        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        files = manager.get_available_parquet_files()
        self.assertEqual(len(files), 2)
        self.assertIn('file1.parquet', files)
        self.assertIn('file2.parquet', files)

    @patch('pathlib.Path.exists', return_value=True)
    def test_get_available_parquet_files_only_common(self, mock_exists):
        """测试只返回两个文件夹共有的文件"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')

        with patch('pathlib.Path.glob') as mock_glob:
            mock_glob.side_effect = [
                [Path('a.parquet'), Path('b.parquet'), Path('c.parquet')],
                [Path('a.parquet'), Path('c.parquet')],
            ]
            files = manager.get_available_parquet_files()
            self.assertEqual(files, ['a.parquet', 'c.parquet'])

    def test_get_available_parquet_files_no_path(self):
        """测试路径为空时返回空列表"""
        manager = ParquetManager({'folder_path_1': '', 'folder_path_2': ''}, '/mock/processed.json')
        files = manager.get_available_parquet_files()
        self.assertEqual(files, [])

    @patch('pandas.read_parquet')
    @patch('pandas.merge')
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_parquet_data(self, mock_exists, mock_merge, mock_read_parquet):
        """测试加载并合并parquet数据"""
        import pandas as pd
        df1 = pd.DataFrame({'record_id': ['C001'], 'record_name': ['记录A'], 'col1': ['val1']})
        df2 = pd.DataFrame({'record_id': ['C001'], 'record_name': ['记录A'], 'col2': ['val2']})
        mock_read_parquet.side_effect = [df1, df2]
        mock_merge.return_value = pd.DataFrame({
            'record_id': ['C001'], 'record_name': ['记录A'], 'col1': ['val1'], 'col2': ['val2']
        })

        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        result = manager.load_parquet_data_from_folders('test.parquet')

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['record_id'], 'C001')
        self.assertEqual(mock_read_parquet.call_count, 2)
        mock_merge.assert_called_once()

    @patch('pathlib.Path.exists', return_value=True)
    def test_get_processing_status(self, mock_exists):
        """测试处理状态统计"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        manager.processed_files_data = {'files': ['file1.parquet'], 'last_updated': '2025-01-01'}

        with patch.object(manager, 'get_available_parquet_files', return_value=['file1.parquet', 'file2.parquet']):
            status = manager.get_processing_status()

        self.assertEqual(status['total_available_files'], 2)
        self.assertEqual(status['processed_files_count'], 1)
        self.assertEqual(status['unprocessed_files_count'], 1)
        self.assertEqual(status['completion_rate'], '50.0%')

    def test_get_processing_status_no_files(self):
        """测试无可用文件时状态"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        with patch.object(manager, 'get_available_parquet_files', return_value=[]):
            status = manager.get_processing_status()

        self.assertEqual(status['total_available_files'], 0)
        self.assertEqual(status['completion_rate'], '0%')

    def test_validate_config_missing_paths(self):
        """测试配置验证缺少路径"""
        manager = ParquetManager({'folder_path_1': '', 'folder_path_2': ''}, '/mock/processed.json')
        with self.assertRaises(ValueError):
            manager._validate_parquet_config()

    def test_validate_config_missing_merge_columns(self):
        """测试配置验证缺少合并列"""
        config = {'folder_path_1': '/p1', 'folder_path_2': '/p2', 'merge_on_columns': []}
        manager = ParquetManager(config, '/mock/processed.json')
        with patch('pathlib.Path.exists', return_value=True):
            with self.assertRaises(ValueError):
                manager._validate_parquet_config()

    @patch('pathlib.Path.exists', return_value=True)
    def test_validate_config_valid(self, mock_exists):
        """测试有效配置验证通过"""
        manager = ParquetManager(self.mock_config, '/mock/processed.json')
        try:
            manager._validate_parquet_config()
        except ValueError:
            self.fail("_validate_parquet_config() 不应该对有效配置抛出异常")


def run_all_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParquetManager)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite).wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
