"""
配置管理器 - Configuration Manager

功能描述：
- 支持JSON配置文件的读取和管理
- 提供类型安全的配置获取方法
- 支持配置验证和默认值
- 向后兼容原有的.env配置方式

作者：系统重构
日期：2024年
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

class ConfigManager:
    """配置管理器类 - 支持JSON和ENV两种配置方式"""
    
    def __init__(self, config_file: str = "config.json", load_env: bool = True):
        """
        初始化配置管理器
        
        Args:
            config_file (str): JSON配置文件路径
            load_env (bool): 是否同时加载.env文件
        """
        self.config_file = config_file
        self.config_data = {}
        self.env_loaded = False
        
        # 加载配置
        self._load_config()
        
        if load_env:
            self._load_env()
    
    def _load_config(self):
        """加载JSON配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                # 尝试回退到示例配置文件
                example_file = "config.example.json"
                if os.path.exists(example_file):
                    print(f"ℹ️ {self.config_file} 不存在，使用 {example_file} 作为配置")
                    print(f"   提示：可将 {example_file} 复制为 {self.config_file} 后进行自定义")
                    with open(example_file, 'r', encoding='utf-8') as f:
                        self.config_data = json.load(f)
                else:
                    print(f"⚠️ 配置文件不存在: {self.config_file}")
                    self.config_data = {}
        except json.JSONDecodeError as e:
            print(f"❌ JSON配置文件格式错误: {e}")
            self.config_data = {}
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            self.config_data = {}
    
    def _load_env(self):
        """加载.env环境变量（向后兼容）"""
        try:
            load_dotenv(override=True)
            self.env_loaded = True
        except Exception as e:
            print(f"⚠️ 加载环境变量失败: {e}")
    
    def _get_nested_value(self, path: str, default: Any = None) -> Any:
        """
        获取嵌套路径的配置值
        
        Args:
            path (str): 配置路径，用.分隔，如 "excel.file_path"
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        keys = path.split('.')
        current = self.config_data
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except (KeyError, TypeError):
            return default
    
    def get_str(self, key: str, default: str = '') -> str:
        """
        获取字符串类型的配置
        
        Args:
            key (str): 配置键名或路径
            default (str): 默认值
            
        Returns:
            str: 配置值
        """
        # 首先尝试从JSON配置获取
        value = self._get_nested_value(key)
        if value is not None:
            return str(value)
        
        # 回退到环境变量（向后兼容）
        if self.env_loaded:
            env_value = os.getenv(key.upper().replace('.', '_'), default)
            return env_value.strip() if isinstance(env_value, str) else str(env_value)
        
        return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        获取整数类型的配置
        
        Args:
            key (str): 配置键名或路径
            default (int): 默认值
            
        Returns:
            int: 配置值
        """
        value = self._get_nested_value(key)
        if value is not None:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        # 回退到环境变量
        if self.env_loaded:
            try:
                env_value = os.getenv(key.upper().replace('.', '_'), str(default))
                return int(env_value.strip())
            except (ValueError, TypeError):
                return default
        
        return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        获取浮点数类型的配置
        
        Args:
            key (str): 配置键名或路径
            default (float): 默认值
            
        Returns:
            float: 配置值
        """
        value = self._get_nested_value(key)
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        获取布尔类型的配置
        
        Args:
            key (str): 配置键名或路径
            default (bool): 默认值
            
        Returns:
            bool: 配置值
        """
        value = self._get_nested_value(key)
        if value is not None:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        
        return default
    
    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """
        获取列表类型的配置
        
        Args:
            key (str): 配置键名或路径
            default (List): 默认值
            
        Returns:
            List: 配置值
        """
        if default is None:
            default = []
        
        value = self._get_nested_value(key)
        if value is not None:
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                # 支持逗号分隔的字符串（向后兼容）
                return [x.strip() for x in value.split(',') if x.strip()]
        
        # 回退到环境变量
        if self.env_loaded:
            env_value = os.getenv(key.upper().replace('.', '_'), '')
            if env_value:
                return [x.strip() for x in env_value.split(',') if x.strip()]
        
        return default
    
    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
        """
        获取字典类型的配置
        
        Args:
            key (str): 配置键名或路径
            default (Dict): 默认值
            
        Returns:
            Dict: 配置值
        """
        if default is None:
            default = {}
        
        value = self._get_nested_value(key)
        if value is not None:
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return default
        
        # 回退到环境变量
        if self.env_loaded:
            env_value = os.getenv(key.upper().replace('.', '_'), '')
            if env_value:
                try:
                    return json.loads(env_value)
                except json.JSONDecodeError:
                    return default
        
        return default
    
    def get_config_section(self, section: str) -> Dict:
        """
        获取整个配置段
        
        Args:
            section (str): 配置段名称
            
        Returns:
            Dict: 配置段内容
        """
        return self._get_nested_value(section, {})
    
    def reload_config(self):
        """重新加载配置文件"""
        self._load_config()
        if self.env_loaded:
            self._load_env()
    
    def validate_config(self) -> Dict[str, Any]:
        """
        验证配置完整性
        
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查必需的配置项
        required_configs = [
            'excel.file_path',
            'excel.sheet_name',
            'keyword_columns'
        ]
        
        for config_key in required_configs:
            value = self._get_nested_value(config_key)
            if value is None or value == '':
                validation_result['valid'] = False
                validation_result['errors'].append(f"缺少必需配置项: {config_key}")
        
        # 检查文件路径是否存在
        excel_path = self.get_str('excel.file_path')
        if excel_path and not os.path.exists(excel_path):
            validation_result['warnings'].append(f"Excel文件不存在: {excel_path}")
        
        # 检查关键词列配置
        keyword_columns = self.get_list('keyword_columns')
        if not keyword_columns:
            validation_result['errors'].append("关键词列配置为空")
        
        return validation_result
    
    def get_all_configs(self) -> Dict:
        """获取所有配置项（用于调试）"""
        return self.config_data.copy()


# 创建全局配置实例（向后兼容）
config_manager = ConfigManager()

class Config:
    """
    向后兼容的Config类
    保持原有API不变，内部使用新的ConfigManager
    """
    
    @staticmethod
    def get_str(key: str, default: str = '') -> str:
        """获取字符串类型的配置（向后兼容）"""
        return config_manager.get_str(key, default)
    
    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        """获取整数类型的配置（向后兼容）"""
        return config_manager.get_int(key, default)
    
    @staticmethod
    def get_list(key: str, default: str = '') -> List[str]:
        """获取列表类型的配置（向后兼容）"""
        if default:
            default_list = [x.strip() for x in default.split(',') if x.strip()]
        else:
            default_list = []
        return config_manager.get_list(key, default_list)
    
    @staticmethod
    def get_dict(key: str, default: Dict = None) -> Dict:
        """获取字典类型的配置（向后兼容）"""
        return config_manager.get_dict(key, default or {})


# 使用示例和测试函数
def test_configuration():
    """测试配置管理器功能"""
    print("=" * 60)
    print("配置管理器测试")
    print("=" * 60)
    
    # 测试各种配置获取
    print("\n基本配置测试:")
    print(f"Excel文件路径: {config_manager.get_str('excel.file_path')}")
    print(f"工作表名称: {config_manager.get_str('excel.sheet_name')}")
    print(f"关键词列: {config_manager.get_list('keyword_columns')}")
    
    print("\n嵌套配置测试:")
    print(f"列映射: {config_manager.get_dict('column_mappings')}")
    print(f"验证规则: {config_manager.get_dict('validation_rules')}")
    
    print("\n配置验证:")
    validation = config_manager.validate_config()
    if validation['valid']:
        print("✓ 配置验证通过")
    else:
        print("❌ 配置验证失败:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if validation['warnings']:
        print("⚠️ 警告:")
        for warning in validation['warnings']:
            print(f"  - {warning}")


if __name__ == "__main__":
    test_configuration()