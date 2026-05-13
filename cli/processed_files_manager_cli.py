#!/usr/bin/env python3
"""
已处理文件列表管理CLI工具

该工具提供命令行界面来管理批量处理中的已处理文件列表

功能:
1. 查看处理状态
2. 添加/移除已处理文件
3. 清空已处理文件列表
4. 启用/禁用跳过已处理文件功能
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.keyword_matcher import KeywordMatcher
from config import config_manager
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ProcessedFilesManager:
    """已处理文件列表管理器"""
    
    def __init__(self):
        """初始化管理器"""
        self.matcher = KeywordMatcher()
        self.logger = logging.getLogger(__name__)
    
    def show_status(self):
        """显示处理状态"""
        print("\n" + "=" * 80)
        print("文件处理状态")
        print("=" * 80)
        
        self.matcher.print_processing_status()
    
    def list_processed_files(self):
        """列出已处理文件"""
        processed_files = self.matcher.get_processed_files()
        
        print(f"\n已处理文件列表 ({len(processed_files)} 个):")
        print("-" * 50)
        
        if not processed_files:
            print("  (无已处理文件)")
        else:
            for i, file_name in enumerate(processed_files, 1):
                print(f"  {i:2d}. {Path(file_name).name}")
    
    def list_unprocessed_files(self):
        """列出未处理文件"""
        status = self.matcher.get_processing_status()
        unprocessed_files = status.get('unprocessed_files', [])
        
        print(f"\n未处理文件列表 ({len(unprocessed_files)} 个):")
        print("-" * 50)
        
        if not unprocessed_files:
            print("  (所有文件都已处理)")
        else:
            for i, file_name in enumerate(unprocessed_files, 1):
                print(f"  {i:2d}. {Path(file_name).name}")
    
    def add_processed_file(self, file_name: str):
        """添加已处理文件"""
        try:
            # 检查文件是否存在于可用文件列表中
            available_files = self.matcher.get_available_parquet_files()
            file_basename = Path(file_name).name
            
            # 查找匹配的文件
            matched_file = None
            for available_file in available_files:
                if file_name == available_file or file_basename == Path(available_file).name:
                    matched_file = available_file
                    break
            
            if not matched_file:
                print(f"❌ 文件不存在于可用文件列表中: {file_name}")
                return False
            
            if self.matcher.is_file_processed(matched_file):
                print(f"⚠️  文件已在已处理列表中: {Path(matched_file).name}")
                return False
            
            self.matcher.add_processed_file(matched_file)
            print(f"✅ 已添加文件到已处理列表: {Path(matched_file).name}")
            return True
            
        except Exception as e:
            print(f"❌ 添加文件失败: {e}")
            return False
    
    def remove_processed_file(self, file_name: str):
        """移除已处理文件"""
        try:
            processed_files = self.matcher.get_processed_files()
            file_basename = Path(file_name).name
            
            # 查找匹配的文件
            matched_file = None
            for processed_file in processed_files:
                if file_name == processed_file or file_basename == Path(processed_file).name:
                    matched_file = processed_file
                    break
            
            if not matched_file:
                print(f"❌ 文件不在已处理列表中: {file_name}")
                return False
            
            self.matcher.remove_processed_file(matched_file)
            print(f"✅ 已从已处理列表中移除文件: {Path(matched_file).name}")
            return True
            
        except Exception as e:
            print(f"❌ 移除文件失败: {e}")
            return False
    
    def clear_processed_files(self):
        """清空已处理文件列表"""
        try:
            processed_count = len(self.matcher.get_processed_files())
            
            if processed_count == 0:
                print("⚠️  已处理文件列表已为空")
                return
            
            # 确认操作
            response = input(f"确定要清空 {processed_count} 个已处理文件记录吗? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("操作已取消")
                return
            
            self.matcher.clear_processed_files()
            print(f"✅ 已清空 {processed_count} 个已处理文件记录")
            
        except Exception as e:
            print(f"❌ 清空操作失败: {e}")
    
    def toggle_skip_processed(self, enable: Optional[bool] = None):
        """切换跳过已处理文件功能"""
        try:
            current_status = config_manager.get_bool(
                'keyword_matching.parquet_data_source.batch_processing.processed_files.enable_skip_processed',
                True
            )
            
            if enable is None:
                new_status = not current_status
            else:
                new_status = enable
            
            config_manager.set_value(
                'keyword_matching.parquet_data_source.batch_processing.processed_files.enable_skip_processed',
                new_status
            )
            config_manager.save_config()
            
            status_text = "启用" if new_status else "禁用"
            print(f"✅ 已{status_text}跳过已处理文件功能")
            
        except Exception as e:
            print(f"❌ 切换功能失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="已处理文件列表管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s status                    # 显示处理状态
  %(prog)s list                      # 列出已处理文件
  %(prog)s list --unprocessed        # 列出未处理文件
  %(prog)s add file1.parquet         # 添加已处理文件
  %(prog)s remove file1.parquet      # 移除已处理文件
  %(prog)s clear                     # 清空已处理文件列表
  %(prog)s toggle                    # 切换跳过功能
  %(prog)s toggle --enable           # 启用跳过功能
  %(prog)s toggle --disable          # 禁用跳过功能
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status命令
    subparsers.add_parser('status', help='显示文件处理状态')
    
    # list命令
    list_parser = subparsers.add_parser('list', help='列出文件')
    list_parser.add_argument('--unprocessed', action='store_true', help='列出未处理文件')
    
    # add命令
    add_parser = subparsers.add_parser('add', help='添加已处理文件')
    add_parser.add_argument('file', help='要添加的文件名')
    
    # remove命令
    remove_parser = subparsers.add_parser('remove', help='移除已处理文件')
    remove_parser.add_argument('file', help='要移除的文件名')
    
    # clear命令
    subparsers.add_parser('clear', help='清空已处理文件列表')
    
    # toggle命令
    toggle_parser = subparsers.add_parser('toggle', help='切换跳过已处理文件功能')
    toggle_group = toggle_parser.add_mutually_exclusive_group()
    toggle_group.add_argument('--enable', action='store_true', help='启用跳过功能')
    toggle_group.add_argument('--disable', action='store_true', help='禁用跳过功能')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建管理器
    manager = ProcessedFilesManager()
    
    try:
        if args.command == 'status':
            manager.show_status()
        
        elif args.command == 'list':
            if args.unprocessed:
                manager.list_unprocessed_files()
            else:
                manager.list_processed_files()
        
        elif args.command == 'add':
            manager.add_processed_file(args.file)
        
        elif args.command == 'remove':
            manager.remove_processed_file(args.file)
        
        elif args.command == 'clear':
            manager.clear_processed_files()
        
        elif args.command == 'toggle':
            if args.enable:
                manager.toggle_skip_processed(True)
            elif args.disable:
                manager.toggle_skip_processed(False)
            else:
                manager.toggle_skip_processed()
    
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"❌ 执行命令时发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()