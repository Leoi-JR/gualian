#!/usr/bin/env python3
"""
筛选逻辑模块
Filter Logic Module

该模块实现行业类型筛选和数据源范围筛选逻辑，
支持多种筛选条件组合，为关键词匹配提供预筛选功能。

筛选规则：
1. 类型筛选：基于 type_filter 和 category_code 进行匹配
2. 字段范围筛选：基于 field_scope 控制参与匹配的文本列

作者：系统开发
日期：2024年
"""

import logging
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config_manager


@dataclass
class FilterResult:
    """筛选结果数据类"""
    passed: bool
    reason: Optional[str] = None
    filtered_columns: Optional[List[str]] = None


class FilterLogic:
    """
    筛选逻辑类
    
    负责实现行业类型和数据源范围的筛选逻辑，
    为关键词匹配提供高效的预筛选功能。
    """
    
    def __init__(self):
        """初始化筛选逻辑"""
        self.logger = logging.getLogger(__name__)
        
        # 从配置获取筛选规则
        self.industry_config = config_manager.get_dict('keyword_matching.matching_rules.industry_filter')
        self.source_scope_config = config_manager.get_dict('keyword_matching.matching_rules.source_scope_filter')
        
        # 获取文本列定义
        self.text_columns = config_manager.get_list('keyword_matching.input_table_columns.text_content_columns')
        
        # 预处理except映射
        self.except_mappings = self.source_scope_config.get('except_mappings', {})
        
        self.logger.info("筛选逻辑初始化完成")
    
    def apply_industry_filter(self, keyword_industry_type: str, input_industry_code: str) -> FilterResult:
        """
        应用行业类型筛选
        
        Args:
            keyword_industry_type: 关键词规则中的行业类型
            input_industry_code: 输入数据中的行业代码
            
        Returns:
            FilterResult: 筛选结果
        """
        if not self.industry_config.get('enable', True):
            return FilterResult(passed=True, reason="行业筛选已禁用")
        
        # 处理空值
        if not keyword_industry_type or not input_industry_code:
            return FilterResult(
                passed=False, 
                reason=f"行业信息缺失: keyword_type={keyword_industry_type}, input_code={input_industry_code}"
            )
        
        keyword_industry_type = str(keyword_industry_type).strip()
        input_industry_code = str(input_industry_code).strip()
        
        # 检查默认值
        default_value = self.industry_config.get('default_value', 'default')
        if keyword_industry_type == default_value:
            return FilterResult(passed=True, reason="使用默认行业类型，跳过筛选")
        
        # 解析行业类型列表
        separator = self.industry_config.get('separator', '、')
        industry_types = [t.strip() for t in keyword_industry_type.split(separator) if t.strip()]
        
        if not industry_types:
            return FilterResult(passed=False, reason="行业类型列表为空")
        
        # 检查输入的行业代码是否在允许的类型中
        if input_industry_code in industry_types:
            return FilterResult(passed=True, reason=f"行业代码匹配: {input_industry_code}")
        
        return FilterResult(
            passed=False, 
            reason=f"行业代码不匹配: {input_industry_code} 不在 {industry_types} 中"
        )
    
    def apply_source_scope_filter(self, source_scope: str) -> FilterResult:
        """
        应用数据源范围筛选
        
        Args:
            source_scope: 关键词规则中的数据源范围
            
        Returns:
            FilterResult: 筛选结果，包含过滤后的列列表
        """
        if not self.source_scope_config.get('enable', True):
            return FilterResult(
                passed=True, 
                reason="数据源筛选已禁用",
                filtered_columns=self.text_columns.copy()
            )
        
        # 处理空值
        if not source_scope:
            return FilterResult(
                passed=False,
                reason="数据源范围信息缺失"
            )
        
        source_scope = str(source_scope).strip()
        
        # 检查默认值
        default_value = self.source_scope_config.get('default_value', 'default')
        if source_scope == default_value:
            return FilterResult(
                passed=True,
                reason="使用默认数据源范围，包含所有文本列",
                filtered_columns=self.text_columns.copy()
            )
        
        # 解析数据源范围
        separator = self.source_scope_config.get('separator', '、')
        scope_items = [item.strip() for item in source_scope.split(separator) if item.strip()]
        
        # 获取需要排除的列
        excluded_columns = set()
        for scope_item in scope_items:
            if scope_item in self.except_mappings:
                excluded_columns.update(self.except_mappings[scope_item])
            else:
                self.logger.warning(f"未知的字段范围类型: {scope_item}")
        
        # 计算过滤后的列
        filtered_columns = [col for col in self.text_columns if col not in excluded_columns]
        
        if not filtered_columns:
            return FilterResult(
                passed=False,
                reason="所有文本列都被排除"
            )
        
        return FilterResult(
            passed=True,
            reason=f"数据源筛选完成，排除列: {list(excluded_columns)}",
            filtered_columns=filtered_columns
        )
    
    def apply_combined_filter(self, keyword_row: Dict[str, Any], input_row: Dict[str, Any]) -> FilterResult:
        """
        应用组合筛选（行业类型 + 数据源范围）
        
        Args:
            keyword_row: 关键词规则行数据
            input_row: 输入数据行数据
            
        Returns:
            FilterResult: 组合筛选结果
        """
        # 获取筛选字段
        keyword_industry_type = keyword_row.get('type_filter', '')
        input_industry_code = input_row.get('category_code', '')
        source_scope = keyword_row.get('field_scope', '')
        
        # 应用行业类型筛选
        industry_result = self.apply_industry_filter(keyword_industry_type, input_industry_code)
        if not industry_result.passed:
            return FilterResult(
                passed=False,
                reason=f"行业筛选失败: {industry_result.reason}"
            )
        
        # 应用数据源范围筛选
        source_result = self.apply_source_scope_filter(source_scope)
        if not source_result.passed:
            return FilterResult(
                passed=False,
                reason=f"数据源筛选失败: {source_result.reason}"
            )
        
        return FilterResult(
            passed=True,
            reason=f"组合筛选通过: {industry_result.reason}; {source_result.reason}",
            filtered_columns=source_result.filtered_columns
        )
    
    def batch_filter(self, keyword_rows: List[Dict[str, Any]], input_row: Dict[str, Any]) -> List[FilterResult]:
        """
        批量筛选
        
        Args:
            keyword_rows: 关键词规则行列表
            input_row: 输入数据行
            
        Returns:
            List[FilterResult]: 筛选结果列表
        """
        results = []
        for keyword_row in keyword_rows:
            result = self.apply_combined_filter(keyword_row, input_row)
            results.append(result)
        
        return results
    
    def get_valid_text_columns(self, source_scope: str) -> List[str]:
        """
        获取有效的文本列列表
        
        Args:
            source_scope: 数据源范围
            
        Returns:
            List[str]: 有效的文本列列表
        """
        result = self.apply_source_scope_filter(source_scope)
        if result.passed and result.filtered_columns:
            return result.filtered_columns
        return []
    
    def validate_filter_config(self) -> Dict[str, Any]:
        """
        验证筛选配置
        
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查行业筛选配置
        if not self.industry_config:
            validation_result['errors'].append("缺少行业筛选配置")
            validation_result['valid'] = False
        
        # 检查数据源筛选配置
        if not self.source_scope_config:
            validation_result['errors'].append("缺少数据源筛选配置")
            validation_result['valid'] = False
        
        # 检查文本列配置
        if not self.text_columns:
            validation_result['errors'].append("缺少文本列配置")
            validation_result['valid'] = False
        
        # 检查except映射
        for except_type, columns in self.except_mappings.items():
            for column in columns:
                if column not in self.text_columns:
                    validation_result['warnings'].append(
                        f"except映射中的列 '{column}' 不在文本列配置中"
                    )
        
        return validation_result


def test_filter_logic():
    """测试筛选逻辑"""
    print("=" * 60)
    print("筛选逻辑测试")
    print("=" * 60)
    
    filter_logic = FilterLogic()
    
    # 测试行业类型筛选
    print("\n1. 行业类型筛选测试:")
    test_cases = [
        ("default", "123", "默认值测试"),
        ("123、456、789", "456", "匹配测试"),
        ("123、456、789", "999", "不匹配测试"),
        ("", "123", "空值测试"),
    ]
    
    for keyword_type, input_code, desc in test_cases:
        result = filter_logic.apply_industry_filter(keyword_type, input_code)
        print(f"{desc}: {result.passed} - {result.reason}")
    
    # 测试数据源范围筛选
    print("\n2. 数据源范围筛选测试:")
    test_cases = [
        ("default", "默认值测试"),
        ("scope_a", "排除范围A测试"),
        ("scope_b", "排除范围B测试"),
        ("scope_a、scope_b", "组合排除测试"),
    ]

    for field_scope, desc in test_cases:
        result = filter_logic.apply_source_scope_filter(field_scope)
        print(f"{desc}: {result.passed} - {result.reason}")
        if result.filtered_columns:
            print(f"  过滤后列数: {len(result.filtered_columns)}")
    
    # 测试组合筛选
    print("\n3. 组合筛选测试:")
    keyword_row = {
        'type_filter': '123、456',
        'field_scope': 'scope_a'
    }
    input_row = {
        'category_code': '456'
    }
    
    result = filter_logic.apply_combined_filter(keyword_row, input_row)
    print(f"组合筛选: {result.passed} - {result.reason}")
    if result.filtered_columns:
        print(f"可用文本列数: {len(result.filtered_columns)}")
    
    # 验证配置
    print("\n4. 配置验证:")
    validation = filter_logic.validate_filter_config()
    print(f"配置有效: {validation['valid']}")
    if validation['errors']:
        print(f"错误: {validation['errors']}")
    if validation['warnings']:
        print(f"警告: {validation['warnings']}")


if __name__ == "__main__":
    test_filter_logic()
