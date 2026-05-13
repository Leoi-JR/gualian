"""
Parquet数据管理模块
Parquet Data Manager Module

提供Parquet文件发现、加载、合并以及已处理文件追踪功能。
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd


class ParquetManager:
    """
    Parquet文件管理器

    负责Parquet文件的发现、数据加载与合并、已处理文件追踪等功能。
    """

    def __init__(self, config: Dict[str, Any], processed_files_path: str):
        """
        初始化Parquet管理器

        Args:
            config: parquet配置字典
            processed_files_path: 已处理文件列表的存储路径
        """
        self.logger = logging.getLogger(__name__)

        self.folder_path_1 = config.get('folder_path_1', '')
        self.folder_path_2 = config.get('folder_path_2', '')
        self.file_extension = config.get('file_extension', '.parquet')

        batch_processing_config = config.get('batch_processing', {})
        self.enable_full_batch = batch_processing_config.get('enable_full_batch', True)
        self.enable_random_test = batch_processing_config.get('enable_random_test', True)
        self.progress_report_interval = batch_processing_config.get('progress_report_interval', 10)
        self.enable_skip_processed = batch_processing_config.get('enable_skip_processed', True)

        error_config = batch_processing_config.get('error_handling', {})
        self.continue_on_error = error_config.get('continue_on_error', True)
        self.max_errors = error_config.get('max_errors', 50)
        self.log_errors = error_config.get('log_errors', True)

        self.merge_columns = config.get('merge_on_columns', ['record_id', 'record_name'])
        self.processed_files_path = processed_files_path
        self.processed_files_data: Dict[str, Any] = {}

    def initialize(self):
        """初始化：验证配置并加载已处理文件列表"""
        self._validate_parquet_config()
        self._load_processed_files()

    def _load_processed_files(self):
        """从文件加载已处理文件列表"""
        try:
            if os.path.exists(self.processed_files_path):
                with open(self.processed_files_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_files_data = data
            else:
                self.processed_files_data = {
                    'files': [],
                    'last_updated': ''
                }
        except Exception as e:
            self.logger.error(f"加载已处理文件列表失败: {e}")
            self.processed_files_data = {
                'files': [],
                'last_updated': ''
            }

    def _save_processed_files(self):
        """保存已处理文件列表到文件"""
        try:
            self.processed_files_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with open(self.processed_files_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"保存已处理文件列表失败: {e}")

    def get_processed_files(self) -> List[str]:
        """获取已处理文件列表"""
        return self.processed_files_data.get('files', [])

    def is_file_processed(self, file_name: str) -> bool:
        """检查文件是否已处理"""
        if not self.enable_skip_processed:
            return False

        processed_files = self.get_processed_files()
        file_basename = Path(file_name).name

        for processed_file in processed_files:
            if file_name == processed_file or file_basename == Path(processed_file).name:
                return True

        return False

    def add_processed_file(self, file_name: str):
        """添加文件到已处理列表"""
        if not self.enable_skip_processed:
            return

        try:
            if file_name not in self.processed_files_data['files']:
                self.processed_files_data['files'].append(file_name)

            self._save_processed_files()
            self.logger.info(f"已添加文件到已处理列表: {file_name}")

        except Exception as e:
            self.logger.error(f"添加已处理文件失败: {e}")

    def remove_processed_file(self, file_name: str):
        """从已处理列表中移除文件"""
        if not self.enable_skip_processed:
            return

        try:
            if file_name in self.processed_files_data['files']:
                self.processed_files_data['files'].remove(file_name)

            self._save_processed_files()
            self.logger.info(f"已从已处理列表中移除文件: {file_name}")

        except Exception as e:
            self.logger.error(f"移除已处理文件失败: {e}")

    def clear_processed_files(self):
        """清空已处理文件列表"""
        if not self.enable_skip_processed:
            return

        try:
            self.processed_files_data['files'] = []
            self._save_processed_files()
            self.logger.info("已清空已处理文件列表")

        except Exception as e:
            self.logger.error(f"清空已处理文件列表失败: {e}")

    def get_available_parquet_files(self) -> List[str]:
        """获取两个文件夹中的同名parquet文件列表"""
        if not self.folder_path_1 or not self.folder_path_2:
            return []

        try:
            folder1 = Path(self.folder_path_1)
            folder2 = Path(self.folder_path_2)

            if not folder1.exists() or not folder2.exists():
                self.logger.warning(f"Parquet文件夹不存在: {folder1} 或 {folder2}")
                return []

            glob_pattern = f'*{self.file_extension}'
            files1 = set(f.name for f in folder1.glob(glob_pattern))
            files2 = set(f.name for f in folder2.glob(glob_pattern))

            common_files = list(files1.intersection(files2))
            common_files.sort()

            self.logger.info(f"找到 {len(common_files)} 个同名parquet文件")
            return common_files

        except Exception as e:
            self.logger.error(f"获取parquet文件列表失败: {e}")
            return []

    def get_random_parquet_file(self) -> Optional[str]:
        """随机选择一个parquet文件用于测试"""
        import random
        available_files = self.get_available_parquet_files()
        if not available_files:
            return None

        import random
        selected_file = random.choice(available_files)
        self.logger.info(f"随机选择的parquet文件: {selected_file}")
        return selected_file

    def load_parquet_data_from_folders(self, file_name: str) -> pd.DataFrame:
        """从两个parquet文件夹中读取同名文件并合并"""
        if not self.folder_path_1 or not self.folder_path_2:
            raise ValueError("Parquet文件夹路径未配置")

        file_path_1 = Path(self.folder_path_1) / file_name
        file_path_2 = Path(self.folder_path_2) / file_name

        if not file_path_1.exists():
            raise FileNotFoundError(f"文件不存在: {file_path_1}")
        if not file_path_2.exists():
            raise FileNotFoundError(f"文件不存在: {file_path_2}")

        try:
            self.logger.info(f"读取parquet文件: {file_path_1}")
            df1 = pd.read_parquet(file_path_1)

            self.logger.info(f"读取parquet文件: {file_path_2}")
            df2 = pd.read_parquet(file_path_2)

            for col in self.merge_columns:
                if col not in df1.columns:
                    raise ValueError(f"合并列 '{col}' 在文件1中不存在: {file_path_1}")
                if col not in df2.columns:
                    raise ValueError(f"合并列 '{col}' 在文件2中不存在: {file_path_2}")

            self.logger.info(f"合并数据，基于列: {self.merge_columns}")
            merged_df = pd.merge(df1, df2, on=self.merge_columns, how='inner')

            self.logger.info(f"成功合并parquet数据: 文件1 {len(df1)} 行, 文件2 {len(df2)} 行, 合并后 {len(merged_df)} 行")
            return merged_df

        except Exception as e:
            self.logger.error(f"加载和合并parquet数据失败: {e}")
            raise

    def _validate_parquet_config(self):
        """验证parquet配置的有效性"""
        errors = []
        warnings = []

        if not self.folder_path_1:
            errors.append("Parquet文件夹路径1未配置")
        elif not Path(self.folder_path_1).exists():
            warnings.append(f"Parquet文件夹1不存在: {self.folder_path_1}")

        if not self.folder_path_2:
            errors.append("Parquet文件夹路径2未配置")
        elif not Path(self.folder_path_2).exists():
            warnings.append(f"Parquet文件夹2不存在: {self.folder_path_2}")

        if not self.merge_columns:
            errors.append("合并列配置为空")
        elif not isinstance(self.merge_columns, list):
            errors.append("合并列配置必须是列表格式")

        if errors:
            error_msg = "Parquet配置验证失败: " + "; ".join(errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        if warnings:
            for warning in warnings:
                self.logger.warning(f"Parquet配置警告: {warning}")

        if not errors:
            self.logger.info("Parquet配置验证通过")

    def get_processing_status(self) -> Dict[str, Any]:
        """获取文件处理状态统计"""
        try:
            available_files = self.get_available_parquet_files()
            processed_files = self.get_processed_files()

            processed_count = 0
            unprocessed_files = []

            for file_name in available_files:
                if self.is_file_processed(file_name):
                    processed_count += 1
                else:
                    unprocessed_files.append(file_name)

            status = {
                'total_available_files': len(available_files),
                'processed_files_count': processed_count,
                'unprocessed_files_count': len(unprocessed_files),
                'processed_files': processed_files,
                'unprocessed_files': unprocessed_files,
                'skip_processed_enabled': self.enable_skip_processed,
                'last_updated': self.processed_files_data.get('last_updated', ''),
                'completion_rate': f"{processed_count / len(available_files) * 100:.1f}%" if available_files else "0%"
            }

            return status

        except Exception as e:
            self.logger.error(f"获取处理状态失败: {e}")
            return {
                'error': str(e),
                'skip_processed_enabled': self.enable_skip_processed
            }

    def print_processing_status(self):
        """打印文件处理状态信息"""
        status = self.get_processing_status()

        if 'error' in status:
            self.logger.error(f"无法获取处理状态: {status['error']}")
            return

        self.logger.info("=" * 60)
        self.logger.info("文件处理状态统计")
        self.logger.info("=" * 60)
        self.logger.info(f"总可用文件数: {status['total_available_files']}")
        self.logger.info(f"已处理文件数: {status['processed_files_count']}")
        self.logger.info(f"未处理文件数: {status['unprocessed_files_count']}")
        self.logger.info(f"完成率: {status['completion_rate']}")
        self.logger.info(f"跳过已处理文件: {'启用' if status['skip_processed_enabled'] else '禁用'}")

        if status['last_updated']:
            self.logger.info(f"最后更新时间: {status['last_updated']}")

        if status['unprocessed_files']:
            self.logger.info(f"\n未处理文件列表 ({len(status['unprocessed_files'])} 个):")
            for i, file_name in enumerate(status['unprocessed_files'][:10], 1):
                self.logger.info(f"  {i}. {Path(file_name).name}")

            if len(status['unprocessed_files']) > 10:
                self.logger.info(f"  ... 还有 {len(status['unprocessed_files']) - 10} 个文件")

        self.logger.info("=" * 60)
