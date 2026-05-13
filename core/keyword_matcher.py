#!/usr/bin/env python3
"""
关键词匹配器主控制模块
Keyword Matcher Main Controller Module

该模块是智能关键词匹配功能的主控制器，协调各个子模块完成整体匹配流程。
实现choice=4的核心功能，提供完整的关键词匹配和标记服务。

主要功能：
1. 读取关键词表格和输入数据表格
2. 协调筛选逻辑、匹配引擎和结果处理
3. 提供批量处理和性能优化
4. 生成详细的匹配报告

作者：系统开发
日期：2024年
"""

import pandas as pd
import logging
import psutil
import time
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import sys
import os
import random
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config_manager


def process_single_file_worker_static(file_name: str,
                                    keyword_file_path: Optional[str],
                                    output_file: str) -> Tuple[str, str]:
    """
    静态工作函数 - 用于多进程环境，避免序列化锁对象

    这个函数是模块级函数，不依赖任何实例状态，可以安全地在多进程中使用

    Args:
        file_name: 要处理的parquet文件名
        keyword_file_path: 关键词文件路径
        output_file: 输出文件路径

    Returns:
        Tuple[str, str]: (结果文件路径, 报告文件路径)
    """
    try:
        # 在工作进程中记录开始信息
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[工作进程] 开始处理文件: {file_name}")

        # 在工作进程中重新创建KeywordMatcher实例
        # 避免传递包含线程锁的对象
        worker_matcher = KeywordMatcher()

        # 执行单个文件的匹配
        result_file, report_file = worker_matcher.run_complete_matching(
            input_file_path=file_name,
            keyword_file_path=keyword_file_path,
            output_file_path=output_file
        )

        logger.info(f"[工作进程] 完成处理文件: {file_name}")
        return result_file, report_file

    except Exception as e:
        # 在工作进程中记录错误
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[工作进程] 处理文件 {file_name} 失败: {e}")
        raise


class PerformanceProfiler:
    """性能分析器 - 用于深入分析execute_matching方法的性能瓶颈"""

    def __init__(self):
        self.start_time = None
        self.step_times = {}
        self.memory_usage = {}
        self.counters = {}
        self.process = psutil.Process()

        # 性能统计
        self.regex_compile_count = 0
        self.regex_match_count = 0
        self.dataframe_to_dict_count = 0
        self.filter_apply_count = 0
        self.text_processing_count = 0

    def start_timing(self, step_name: str):
        """开始计时"""
        current_time = time.time()
        if self.start_time is None:
            self.start_time = current_time

        self.step_times[step_name] = {'start': current_time}

        # 记录内存使用
        memory_info = self.process.memory_info()
        self.memory_usage[step_name] = {
            'start_rss': memory_info.rss / 1024 / 1024,  # MB
            'start_vms': memory_info.vms / 1024 / 1024   # MB
        }

    def end_timing(self, step_name: str):
        """结束计时"""
        current_time = time.time()
        if step_name in self.step_times:
            self.step_times[step_name]['end'] = current_time
            self.step_times[step_name]['duration'] = current_time - self.step_times[step_name]['start']

            # 记录结束时的内存使用
            memory_info = self.process.memory_info()
            self.memory_usage[step_name].update({
                'end_rss': memory_info.rss / 1024 / 1024,
                'end_vms': memory_info.vms / 1024 / 1024
            })

            # 计算内存增长
            self.memory_usage[step_name]['rss_growth'] = (
                self.memory_usage[step_name]['end_rss'] -
                self.memory_usage[step_name]['start_rss']
            )

    def increment_counter(self, counter_name: str, count: int = 1):
        """增加计数器"""
        self.counters[counter_name] = self.counters.get(counter_name, 0) + count

    def get_total_time(self) -> float:
        """获取总耗时"""
        if self.start_time is None:
            return 0
        return time.time() - self.start_time

    def get_step_duration(self, step_name: str) -> float:
        """获取步骤耗时"""
        return self.step_times.get(step_name, {}).get('duration', 0)

    def get_memory_growth(self, step_name: str) -> float:
        """获取内存增长"""
        return self.memory_usage.get(step_name, {}).get('rss_growth', 0)

    def log_performance_summary(self, logger):
        """记录性能摘要"""
        total_time = self.get_total_time()
        logger.info("🚀 性能监控摘要:")
        logger.info(f"  总耗时: {total_time:.2f}秒")

        for step_name, timing in self.step_times.items():
            duration = timing.get('duration', 0)
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            memory_growth = self.get_memory_growth(step_name)
            logger.info(f"  {step_name}: {duration:.2f}秒 ({percentage:.1f}%), 内存增长: {memory_growth:.1f}MB")

    def get_cache_performance(self) -> Dict[str, Any]:
        """获取缓存性能统计"""
        return {
            'step_count': len(self.step_times),
            'total_time': self.get_total_time(),
            'memory_peak': max([mem.get('rss_mb', 0) for mem in self.memory_usage.values()], default=0)
        }


def process_enterprise_batch_worker(enterprise_batch: List[Dict], keyword_dicts: List[Dict]) -> List[Dict[str, Any]]:
    """
    🚀 数据分片优化：按数据记录分片的工作函数

    每个进程处理完整的数据记录子集，避免重复数据传输和序列化开销

    Args:
        enterprise_batch: 数据记录批次列表
        keyword_dicts: 关键词字典列表（所有进程共享）

    Returns:
        List[Dict[str, Any]]: 匹配结果列表
    """
    batch_results = []

    # 🚀 优化：在工作进程中初始化组件，使用本地缓存避免进程间通信开销
    from core.filter_logic import FilterLogic
    from core.matching_engine import MatchingEngine

    filter_logic = FilterLogic()
    # 🚀 实际情况：多进程环境中共享缓存有技术限制，使用本地缓存但优化编译策略
    matching_engine = MatchingEngine(use_shared_cache=False)

    # 🚀 数据分片优化：每条记录与所有关键词进行匹配
    for input_dict in enterprise_batch:
        if not input_dict:
            continue

        # 🚀 优化：对当前记录与所有关键词进行匹配
        for keyword_dict in keyword_dicts:
            if not keyword_dict:
                continue

            try:
                # 🚀 快速预筛选：避免不必要的深度处理
                if not input_dict.get('record_name') or not keyword_dict.get('like_keyword'):
                    continue

                # 应用筛选逻辑
                filter_result = filter_logic.apply_combined_filter(keyword_dict, input_dict)
                if not filter_result.passed:
                    continue

                # 执行关键词匹配
                match_result = matching_engine.match_keywords(
                    keyword_dict, input_dict, filter_result.filtered_columns
                )

                # 🚀 优化：构建精简的结果记录，减少内存占用
                match_details = match_result.match_details or {}
                stage_stats = match_details.get('stage_stats', {})

                result = {
                    # 标识信息
                    'keyword_index': keyword_dict.get('id', ''),
                    'record_id': input_dict.get('record_id', ''),
                    'record_name': input_dict.get('record_name', ''),

                    # 关键词信息
                    'keyword_id': keyword_dict.get('id', ''),
                    'like_keyword': keyword_dict.get('like_keyword', ''),
                    'must_keyword': keyword_dict.get('must_keyword', ''),
                    'unlike_keyword': keyword_dict.get('unlike_keyword', ''),

                    # 匹配结果信息
                    'match_success': match_result.success,
                    'matched_texts': match_result.matched_texts,
                    'match_details': match_details,
                    'failure_reason': match_result.failure_reason if not match_result.success else None,

                    # 展开的统计信息字段
                    'total_texts_processed': match_details.get('total_texts_processed', 0),
                    'texts_passed_all_stages': match_details.get('texts_passed_all_stages', 0),
                    'like_passed_count': stage_stats.get('like_passed', 0),
                    'must_passed_count': stage_stats.get('must_passed', 0),
                    'unlike_passed_count': stage_stats.get('unlike_passed', 0),
                    'like_failed_count': stage_stats.get('like_failed', 0),
                    'must_failed_count': stage_stats.get('must_failed', 0),
                    'unlike_failed_count': stage_stats.get('unlike_failed', 0)
                }
                batch_results.append(result)

            except Exception as e:
                # 🚀 优化：减少日志开销，只在调试模式下记录详细错误
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"处理记录数据失败 (record_id={input_dict.get('record_id', 'unknown')}): {e}")
                continue

    return batch_results


# 🚀 向后兼容：保持原函数名的别名，适配参数
def process_optimized_batch_worker(index_batch: List[Tuple], keyword_dicts: List[Dict], input_dicts: List[Dict]) -> List[Dict[str, Any]]:
    """
    向后兼容的批处理工作函数 - 适配原有的参数格式
    """
    # 将索引批次转换为企业批次格式
    enterprise_batch = []
    for keyword_idx, input_idx in index_batch:
        if input_idx < len(input_dicts):
            enterprise_batch.append(input_dicts[input_idx])

    # 调用新的企业分片函数
    return process_enterprise_batch_worker(enterprise_batch, keyword_dicts)


def process_combination_batch_worker(combination_batch: List[Tuple]) -> List[Dict[str, Any]]:
    """
    传统的批处理工作函数 - 用于进程池处理（保持向后兼容）

    Args:
        combination_batch: 包含(keyword_idx, keyword_row_dict, input_row_dict)元组的列表

    Returns:
        List[Dict[str, Any]]: 匹配结果列表
    """
    batch_results = []

    # 在工作进程中重新初始化组件
    from core.filter_logic import FilterLogic
    from core.matching_engine import MatchingEngine
    from config import config_manager

    filter_logic = FilterLogic()
    matching_engine = MatchingEngine()

    # 获取标识列配置
    identifier_columns = config_manager.get_list('keyword_matching.input_table_columns.identifier_columns')

    for keyword_idx, keyword_row_dict, input_row_dict in combination_batch:
        try:
            # 应用筛选逻辑
            filter_result = filter_logic.apply_combined_filter(keyword_row_dict, input_row_dict)
            if not filter_result.passed:
                continue

            # 执行关键词匹配
            match_result = matching_engine.match_keywords(
                keyword_row_dict, input_row_dict, filter_result.filtered_columns
            )

            # 构建结果字典 - 包括成功和失败的匹配
            result = {
                'keyword_index': keyword_idx,
                'keyword_rule_id': keyword_row_dict.get('id', keyword_idx),
                'keyword_rule_name': keyword_row_dict.get('name', f'规则{keyword_idx}'),
                'match_success': match_result.success,
                'matched_texts': match_result.matched_texts,
                'match_details': match_result.match_details,  # 添加完整的match_details
                'failure_reason': match_result.failure_reason if not match_result.success else None,
                'total_texts_processed': match_result.match_details.get('total_texts_processed', 0),
                'texts_passed_all_stages': match_result.match_details.get('texts_passed_all_stages', 0),
                'like_passed_count': match_result.match_details.get('stage_stats', {}).get('like_passed', 0),
                'must_passed_count': match_result.match_details.get('stage_stats', {}).get('must_passed', 0),
                'unlike_passed_count': match_result.match_details.get('stage_stats', {}).get('unlike_passed', 0),
                'like_failed_count': match_result.match_details.get('stage_stats', {}).get('like_failed', 0),
                'must_failed_count': match_result.match_details.get('stage_stats', {}).get('must_failed', 0),
                'unlike_failed_count': match_result.match_details.get('stage_stats', {}).get('unlike_failed', 0)
            }

            # 添加输入数据的标识列
            for col in identifier_columns:
                if col in input_row_dict:
                    result[col] = input_row_dict[col]

            # 添加配置化的标识字段（用于过滤验证）
            # 从配置获取字段名称
            keyword_identifier_field = config_manager.get_str('keyword_matching.result_fields.keyword_identifier.field_name', 'keyword_index')
            company_identifier_field = config_manager.get_str('keyword_matching.result_fields.company_identifier.field_name', 'company_id')

            # 设置配置化字段
            result[keyword_identifier_field] = keyword_idx
            result[company_identifier_field] = input_row_dict.get('record_id', '')

            batch_results.append(result)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"处理组合失败 (keyword_idx={keyword_idx}): {e}")

    return batch_results
from core.filter_logic import FilterLogic
from core.matching_engine import MatchingEngine
from core.result_processor import ResultProcessor
from utils.progress_bar import (
    create_progress_bar,
    create_process_safe_progress_bar,
    multiprocess_progress_manager,
    ProgressBar,
    ProcessSafeProgressBar,
    is_multiprocess_worker
)


class MatchingProgress:
    """匹配进度数据类 - 线程安全版本"""

    def __init__(self):
        import threading
        self._lock = threading.Lock()
        self.total_combinations: int = 0
        self.processed_combinations: int = 0
        self.successful_matches: int = 0
        self.failed_matches: int = 0
        self.current_input_row: int = 0
        self.total_input_rows: int = 0

    def increment_success(self):
        """线程安全地增加成功计数"""
        with self._lock:
            self.successful_matches += 1

    def increment_failure(self):
        """线程安全地增加失败计数"""
        with self._lock:
            self.failed_matches += 1

    def increment_processed(self):
        """线程安全地增加处理计数"""
        with self._lock:
            self.processed_combinations += 1


class KeywordMatcher:
    """
    关键词匹配器主控制类
    
    协调各个子模块完成智能关键词匹配的完整流程，
    提供高效的批量处理和详细的进度跟踪。
    """
    
    def __init__(self):
        """初始化关键词匹配器"""
        self.logger = logging.getLogger(__name__)

        # 🚀 优化：初始化子模块，使用本地缓存避免多进程冲突
        self.filter_logic = FilterLogic()
        self.matching_engine = MatchingEngine(use_shared_cache=False)
        self.result_processor = ResultProcessor()

        # 从配置获取设置
        self.max_workers = config_manager.get_int('keyword_matching.max_workers', 4)
        self.enable_optimization = config_manager.get_bool('keyword_matching.enable_performance_optimization', True)   

        # 🚀 内存换效率优化：预计算数据缓存
        self._precomputed_keyword_dicts = None
        self._precomputed_input_dicts = None
        self._data_fingerprint = None  # 用于检测数据变化

        # 获取文件路径配置
        self.keyword_file_path = config_manager.get_str('keyword_matching.keyword_file_path')
        self.keyword_sheet_name = config_manager.get_str('keyword_matching.keyword_sheet_name')
        self.input_file_path = config_manager.get_str('keyword_matching.input_file_path')
        self.input_sheet_name = config_manager.get_str('keyword_matching.input_sheet_name')

        # 从配置获取结果字段名称
        self.keyword_identifier_field = config_manager.get_str('keyword_matching.result_fields.keyword_identifier.field_name', 'keyword_index')
        self.company_identifier_field = config_manager.get_str('keyword_matching.result_fields.company_identifier.field_name', 'company_id')

        # 获取parquet数据源配置
        self.parquet_config = config_manager.get_dict('keyword_matching.parquet_data_source', {})
        self.folder_path_1 = self.parquet_config.get('folder_path_1', '')
        self.folder_path_2 = self.parquet_config.get('folder_path_2', '')
        self.merge_columns = self.parquet_config.get('merge_on_columns', ['record_id', 'record_name'])

        # 验证parquet配置
        self._validate_parquet_config()

        # 进度跟踪
        self.progress = MatchingProgress()
        self.progress_bar: Optional[ProgressBar] = None

        # 已处理文件列表管理
        batch_processing_config = self.parquet_config.get('batch_processing', {}).get('processed_files', {})
        self.enable_skip_processed = batch_processing_config.get('enable_skip_processed', True)
        
        # 已处理文件列表保存在单独文件中
        self.processed_files_path = os.path.join(project_root, 'processed_files.json')
        self._load_processed_files()
        
        self.logger.info("关键词匹配器初始化完成")

    def _load_processed_files(self):
        """从文件加载已处理文件列表"""
        try:
            if os.path.exists(self.processed_files_path):
                import json
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
            import json
            from datetime import datetime
            
            # 更新最后更新时间
            self.processed_files_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.processed_files_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"保存已处理文件列表失败: {e}")

    def get_processed_files(self) -> List[str]:
        """获取已处理文件列表"""
        return self.processed_files_data.get('files', [])
    
    def is_file_processed(self, file_name: str) -> bool:
        """检查文件是否已处理
        
        Args:
            file_name: 文件名（可以是完整路径或仅文件名）
            
        Returns:
            bool: 如果文件已处理返回True
        """
        if not self.enable_skip_processed:
            return False
            
        processed_files = self.get_processed_files()
        
        # 支持完整路径和文件名匹配
        file_basename = Path(file_name).name
        
        for processed_file in processed_files:
            if file_name == processed_file or file_basename == Path(processed_file).name:
                return True
        
        return False
    
    def add_processed_file(self, file_name: str):
        """添加文件到已处理列表
        
        Args:
            file_name: 要添加的文件名
        """
        if not self.enable_skip_processed:
            return
            
        try:
            # 添加到文件列表（避免重复）
            if file_name not in self.processed_files_data['files']:
                self.processed_files_data['files'].append(file_name)
                
            # 保存到文件
            self._save_processed_files()
            
            self.logger.info(f"已添加文件到已处理列表: {file_name}")
            
        except Exception as e:
            self.logger.error(f"添加已处理文件失败: {e}")
    
    def remove_processed_file(self, file_name: str):
        """从已处理列表中移除文件
        
        Args:
            file_name: 要移除的文件名
        """
        if not self.enable_skip_processed:
            return
            
        try:
            # 从文件列表中移除
            if file_name in self.processed_files_data['files']:
                self.processed_files_data['files'].remove(file_name)
                
            # 保存到文件
            self._save_processed_files()
            
            self.logger.info(f"已从已处理列表中移除文件: {file_name}")
            
        except Exception as e:
            self.logger.error(f"移除已处理文件失败: {e}")
    
    def clear_processed_files(self):
        """清空已处理文件列表"""
        if not self.enable_skip_processed:
            return
            
        try:
            # 清空文件列表
            self.processed_files_data['files'] = []
            
            # 保存到文件
            self._save_processed_files()
            
            self.logger.info("已清空已处理文件列表")
            
        except Exception as e:
            self.logger.error(f"清空已处理文件列表失败: {e}")
    
    def get_processing_status(self) -> Dict[str, Any]:
        """获取文件处理状态统计
        
        Returns:
            Dict: 包含处理状态的统计信息
        """
        try:
            available_files = self.get_available_parquet_files()
            processed_files = self.get_processed_files()
            
            # 计算已处理和未处理的文件
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
            for i, file_name in enumerate(status['unprocessed_files'][:10], 1):  # 只显示前10个
                self.logger.info(f"  {i}. {Path(file_name).name}")
            
            if len(status['unprocessed_files']) > 10:
                self.logger.info(f"  ... 还有 {len(status['unprocessed_files']) - 10} 个文件")
        
        self.logger.info("=" * 60)

    def _validate_parquet_config(self):
        """验证parquet配置的有效性"""
        errors = []
        warnings = []

        # 检查文件夹路径
        if not self.folder_path_1:
            errors.append("Parquet文件夹路径1未配置")
        elif not Path(self.folder_path_1).exists():
            warnings.append(f"Parquet文件夹1不存在: {self.folder_path_1}")

        if not self.folder_path_2:
            errors.append("Parquet文件夹路径2未配置")
        elif not Path(self.folder_path_2).exists():
            warnings.append(f"Parquet文件夹2不存在: {self.folder_path_2}")

        # 检查合并列配置
        if not self.merge_columns:
            errors.append("合并列配置为空")
        elif not isinstance(self.merge_columns, list):
            errors.append("合并列配置必须是列表格式")

        # 记录验证结果
        if errors:
            error_msg = "Parquet配置验证失败: " + "; ".join(errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        if warnings:
            for warning in warnings:
                self.logger.warning(f"Parquet配置警告: {warning}")

        if not errors:
            self.logger.info("Parquet配置验证通过")

    def _calculate_progress_update_interval(self) -> float:
        """
        根据数据量动态计算进度条更新间隔

        Returns:
            float: 更新间隔（秒）
        """
        total_combinations = self.progress.total_combinations

        if total_combinations <= 10000:
            # 小数据量：更频繁更新
            return 0.1
        elif total_combinations <= 100000:
            # 中等数据量：标准更新
            return 0.5
        elif total_combinations <= 1000000:
            # 大数据量：较少更新
            return 1.0
        else:
            # 超大数据量：最少更新
            return 2.0

    def _get_progress_update_frequency(self) -> int:
        """
        获取进度条更新频率（每多少次处理更新一次）

        Returns:
            int: 更新频率
        """
        total_combinations = self.progress.total_combinations

        if total_combinations <= 1000:
            # 小数据量：每次都更新
            return 1
        elif total_combinations <= 10000:
            # 小中数据量：每10次更新
            return 10
        elif total_combinations <= 100000:
            # 中等数据量：每100次更新
            return 100
        elif total_combinations <= 1000000:
            # 大数据量：每1000次更新
            return 1000
        else:
            # 超大数据量：每5000次更新
            return 5000
    
    def load_keyword_data(self, file_path: Optional[str] = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        加载关键词数据表格
        
        Args:
            file_path: 关键词文件路径（可选）
            sheet_name: 工作表名称（可选）
            
        Returns:
            pd.DataFrame: 关键词数据表格
        """
        # 使用参数或配置中的路径
        file_path = file_path or self.keyword_file_path
        sheet_name = sheet_name or self.keyword_sheet_name
        
        # 自动检测文件路径
        if file_path == "auto_detect":
            file_path = self._auto_detect_keyword_file()
        
        if not file_path or not Path(file_path).exists():
            raise FileNotFoundError(f"关键词文件不存在: {file_path}")
        
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            self.logger.info(f"成功加载关键词数据: {len(df)} 行, 文件: {file_path}")
            return df
        except Exception as e:
            self.logger.error(f"加载关键词数据失败: {e}")
            raise

    def load_input_data(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        加载输入数据表格

        Args:
            file_path: 输入文件路径或parquet文件名
            sheet_name: 工作表名称（可选）

        Returns:
            pd.DataFrame: 输入数据表格
        """
        sheet_name = sheet_name or self.input_sheet_name

        # 检查是否为parquet文件名（不含路径分隔符）
        if '/' not in file_path and '\\' not in file_path and file_path.endswith('.parquet'):
            # 使用parquet文件夹模式
            return self.load_parquet_data_from_folders(file_path)

        # 传统文件路径模式
        if not Path(file_path).exists():
            raise FileNotFoundError(f"输入文件不存在: {file_path}")

        try:
            # 根据文件扩展名选择读取方法
            file_ext = Path(file_path).suffix.lower()
            if file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            elif file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")

            self.logger.info(f"成功加载输入数据: {len(df)} 行, 文件: {file_path}")
            return df
        except Exception as e:
            self.logger.error(f"加载输入数据失败: {e}")
            raise

    def load_parquet_data_from_folders(self, file_name: str) -> pd.DataFrame:
        """
        从两个parquet文件夹中读取同名文件并合并

        Args:
            file_name: parquet文件名（不含路径）

        Returns:
            pd.DataFrame: 合并后的数据表格
        """


        if not self.folder_path_1 or not self.folder_path_2:
            raise ValueError("Parquet文件夹路径未配置")

        # 构建完整文件路径
        file_path_1 = Path(self.folder_path_1) / file_name
        file_path_2 = Path(self.folder_path_2) / file_name

        # 检查文件是否存在
        if not file_path_1.exists():
            raise FileNotFoundError(f"文件不存在: {file_path_1}")
        if not file_path_2.exists():
            raise FileNotFoundError(f"文件不存在: {file_path_2}")

        try:
            # 读取两个parquet文件
            self.logger.info(f"读取parquet文件: {file_path_1}")
            df1 = pd.read_parquet(file_path_1)

            self.logger.info(f"读取parquet文件: {file_path_2}")
            df2 = pd.read_parquet(file_path_2)

            # 验证合并列是否存在
            for col in self.merge_columns:
                if col not in df1.columns:
                    raise ValueError(f"合并列 '{col}' 在文件1中不存在: {file_path_1}")
                if col not in df2.columns:
                    raise ValueError(f"合并列 '{col}' 在文件2中不存在: {file_path_2}")

            # 合并数据
            self.logger.info(f"合并数据，基于列: {self.merge_columns}")
            merged_df = pd.merge(df1, df2, on=self.merge_columns, how='inner')

            self.logger.info(f"成功合并parquet数据: 文件1 {len(df1)} 行, 文件2 {len(df2)} 行, 合并后 {len(merged_df)} 行")
            return merged_df

        except Exception as e:
            self.logger.error(f"加载和合并parquet数据失败: {e}")
            raise

    def get_available_parquet_files(self) -> List[str]:
        """
        获取两个文件夹中的同名parquet文件列表

        Returns:
            List[str]: 同名parquet文件名列表
        """


        if not self.folder_path_1 or not self.folder_path_2:
            return []

        try:
            folder1 = Path(self.folder_path_1)
            folder2 = Path(self.folder_path_2)

            if not folder1.exists() or not folder2.exists():
                self.logger.warning(f"Parquet文件夹不存在: {folder1} 或 {folder2}")
                return []

            # 获取两个文件夹中的parquet文件
            files1 = set(f.name for f in folder1.glob('*.parquet'))
            files2 = set(f.name for f in folder2.glob('*.parquet'))

            # 返回同名文件
            common_files = list(files1.intersection(files2))
            common_files.sort()

            self.logger.info(f"找到 {len(common_files)} 个同名parquet文件")
            return common_files

        except Exception as e:
            self.logger.error(f"获取parquet文件列表失败: {e}")
            return []

    def get_random_parquet_file(self) -> Optional[str]:
        """
        随机选择一个parquet文件用于测试

        Returns:
            Optional[str]: 随机选择的文件名，如果没有文件则返回None
        """
        available_files = self.get_available_parquet_files()
        if not available_files:
            return None

        selected_file = random.choice(available_files)
        self.logger.info(f"随机选择测试文件: {selected_file}")
        return selected_file

    def run_batch_processing(self, keyword_file_path: Optional[str] = None,
                           output_base_path: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        批量处理所有parquet文件 - 支持多进程优化

        Args:
            keyword_file_path: 关键词文件路径（可选）
            output_base_path: 输出文件基础路径（可选）

        Returns:
            List[Tuple[str, str, str]]: (文件名, 结果文件路径, 报告文件路径) 的列表
        """
        available_files = self.get_available_parquet_files()
        if not available_files:
            raise ValueError("没有找到可处理的parquet文件")
        
        # 过滤掉已处理的文件
        if self.enable_skip_processed:
            original_count = len(available_files)
            available_files = [f for f in available_files if not self.is_file_processed(f)]
            skipped_count = original_count - len(available_files)
            
            if skipped_count > 0:
                self.logger.info(f"跳过 {skipped_count} 个已处理的文件")
                
            if not available_files:
                self.logger.info("所有文件都已处理完成，无需重复处理")
                return []

        # 从配置读取性能优化设置
        enable_performance_optimization = self.enable_optimization
        max_workers_config = self.max_workers

        # 计算实际使用的进程数
        if max_workers_config == -1:
            # 使用总CPU核心数 - 1
            actual_max_workers = max(1, psutil.cpu_count() - 1)
        else:
            actual_max_workers = max(1, max_workers_config)

        batch_config = self.parquet_config.get('batch_processing', {})
        
        # 显示处理状态信息
        if self.enable_skip_processed:
            self.print_processing_status()

        self.logger.info(f"开始批量处理 {len(available_files)} 个parquet文件")
        self.logger.info(f"性能优化: {'启用' if enable_performance_optimization else '禁用'}")
        if enable_performance_optimization:
            self.logger.info(f"多进程配置: {actual_max_workers} 个工作进程")

        # 根据配置选择处理方式
        if enable_performance_optimization and len(available_files) > 1:
            return self._run_batch_processing_multiprocess(
                available_files, keyword_file_path, output_base_path,
                actual_max_workers, batch_config
            )
        else:
            return self._run_batch_processing_serial(
                available_files, keyword_file_path, output_base_path, batch_config
            )

    def _run_batch_processing_serial(self, available_files: List[str],
                                   keyword_file_path: Optional[str],
                                   output_base_path: Optional[str],
                                   batch_config: Dict) -> List[Tuple[str, str, str]]:
        """
        串行批量处理 - 原有的逐个处理方式

        Args:
            available_files: 可用文件列表
            keyword_file_path: 关键词文件路径
            output_base_path: 输出基础路径
            batch_config: 批处理配置

        Returns:
            List[Tuple[str, str, str]]: 处理结果列表
        """
        continue_on_error = batch_config.get('continue_on_error', True)
        max_errors = batch_config.get('max_errors', 50)
        progress_interval = batch_config.get('progress_report_interval', 10)

        results = []
        error_count = 0

        for i, file_name in enumerate(available_files, 1):
            try:
                self.logger.info(f"串行处理文件 {i}/{len(available_files)}: {file_name}")

                # 生成输出文件路径
                base_name = Path(file_name).stem
                if output_base_path:
                    output_file = f"{output_base_path}_{base_name}.xlsx"
                else:
                    output_file = f"batch_results_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                # 执行单个文件的匹配
                result_file, report_file = self.run_complete_matching(
                    input_file_path=file_name,
                    keyword_file_path=keyword_file_path,
                    output_file_path=output_file
                )

                results.append((file_name, result_file, report_file))
                
                # 添加到已处理文件列表
                self.add_processed_file(file_name)

                # 定期报告进度
                if i % progress_interval == 0:
                    self.logger.info(f"串行批处理进度: {i}/{len(available_files)} 完成")

            except Exception as e:
                error_count += 1
                self.logger.error(f"处理文件 {file_name} 失败: {e}")

                if not continue_on_error or error_count >= max_errors:
                    self.logger.error(f"错误过多或设置不继续处理，停止批处理")
                    break

        self.logger.info(f"串行批处理完成: 成功 {len(results)} 个文件, 失败 {error_count} 个文件")
        return results

    def _run_batch_processing_multiprocess(self, available_files: List[str],
                                         keyword_file_path: Optional[str],
                                         output_base_path: Optional[str],
                                         max_workers: int,
                                         batch_config: Dict) -> List[Tuple[str, str, str]]:
        """
        多进程批量处理 - 并行处理多个parquet文件

        Args:
            available_files: 可用文件列表
            keyword_file_path: 关键词文件路径
            output_base_path: 输出基础路径
            max_workers: 最大工作进程数
            batch_config: 批处理配置

        Returns:
            List[Tuple[str, str, str]]: 处理结果列表
        """
        continue_on_error = batch_config.get('continue_on_error', True)
        max_errors = batch_config.get('max_errors', 50)
        progress_interval = batch_config.get('progress_report_interval', 10)

        results = []
        error_count = 0
        completed_count = 0

        self.logger.info(f"启动多进程批处理: {max_workers} 个工作进程处理 {len(available_files)} 个文件")

        # 启动多进程批量处理的主进度条
        main_progress = multiprocess_progress_manager.start_batch_progress(
            total_files=len(available_files),
            description=f"多进程批量处理({max_workers}进程)"
        )

        # 使用ProcessPoolExecutor进行多进程处理
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务到进程池
            future_to_file = {}
            for file_name in available_files:
                # 生成输出文件路径
                base_name = Path(file_name).stem
                if output_base_path:
                    output_file = f"{output_base_path}_{base_name}.xlsx"
                else:
                    output_file = f"batch_results_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                # 提交任务到进程池 - 使用静态函数避免序列化锁对象
                future = executor.submit(
                    process_single_file_worker_static,
                    file_name,
                    keyword_file_path,
                    output_file
                )
                future_to_file[future] = file_name

            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_name = future_to_file[future]
                completed_count += 1

                try:
                    # 获取处理结果
                    result_file, report_file = future.result()
                    results.append((file_name, result_file, report_file))
                    
                    # 添加到已处理文件列表
                    self.add_processed_file(file_name)

                    # 更新多进程进度条
                    multiprocess_progress_manager.update_file_progress(file_name, "完成")

                    self.logger.info(f"多进程处理完成 ({completed_count}/{len(available_files)}): {file_name}")

                    # 定期报告进度
                    if completed_count % progress_interval == 0:
                        self.logger.info(f"多进程批处理进度: {completed_count}/{len(available_files)} 完成")

                except Exception as e:
                    error_count += 1

                    # 更新多进程进度条（标记为失败）
                    multiprocess_progress_manager.update_file_progress(file_name, "失败")

                    self.logger.error(f"多进程处理文件 {file_name} 失败: {e}")

                    if not continue_on_error or error_count >= max_errors:
                        self.logger.error(f"错误过多或设置不继续处理，停止批处理")
                        # 取消剩余的任务
                        for remaining_future in future_to_file:
                            if not remaining_future.done():
                                remaining_future.cancel()
                        break

        # 完成多进程批量处理的主进度条
        multiprocess_progress_manager.finish_batch_progress(
            f"多进程批处理完成: 成功 {len(results)} 个文件, 失败 {error_count} 个文件"
        )

        self.logger.info(f"多进程批处理完成: 成功 {len(results)} 个文件, 失败 {error_count} 个文件")
        return results



    def run_random_test(self, keyword_file_path: Optional[str] = None,
                       output_file_path: Optional[str] = None) -> Tuple[str, str, str]:
        """
        随机选择一个文件进行快速测试

        Args:
            keyword_file_path: 关键词文件路径（可选）
            output_file_path: 输出文件路径（可选）

        Returns:
            Tuple[str, str, str]: (测试文件名, 结果文件路径, 报告文件路径)
        """


        test_file = self.get_random_parquet_file()
        if not test_file:
            raise ValueError("没有找到可测试的parquet文件")

        # 生成输出文件路径
        if not output_file_path:
            base_name = Path(test_file).stem
            output_file_path = f"random_test_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        self.logger.info(f"开始随机测试，文件: {test_file}")

        # 执行匹配
        result_file, report_file = self.run_complete_matching(
            input_file_path=test_file,  # 传递文件名，load_input_data会识别为parquet模式
            keyword_file_path=keyword_file_path,
            output_file_path=output_file_path
        )

        self.logger.info(f"随机测试完成: {test_file}")
        return test_file, result_file, report_file

    def execute_matching(self, keyword_df: pd.DataFrame, input_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        执行关键词匹配

        Args:
            keyword_df: 关键词数据表格
            input_df: 输入数据表格

        Returns:
            List[Dict[str, Any]]: 匹配结果列表
        """
        start_time = datetime.now()

        # 初始化进度
        self.progress.total_input_rows = len(input_df)
        self.progress.total_combinations = len(keyword_df) * len(input_df)
        self.progress.processed_combinations = 0
        self.progress.successful_matches = 0
        self.progress.failed_matches = 0

        self.logger.info(f"开始执行匹配: {len(keyword_df)} 个关键词规则 × {len(input_df)} 条输入数据")

        # 启动进度条（根据数据量动态调整更新间隔）
        update_interval = self._calculate_progress_update_interval()

        # 使用进程安全的进度条，在工作进程中自动简化显示
        self.progress_bar = create_process_safe_progress_bar(
            total=self.progress.total_combinations,
            description="关键词匹配",
            bar_length=20,
            update_interval=update_interval,
            enable_in_worker=False  # 在工作进程中禁用详细进度条
        )
        self.progress_bar.start()

        matching_results = []

        try:
            matching_results = self._execute_serial_matching(keyword_df, input_df)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # 完成进度条显示
            if self.progress_bar:
                self.progress_bar.finish(f"匹配完成! 成功: {self.progress.successful_matches}, 失败: {self.progress.failed_matches}")
                self.progress_bar = None

            self.logger.info(f"匹配完成: 处理时间 {processing_time:.2f}s, "
                           f"成功匹配 {self.progress.successful_matches} 条, "
                           f"失败 {self.progress.failed_matches} 条")

            # 🚀 优化：记录性能对比数据
            combinations_per_second = self.progress.total_combinations / processing_time if processing_time > 0 else 0
            self.logger.info(f"🚀 性能统计: {combinations_per_second:.0f} 组合/秒, ")

            # 🚀 修复：记录缓存性能 - 查看正确的统计对象
            try:
                # 获取匹配引擎的缓存统计（正确的统计来源）
                engine_cache_stats = self.matching_engine.get_performance_stats()
                self.logger.info(f"🚀 缓存性能: 命中率 {engine_cache_stats.get('cache_hit_rate', '0.0%')}, "
                               f"缓存大小 {engine_cache_stats.get('pattern_cache_size', 0)}, "
                               f"总请求 {engine_cache_stats.get('total_cache_requests', 0)}")

            except Exception as e:
                self.logger.warning(f"获取缓存统计失败: {e}")

            return matching_results

        except Exception as e:
            # 确保进度条在异常时也能正确关闭
            if self.progress_bar:
                self.progress_bar.finish("匹配过程中发生错误")
                self.progress_bar = None
            self.logger.error(f"执行匹配时发生错误: {e}")
            raise

    def _execute_serial_matching(self, keyword_df: pd.DataFrame, input_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """串行执行匹配 - 重构的批量处理版本"""
        matching_results = []

        # 🚀 优化1：预先转换为字典，避免重复调用to_dict()
        self.logger.info("开始预处理数据结构（串行模式）...")
        start_time = time.time()

        keyword_dicts = [row.to_dict() for _, row in keyword_df.iterrows()]
        input_dicts = [row.to_dict() for _, row in input_df.iterrows()]

        # 🚀 优化2：批量预处理所有输入数据的文本，消除重复解析
        self.logger.info("开始批量预处理文本数据...")
        preprocessed_input_data = self._batch_preprocess_input_texts(input_dicts)

        preprocess_time = time.time() - start_time
        self.logger.info(f"预处理完成: {len(keyword_dicts)} 个关键词, {len(input_dicts)} 个输入数据, 耗时: {preprocess_time:.3f}秒")

        # 🚀 架构重构：批量处理多个企业-关键词组合，实现真正的向量化
        for keyword_idx, keyword_dict in enumerate(keyword_dicts):
            # 对当前关键词，批量处理所有企业数据
            batch_results = self._process_keyword_batch_optimized(
                keyword_idx, keyword_dict, preprocessed_input_data
            )
            matching_results.extend(batch_results)

            # 更新进度
            self.progress.processed_combinations += len(preprocessed_input_data)

            # 根据数据量动态调整进度条更新频率
            update_frequency = self._get_progress_update_frequency()
            if self.progress_bar and self.progress.processed_combinations % update_frequency == 0:
                self.progress_bar.update(self.progress.processed_combinations)

            # 定期输出进度日志
            if (keyword_idx + 1) % max(1, len(keyword_dicts) // 10) == 0:
                self.logger.info(f"已处理关键词: {keyword_idx + 1}/{len(keyword_dicts)}, "
                               f"累计匹配结果: {len(matching_results)}")

        return matching_results

    def _batch_preprocess_input_texts(self, input_dicts: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, List[str]]]]:
        """
        批量预处理所有输入数据的文本，消除重复解析操作

        🚀 性能优化：一次性处理所有文本数据，避免在三阶段匹配中重复调用 _smart_parse_text_data()

        Args:
            input_dicts: 输入数据字典列表

        Returns:
            List[Tuple[Dict, Dict]]: (原始输入字典, 预处理后的文本字典) 的列表
        """
        preprocessed_data = []

        # 🚀 修复：从配置文件获取需要处理的文本列，避免硬编码
        from config import config_manager
        text_columns = config_manager.get_list(
            'keyword_matching.input_table_columns.text_content_columns',
            ['company_profile', 'main_product', 'business_scope', 'service_intro']  # 回退默认值
        )

        for input_dict in input_dicts:
            # 🚀 优化：一次性预处理当前输入数据的所有文本列
            preprocessed_texts = {}

            for col in text_columns:
                col_texts = input_dict.get(col, [])
                # 使用匹配引擎的文本解析方法，但只调用一次
                parsed_texts = self.matching_engine._smart_parse_text_data(col_texts)
                preprocessed_texts[col] = parsed_texts

            preprocessed_data.append((input_dict, preprocessed_texts))

        return preprocessed_data

    def _process_keyword_batch_optimized(self, keyword_idx: int, keyword_dict: Dict[str, Any],
                                       preprocessed_input_data: List[Tuple[Dict[str, Any], Dict[str, List[str]]]]) -> List[Dict[str, Any]]:
        """
        批量处理一个关键词对所有企业的匹配 - 🚀 真正的向量化优化

        这是重构后的核心方法，实现了真正的批量处理：
        1. 收集所有企业的文本数据
        2. 使用向量化方法批量匹配
        3. 分配结果到对应的企业

        Args:
            keyword_idx: 关键词索引
            keyword_dict: 关键词字典
            preprocessed_input_data: 预处理的企业数据列表

        Returns:
            List[Dict[str, Any]]: 匹配成功的结果列表
        """
        batch_results = []

        # 🚀 步骤1：应用筛选逻辑，过滤不符合条件的企业
        filtered_enterprises = []
        for input_dict, preprocessed_texts in preprocessed_input_data:
            filter_result = self.filter_logic.apply_combined_filter(keyword_dict, input_dict)
            if filter_result.passed:
                filtered_enterprises.append((input_dict, preprocessed_texts, filter_result.filtered_columns))
            else:
                self.progress.increment_failure()

        if not filtered_enterprises:
            return batch_results

        # 🚀 步骤2：使用重构的批量匹配引擎

        batch_match_results = self.matching_engine.batch_match_keywords_optimized(
            keyword_dict, filtered_enterprises
        )

        # 🚀 步骤3：构建结果记录
        for i, (input_dict, _, _) in enumerate(filtered_enterprises):
            if i < len(batch_match_results) and batch_match_results[i].success:
                self.progress.increment_success()

                # 构建完整的结果记录，确保与过滤逻辑兼容
                match_result = batch_match_results[i]
                total_matched_texts = sum(len(texts) for texts in match_result.matched_texts.values())

                result_record = {
                    # 🚀 修复：使用配置化的字段名，确保与过滤逻辑兼容
                    self.keyword_identifier_field: keyword_idx,  # 使用配置的关键词标识字段名
                    self.company_identifier_field: input_dict.get('record_id', ''),  # 使用配置的标识字段名

                    # 保留原有字段以确保兼容性
                    'keyword_index': keyword_idx,
                    'input_index': input_dict.get('index', 0),
                    'keyword_id': keyword_dict.get('id', keyword_idx),
                    'input_id': input_dict.get('id', input_dict.get('record_id', '')),
                    'record_name': input_dict.get('record_name', ''),
                    # 🚀 修复：显式添加 record_id 字段
                    'record_id': input_dict.get('record_id', ''),
                    'match_success': True,
                    'matched_texts_count': total_matched_texts,
                    'matched_columns': [col for col, texts in match_result.matched_texts.items() if texts],
                    'match_timestamp': datetime.now().isoformat(),
                    # 🚀 修复：添加过滤逻辑需要的字段
                    'matched_texts': match_result.matched_texts,  # 过滤逻辑需要此字段
                    'match_details': match_result.match_details or {'batch_processed': True}  # 过滤逻辑需要此字段
                }

                batch_results.append(result_record)
            else:
                self.progress.increment_failure()

        return batch_results

    def _process_single_combination(self, keyword_idx: int, keyword_row: pd.Series, input_row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        处理单个关键词-输入数据组合

        Args:
            keyword_idx: 关键词索引
            keyword_row: 关键词行数据
            input_row: 输入行数据

        Returns:
            Dict[str, Any]: 匹配结果，只有匹配成功时才返回，失败时返回None
        """
        try:
            # 转换为字典格式
            keyword_dict = keyword_row.to_dict()
            input_dict = input_row.to_dict()

            # 应用筛选逻辑
            filter_result = self.filter_logic.apply_combined_filter(keyword_dict, input_dict)
            if not filter_result.passed:
                self.progress.increment_failure()
                return None

            # 执行关键词匹配
            match_result = self.matching_engine.match_keywords(
                keyword_dict, input_dict, filter_result.filtered_columns
            )

            # 只有匹配成功的记录才构建结果并返回
            if match_result.success:
                # 提取match_details中的关键统计信息
                match_details = match_result.match_details or {}
                stage_stats = match_details.get('stage_stats', {})

                # 构建包含展开统计信息的匹配结果
                result = {
                    # 标识信息（使用配置化字段名称）
                    self.keyword_identifier_field: keyword_idx,  # 关键词规则标识
                    self.company_identifier_field: input_dict.get('record_id', ''),  # 标识字段

                    # 添加所有标识列
                    'record_id': input_dict.get('record_id', ''),
                    'record_name': input_dict.get('record_name', ''),

                    # 匹配结果信息
                    'match_success': True,
                    'matched_texts': match_result.matched_texts,  # 具体匹配到的文本内容和标记
                    'match_details': match_details,  # 保留完整的详细匹配统计信息

                    # 展开的统计信息字段
                    'total_texts_processed': match_details.get('total_texts_processed', 0),
                    'texts_passed_all_stages': match_details.get('texts_passed_all_stages', 0),
                    'like_passed_count': stage_stats.get('like_passed', 0),
                    'must_passed_count': stage_stats.get('must_passed', 0),
                    'unlike_passed_count': stage_stats.get('unlike_passed', 0),
                    'like_failed_count': stage_stats.get('like_failed', 0),
                    'must_failed_count': stage_stats.get('must_failed', 0),
                    'unlike_failed_count': stage_stats.get('unlike_failed', 0),

                    # 筛选信息
                    'filter_reason': filter_result.reason,
                    'filtered_columns': filter_result.filtered_columns,

                    # 处理时间戳
                    'processed_at': datetime.now().isoformat()
                }

                self.progress.increment_success()
                return result
            else:
                # 匹配失败的记录不保留在最终结果中
                self.progress.increment_failure()
                return None

        except Exception as e:
            self.logger.warning(f"处理组合失败 (keyword_idx={keyword_idx}): {e}")
            self.progress.increment_failure()
            return None
    
    def _auto_detect_keyword_file(self) -> Optional[str]:
        """自动检测关键词文件"""
        # 查找最新的转换后关键词文件
        current_dir = Path('.')
        pattern = 'converted_keyword_rules*.xlsx'
        
        files = list(current_dir.glob(pattern))
        if files:
            # 按修改时间排序，返回最新的
            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            return str(latest_file)
        
        return None

    def run_complete_matching(self, input_file_path: str,
                            keyword_file_path: Optional[str] = None,
                            output_file_path: Optional[str] = None) -> Tuple[str, str]:
        """
        运行完整的匹配流程

        Args:
            input_file_path: 输入文件路径
            keyword_file_path: 关键词文件路径（可选）
            output_file_path: 输出文件路径（可选）

        Returns:
            Tuple[str, str]: (结果文件路径, 摘要报告路径)
        """
        try:
            # 加载数据
            self.logger.info("开始加载数据...")
            keyword_df = self.load_keyword_data(keyword_file_path)
            input_df = self.load_input_data(input_file_path)

            # 执行匹配
            self.logger.info("开始执行匹配...")
            matching_results = self.execute_matching(keyword_df, input_df)

            # 过滤和验证匹配结果
            self.logger.info("过滤和验证匹配结果...")
            successful_results = self._filter_successful_results(matching_results)

            # 记录结果统计
            total_results = len(matching_results) if matching_results else 0
            successful_count = len(successful_results)
            self.logger.info(f"匹配结果统计: 总处理 {total_results} 条组合, "
                           f"成功匹配 {successful_count} 条, "
                           f"成功率: {(successful_count/total_results*100):.2f}%" if total_results > 0 else "成功率: 0%")

            # 处理和保存结果
            self.logger.info("开始处理和保存结果...")
            result_file_path = self.result_processor.process_and_save_results(
                successful_results,
                output_file_path
            )

            # 生成摘要报告
            self.logger.info("生成摘要报告...")
            summary_report = self.result_processor.generate_summary_report(successful_results)
            report_file_path = self.result_processor.save_summary_report(summary_report)

            self.logger.info(f"完整匹配流程执行完成")
            self.logger.info(f"结果文件: {result_file_path}")
            self.logger.info(f"摘要报告: {report_file_path}")

            return result_file_path, report_file_path

        except Exception as e:
            self.logger.error(f"完整匹配流程执行失败: {e}")
            raise

    def _filter_successful_results(self, matching_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤出成功匹配的结果，确保数据完整性

        Args:
            matching_results: 原始匹配结果列表

        Returns:
            List[Dict[str, Any]]: 过滤后的成功匹配结果列表
        """
        if not matching_results:
            return []

        successful_results = []

        for result in matching_results:
            # 验证结果的完整性
            if (result and
                result.get('match_success') is True and
                result.get('matched_texts') and
                result.get('match_details')):

                # 确保包含必要的标识信息（使用配置化字段名称）
                if (self.keyword_identifier_field in result and
                    self.company_identifier_field in result):

                    successful_results.append(result)
                else:
                    keyword_id = result.get(self.keyword_identifier_field, 'unknown')
                    self.logger.warning(f"匹配结果缺少必要的标识信息: {keyword_id}")
            else:
                # 记录被过滤的原因
                if result:
                    reason = "未知原因"
                    if not result.get('match_success'):
                        reason = "匹配失败"
                    elif not result.get('matched_texts'):
                        reason = "无匹配文本"
                    elif not result.get('match_details'):
                        reason = "缺少匹配详情"

                    keyword_id = result.get(self.keyword_identifier_field, 'unknown')
                    self.logger.debug(f"过滤结果 (keyword_id={keyword_id}): {reason}")

        return successful_results
    
    def get_progress_info(self) -> MatchingProgress:
        """获取当前进度信息"""
        return self.progress

if __name__ == "__main__":
    pass
