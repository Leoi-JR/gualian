"""
文本预处理器模块
Text Preprocessor Module

提供文本数据解析、清理和标准化功能。
"""

import re
from typing import Any, List


def smart_parse_text_data(col_texts: Any) -> List[str]:
    """
    解析文本数据，支持 numpy.ndarray 和 None 类型

    Args:
        col_texts: 原始文本数据

    Returns:
        List[str]: 解析后的文本列表
    """
    if col_texts is None:
        return []

    try:
        result = []
        for item in col_texts:
            if item is not None:
                item_str = str(item).strip()
                if item_str:
                    result.append(item_str)
        return result
    except Exception:
        return []


def remove_html_tags(text: str) -> str:
    """
    移除HTML标签

    Args:
        text: 包含HTML标签的文本

    Returns:
        str: 清理后的文本
    """
    html_pattern = re.compile(r'<[^>]+>')
    cleaned = html_pattern.sub('', text)

    html_entities = {
        '&nbsp;': ' ',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&#39;': "'",
        '&hellip;': '...',
        '&mdash;': '—',
        '&ndash;': '–'
    }

    for entity, replacement in html_entities.items():
        cleaned = cleaned.replace(entity, replacement)

    return cleaned


def normalize_special_characters(text: str) -> str:
    """
    标准化特殊字符

    Args:
        text: 原始文本

    Returns:
        str: 标准化后的文本
    """
    punctuation_map = {
        '，': ',',
        '。': '.',
        '；': ';',
        '：': ':',
        '？': '?',
        '！': '!',
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '《': '<',
        '》': '>',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '…': '...'
    }

    cleaned = text
    for chinese_punct, english_punct in punctuation_map.items():
        cleaned = cleaned.replace(chinese_punct, english_punct)

    return cleaned


def normalize_whitespace(text: str) -> str:
    """
    规范化空白字符

    Args:
        text: 原始文本

    Returns:
        str: 规范化后的文本
    """
    whitespace_pattern = re.compile(r'\s+')
    cleaned = whitespace_pattern.sub(' ', text)
    return cleaned.strip()


def remove_control_characters(text: str) -> str:
    """
    移除控制字符

    Args:
        text: 原始文本

    Returns:
        str: 清理后的文本
    """
    return ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
