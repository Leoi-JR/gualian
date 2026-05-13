#!/usr/bin/env python3
"""
关键词匹配器 - CLI工具
Keyword Matcher - CLI Tool

该模块提供了智能关键词匹配功能的命令行界面，
实现choice=4的完整功能，支持交互式操作和批量处理。

功能描述：
1. 交互式选择输入文件和关键词文件
2. 配置匹配参数和输出选项
3. 执行完整的匹配流程
4. 显示详细的进度和结果统计

作者：系统开发
日期：2024年
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.keyword_matcher import KeywordMatcher
from config import config_manager


class KeywordMatcherCLI:
    """
    关键词匹配器CLI类
    
    提供交互式的命令行界面，引导用户完成关键词匹配的完整流程。
    """
    
    def __init__(self):
        """初始化CLI"""
        self.matcher = KeywordMatcher()
        self.logger = logging.getLogger(__name__)
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'keyword_matching_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
            ]
        )
    
    def show_welcome(self):
        """显示欢迎信息"""
        print("=" * 70)
        print("RuleKit — 规则驱动文本批量匹配工具")
        print("=" * 70)
        print("\n功能说明：")
        print("• 基于转换后的关键词规则表，对文本数据进行规则匹配和批量标注")
        print("• 支持前置类型筛选和字段范围控制")
        print("• 实现Like/Must/Unlike三步匹配逻辑")
        print("• 生成详细的匹配结果和统计报告")

        # 显示parquet数据源状态
        print("• 支持Parquet文件夹数据源")
        print(f"  - 文件夹1: {self.matcher.folder_path_1}")
        print(f"  - 文件夹2: {self.matcher.folder_path_2}")
        print(f"  - 合并列: {', '.join(self.matcher.merge_columns)}")

        print("\n" + "=" * 70)
    
    def get_input_file_path(self) -> str:
        """获取输入文件路径"""
        print("\n📁 请选择输入数据源：")

        while True:
            print("\n选项：")
            print("1. 手动输入文件路径")
            print("2. 从当前目录选择Excel文件")
            print("3. 从当前目录选择CSV文件")
            print("4. 从Parquet文件夹选择单个文件")
            print("5. 批量处理所有Parquet文件")
            print("6. 随机选择Parquet文件测试")

            choice = input("\n请选择 [1-6]: ").strip()
            
            if choice == '1':
                file_path = input("请输入完整文件路径: ").strip().strip('"\'')
                if Path(file_path).exists():
                    return file_path
                else:
                    print("❌ 文件不存在，请重新输入")
            
            elif choice == '2':
                excel_files = list(Path('.').glob('*.xlsx')) + list(Path('.').glob('*.xls'))
                if not excel_files:
                    print("❌ 当前目录没有找到Excel文件")
                    continue
                
                print("\n找到的Excel文件：")
                for i, file in enumerate(excel_files, 1):
                    print(f"{i}. {file.name}")
                
                try:
                    file_idx = int(input(f"\n请选择文件 [1-{len(excel_files)}]: ")) - 1
                    if 0 <= file_idx < len(excel_files):
                        return str(excel_files[file_idx])
                    else:
                        print("❌ 选择无效")
                except ValueError:
                    print("❌ 请输入有效数字")
            
            elif choice == '3':
                csv_files = list(Path('.').glob('*.csv'))
                if not csv_files:
                    print("❌ 当前目录没有找到CSV文件")
                    continue

                print("\n找到的CSV文件：")
                for i, file in enumerate(csv_files, 1):
                    print(f"{i}. {file.name}")

                try:
                    file_idx = int(input(f"\n请选择文件 [1-{len(csv_files)}]: ")) - 1
                    if 0 <= file_idx < len(csv_files):
                        return str(csv_files[file_idx])
                    else:
                        print("❌ 选择无效")
                except ValueError:
                    print("❌ 请输入有效数字")

            elif choice == '4':
                # 从Parquet文件夹选择单个文件
                try:
                    available_files = self.matcher.get_available_parquet_files()
                    if not available_files:
                        print("❌ 没有找到可用的Parquet文件")
                        print("   请检查配置的文件夹路径是否正确，以及是否包含同名的parquet文件")
                        continue
                except Exception as e:
                    print(f"❌ 获取Parquet文件列表失败: {e}")
                    continue

                print(f"\n找到的Parquet文件（共 {len(available_files)} 个）：")
                for i, file in enumerate(available_files, 1):
                    print(f"{i}. {file}")

                try:
                    file_idx = int(input(f"\n请选择文件 [1-{len(available_files)}]: ")) - 1
                    if 0 <= file_idx < len(available_files):
                        return available_files[file_idx]  # 返回文件名，不是完整路径
                    else:
                        print("❌ 选择无效")
                except ValueError:
                    print("❌ 请输入有效数字")

            elif choice == '5':
                # 批量处理模式
                try:
                    available_files = self.matcher.get_available_parquet_files()
                    if not available_files:
                        print("❌ 没有找到可用的Parquet文件，无法进行批处理")
                        continue
                    print(f"✓ 找到 {len(available_files)} 个可处理的Parquet文件")
                    return "BATCH_MODE"
                except Exception as e:
                    print(f"❌ 检查Parquet文件失败: {e}")
                    continue

            elif choice == '6':
                # 随机测试模式
                try:
                    test_file = self.matcher.get_random_parquet_file()
                    if not test_file:
                        print("❌ 没有找到可用的Parquet文件，无法进行随机测试")
                        continue
                    print(f"✓ 将随机测试文件: {test_file}")
                    return "RANDOM_TEST_MODE"
                except Exception as e:
                    print(f"❌ 选择随机测试文件失败: {e}")
                    continue

            else:
                print("❌ 无效选择，请重新输入")
    
    def get_keyword_file_path(self) -> Optional[str]:
        """获取关键词文件路径"""
        print("\n🔑 请选择关键词规则文件：")
        
        # 尝试自动检测
        auto_detected = self.matcher._auto_detect_keyword_file()
        if auto_detected:
            print(f"\n自动检测到关键词文件: {auto_detected}")
            use_auto = input("是否使用此文件？[Y/n]: ").strip().lower()
            if use_auto in ['', 'y', 'yes']:
                return auto_detected
        
        while True:
            print("\n选项：")
            print("1. 手动输入文件路径")
            print("2. 从当前目录选择转换后的关键词文件")
            
            choice = input("\n请选择 [1-2]: ").strip()
            
            if choice == '1':
                file_path = input("请输入完整文件路径: ").strip().strip('"\'')
                if Path(file_path).exists():
                    return file_path
                else:
                    print("❌ 文件不存在，请重新输入")
            
            elif choice == '2':
                keyword_files = list(Path('.').glob('converted_keyword_rules*.xlsx'))
                if not keyword_files:
                    print("❌ 当前目录没有找到转换后的关键词文件")
                    continue
                
                print("\n找到的关键词文件：")
                for i, file in enumerate(keyword_files, 1):
                    stat = file.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{i}. {file.name} (修改时间: {mod_time})")
                
                try:
                    file_idx = int(input(f"\n请选择文件 [1-{len(keyword_files)}]: ")) - 1
                    if 0 <= file_idx < len(keyword_files):
                        return str(keyword_files[file_idx])
                    else:
                        print("❌ 选择无效")
                except ValueError:
                    print("❌ 请输入有效数字")
            
            else:
                print("❌ 无效选择，请重新输入")
    
    def get_output_settings(self) -> Dict[str, str]:
        """获取输出设置"""
        print("\n💾 输出设置：")
        
        # 输出文件路径
        default_output = f"matching_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = input(f"输出文件路径 (默认: {default_output}): ").strip()
        if not output_path:
            output_path = default_output
        
        return {
            'output_path': output_path
        }
    
    def show_configuration_summary(self, input_file: str, keyword_file: str, output_settings: Dict[str, str]):
        """显示配置摘要"""
        print("\n" + "=" * 50)
        print("配置摘要")
        print("=" * 50)
        print(f"输入数据文件: {input_file}")
        print(f"关键词文件: {keyword_file}")
        print(f"输出文件: {output_settings['output_path']}")
        print("=" * 50)
        
        confirm = input("\n确认开始匹配？[Y/n]: ").strip().lower()
        return confirm in ['', 'y', 'yes']

    def show_results_summary(self, result_file: str, report_file: str):
        """显示结果摘要"""
        print("\n\n" + "=" * 60)
        print("匹配完成！")
        print("=" * 60)
        
        progress = self.matcher.get_progress_info()
        print(f"📊 处理统计:")
        print(f"  • 总组合数: {progress.total_combinations:,}")
        print(f"  • 成功匹配: {progress.successful_matches:,}")
        print(f"  • 失败匹配: {progress.failed_matches:,}")
        
        if progress.total_combinations > 0:
            success_rate = (progress.successful_matches / progress.total_combinations) * 100
            print(f"  • 成功率: {success_rate:.2f}%")
        
        print(f"\n📁 输出文件:")
        print(f"  • 匹配结果: {result_file}")
        print(f"  • 摘要报告: {report_file}")
        
        # 显示文件大小
        try:
            result_size = Path(result_file).stat().st_size
            report_size = Path(report_file).stat().st_size
            print(f"  • 结果文件大小: {result_size:,} 字节")
            print(f"  • 报告文件大小: {report_size:,} 字节")
        except Exception:
            pass
        
        print("=" * 60)

    def show_batch_results_summary(self, results: List[Tuple[str, str, str]], processing_time: float):
        """显示批处理结果摘要"""
        print("\n\n" + "=" * 70)
        print("批量处理完成！")
        print("=" * 70)

        print(f"📊 处理统计:")
        print(f"  • 总文件数: {len(results)}")
        print(f"  • 处理时间: {processing_time:.2f} 秒")
        print(f"  • 平均每文件: {processing_time/len(results):.2f} 秒" if results else "  • 平均每文件: N/A")

        print(f"\n📁 输出文件:")
        for i, (file_name, result_file, report_file) in enumerate(results, 1):
            print(f"  {i}. {file_name}")
            print(f"     结果: {result_file}")
            print(f"     报告: {report_file}")

        print("=" * 70)

    def show_test_results_summary(self, test_file: str, result_file: str, report_file: str, processing_time: float):
        """显示随机测试结果摘要"""
        print("\n\n" + "=" * 60)
        print("随机测试完成！")
        print("=" * 60)

        print(f"🎲 测试文件: {test_file}")
        print(f"⏱️ 处理时间: {processing_time:.2f} 秒")

        progress = self.matcher.get_progress_info()
        print(f"\n📊 处理统计:")
        print(f"  • 总组合数: {progress.total_combinations:,}")
        print(f"  • 成功匹配: {progress.successful_matches:,}")
        print(f"  • 失败匹配: {progress.failed_matches:,}")

        if progress.total_combinations > 0:
            success_rate = (progress.successful_matches / progress.total_combinations) * 100
            print(f"  • 成功率: {success_rate:.2f}%")

        print(f"\n📁 输出文件:")
        print(f"  • 匹配结果: {result_file}")
        print(f"  • 摘要报告: {report_file}")

        # 显示文件大小
        try:
            result_size = Path(result_file).stat().st_size
            report_size = Path(report_file).stat().st_size
            print(f"  • 结果文件大小: {result_size:,} 字节")
            print(f"  • 报告文件大小: {report_size:,} 字节")
        except Exception:
            pass

        print("=" * 60)
    
    def run(self):
        """运行CLI主流程"""
        try:
            # 显示欢迎信息
            self.show_welcome()

            # 获取输入文件或模式
            input_selection = self.get_input_file_path()

            # 获取关键词文件
            keyword_file = self.get_keyword_file_path()

            # 根据选择的模式执行不同的处理
            if input_selection == "BATCH_MODE":
                self.run_batch_mode(keyword_file)
            elif input_selection == "RANDOM_TEST_MODE":
                self.run_random_test_mode(keyword_file)
            else:
                self.run_single_file_mode(input_selection, keyword_file)

        except KeyboardInterrupt:
            print("\n\n操作已中断")
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            self.logger.error(f"CLI执行失败: {e}", exc_info=True)

    def run_single_file_mode(self, input_file: str, keyword_file: str):
        """运行单文件处理模式"""
        # 获取输出设置
        output_settings = self.get_output_settings()

        # 显示配置摘要并确认
        if not self.show_configuration_summary(input_file, keyword_file, output_settings):
            print("操作已取消")
            return

        # 开始执行匹配（进度条将在匹配器内部自动显示）
        print("\n开始执行匹配...")

        # 执行匹配
        result_file, report_file = self.matcher.run_complete_matching(
            input_file_path=input_file,
            keyword_file_path=keyword_file,
            output_file_path=output_settings['output_path']
        )

        # 显示结果摘要
        self.show_results_summary(result_file, report_file)

    def run_batch_mode(self, keyword_file: str):
        """运行批处理模式"""
        print("\n🔄 批量处理模式")
        print("=" * 50)

        # 获取输出基础路径
        output_base = input("输出文件基础名称 (默认: batch_results): ").strip()
        if not output_base:
            output_base = "batch_results"

        # 确认开始批处理
        available_files = self.matcher.get_available_parquet_files()
        print(f"\n将处理 {len(available_files)} 个Parquet文件")
        confirm = input("确认开始批量处理？[Y/n]: ").strip().lower()
        if confirm not in ['', 'y', 'yes']:
            print("操作已取消")
            return

        print("\n开始批量处理...")
        start_time = datetime.now()

        try:
            results = self.matcher.run_batch_processing(
                keyword_file_path=keyword_file,
                output_base_path=output_base
            )

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # 显示批处理结果摘要
            self.show_batch_results_summary(results, processing_time)

        except Exception as e:
            print(f"\n❌ 批处理失败: {e}")
            self.logger.error(f"批处理失败: {e}", exc_info=True)

    def run_random_test_mode(self, keyword_file: str):
        """运行随机测试模式"""
        print("\n🎲 随机测试模式")
        print("=" * 50)

        # 获取输出文件路径
        output_file = input("输出文件路径 (默认: 自动生成): ").strip()
        if not output_file:
            output_file = None

        # 确认开始测试
        confirm = input("确认开始随机测试？[Y/n]: ").strip().lower()
        if confirm not in ['', 'y', 'yes']:
            print("操作已取消")
            return

        print("\n开始随机测试...")
        start_time = datetime.now()

        try:
            test_file, result_file, report_file = self.matcher.run_random_test(
                keyword_file_path=keyword_file,
                output_file_path=output_file
            )

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # 显示测试结果摘要
            self.show_test_results_summary(test_file, result_file, report_file, processing_time)

        except Exception as e:
            print(f"\n❌ 随机测试失败: {e}")
            self.logger.error(f"随机测试失败: {e}", exc_info=True)


def main():
    """主函数"""
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
        
        # 运行CLI
        cli = KeywordMatcherCLI()
        cli.run()
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序执行出错：{e}")
        return 1


def show_help():
    """显示帮助信息"""
    help_text = """
智能关键词匹配器 - 使用帮助

用法:
    python keyword_matcher_cli.py              # 运行交互式匹配
    python keyword_matcher_cli.py --help       # 显示帮助

功能说明:
    基于转换后的关键词规则表，对文本数据进行规则匹配和批量标注

    匹配流程:
    1. 前置类型筛选 - 基于 type_filter 和 category_code 进行预筛选
    2. 字段范围控制 - 基于 field_scope 控制参与匹配的文本列
    3. Like关键词匹配 - 检查是否存在，记录匹配信息
    4. Must关键词匹配 - 检查是否存在，记录匹配信息  
    5. Unlike关键词匹配 - 检查是否存在，如存在则匹配失败

配置文件: config.json
日志文件: keyword_matching_YYYYMMDD.log
"""
    print(help_text)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        show_help()
    else:
        sys.exit(main())
