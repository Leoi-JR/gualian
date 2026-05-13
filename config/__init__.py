"""
配置管理包 - Configuration Package

提供项目的配置管理功能
"""

from .manager import ConfigManager, config_manager, Config

__all__ = ['ConfigManager', 'config_manager', 'Config'] 