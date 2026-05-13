#!/usr/bin/env python3
"""
关键词编译器模块
Keyword Compiler Module

该模块负责将转换后的关键词编译为正则表达式并缓存，
支持3种匹配格式的高效处理，提供性能优化的关键词匹配功能。

转换格式说明：
- 格式0: [0, "关键词"] - 直接字符串匹配
- 格式1: [1, ["左关键词"], ["右关键词"], 最小间隔, 最大间隔] - 有序匹配
- 格式2: [2, ["关键词组1"], ["关键词组2"], 最小间隔, 最大间隔] - 无序匹配

作者：系统开发
日期：2024年
"""

import re
import logging
import hashlib
from typing import Dict, List, Union, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config_manager


@dataclass
class CompiledPattern:
    """编译后的模式数据类 - 🚀 性能优化版本"""
    pattern_type: int
    regex_pattern: Optional[re.Pattern] = None
    keywords: Optional[List[str]] = None
    original_data: Optional[Any] = None
    is_valid: bool = True
    error_message: Optional[str] = None
    # 🚀 新增：标记是否为简单字符串匹配，用于性能优化
    is_simple_string: bool = False
    # 🚀 新增：预处理的小写关键词，用于快速匹配
    lowercase_keywords: Optional[List[str]] = None


class KeywordCompiler:
    """
    关键词编译器类

    负责将转换后的关键词格式编译为正则表达式，
    提供高效的模式匹配和缓存机制。
    """

    def __init__(self, use_shared_cache: bool = True):
        """初始化关键词编译器

        Args:
            use_shared_cache: 保留参数，当前版本中已禁用共享缓存
        """
        self.logger = logging.getLogger(__name__)
        self.use_shared_cache = use_shared_cache

        # 本地缓存
        self.compiled_cache: Dict[str, CompiledPattern] = {}

        self.performance_stats = {
            'compiled_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'compilation_errors': 0
        }

        # 从配置获取设置
        self.enable_optimization = config_manager.get_bool(
            'keyword_matching.enable_performance_optimization', True
        )

        self.logger.info("关键词编译器初始化完成")
    
    def compile_keyword_pattern(self, pattern_data: Union[str, List]) -> CompiledPattern:
        """
        编译单个关键词模式

        Args:
            pattern_data: 关键词模式数据，可以是字符串或列表格式

        Returns:
            CompiledPattern: 编译后的模式对象
        """
        if not self.enable_optimization:
            return self._compile_pattern_direct(pattern_data)

        # 使用MD5哈希生成缓存键
        pattern_str = str(pattern_data)
        cache_key = hashlib.md5(pattern_str.encode('utf-8')).hexdigest()

        # 检查本地缓存
        if cache_key in self.compiled_cache:
            self.performance_stats['cache_hits'] += 1
            return self.compiled_cache[cache_key]

        self.performance_stats['cache_misses'] += 1

        try:
            # 编译新模式
            compiled_pattern = self._compile_pattern_direct(pattern_data)

            # 缓存结果到本地缓存
            self.compiled_cache[cache_key] = compiled_pattern

            self.performance_stats['compiled_count'] += 1
            return compiled_pattern

        except Exception as e:
            self.logger.error(f"编译关键词模式失败: {pattern_data}, 错误: {e}")
            self.performance_stats['compilation_errors'] += 1
            return CompiledPattern(
                pattern_type=-1,
                is_valid=False,
                error_message=str(e),
                original_data=pattern_data
            )
    
    def _parse_pattern_data(self, pattern_data: Union[str, List]) -> Optional[List]:
        """
        解析模式数据
        """
        if isinstance(pattern_data, str):
            pattern_data = pattern_data.strip()
            
            if pattern_data == "0":
                return None
            
            # 检查是否包含"|"分隔符
            if '|' in pattern_data:
                raise ValueError("包含多个规则的字符串应该在上层处理")
            
            try:
                # 尝试解析为Python列表
                import ast
                parsed = ast.literal_eval(pattern_data)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, SyntaxError):
                # 如果不是列表格式，当作单个关键词处理
                return [0, pattern_data]
        
        elif isinstance(pattern_data, list):
            return pattern_data
        
        return None
    
    def _compile_pattern(self, pattern_data: List) -> CompiledPattern:
        """
        编译具体的模式
        
        Args:
            pattern_data: 解析后的模式数据列表
            
        Returns:
            CompiledPattern: 编译结果
        """
        if not pattern_data or len(pattern_data) < 2:
            return CompiledPattern(
                pattern_type=-1,
                is_valid=False,
                error_message="模式数据格式不正确",
                original_data=pattern_data
            )
        
        pattern_type = pattern_data[0]
        
        if pattern_type == 0:
            # 格式0: [0, "关键词"] - 直接字符串匹配
            return self._compile_direct_match(pattern_data)
        elif pattern_type == 1:
            # 格式1: [1, ["左关键词"], ["右关键词"], 最小间隔, 最大间隔] - 有序匹配
            return self._compile_ordered_match(pattern_data)
        elif pattern_type == 2:
            # 格式2: [2, ["关键词组1"], ["关键词组2"], 最小间隔, 最大间隔] - 无序匹配
            return self._compile_unordered_match(pattern_data)
        else:
            return CompiledPattern(
                pattern_type=pattern_type,
                is_valid=False,
                error_message=f"不支持的模式类型: {pattern_type}",
                original_data=pattern_data
            )
    
    def _compile_direct_match(self, pattern_data: List) -> CompiledPattern:
        """编译直接匹配模式"""
        if len(pattern_data) != 2:
            return CompiledPattern(
                pattern_type=0,
                is_valid=False,
                error_message="直接匹配模式数据格式错误",
                original_data=pattern_data
            )
        
        keyword = str(pattern_data[1]).strip()
        if not keyword:
            return CompiledPattern(
                pattern_type=0,
                is_valid=False,
                error_message="关键词为空",
                original_data=pattern_data
            )
        
        try:
            # 🚀 优化1: 检查是否为简单字符串（无特殊正则字符）
            special_regex_chars = set(r'\.^$*+?{}[]|()')
            is_simple = not any(c in special_regex_chars for c in keyword)

            # 🚀 优化2: 预处理小写版本用于快速匹配
            lowercase_keyword = keyword.lower()

            # 编译为简单的包含匹配正则表达式
            escaped_keyword = re.escape(keyword)
            regex_pattern = re.compile(escaped_keyword, re.IGNORECASE)

            return CompiledPattern(
                pattern_type=0,
                regex_pattern=regex_pattern,
                keywords=[keyword],
                original_data=pattern_data,
                is_valid=True,
                is_simple_string=is_simple,  # 🚀 标记是否为简单字符串
                lowercase_keywords=[lowercase_keyword]  # 🚀 预处理小写版本
            )
        except re.error as e:
            return CompiledPattern(
                pattern_type=0,
                is_valid=False,
                error_message=f"正则表达式编译失败: {e}",
                original_data=pattern_data
            )
    
    def _compile_ordered_match(self, pattern_data: List) -> CompiledPattern:
        """编译有序匹配模式"""
        if len(pattern_data) != 5:
            return CompiledPattern(
                pattern_type=1,
                is_valid=False,
                error_message="有序匹配模式数据格式错误",
                original_data=pattern_data
            )
        
        left_keywords = pattern_data[1]
        right_keywords = pattern_data[2]
        min_chars = pattern_data[3]
        max_chars = pattern_data[4]
        
        if not isinstance(left_keywords, list) or not isinstance(right_keywords, list):
            return CompiledPattern(
                pattern_type=1,
                is_valid=False,
                error_message="关键词列表格式错误",
                original_data=pattern_data
            )
        
        try:
            # 构建有序匹配的正则表达式
            left_pattern = '|'.join(re.escape(kw) for kw in left_keywords if kw.strip())
            right_pattern = '|'.join(re.escape(kw) for kw in right_keywords if kw.strip())
            
            if not left_pattern or not right_pattern:
                return CompiledPattern(
                    pattern_type=1,
                    is_valid=False,
                    error_message="关键词列表为空",
                    original_data=pattern_data
                )
            
            # 构建正则表达式：左关键词 + 间隔 + 右关键词
            regex_str = f"({left_pattern}).{{{min_chars},{max_chars}}}({right_pattern})"
            regex_pattern = re.compile(regex_str, re.IGNORECASE | re.DOTALL)
            
            all_keywords = left_keywords + right_keywords
            
            return CompiledPattern(
                pattern_type=1,
                regex_pattern=regex_pattern,
                keywords=all_keywords,
                original_data=pattern_data,
                is_valid=True
            )
        except re.error as e:
            return CompiledPattern(
                pattern_type=1,
                is_valid=False,
                error_message=f"正则表达式编译失败: {e}",
                original_data=pattern_data
            )
    
    def _compile_unordered_match(self, pattern_data: List) -> CompiledPattern:
        """编译无序匹配模式"""
        if len(pattern_data) != 5:
            return CompiledPattern(
                pattern_type=2,
                is_valid=False,
                error_message="无序匹配模式数据格式错误",
                original_data=pattern_data
            )
        
        group1_keywords = pattern_data[1]
        group2_keywords = pattern_data[2]
        min_chars = pattern_data[3]
        max_chars = pattern_data[4]
        
        if not isinstance(group1_keywords, list) or not isinstance(group2_keywords, list):
            return CompiledPattern(
                pattern_type=2,
                is_valid=False,
                error_message="关键词列表格式错误",
                original_data=pattern_data
            )
        
        try:
            # 构建无序匹配的正则表达式
            group1_pattern = '|'.join(re.escape(kw) for kw in group1_keywords if kw.strip())
            group2_pattern = '|'.join(re.escape(kw) for kw in group2_keywords if kw.strip())
            
            if not group1_pattern or not group2_pattern:
                return CompiledPattern(
                    pattern_type=2,
                    is_valid=False,
                    error_message="关键词列表为空",
                    original_data=pattern_data
                )
            
            # 构建正则表达式：(组1 + 间隔 + 组2) 或 (组2 + 间隔 + 组1)
            regex_str = (f"(({group1_pattern}).{{{min_chars},{max_chars}}}({group2_pattern}))|"
                        f"(({group2_pattern}).{{{min_chars},{max_chars}}}({group1_pattern}))")
            regex_pattern = re.compile(regex_str, re.IGNORECASE | re.DOTALL)
            
            all_keywords = group1_keywords + group2_keywords
            
            return CompiledPattern(
                pattern_type=2,
                regex_pattern=regex_pattern,
                keywords=all_keywords,
                original_data=pattern_data,
                is_valid=True
            )
        except re.error as e:
            return CompiledPattern(
                pattern_type=2,
                is_valid=False,
                error_message=f"正则表达式编译失败: {e}",
                original_data=pattern_data
            )
    
    def batch_compile(self, pattern_list: List[Union[str, List]]) -> List[CompiledPattern]:
        """
        批量编译关键词模式
        
        Args:
            pattern_list: 模式数据列表
            
        Returns:
            List[CompiledPattern]: 编译结果列表
        """
        if not self.enable_optimization:
            # 串行处理
            return [self.compile_keyword_pattern(pattern) for pattern in pattern_list]
        
        # 并行处理
        max_workers = config_manager.get_int('keyword_matching.max_workers', 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.compile_keyword_pattern, pattern_list))
        
        return results
    
    def clear_cache(self):
        """清空编译缓存"""
        self.compiled_cache.clear()
        self.logger.info("编译缓存已清空")
    
    def get_performance_stats(self) -> Dict[str, int]:
        """获取性能统计信息"""
        return self.performance_stats.copy()

    def _compile_pattern_direct(self, pattern_data: Union[str, List]) -> CompiledPattern:
        """
        直接编译模式，不使用缓存

        Args:
            pattern_data: 关键词模式数据

        Returns:
            CompiledPattern: 编译后的模式对象
        """
        try:
            # 解析模式数据
            parsed_data = self._parse_pattern_data(pattern_data)
            if not parsed_data:
                return CompiledPattern(
                    pattern_type=-1,
                    is_valid=False,
                    error_message="无法解析模式数据",
                    original_data=pattern_data
                )

            # 编译模式
            return self._compile_pattern(parsed_data)

        except Exception as e:
            return CompiledPattern(
                pattern_type=-1,
                is_valid=False,
                error_message=str(e),
                original_data=pattern_data
            )


    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            'cache_size': len(self.compiled_cache),
            'cache_enabled': self.enable_optimization,
            'performance_stats': self.get_performance_stats()
        }


def test_keyword_compiler():
    """测试关键词编译器"""
    print("=" * 60)
    print("关键词编译器测试")
    print("=" * 60)
    
    compiler = KeywordCompiler()
    
    # 测试用例
    test_cases = [
        [0, "新能源汽车"],  # 直接匹配
        [1, ["新能源"], ["汽车"], 0, 10],  # 有序匹配
        [2, ["电动", "混动"], ["汽车", "车辆"], 0, 20],  # 无序匹配
        "0",  # 空值
        "[0, '测试关键词']",  # 字符串格式
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case}")
        result = compiler.compile_keyword_pattern(test_case)
        print(f"编译结果: 类型={result.pattern_type}, 有效={result.is_valid}")
        if result.error_message:
            print(f"错误信息: {result.error_message}")
        if result.keywords:
            print(f"关键词: {result.keywords}")
    
    # 显示性能统计
    print(f"\n性能统计: {compiler.get_performance_stats()}")
    print(f"缓存信息: {compiler.get_cache_info()}")


if __name__ == "__main__":
    test_keyword_compiler()


