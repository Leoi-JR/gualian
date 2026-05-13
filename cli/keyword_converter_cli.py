#!/usr/bin/env python3
"""
关键词转换器 - CLI工具
Keyword Converter - CLI Tool

该模块提供了读取和处理Excel文件中关键词数据的功能。
主要用于将验证通过的关键词规则表转换为用于正则表达式匹配的格式。

功能描述：
1. 读取验证通过的关键词规则Excel文件
2. 使用PatternTransformer进行模式转换
3. 生成转换后的新Excel文件
4. 支持批量处理多个关键词列

作者：系统重构
日期：2024年
"""

import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.pattern_transformer import PatternTransformer
from config import config_manager


class KeywordConverter:
    """
    关键词转换器类
    
    该类提供了读取Excel文件并处理关键词数据的功能。
    可以处理指定sheet中的关键词列，并进行模式转换。
    """
    
    def __init__(self, source_file_path: Optional[str] = None):
        """
        初始化关键词转换器
        
        Args:
            source_file_path (str, optional): 源Excel文件的路径，如果为None则自动检测
        """
        # 首先从配置获取参数
        self.keyword_columns = config_manager.get_list('keyword_columns')
        self.sheet_name = config_manager.get_str('excel.sheet_name', '原版')
        self.output_file_path = config_manager.get_str('pattern_conversion.output_file_path', 'converted_keyword_rules.xlsx')
        self.output_sheet_name = config_manager.get_str('pattern_conversion.output_sheet_name', '转换后规则')
        self.column_prefix = config_manager.get_str('pattern_conversion.column_prefix', 'converted')
        self.enable_logging = config_manager.get_bool('pattern_conversion.enable_logging', True)
        
        # 设置日志（必须在调用其他方法之前设置）
        if self.enable_logging:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.disabled = True
        
        # 现在可以安全地调用需要logger的方法
        self.source_file_path = self._determine_source_file(source_file_path)
        self.transformer = PatternTransformer()
    
    def _determine_source_file(self, source_file_path: Optional[str]) -> str:
        """
        确定源文件路径
        
        Args:
            source_file_path (str, optional): 用户指定的源文件路径
            
        Returns:
            str: 确定的源文件路径
        """
        if source_file_path:
            return source_file_path
        
        # 检查配置中的自动检测设置
        auto_detect = config_manager.get_str('pattern_conversion.source_file_path', 'auto_detect')
        
        if auto_detect == 'auto_detect':
            # 自动检测最新的高亮文件
            base_path = config_manager.get_str('excel.file_path', '')
            if base_path:
                base_dir = os.path.dirname(base_path)
                base_name = os.path.splitext(os.path.basename(base_path))[0]
                
                # 查找最新的高亮文件
                pattern = f"{base_name}_checked_highlighted_*.xlsx"
                import glob
                files = glob.glob(os.path.join(base_dir, pattern))
                if files:
                    # 按修改时间排序，取最新的
                    latest_file = max(files, key=os.path.getmtime)
                    self.logger.info(f"自动检测到最新的验证文件: {latest_file}")
                    return latest_file
                else:
                    # 如果没有找到高亮文件，使用原文件
                    self.logger.warning("未找到验证高亮文件，使用原始文件")
                    return base_path
            else:
                raise ValueError("配置中未找到有效的Excel文件路径")
        else:
            return auto_detect
    
    def process_keywords(self) -> Optional[pd.DataFrame]:
        """
        处理关键词数据
        
        Returns:
            pandas.DataFrame: 处理后的数据表，如果失败则返回None
        """
        try:
            # 验证源文件是否存在
            if not os.path.exists(self.source_file_path):
                raise FileNotFoundError(f"源文件不存在: {self.source_file_path}")
            
            self.logger.info(f"开始处理文件: {self.source_file_path}")
            
            # 读取Excel文件
            df = pd.read_excel(self.source_file_path, sheet_name=self.sheet_name)
            self.logger.info(f"成功读取Excel文件，共 {len(df)} 行数据")
            
            # 检查必需的列是否存在
            missing_columns = [col for col in self.keyword_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Excel文件中缺少以下列: {missing_columns}")
            
            # 处理关键词列
            conversion_stats = {'success': 0, 'failed': 0, 'empty': 0}

            for col in self.keyword_columns:
                if col in df.columns:
                    # 首先将关键词列中的字母转换为小写
                    self.logger.info(f"开始处理列: {col} - 转换字母为小写")
                    df[col] = df[col].apply(self._convert_to_lowercase)

                    # 创建新列名
                    new_col = f'{self.column_prefix}_{col}'
                    self.logger.info(f"开始转换列: {col} -> {new_col}")

                    # 处理每一行数据
                    df[new_col] = df[col].apply(lambda x: self._transform_value(x, conversion_stats))

                    self.logger.info(f"列 {col} 转换完成")
            
            # 输出转换统计信息
            total_cells = conversion_stats['success'] + conversion_stats['failed'] + conversion_stats['empty']
            self.logger.info(f"转换统计: 总计 {total_cells} 个单元格, "
                           f"成功 {conversion_stats['success']}, "
                           f"失败 {conversion_stats['failed']}, "
                           f"空值 {conversion_stats['empty']}")
            
            return df
            
        except Exception as e:
            self.logger.error(f'处理Excel文件时发生错误：{str(e)}')
            return None
    
    def _convert_to_lowercase(self, value: Any) -> Any:
        """
        将关键词列中的字母转换为小写

        Args:
            value: 单元格的值

        Returns:
            Any: 转换后的值（字母转为小写，其他字符保持不变）
        """
        # 处理空值
        if pd.isna(value) or value == 0 or value == '0' or value == '':
            return value

        try:
            # 将字符串中的字母转换为小写，保持其他字符不变
            return str(value).lower()
        except Exception as e:
            self.logger.warning(f'转换小写时发生错误：{str(e)}, 原值: {value}')
            return value

    def _transform_value(self, value: Any, stats: Dict[str, int]) -> str:
        """
        转换单个单元格的值

        Args:
            value: 单元格的值
            stats: 统计信息字典

        Returns:
            str: 转换后的值
        """
        # 处理空值或0值
        if pd.isna(value) or value == 0 or value == '0' or value == '':
            stats['empty'] += 1
            return '0'
        
        try:
            # 转换关键词模式
            results = self.transformer.transform(str(value))
            if not results:
                stats['failed'] += 1
                return '0'
            
            # 将结果转换为字符串并用'|'连接
            result_str = '|'.join(map(str, results))
            stats['success'] += 1
            return result_str
            
        except Exception as e:
            self.logger.warning(f'转换值时发生错误：{str(e)}, 原值: {value}')
            stats['failed'] += 1
            return '0'
    
    def save_results(self, df: pd.DataFrame) -> str:
        """
        保存转换结果到Excel文件
        
        Args:
            df: 转换后的数据框
            
        Returns:
            str: 保存的文件路径
        """
        try:
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name, ext = os.path.splitext(self.output_file_path)
            output_path = f"{base_name}_{timestamp}{ext}"
            
            # 保存到Excel文件
            df.to_excel(output_path, index=False, sheet_name=self.output_sheet_name)
            
            self.logger.info(f"转换结果已保存到: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f'保存文件时发生错误：{str(e)}')
            raise
    
    def convert_and_save(self) -> Optional[str]:
        """
        执行完整的转换和保存流程
        
        Returns:
            str: 保存的文件路径，如果失败则返回None
        """
        try:
            # 处理关键词
            df = self.process_keywords()
            if df is None:
                return None
            
            # 保存结果
            output_path = self.save_results(df)
            return output_path
            
        except Exception as e:
            self.logger.error(f'转换和保存流程失败：{str(e)}')
            return None


def main():
    """主函数 - 运行关键词转换"""
    print("=" * 60)
    print("关键词转换器")
    print("=" * 60)
    
    try:
        # 验证配置
        validation_result = config_manager.validate_config()
        if not validation_result['valid']:
            print("❌ 配置验证失败：")
            for error in validation_result['errors']:
                print(f"  - {error}")
            return 1
        
        if validation_result['warnings']:
            print("⚠️ 配置警告：")
            for warning in validation_result['warnings']:
                print(f"  - {warning}")
            print()
        
        # 创建转换器并运行转换
        converter = KeywordConverter()
        
        print("开始转换关键词规则...")
        output_path = converter.convert_and_save()
        
        if output_path:
            print(f"✓ 转换完成！")
            print(f"转换后的文件已保存到: {output_path}")
        else:
            print("❌ 转换失败！")
            return 1
            
    except Exception as e:
        print(f"❌ 程序执行出错：{e}")
        return 1
    
    return 0


def show_help():
    """显示帮助信息"""
    help_text = """
关键词转换器 - 使用帮助

用法:
    python keyword_converter_cli.py              # 运行转换
    python keyword_converter_cli.py --help       # 显示帮助
    python keyword_converter_cli.py --test       # 运行测试模式

功能说明:
    将验证通过的关键词规则表转换为用于正则表达式匹配的格式
    
    转换格式:
    - 单个关键词: 直接匹配
    - 有序匹配: 左边关键词必须在右边关键词之前
    - 无序匹配: 左右关键词可以交替出现

配置文件: config.json
转换规则: 详见 core/pattern_transformer.py 模块
"""
    print(help_text)


def run_tests():
    """运行测试模式"""
    print("=" * 60)
    print("测试模式")
    print("=" * 60)
    
    from core.pattern_transformer import test_transformer
    test_transformer()


if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['--help', '-h', 'help']:
            show_help()
            sys.exit(0)
        elif arg in ['--test', '-t', 'test']:
            run_tests()
            sys.exit(0)
        else:
            print(f"未知参数: {arg}")
            print("使用 --help 查看帮助信息")
            sys.exit(1)
    
    # 运行主程序
    exit_code = main()
    sys.exit(exit_code) 