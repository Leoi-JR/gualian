#!/usr/bin/env python3
"""
关键词模式转换器
Keyword Pattern Transformer

该模块提供了将特定格式的字符串转换为指定输出格式的功能。
支持十种不同的输入模式，包括关键词匹配、数字范围和括号列表等。

转换结果格式说明：
- [0, keyword] - 单个关键词的直接匹配
- [1, left_list, right_list, min_chars, max_chars] - 有序匹配（左边关键词在前）
- [2, left_list, right_list, min_chars, max_chars] - 无序匹配（左右关键词可交替）

作者：系统重构
日期：2024年
"""

import re
import logging
from typing import List, Union, Optional, Tuple
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config_manager


class PatternTransformer:
    """
    字符串模式转换器类
    
    该类提供了将特定格式的字符串转换为指定输出格式的功能。
    支持十种不同的输入模式，并将其转换为相应的列表格式。
    """
    
    def __init__(self, default_max_chars: Optional[int] = None):
        """
        初始化模式转换器
        
        Args:
            default_max_chars (int, optional): 默认的最大字符长度，用于&和&&模式
        """
        self.default_max_chars = default_max_chars or config_manager.get_int('pattern_conversion.max_chars', 200)
        self.enable_logging = config_manager.get_bool('pattern_conversion.enable_logging', True)
        
        # 设置日志
        if self.enable_logging:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.disabled = True
        
        # 编译正则表达式以提高性能
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """编译正则表达式模式以提高性能"""
        try:
            self.pattern_range = re.compile(r'(.+?)\.\{(\d+),(\d+)\}(.+)')
            self.pattern_and = re.compile(r'(.+?)&(.+)')
            self.pattern_and_and = re.compile(r'(.+?)&&(.+)')
            self.pattern_brackets = re.compile(r'\(([^)]+)\)')
            self.logger.info("正则表达式模式编译完成")
        except Exception as e:
            self.logger.error(f"正则表达式编译失败: {e}")
            raise
    
    def _extract_bracket_items(self, text: str) -> Optional[List[str]]:
        """
        从括号中提取项目列表
        
        Args:
            text (str): 包含括号的文本
            
        Returns:
            Optional[List[str]]: 括号内的项目列表，如果格式不正确则返回None
        """
        if not text or not isinstance(text, str):
            return None
            
        text = text.strip()
        if not text.startswith('(') or not text.endswith(')'):
            return None
        
        try:
            items_str = text[1:-1]  # 去掉括号
            items = [item.strip() for item in items_str.split(',')]
            # 过滤空项目
            items = [item for item in items if item]
            return items if len(items) >= 2 else None
        except Exception as e:
            self.logger.warning(f"提取括号项目失败: {text}, 错误: {e}")
            return None
    
    def _validate_range_values(self, num1: str, num2: str) -> Tuple[int, int]:
        """
        验证和转换范围值
        
        Args:
            num1 (str): 最小值字符串
            num2 (str): 最大值字符串
            
        Returns:
            Tuple[int, int]: 验证后的最小值和最大值
            
        Raises:
            ValueError: 当范围值无效时
        """
        try:
            min_val = int(num1)
            max_val = int(num2)
            
            if min_val < 0 or max_val < 0:
                raise ValueError("范围值不能为负数")
            if min_val > max_val:
                raise ValueError("最小值不能大于最大值")
            if max_val > 10000:  # 设置合理的上限
                raise ValueError("最大值过大")
                
            return min_val, max_val
        except ValueError as e:
            self.logger.error(f"范围值验证失败: {num1}, {num2}, 错误: {e}")
            raise
    
    def transform_pattern(self, pattern: str) -> List[Union[int, str, List[str]]]:
        """
        转换单个模式字符串
        
        Args:
            pattern (str): 要转换的模式字符串
            
        Returns:
            List[Union[int, str, List[str]]]: 转换后的结果
            格式：
            - [0, keyword] - 单个关键词
            - [1, left_list, right_list, min_chars, max_chars] - 有序匹配
            - [2, left_list, right_list, min_chars, max_chars] - 无序匹配
        """
        if not pattern or not isinstance(pattern, str):
            self.logger.warning(f"无效的模式字符串: {pattern}")
            return [0, ""]
        
        pattern = pattern.strip()
        if not pattern:
            return [0, ""]
        
        try:
            # 处理范围模式：xx.{num1,num2}yy
            range_match = self.pattern_range.match(pattern)
            if range_match:
                xx, num1, num2, yy = range_match.groups()
                min_val, max_val = self._validate_range_values(num1, num2)
                result = [1, [xx.strip()], [yy.strip()], min_val, max_val]
                self.logger.debug(f"范围模式匹配: {pattern} -> {result}")
                return result
            
            # 处理&&模式
            and_and_match = self.pattern_and_and.match(pattern)
            if and_and_match:
                left, right = and_and_match.groups()
                left = left.strip()
                right = right.strip()
                
                left_items = self._extract_bracket_items(left)
                right_items = self._extract_bracket_items(right)
                
                if left_items and right_items:
                    # (xx1,xx2,...)&&(yy1,yy2,...)
                    result = [2, left_items, right_items, 0, self.default_max_chars]
                elif left_items:
                    # (xx1,xx2,...)&&yy
                    result = [2, left_items, [right], 0, self.default_max_chars]
                elif right_items:
                    # xx&&(yy1,yy2,...)
                    result = [2, [left], right_items, 0, self.default_max_chars]
                else:
                    # xx&&yy
                    result = [2, [left], [right], 0, self.default_max_chars]
                
                self.logger.debug(f"&&模式匹配: {pattern} -> {result}")
                return result
            
            # 处理&模式
            and_match = self.pattern_and.match(pattern)
            if and_match:
                left, right = and_match.groups()
                left = left.strip()
                right = right.strip()
                
                left_items = self._extract_bracket_items(left)
                right_items = self._extract_bracket_items(right)
                
                if left_items and right_items:
                    # (xx1,xx2,...)&(yy1,yy2,...)
                    result = [1, left_items, right_items, 0, self.default_max_chars]
                elif left_items:
                    # (xx1,xx2,...)&yy
                    result = [1, left_items, [right], 0, self.default_max_chars]
                elif right_items:
                    # xx&(yy1,yy2,...)
                    result = [1, [left], right_items, 0, self.default_max_chars]
                else:
                    # xx&yy
                    result = [1, [left], [right], 0, self.default_max_chars]
                
                self.logger.debug(f"&模式匹配: {pattern} -> {result}")
                return result
            
            # 处理单个词：xx
            result = [0, pattern]
            self.logger.debug(f"单词模式匹配: {pattern} -> {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"转换模式时发生错误: {pattern}, 错误: {e}")
            return [0, pattern]  # 出错时返回原始模式作为单词
    
    def transform(self, text: str) -> List[List[Union[int, str, List[str]]]]:
        """
        转换包含多个模式的文本
        
        Args:
            text (str): 要转换的文本，包含以|分隔的多个模式
            
        Returns:
            List[List[Union[int, str, List[str]]]]: 转换后的结果列表
        """
        if not text or not isinstance(text, str):
            self.logger.warning(f"输入文本无效: {text}")
            return []
        
        try:
            patterns = text.split('|')
            results = []
            
            for pattern in patterns:
                pattern = pattern.strip()
                if pattern:  # 只处理非空模式
                    result = self.transform_pattern(pattern)
                    results.append(result)
            
            self.logger.info(f"成功转换 {len(results)} 个模式")
            return results
            
        except Exception as e:
            self.logger.error(f"转换文本时发生错误: {text}, 错误: {e}")
            return []
    
    def get_pattern_description(self, result: List[Union[int, str, List[str]]]) -> str:
        """
        获取转换结果的描述
        
        Args:
            result: 转换结果
            
        Returns:
            str: 结果描述
        """
        if not result or len(result) < 2:
            return "无效结果"
        
        pattern_type = result[0]
        
        if pattern_type == 0:
            return f"单个关键词: {result[1]}"
        elif pattern_type == 1:
            return f"有序匹配: {result[1]} -> {result[2]}, 间隔: {result[3]}-{result[4]}"
        elif pattern_type == 2:
            return f"无序匹配: {result[1]} <-> {result[2]}, 间隔: {result[3]}-{result[4]}"
        else:
            return f"未知类型: {pattern_type}"


def test_transformer():
    """测试函数"""
    transformer = PatternTransformer()
    
    test_cases = [
        "车载.{0,5}充电机",  # 范围模式
        "新能源&电池",  # 简单&模式
        "光刻机&(研发,制造,销售)",  # &带括号模式
        "新能源&&电池",  # 简单&&模式
        "光刻机&&(研发,制造,销售)",  # &&带括号模式
        "(研发,制造,销售)&光刻机",  # 括号&模式
        "(研发,制造,销售)&&光刻机",  # 括号&&模式
        "(新能源,氢能源)&(汽车,载具)",  # 双括号&模式
        "(新能源,氢能源)&&(汽车,载具)",  # 双括号&&模式
        "新能源"  # 单词模式
    ]
    
    print("模式转换测试结果：")
    print("=" * 60)
    
    for test_case in test_cases:
        try:
            result = transformer.transform_pattern(test_case)
            description = transformer.get_pattern_description(result)
            print(f"输入: {test_case}")
            print(f"输出: {result}")
            print(f"描述: {description}")
            print("-" * 40)
        except Exception as e:
            print(f"测试失败: {test_case}, 错误: {e}")


if __name__ == "__main__":
    test_transformer() 