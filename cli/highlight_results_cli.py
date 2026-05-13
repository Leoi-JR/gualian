#!/usr/bin/env python3
"""
匹配结果关键词高亮生成器 - CLI 工具

功能：
- 交互式选择时间范围，从 results/<timestamp> 目录中筛选结果Excel文件
- 批量（每10个文件）读取并合并到单个Excel，新增 full_category_name 列
- 解析匹配标记，依据原始规则通过 PatternTransformer + KeywordCompiler 转为正则
- 对单元格中“成功匹配的文本”部分的关键词进行局部富文本高亮（字体加粗+红色）
- 输出文件放置于新的 results/<timestamp>/ 目录，文件名 matching_results_highlighted.xlsx

注意：保持原有数据完整性，仅新增 full_category_name 列与高亮效果
"""
from __future__ import annotations

import os
import re
import sys
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import pandas as pd

# 路径与项目导入
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import config_manager
from core.pattern_transformer import PatternTransformer
from core.keyword_compiler import KeywordCompiler
from core.result_processor import ResultProcessor
from cli.keyword_matcher_cli import KeywordMatcherCLI

from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont


@dataclass
class ParsedEntry:
    text: str
    raw_rules: List[str]  # 原始规则字符串（可能包含多个，用逗号分割已拆分）
    original_position: int  # 在原始单元格字符串中的起始位置
    original_length: int    # 在原始单元格字符串中的长度


class HighlightResultsCLI:
    def __init__(self):
        self.transformer = PatternTransformer()
        self.compiler = KeywordCompiler(use_shared_cache=False)
        self.result_processor = ResultProcessor()
        # 缓存：原始规则字符串 -> 编译后的正则对象（re.Pattern）
        self._regex_cache: Dict[str, re.Pattern] = {}
        self._compiled_cache_hit = 0
        self._compiled_cache_miss = 0

        # 列配置
        self.text_columns: List[str] = config_manager.get_list(
            'keyword_matching.input_table_columns.text_content_columns'
        )
        self.identifier_columns: List[str] = config_manager.get_list(
            'keyword_matching.input_table_columns.identifier_columns'
        )

        # 高亮结果配置
        self.output_base_path: str = config_manager.get_str(
            'highlight_results.output_base_path', 'highlighted_results'
        )
        self.batch_size: int = config_manager.get_int(
            'highlight_results.batch_size', 10
        )

        # 高亮样式（字体颜色红、加粗）
        self.highlight_font = InlineFont(b=True, color='00FF0000')

    def _parse_datetime_input(self, prompt: str, allow_empty: bool = False) -> Optional[datetime]:
        while True:
            s = input(prompt).strip()
            if allow_empty and s == '':
                return None
            # 支持 YYYYMMDD 或 YYYY-MM-DD
            for fmt in ('%Y%m%d', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt
                except ValueError:
                    continue
            print('❌ 时间格式无效，请使用 YYYYMMDD 或 YYYY-MM-DD')

    def _list_result_files_in_range(self, start_dt: datetime, end_dt: datetime) -> List[Path]:
        base = Path('results')
        if not base.exists():
            print('❌ 未找到 results 目录')
            return []
        candidates: List[Path] = []
        for sub in base.iterdir():
            if not sub.is_dir():
                continue
            name = sub.name
            # 目录名格式: YYYYMMDD_HHMMSS
            try:
                ts = datetime.strptime(name, '%Y%m%d_%H%M%S')
            except ValueError:
                continue
            if start_dt <= ts <= end_dt:
                # 收集该目录下的xlsx（排除 *_highlighted* 以避免重复处理）
                files = list(sub.glob('*.xlsx'))
                for f in files:
                    if 'highlighted' in f.name.lower():
                        continue
                    candidates.append(f)
        candidates.sort()
        return candidates

    def _ensure_keyword_file(self) -> pd.DataFrame:
        # 通过现有CLI复用获取路径逻辑
        km_cli = KeywordMatcherCLI()
        keyword_file = km_cli.get_keyword_file_path()
        if not keyword_file:
            raise FileNotFoundError('未选择关键词文件')
        df = pd.read_excel(keyword_file)

        # 如果已有 full_category_name 列则直接使用，否则从 label_columns 组合生成
        if 'full_category_name' not in df.columns:
            label_cols = config_manager.get_list(
                'keyword_matching.keyword_table_columns.label_columns', []
            )
            existing_label_cols = [c for c in label_cols if c in df.columns]
            if existing_label_cols:
                df['full_category_name'] = df[existing_label_cols].astype(str).agg(
                    lambda x: x.str.cat(sep=' - ').strip(' - '), axis=1
                )
            else:
                df['full_category_name'] = ''

        # 确保行索引可用（用于 keyword_index 定位）
        df = df.reset_index(drop=True)
        return df

    def _extract_entries_from_cell(self, cell_value: str) -> List[ParsedEntry]:
        """重新实现的单元格解析：正确处理JSON格式的匹配文本列表"""
        if not cell_value or not cell_value.strip():
            return []

        original_cell_str = str(cell_value).strip()

        # 解析JSON格式的列表
        try:
            import json
            # 尝试直接解析JSON
            if original_cell_str.startswith('[') and original_cell_str.endswith(']'):
                entries_list = json.loads(original_cell_str)
            else:
                # 如果不是JSON格式，使用ResultProcessor的解析器
                entries_list = self.result_processor.parse_matched_texts_string(original_cell_str)
        except (json.JSONDecodeError, Exception):
            # JSON解析失败，使用ResultProcessor的解析器作为后备
            entries_list = self.result_processor.parse_matched_texts_string(original_cell_str)

        if not entries_list:
            return []

        parsed_list: List[ParsedEntry] = []

        for entry in entries_list:
            if not entry:
                continue

            entry_str = str(entry).strip()
            if not entry_str:
                continue

            # 解析单个条目：提取匹配文本和规则
            parsed_entry = self._parse_single_entry(entry_str, original_cell_str)
            if parsed_entry:
                parsed_list.append(parsed_entry)

        return parsed_list

    def _parse_single_entry(self, entry_str: str, original_cell_str: str) -> Optional[ParsedEntry]:
        """解析单个匹配条目，提取文本和规则"""
        # 查找第一个匹配类型分隔符
        first_delim_pos = -1

        # 按顺序查找分隔符（_like_matched_ 或 _must_matched_）
        for delim in ['_like_matched_', '_must_matched_']:
            pos = entry_str.find(delim)
            if pos >= 0:
                if first_delim_pos < 0 or pos < first_delim_pos:
                    first_delim_pos = pos

        if first_delim_pos < 0:
            # 没有找到匹配类型分隔符，跳过
            return None

        # 提取匹配文本
        matched_text = entry_str[:first_delim_pos]
        if not matched_text.strip():
            return None

        # 提取规则部分
        rules_part = entry_str[first_delim_pos:]

        # 解析所有规则
        all_rules = self._extract_rules_from_entry(rules_part)
        if not all_rules:
            return None

        # 在原始字符串中查找匹配文本的位置
        text_pos = self._find_text_position_in_original(matched_text, original_cell_str)
        if text_pos < 0:
            return None

        return ParsedEntry(
            text=matched_text,
            raw_rules=all_rules,
            original_position=text_pos,
            original_length=len(matched_text)
        )

    def _extract_rules_from_entry(self, rules_part: str) -> List[str]:
        """从规则部分提取所有规则，正确处理多种匹配类型和括号内的逗号"""
        all_rules = []

        # 按 | 分割不同的匹配类型
        match_type_parts = rules_part.split('|')

        for part in match_type_parts:
            part = part.strip()
            if not part:
                continue

            # 识别匹配类型并提取规则字符串
            rules_str = None
            if part.startswith('_like_matched_'):
                rules_str = part[len('_like_matched_'):]
            elif part.startswith('_must_matched_'):
                rules_str = part[len('_must_matched_'):]
            elif part.startswith('like_matched_'):  # 后续匹配类型缺少前导下划线
                rules_str = part[len('like_matched_'):]
            elif part.startswith('must_matched_'):  # 后续匹配类型缺少前导下划线
                rules_str = part[len('must_matched_'):]

            if rules_str:
                # 智能分割规则（考虑括号内的逗号）
                individual_rules = self._smart_split_rules(rules_str)
                all_rules.extend(individual_rules)

        return all_rules

    def _smart_split_rules(self, rules_str: str) -> List[str]:
        """智能分割规则字符串，只分割括号外的逗号"""
        if not rules_str:
            return []

        rules = []
        current_rule = ""
        paren_depth = 0

        for char in rules_str:
            if char == '(':
                paren_depth += 1
                current_rule += char
            elif char == ')':
                paren_depth -= 1
                current_rule += char
            elif char == ',' and paren_depth == 0:
                # 只有在括号外的逗号才作为分隔符
                if current_rule.strip():
                    rules.append(current_rule.strip())
                current_rule = ""
            else:
                current_rule += char

        # 添加最后一个规则
        if current_rule.strip():
            rules.append(current_rule.strip())

        return rules

    def _find_text_position_in_original(self, matched_text: str, original_cell_str: str) -> int:
        """在原始单元格字符串中查找匹配文本的位置"""
        # 直接查找
        pos = original_cell_str.find(matched_text)
        if pos >= 0:
            return pos

        # 如果直接查找失败，尝试在JSON解析的上下文中查找
        # 处理可能的引号包围情况
        quoted_text = f'"{matched_text}"'
        pos = original_cell_str.find(quoted_text)
        if pos >= 0:
            return pos + 1  # 跳过开头的引号

        # 如果仍然找不到，返回-1
        return -1

    def _compile_regex_for_rule(self, rule: str) -> Optional[re.Pattern]:
        """优化的正则编译方法：增强缓存 + 快速失败 + 详细错误处理"""
        if not rule or rule.strip() == '':
            return None

        rule = rule.strip()
        if rule in self._regex_cache:
            self._compiled_cache_hit += 1
            return self._regex_cache[rule]

        self._compiled_cache_miss += 1
        try:
            # 使用 PatternTransformer 将原始规则转换为结构化格式
            transformed = self.transformer.transform_pattern(rule)
            if not transformed:
                self._regex_cache[rule] = None
                return None

            # 使用 KeywordCompiler 将结构化格式编译为正则
            compiled = self.compiler.compile_keyword_pattern(transformed)
            if compiled and compiled.is_valid and compiled.regex_pattern is not None:
                self._regex_cache[rule] = compiled.regex_pattern
                return compiled.regex_pattern
            else:
                # 缓存失败结果，避免重复尝试
                self._regex_cache[rule] = None
                return None
        except Exception:
            # 缓存异常结果
            self._regex_cache[rule] = None
            return None

    def _collect_highlight_spans(self, base_string: str, entries: List[ParsedEntry]) -> List[Tuple[int, int]]:
        """修复的高亮区间计算：基于准确的位置信息计算高亮范围"""
        spans: List[Tuple[int, int]] = []

        for entry in entries:
            if not entry.text or not entry.raw_rules:
                continue

            # 使用已记录的原始位置信息，避免重复查找
            text_start_in_base = entry.original_position
            text_end_in_base = text_start_in_base + entry.original_length

            # 验证位置信息的有效性
            if (text_start_in_base < 0 or
                text_end_in_base > len(base_string) or
                text_start_in_base >= text_end_in_base):
                continue

            # 提取实际的匹配文本（基于位置信息）
            actual_text = base_string[text_start_in_base:text_end_in_base]

            # 在匹配文本内部用规则进行正则匹配
            inner_spans: List[Tuple[int, int]] = []
            for rule in entry.raw_rules:
                regex = self._compile_regex_for_rule(rule)
                if not regex:
                    continue

                try:
                    # 在实际文本中进行正则匹配
                    for match in regex.finditer(actual_text):
                        start, end = match.span()
                        if start < end:  # 确保是有效区间
                            inner_spans.append((start, end))
                except Exception:
                    # 正则匹配失败时跳过该规则，不中断处理
                    continue

            # 合并当前条目内的重叠区间
            if inner_spans:
                inner_spans.sort()
                merged_inner: List[Tuple[int, int]] = []
                cur_start, cur_end = inner_spans[0]

                for start, end in inner_spans[1:]:
                    if start <= cur_end:
                        # 重叠或相邻，合并区间
                        cur_end = max(cur_end, end)
                    else:
                        # 不重叠，保存当前区间并开始新区间
                        merged_inner.append((cur_start, cur_end))
                        cur_start, cur_end = start, end

                merged_inner.append((cur_start, cur_end))

                # 将相对位置转换为在base_string中的绝对位置
                for rel_start, rel_end in merged_inner:
                    abs_start = text_start_in_base + rel_start
                    abs_end = text_start_in_base + rel_end
                    # 边界检查
                    if abs_start >= 0 and abs_end <= len(base_string) and abs_start < abs_end:
                        spans.append((abs_start, abs_end))

        # 最终合并所有条目的高亮区间（处理不同条目间的重叠）
        if spans:
            spans.sort()
            final_merged: List[Tuple[int, int]] = []
            current_start, current_end = spans[0]

            for start, end in spans[1:]:
                if start <= current_end:
                    # 重叠或相邻，合并
                    current_end = max(current_end, end)
                else:
                    # 不重叠，保存当前区间
                    final_merged.append((current_start, current_end))
                    current_start, current_end = start, end

            final_merged.append((current_start, current_end))
            return final_merged

        return spans

    def _build_rich_text(self, s: str, spans: List[Tuple[int, int]]) -> CellRichText:
        """构建富文本对象，对指定区间应用高亮格式"""
        if not spans or not s:
            return CellRichText(s)

        # 验证和修正区间边界
        valid_spans = []
        for start, end in spans:
            # 确保区间在字符串范围内
            start = max(0, min(start, len(s)))
            end = max(start, min(end, len(s)))
            if start < end:
                valid_spans.append((start, end))

        if not valid_spans:
            return CellRichText(s)

        rt = CellRichText()
        last_pos = 0

        for start, end in valid_spans:
            # 添加高亮前的普通文本
            if start > last_pos:
                normal_text = s[last_pos:start]
                if normal_text:
                    rt.append(normal_text)

            # 添加高亮文本
            if start < end:
                highlight_text = s[start:end]
                if highlight_text:
                    rt.append(TextBlock(self.highlight_font, highlight_text))

            last_pos = end

        # 添加最后剩余的普通文本
        if last_pos < len(s):
            remaining_text = s[last_pos:]
            if remaining_text:
                rt.append(remaining_text)

        return rt

    def _generate_output_directory(self) -> Path:
        """生成高亮结果的专用输出目录"""
        # 使用配置的专用目录，避免与原始匹配结果混淆
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.output_base_path) / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _generate_batch_output_path(self, output_dir: Path, batch_num: int) -> Path:
        """生成批次文件的输出路径"""
        filename = f"highlighted_batch_{batch_num:03d}.xlsx"
        return output_dir / filename

    def _batch_load_and_merge_files(self, files: List[Path], keywords_df: pd.DataFrame) -> pd.DataFrame:
        """批量加载并合并Excel文件，预处理full_category_name列"""
        print(f'→ 批量加载 {len(files)} 个Excel文件...')

        dfs = []
        for fp in files:
            try:
                df = pd.read_excel(fp)
                if 'keyword_index' not in df.columns:
                    print(f'跳过文件（缺少 keyword_index 列）: {fp}')
                    continue
                dfs.append(df)
            except Exception as e:
                print(f'跳过无法读取的文件: {fp}，错误: {e}')
                continue

        if not dfs:
            return pd.DataFrame()

        # 合并所有DataFrame
        print('→ 合并DataFrame...')
        merged_df = pd.concat(dfs, ignore_index=True)

        # 插入 full_category_name 列（紧跟在 keyword_index 之后）
        if 'full_category_name' not in merged_df.columns:
            insert_pos = list(merged_df.columns).index('keyword_index') + 1
            merged_df.insert(insert_pos, 'full_category_name', '')

        # 向量化填充 full_category_name
        print('→ 映射 full_category_name...')
        def map_category_vectorized(idx_series):
            def map_single(idx):
                try:
                    if pd.isna(idx):
                        return ''
                    ii = int(idx)
                    if 0 <= ii < len(keywords_df):
                        val = keywords_df.iloc[ii].get('full_category_name', None)
                        return '' if pd.isna(val) else str(val)
                    return ''
                except Exception:
                    return ''
            return idx_series.apply(map_single)

        merged_df['full_category_name'] = map_category_vectorized(merged_df['keyword_index'])

        print(f'✓ 合并完成，共 {len(merged_df)} 行数据')
        return merged_df

    def run(self):
        print('\n=== 关键词高亮生成器 ===')
        start_dt = self._parse_datetime_input('请输入起始日期 (YYYYMMDD或YYYY-MM-DD): ')
        end_dt = self._parse_datetime_input('请输入终止日期 (YYYYMMDD或YYYY-MM-DD，回车默认当前时间): ', allow_empty=True)
        if end_dt is None:
            end_dt = datetime.now()
        # 将起始时间与终止时间扩展到整天范围
        start_dt = datetime.combine(start_dt.date(), datetime.min.time())
        end_dt = datetime.combine(end_dt.date(), datetime.max.time())

        files = self._list_result_files_in_range(start_dt, end_dt)
        if not files:
            print('❌ 指定时间范围内未找到结果Excel文件')
            return
        print(f'✓ 共找到 {len(files)} 个Excel结果文件')

        # 加载关键词文件
        keywords_df = self._ensure_keyword_file()

        # 生成输出目录
        output_dir = self._generate_output_directory()

        # 使用优化的分批次独立保存方法
        start_time = time.time()
        batch_results = self._process_files_with_batch_saving(files, keywords_df, output_dir)
        self._print_performance_stats_with_batches(batch_results, start_time)

    def _process_files_with_batch_saving(self, files: List[Path], keywords_df: pd.DataFrame,
                                        output_dir: Path) -> List[Dict]:
        """分批次独立保存的文件处理方法"""
        batch_results = []
        total_batches = (len(files) - 1) // self.batch_size + 1

        print(f'→ 将处理 {len(files)} 个文件，分为 {total_batches} 个批次')
        print(f'→ 每批次处理 {self.batch_size} 个文件，独立保存到 {output_dir}')

        # 分批处理文件
        for i in range(0, len(files), self.batch_size):
            batch_num = i // self.batch_size + 1
            batch_files = files[i:i+self.batch_size]

            print(f'\n→ 处理批次 {batch_num}/{total_batches}: {len(batch_files)} 个文件')

            # 批量加载并合并当前批次的文件
            merged_df = self._batch_load_and_merge_files(batch_files, keywords_df)
            if merged_df.empty:
                print(f'  ⚠️ 批次 {batch_num} 无有效数据，跳过')
                continue

            # 预处理高亮信息
            highlight_cols = [c for c in merged_df.columns if c.endswith('_matched_texts')]
            highlight_data = self._preprocess_highlight_data(merged_df, highlight_cols)

            # 生成批次输出文件路径
            batch_output_path = self._generate_batch_output_path(output_dir, batch_num)

            # 创建并保存当前批次的Excel文件
            batch_result = self._save_batch_to_excel(merged_df, highlight_data, batch_output_path)
            batch_result.update({
                'batch_num': batch_num,
                'file_count': len(batch_files),
                'output_path': batch_output_path
            })
            batch_results.append(batch_result)

            print(f'  ✓ 批次 {batch_num} 完成: {batch_result["row_count"]} 行 → {batch_output_path.name}')

            # 定期清理内存
            if batch_num % 3 == 0:
                self._optimize_memory_usage()

        return batch_results

    def _save_batch_to_excel(self, df: pd.DataFrame, highlight_data: Dict[Tuple[int, str], List[Tuple[int, int]]],
                            output_path: Path) -> Dict:
        """保存单个批次到Excel文件"""
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = 'Results'

        # 写入表头
        ws.append(list(df.columns))

        # 批量写入数据
        data_rows = df.values.tolist()
        for row_data in data_rows:
            ws.append(row_data)

        # 应用高亮效果
        highlight_count = 0
        for (df_row_idx, col_name), spans in highlight_data.items():
            excel_row = df_row_idx + 2  # +1 for header, +1 for 0-based to 1-based
            col_idx = list(df.columns).index(col_name) + 1

            cell = ws.cell(row=excel_row, column=col_idx)
            cell_value = str(df.iloc[df_row_idx][col_name])

            # 构建富文本
            rich_text = self._build_rich_text(cell_value, spans)
            cell.value = rich_text
            highlight_count += 1

        # 保存文件
        wb.save(output_path)

        return {
            'row_count': len(df),
            'highlight_count': highlight_count,
            'file_size': output_path.stat().st_size if output_path.exists() else 0
        }

    def _preprocess_highlight_data(self, df: pd.DataFrame, highlight_cols: List[str]) -> Dict[Tuple[int, str], List[Tuple[int, int]]]:
        """预处理高亮数据：批量解析匹配标记并计算高亮位置

        Returns:
            Dict[Tuple[row_idx, col_name], List[Tuple[start, end]]]: 高亮位置映射表
        """
        print('→ 预处理高亮位置信息...')
        highlight_data = {}

        for col_name in highlight_cols:
            # 向量化处理该列的所有单元格
            for row_idx, cell_value in enumerate(df[col_name]):
                if pd.isna(cell_value):
                    continue

                cell_str = str(cell_value)
                if not cell_str.strip():
                    continue

                try:
                    # 解析匹配标记
                    entries = self._extract_entries_from_cell(cell_str)
                    if not entries:
                        continue

                    # 计算高亮区间
                    spans = self._collect_highlight_spans(cell_str, entries)
                    if spans:
                        highlight_data[(row_idx, col_name)] = spans

                except Exception:
                    continue

        print(f'  ✓ 预处理完成，{len(highlight_data)} 个单元格需要高亮')

        return highlight_data



    def _optimize_memory_usage(self):
        """内存优化：清理不必要的缓存"""
        # 定期清理正则缓存，避免内存过度占用
        if len(self._regex_cache) > 1000:
            # 保留最近使用的500个
            cache_items = list(self._regex_cache.items())
            self._regex_cache = dict(cache_items[-500:])

    def _print_performance_stats_with_batches(self, batch_results: List[Dict], start_time: float):
        """打印包含批次信息的性能统计"""
        end_time = time.time()
        elapsed = end_time - start_time

        # 计算汇总信息
        total_rows = sum(result['row_count'] for result in batch_results)
        total_highlights = sum(result['highlight_count'] for result in batch_results)
        total_files = sum(result['file_count'] for result in batch_results)
        total_size = sum(result['file_size'] for result in batch_results)

        print(f'\n=== 处理完成 ===')
        print(f'✓ 共处理 {total_files} 个输入文件')
        print(f'✓ 生成 {len(batch_results)} 个批次文件')
        print(f'✓ 总数据行数: {total_rows:,}')
        print(f'✓ 高亮单元格数: {total_highlights:,}')
        print(f'✓ 输出文件总大小: {total_size/1024/1024:.2f} MB')
        print(f'✓ 总耗时: {elapsed:.2f} 秒')
        print(f'✓ 平均速度: {total_rows/elapsed:.1f} 行/秒')

        print(f'\n=== 输出文件列表 ===')
        for result in batch_results:
            print(f'批次 {result["batch_num"]:03d}: {result["output_path"].name} '
                  f'({result["row_count"]:,} 行, {result["highlight_count"]:,} 高亮)')

        # 显示输出目录
        if batch_results:
            output_dir = batch_results[0]['output_path'].parent
            print(f'\n📁 所有文件保存在: {output_dir.absolute()}')


def main():
    HighlightResultsCLI().run()


if __name__ == '__main__':
    main()

