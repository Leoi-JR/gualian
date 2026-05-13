#!/usr/bin/env python3
"""
结果处理模块
Result Processor Module

该模块负责格式化和保存匹配结果，生成标准化的输出文件，
支持多种输出格式和结果统计功能。

输出格式：
df_keyword索引值,record_id,record_name,*_matched_texts,...

作者：系统开发
日期：2024年
"""

import pandas as pd
import csv
import logging
import os
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config_manager


@dataclass
class ProcessingStats:
    """处理统计数据类"""
    total_matches: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    processing_time: float = 0.0
    output_file_size: int = 0


class ResultProcessor:
    """
    结果处理器类
    
    负责格式化匹配结果并保存到文件，
    提供多种输出格式和统计功能。
    """
    
    def __init__(self):
        """初始化结果处理器"""
        self.logger = logging.getLogger(__name__)

        # 从配置获取设置
        self.output_file_path = config_manager.get_str('keyword_matching.output_file_path', 'matching_results.csv')
        self.text_columns = config_manager.get_list('keyword_matching.input_table_columns.text_content_columns')
        self.identifier_columns = config_manager.get_list('keyword_matching.input_table_columns.identifier_columns')

        # 处理统计
        self.stats = ProcessingStats()

        # 创建结果文件夹结构
        self.results_base_dir = Path("results")
        self.results_base_dir.mkdir(exist_ok=True)

        self.logger.info("结果处理器初始化完成")
    
    def process_and_save_results(self, 
                               matching_results: List[Dict[str, Any]], 
                               output_path: Optional[str] = None) -> str:
        """
        处理并保存匹配结果
        
        Args:
            matching_results: 匹配结果列表
            output_path: 输出文件路径（可选）
            
        Returns:
            str: 输出文件路径
        """
        start_time = datetime.now()
        
        try:
            # 确定输出路径
            if not output_path:
                output_path = self._generate_output_path()
            else:
                output_path = self._generate_output_path(output_path)

            # 格式化结果数据
            formatted_data = self._format_results(matching_results)

            # 根据文件扩展名选择保存方法
            self._save_results_file(formatted_data, output_path)
            
            # 更新统计信息
            end_time = datetime.now()
            self.stats.processing_time = (end_time - start_time).total_seconds()
            self.stats.total_matches = len(matching_results)
            self.stats.successful_matches = len([r for r in matching_results if r.get('match_success', False)])
            self.stats.failed_matches = self.stats.total_matches - self.stats.successful_matches
            
            # 获取文件大小
            try:
                self.stats.output_file_size = Path(output_path).stat().st_size
            except Exception:
                self.stats.output_file_size = 0
            
            self.logger.info(f"结果处理完成，输出文件: {output_path}")
            self.logger.info(f"处理统计: {self.stats}")
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"处理和保存结果时发生错误: {e}")
            raise
    
    def _generate_output_path(self, custom_path: Optional[str] = None) -> str:
        """
        生成输出文件路径，支持文件夹组织和格式检测

        Args:
            custom_path: 用户指定的自定义路径

        Returns:
            str: 完整的输出文件路径
        """
        # 生成时间戳文件夹
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.results_base_dir / timestamp
        session_dir.mkdir(exist_ok=True)

        # 确定基础文件名和扩展名
        if custom_path:
            # 使用用户指定的路径
            path_obj = Path(custom_path)
            base_name = path_obj.stem
            file_extension = path_obj.suffix.lower()
        else:
            # 使用配置中的默认路径
            path_obj = Path(self.output_file_path)
            base_name = path_obj.stem
            file_extension = path_obj.suffix.lower()

        # 如果文件名不包含时间戳，则使用简化名称
        if not any(x in base_name for x in ['%Y', '%m', '%d', '%H', '%M', '%S']):
            if custom_path:
                # 保持用户指定的文件名
                final_name = f"{base_name}{file_extension}"
            else:
                # 使用标准名称
                final_name = f"matching_results{file_extension}"
        else:
            final_name = f"{base_name}{file_extension}"

        # 生成完整路径
        full_path = session_dir / final_name

        # 存储会话目录供后续使用（如摘要报告）
        self.current_session_dir = session_dir

        return str(full_path)
    
    def _format_results(self, matching_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化匹配结果

        Args:
            matching_results: 原始匹配结果

        Returns:
            List[Dict[str, Any]]: 格式化后的结果
        """
        formatted_results = []

        for result in matching_results:
            try:
                formatted_row = self._format_single_result(result)
                if formatted_row:
                    formatted_results.append(formatted_row)
            except Exception as e:
                self.logger.warning(f"格式化单个结果失败: {e}, 结果: {result}")
                continue

        return formatted_results
    
    def _format_single_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        格式化单个匹配结果

        Args:
            result: 单个匹配结果

        Returns:
            Dict[str, Any]: 格式化后的结果行，如果失败返回None
        """
        if not result.get('match_success', False):
            return None
        
        formatted_row = {}
        
        # 添加关键词索引
        formatted_row['keyword_index'] = result.get('keyword_index', '')
        
        # 添加标识列
        for col in self.identifier_columns:
            formatted_row[col] = result.get(col, '')
        
        # 添加匹配文本列
        matched_texts = result.get('matched_texts', {})
        for col in self.text_columns:
            col_matched_texts = matched_texts.get(col, [])
            # 将列表转换为字符串格式
            formatted_row[f'{col}_matched_texts'] = self._format_matched_texts_list(col_matched_texts)

        return formatted_row
    
    def _format_matched_texts_list(self, matched_texts: List[str]) -> str:
        """
        格式化匹配文本列表，使用更安全的序列化方式

        优化特性：
        1. 优先使用JSON格式，便于后续解析
        2. 使用安全分隔符作为回退方案
        3. 处理特殊字符和转义
        4. 支持空值和异常情况

        Args:
            matched_texts: 匹配文本列表

        Returns:
            str: 格式化后的字符串
        """
        if not matched_texts:
            return ''

        # 清理和验证输入数据
        cleaned_texts = []
        for text in matched_texts:
            if text is not None:
                cleaned_text = str(text).strip()
                if cleaned_text:
                    cleaned_texts.append(cleaned_text)

        if not cleaned_texts:
            return ''

        # 方法1：优先使用JSON格式
        try:
            import json
            json_result = json.dumps(cleaned_texts, ensure_ascii=False, separators=(',', ':'))
            # 验证JSON结果的长度是否合理
            if len(json_result) < 50000:  # 避免过长的JSON字符串
                return json_result
            else:
                self.logger.warning(f"JSON结果过长 ({len(json_result)} 字符)，使用回退方案")
        except (TypeError, ValueError, OverflowError) as e:
            self.logger.warning(f"JSON序列化失败: {e}")

        # 方法2：使用安全分隔符
        safe_separator = '|||'  # 使用不太可能出现在文本中的分隔符

        # 检查分隔符是否与文本内容冲突
        if any(safe_separator in text for text in cleaned_texts):
            # 如果冲突，使用更复杂的分隔符
            safe_separator = '§§§'
            if any(safe_separator in text for text in cleaned_texts):
                # 最后的回退方案：使用转义
                safe_separator = '|'
                escaped_texts = []
                for text in cleaned_texts:
                    # 转义分隔符
                    escaped_text = text.replace('|', '\\|')
                    escaped_texts.append(escaped_text)
                result = safe_separator.join(escaped_texts)
                self.logger.debug(f"使用转义分隔符格式化 {len(cleaned_texts)} 个匹配文本")
                return result

        # 使用安全分隔符连接
        result = safe_separator.join(cleaned_texts)
        self.logger.debug(f"使用安全分隔符 '{safe_separator}' 格式化 {len(cleaned_texts)} 个匹配文本")
        return result

    def parse_matched_texts_string(self, formatted_string: str) -> List[str]:
        """
        解析格式化的匹配文本字符串，与_format_matched_texts_list对应

        Args:
            formatted_string: 格式化后的字符串

        Returns:
            List[str]: 解析后的文本列表
        """
        if not formatted_string:
            return []

        # 尝试JSON解析
        try:
            import json
            if formatted_string.startswith('[') and formatted_string.endswith(']'):
                parsed = json.loads(formatted_string)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed if item is not None]
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试分隔符解析
        for separator in ['|||', '§§§', '|']:
            if separator in formatted_string:
                parts = formatted_string.split(separator)
                if separator == '|':
                    # 处理转义
                    result = []
                    for part in parts:
                        unescaped = part.replace('\\|', '|')
                        if unescaped.strip():
                            result.append(unescaped.strip())
                    return result
                else:
                    return [part.strip() for part in parts if part.strip()]

        # 单个文本
        return [formatted_string.strip()] if formatted_string.strip() else []

    def _save_results_file(self, formatted_data: List[Dict[str, Any]], output_path: str):
        """
        根据文件扩展名保存结果文件

        Args:
            formatted_data: 格式化后的数据
            output_path: 输出文件路径
        """
        file_extension = Path(output_path).suffix.lower()

        if file_extension == '.xlsx':
            self._save_to_excel(formatted_data, output_path)
        elif file_extension == '.csv':
            self._save_to_csv(formatted_data, output_path)
        else:
            # 默认保存为CSV格式
            self.logger.warning(f"未识别的文件扩展名 {file_extension}，默认保存为CSV格式")
            self._save_to_csv(formatted_data, output_path)

    def _save_to_excel(self, formatted_data: List[Dict[str, Any]], output_path: str):
        """
        保存数据到Excel文件

        Args:
            formatted_data: 格式化后的数据
            output_path: 输出文件路径
        """
        if not formatted_data:
            self.logger.warning("没有数据需要保存")
            # 创建空的Excel文件
            df = pd.DataFrame()
            # 添加标准列头
            headers = ['keyword_index'] + self.identifier_columns + [f'{col}_matched_texts' for col in self.text_columns]
            for header in headers:
                df[header] = []
            df.to_excel(output_path, index=False, engine='openpyxl')
            return

        try:
            # 使用pandas保存为Excel格式
            df = pd.DataFrame(formatted_data)
            df.to_excel(output_path, index=False, engine='openpyxl')

            self.logger.info(f"成功保存 {len(formatted_data)} 条匹配结果到Excel文件: {output_path}")

        except Exception as e:
            self.logger.error(f"保存Excel文件失败: {e}")
            # 回退到CSV格式
            csv_path = output_path.replace('.xlsx', '.csv')
            self.logger.info(f"回退到CSV格式: {csv_path}")
            self._save_to_csv(formatted_data, csv_path)

    def _save_to_csv(self, formatted_data: List[Dict[str, Any]], output_path: str):
        """
        保存数据到CSV文件
        
        Args:
            formatted_data: 格式化后的数据
            output_path: 输出文件路径
        """
        if not formatted_data:
            self.logger.warning("没有数据需要保存")
            # 创建空文件
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入表头
                headers = ['keyword_index'] + self.identifier_columns + [f'{col}_matched_texts' for col in self.text_columns]
                writer.writerow(headers)
            return
        
        try:
            # 使用pandas保存，处理中文编码
            df = pd.DataFrame(formatted_data)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"成功保存 {len(formatted_data)} 条匹配结果到 {output_path}")
            
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {e}")
            # 回退到基本的CSV写入
            self._save_to_csv_fallback(formatted_data, output_path)

    def _save_to_csv_fallback(self, formatted_data: List[Dict[str, Any]], output_path: str):
        """
        回退的CSV保存方法
        
        Args:
            formatted_data: 格式化后的数据
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if not formatted_data:
                    return
                
                # 获取所有字段名
                fieldnames = list(formatted_data[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 写入表头和数据
                writer.writeheader()
                writer.writerows(formatted_data)
                
            self.logger.info(f"使用回退方法成功保存 {len(formatted_data)} 条结果")
            
        except Exception as e:
            self.logger.error(f"回退CSV保存方法也失败: {e}")
            raise
    
    def generate_summary_report(self, matching_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成匹配结果摘要报告
        
        Args:
            matching_results: 匹配结果列表
            
        Returns:
            Dict[str, Any]: 摘要报告
        """
        report = {
            'total_processed': len(matching_results),
            'successful_matches': 0,
            'failed_matches': 0,
            'match_rate': 0.0,
            'column_match_stats': {},
            'processing_stats': self.stats.__dict__.copy()
        }
        
        # 统计成功和失败的匹配
        successful_results = []
        for result in matching_results:
            if result.get('match_success', False):
                report['successful_matches'] += 1
                successful_results.append(result)
            else:
                report['failed_matches'] += 1
        
        # 计算匹配率
        if report['total_processed'] > 0:
            report['match_rate'] = report['successful_matches'] / report['total_processed']
        
        # 统计各列的匹配情况
        for col in self.text_columns:
            col_matches = 0
            for result in successful_results:
                matched_texts = result.get('matched_texts', {})
                if matched_texts.get(col):
                    col_matches += 1
            
            report['column_match_stats'][col] = {
                'matches': col_matches,
                'rate': col_matches / len(successful_results) if successful_results else 0.0
            }
        
        return report
    
    def save_summary_report(self, report: Dict[str, Any], report_path: Optional[str] = None) -> str:
        """
        保存摘要报告到当前会话文件夹

        Args:
            report: 摘要报告数据
            report_path: 报告文件路径（可选）

        Returns:
            str: 报告文件路径
        """
        if not report_path:
            # 使用当前会话文件夹
            if hasattr(self, 'current_session_dir') and self.current_session_dir:
                report_path = str(self.current_session_dir / "matching_summary.json")
            else:
                # 回退到原有逻辑
                output_path = Path(self.output_file_path)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = str(output_path.parent / f"matching_summary_{timestamp}.json")
        
        try:
            import json
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"摘要报告已保存到: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"保存摘要报告失败: {e}")
            raise
    
    def get_processing_stats(self) -> ProcessingStats:
        """获取处理统计信息"""
        return self.stats


def test_result_processor():
    """测试结果处理器"""
    print("=" * 60)
    print("结果处理器测试")
    print("=" * 60)
    
    processor = ResultProcessor()
    
    # 测试数据
    test_results = [
        {
            'keyword_index': 0,
            'record_id': 'C001',
            'record_name': '记录A',
            'match_success': True,
            'matched_texts': {
                'company_profile': ['新能源汽车制造_like_新能源'],
                'main_product': ['电动汽车_must_汽车']
            }
        },
        {
            'keyword_index': 1,
            'record_id': 'C002',
            'record_name': '记录B',
            'match_success': False,
            'failure_reason': 'Must关键词未找到匹配'
        }
    ]
    
    # 处理和保存结果
    try:
        output_path = processor.process_and_save_results(test_results, 'test_results.csv')
        print(f"结果已保存到: {output_path}")
        
        # 生成摘要报告
        report = processor.generate_summary_report(test_results)
        print(f"\n摘要报告:")
        for key, value in report.items():
            print(f"  {key}: {value}")
        
        # 保存摘要报告
        report_path = processor.save_summary_report(report, 'test_summary.json')
        print(f"\n摘要报告已保存到: {report_path}")
        
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    test_result_processor()
