"""
批量匹配器模块
Batch Matcher Module

提供批量关键词匹配策略选择和执行功能，
根据数据规模智能选择最优匹配方法。
"""

import logging
from typing import List


class BatchMatcher:
    """
    批量匹配器类

    根据数据规模智能选择最优的匹配策略：
    - 小数据量（<50文本）：使用传统逐个匹配
    - 中等数据量（50-1000文本）：使用pandas向量化匹配
    - 大数据量（>1000文本）：使用分块向量化匹配
    """

    def __init__(self, generate_match_tag_func):
        """
        初始化批量匹配器

        Args:
            generate_match_tag_func: 用于生成匹配标记的函数
        """
        self.logger = logging.getLogger(__name__)
        self._generate_match_tag = generate_match_tag_func

    def batch_match_texts_optimized(self, texts: List[str], compiled_patterns,
                                    match_type: str, original_keyword: str,
                                    early_exit: bool = False) -> List[str]:
        """
        批量匹配文本优化版本

        Args:
            texts: 要匹配的文本列表
            compiled_patterns: 编译后的模式列表
            match_type: 匹配类型
            original_keyword: 原始关键词
            early_exit: 是否启用早期退出

        Returns:
            List[str]: 匹配到的文本列表
        """
        if not texts or not compiled_patterns:
            return []

        try:
            total_operations = len(texts) * len(compiled_patterns)

            if total_operations < 5000:
                return self._traditional_batch_match(texts, compiled_patterns, match_type, original_keyword, early_exit)
            elif total_operations < 50000:
                return self._vectorized_batch_match(texts, compiled_patterns, match_type, original_keyword, early_exit)
            else:
                return self._chunked_vectorized_match(texts, compiled_patterns, match_type, original_keyword, early_exit)

        except Exception as e:
            self.logger.warning(f"向量化批量匹配失败，回退到传统方法: {e}")
            return self._traditional_batch_match(texts, compiled_patterns, match_type, original_keyword, early_exit)

    def _traditional_batch_match(self, texts, compiled_patterns, match_type, original_keyword, early_exit=False):
        """传统的逐个匹配方法"""
        matched_texts = []

        for text in texts:
            text_matched = False

            for compiled_pattern in compiled_patterns:
                if compiled_pattern.regex_pattern and compiled_pattern.regex_pattern.search(text):
                    match_tag = self._generate_match_tag(text, original_keyword, match_type)
                    matched_texts.append(match_tag)
                    text_matched = True

                    if early_exit:
                        break

            if early_exit and text_matched:
                break

        return matched_texts

    def _vectorized_batch_match(self, texts, compiled_patterns, match_type, original_keyword, early_exit=False):
        """pandas向量化批量匹配"""
        try:
            import pandas as pd
            import numpy as np

            text_series = pd.Series(texts)
            matched_results = []

            for compiled_pattern in compiled_patterns:
                if not compiled_pattern.regex_pattern:
                    continue

                matches = text_series.str.contains(
                    compiled_pattern.regex_pattern,
                    regex=True,
                    na=False
                )

                matched_indices = np.where(matches)[0]

                if len(matched_indices) > 0:
                    for idx in matched_indices:
                        match_tag = self._generate_match_tag(texts[idx], original_keyword, match_type)
                        matched_results.append(match_tag)

                    if early_exit:
                        break

            return matched_results

        except ImportError:
            self.logger.warning("pandas未安装，回退到传统匹配方法")
            return self._traditional_batch_match(texts, compiled_patterns, match_type, original_keyword, early_exit)
        except Exception as e:
            self.logger.warning(f"向量化匹配失败: {e}，回退到传统方法")
            return self._traditional_batch_match(texts, compiled_patterns, match_type, original_keyword, early_exit)

    def _chunked_vectorized_match(self, texts, compiled_patterns, match_type, original_keyword,
                                  early_exit=False, chunk_size=500):
        """分块向量化匹配 - 大数据量优化"""
        matched_results = []

        for i in range(0, len(texts), chunk_size):
            chunk_texts = texts[i:i + chunk_size]

            chunk_results = self._vectorized_batch_match(
                chunk_texts, compiled_patterns, match_type, original_keyword, early_exit
            )

            matched_results.extend(chunk_results)

            if early_exit and chunk_results:
                break

        return matched_results
