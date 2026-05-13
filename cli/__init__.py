"""
CLI工具包
Command Line Interface Tools Package
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from .keyword_rules_validator_cli import main as validate_rules
    from .keyword_converter_cli import main as convert_keywords
    
    __all__ = ['validate_rules', 'convert_keywords']
except ImportError as e:
    print(f"警告: CLI模块导入失败: {e}")
    __all__ = [] 