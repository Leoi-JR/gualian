#!/usr/bin/env python3
"""
RuleKit - 主入口文件
RuleKit - Main Entry Point

这是整个项目的统一入口点，提供对各个功能模块的访问
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入子功能模块
import cli.keyword_rules_validator_cli as keyword_rules_validator_cli
import cli.keyword_converter_cli as keyword_converter_cli
import cli.keyword_matcher_cli as keyword_matcher_cli
import cli.highlight_results_cli as highlight_results_cli


def check_first_run():
    """首次运行检测，引导新用户生成示例数据"""
    sample_xlsx = Path("sample_data/keyword_rules.xlsx")
    if not sample_xlsx.exists():
        print("=" * 60)
        print("🔧 首次使用检测")
        print("=" * 60)
        print("\n检测到尚未生成示例数据。首次使用请运行：")
        print("")
        print("  python scripts/generate_sample_data.py")
        print("")
        print("该脚本将生成虚构的示例文本数据和关键词规则表，")
        print("可用于测试和体验完整的工具流程。")
        print("")
        print("也可以直接使用文本数据，")
        print("或修改 config.json/example.json 中的路径配置。")
        print("=" * 60)


def show_main_menu():
    """显示主菜单"""
    print("=" * 60)
    print("RuleKit - 主菜单")
    print("=" * 60)
    print("\n请选择要使用的功能：\n")
    print("1. 关键词规则验证")
    print("2. 关键词模式转换")
    print("3. 智能关键词匹配")
    print("4. 匹配结果高亮导出")
    print("5. 退出程序")

    while True:
        try:
            choice = input("\n请输入选项编号 [1-5]: ")
            if choice in ['1', '2', '3', '4', '5']:
                return choice
            else:
                print("❌ 无效的选项，请重新输入")
        except KeyboardInterrupt:
            print("\n程序已中断")
            return '4'

def main():
    """主函数"""
    check_first_run()

    while True:
        choice = show_main_menu()

        if choice == '1':
            # 运行关键词规则验证器
            print("\n正在启动关键词规则验证器...\n")
            keyword_rules_validator_cli.main()
        elif choice == '2':
            # 运行关键词模式转换器
            print("\n正在启动关键词模式转换器...\n")
            keyword_converter_cli.main()
        elif choice == '3':
            # 运行智能关键词匹配器
            print("\n正在启动智能关键词匹配器...\n")
            keyword_matcher_cli.main()
        elif choice == '4':
            # 运行匹配结果高亮导出
            print("\n正在启动匹配结果高亮导出...\n")
            highlight_results_cli.main()
        elif choice == '5':
            print("\n感谢使用 RuleKit，再见！")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序执行出错：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)