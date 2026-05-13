#!/usr/bin/env python3
"""
进度条显示模块
Progress Bar Display Module

提供实时进度条显示功能，支持百分比、数量统计、预估时间等信息。
设计为轻量级、高性能的控制台进度显示工具。

作者：系统开发
日期：2024年
"""

import sys
import time
import threading
import os
import multiprocessing
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any


def is_multiprocess_worker() -> bool:
    """
    检测当前是否运行在多进程工作进程中

    Returns:
        bool: 如果是工作进程返回True，否则返回False
    """
    # 检查是否有父进程且不是主进程
    try:
        current_process = multiprocessing.current_process()
        return current_process.name != 'MainProcess'
    except:
        return False


class ProcessSafeProgressBar:
    """
    进程安全的进度条类

    根据运行环境自动选择合适的显示策略：
    - 主进程：显示完整进度条
    - 工作进程：只显示简化日志信息
    """

    def __init__(self, total: int, description: str = "处理中",
                 bar_length: int = 20, update_interval: float = 0.5,
                 enable_in_worker: bool = False):
        """
        初始化进程安全进度条

        Args:
            total: 总任务数量
            description: 进度描述文本
            bar_length: 进度条长度（字符数）
            update_interval: 更新间隔（秒）
            enable_in_worker: 是否在工作进程中启用进度条
        """
        self.total = total
        self.description = description
        self.bar_length = bar_length
        self.update_interval = update_interval
        self.enable_in_worker = enable_in_worker

        # 检测运行环境
        self.is_worker_process = is_multiprocess_worker()

        # 根据环境决定是否创建真实的进度条
        if self.is_worker_process and not self.enable_in_worker:
            # 工作进程中禁用进度条，使用简化日志
            self._progress_bar = None
            self._use_simple_logging = True
        else:
            # 主进程或明确启用的情况下使用完整进度条
            self._progress_bar = ProgressBar(total, description, bar_length, update_interval)
            self._use_simple_logging = False

        # 简化日志相关
        self.current = 0
        self.start_time = None
        self._last_log_time = 0
        self._log_interval = 5.0  # 每5秒输出一次日志

    def start(self):
        """启动进度条"""
        if self._progress_bar:
            self._progress_bar.start()
        else:
            self.start_time = time.time()
            print(f"[工作进程] 开始{self.description}: 总计 {self.total:,} 项任务")

    def update(self, value: Optional[int] = None):
        """更新进度"""
        if self._progress_bar:
            self._progress_bar.update(value)
        else:
            # 简化日志模式
            if value is not None:
                self.current = value
            else:
                self.current += 1

            # 定期输出日志
            current_time = time.time()
            if current_time - self._last_log_time >= self._log_interval:
                percentage = (self.current / self.total) * 100 if self.total > 0 else 0
                print(f"[工作进程] {self.description}进度: {self.current:,}/{self.total:,} ({percentage:.1f}%)")
                self._last_log_time = current_time

    def finish(self, message: str = "完成"):
        """完成进度条"""
        if self._progress_bar:
            self._progress_bar.finish(message)
        else:
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            print(f"[工作进程] {self.description}{message}: {self.current:,}/{self.total:,} 项任务，耗时 {elapsed_time:.2f}秒")

    @property
    def is_running(self) -> bool:
        """检查是否正在运行"""
        if self._progress_bar:
            return self._progress_bar.is_running
        return self.start_time is not None

    @property
    def is_finished(self) -> bool:
        """检查是否已完成"""
        if self._progress_bar:
            return self._progress_bar.is_finished
        return False


class ProgressBar:
    """
    实时进度条显示类
    
    特性：
    - 显示百分比进度
    - 显示已处理/总计数量（支持千分位分隔符）
    - 显示预估剩余时间
    - 使用简洁的文本进度条格式
    - 线程安全的更新机制
    - 可配置的更新频率
    """
    
    def __init__(self, total: int, description: str = "处理中", 
                 bar_length: int = 20, update_interval: float = 0.5):
        """
        初始化进度条
        
        Args:
            total: 总任务数量
            description: 进度描述文本
            bar_length: 进度条长度（字符数）
            update_interval: 更新间隔（秒）
        """
        self.total = total
        self.description = description
        self.bar_length = bar_length
        self.update_interval = update_interval
        
        # 进度状态
        self.current = 0
        self.start_time = None
        self.last_update_time = 0
        self.is_running = False
        self.is_finished = False
        
        # 线程安全锁
        self._lock = threading.Lock()
        
        # 显示相关
        self._last_line_length = 0
        
    def start(self):
        """启动进度条"""
        with self._lock:
            self.start_time = time.time()
            self.is_running = True
            self.is_finished = False
            self.current = 0
            
        # 显示初始进度条
        self._display_progress()
    
    def update(self, current: Optional[int] = None, increment: int = 1):
        """
        更新进度
        
        Args:
            current: 当前进度值（如果提供，则直接设置；否则增加increment）
            increment: 增量值（当current为None时使用）
        """
        with self._lock:
            if not self.is_running:
                return
                
            if current is not None:
                self.current = current
            else:
                self.current += increment
                
            # 限制在有效范围内
            self.current = min(self.current, self.total)
            
            # 检查是否需要更新显示
            current_time = time.time()
            if (current_time - self.last_update_time >= self.update_interval or 
                self.current >= self.total):
                self.last_update_time = current_time
                self._display_progress()
                
            # 检查是否完成
            if self.current >= self.total and not self.is_finished:
                self.is_finished = True
    
    def finish(self, message: Optional[str] = None):
        """
        完成进度条显示
        
        Args:
            message: 完成时显示的消息
        """
        with self._lock:
            if not self.is_running:
                return
                
            self.current = self.total
            self.is_finished = True
            self.is_running = False
            
        # 显示最终进度
        self._display_progress()
        
        # 显示完成消息
        if message:
            print(f"\n{message}")
        else:
            print()  # 换行
    
    def _display_progress(self):
        """显示进度条"""
        if self.total <= 0:
            return
            
        # 计算进度百分比
        percentage = (self.current / self.total) * 100
        
        # 生成进度条
        filled_length = int(self.bar_length * self.current // self.total)
        bar = '█' * filled_length + '░' * (self.bar_length - filled_length)
        
        # 格式化数量（添加千分位分隔符）
        current_str = f"{self.current:,}"
        total_str = f"{self.total:,}"
        
        # 计算预估剩余时间
        time_info = self._calculate_time_info()
        
        # 构建进度行
        progress_line = (f"\r{self.description}: [{bar}] {percentage:.1f}% "
                        f"({current_str}/{total_str}){time_info}")
        
        # 清除之前的行（如果新行更短）
        if len(progress_line) < self._last_line_length:
            clear_line = "\r" + " " * self._last_line_length + "\r"
            sys.stdout.write(clear_line)
        
        # 输出进度行
        sys.stdout.write(progress_line)
        sys.stdout.flush()
        
        self._last_line_length = len(progress_line)
    
    def _calculate_time_info(self) -> str:
        """计算时间信息"""
        if not self.start_time or self.current <= 0:
            return ""
            
        elapsed_time = time.time() - self.start_time
        
        if self.current >= self.total:
            # 已完成，显示总耗时
            return f" 耗时: {self._format_duration(elapsed_time)}"
        
        # 计算预估剩余时间
        if elapsed_time > 0:
            rate = self.current / elapsed_time
            if rate > 0:
                remaining_items = self.total - self.current
                estimated_remaining = remaining_items / rate
                return f" 预计剩余: {self._format_duration(estimated_remaining)}"
        
        return ""
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时间长度"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}小时{minutes}分"


class ProgressBarManager:
    """
    进度条管理器
    
    用于管理多个进度条的显示，确保线程安全和正确的显示顺序。
    """
    
    def __init__(self):
        self._current_bar: Optional[ProgressBar] = None
        self._lock = threading.Lock()
    
    def create_progress_bar(self, total: int, description: str = "处理中", 
                           bar_length: int = 20, update_interval: float = 0.5) -> ProgressBar:
        """
        创建新的进度条
        
        Args:
            total: 总任务数量
            description: 进度描述文本
            bar_length: 进度条长度
            update_interval: 更新间隔
            
        Returns:
            ProgressBar: 进度条实例
        """
        with self._lock:
            # 如果有当前进度条，先完成它
            if self._current_bar and self._current_bar.is_running:
                self._current_bar.finish()
            
            # 创建新进度条
            progress_bar = ProgressBar(total, description, bar_length, update_interval)
            self._current_bar = progress_bar
            
            return progress_bar
    
    def get_current_bar(self) -> Optional[ProgressBar]:
        """获取当前活动的进度条"""
        return self._current_bar


# 全局进度条管理器实例
progress_manager = ProgressBarManager()


def create_progress_bar(total: int, description: str = "处理中",
                       bar_length: int = 20, update_interval: float = 0.5) -> ProgressBar:
    """
    便捷函数：创建进度条

    Args:
        total: 总任务数量
        description: 进度描述文本
        bar_length: 进度条长度
        update_interval: 更新间隔

    Returns:
        ProgressBar: 进度条实例
    """
    return progress_manager.create_progress_bar(total, description, bar_length, update_interval)


def create_process_safe_progress_bar(total: int, description: str = "处理中",
                                   bar_length: int = 20, update_interval: float = 0.5,
                                   enable_in_worker: bool = False) -> ProcessSafeProgressBar:
    """
    便捷函数：创建进程安全的进度条

    Args:
        total: 总任务数量
        description: 进度描述文本
        bar_length: 进度条长度
        update_interval: 更新间隔
        enable_in_worker: 是否在工作进程中启用进度条

    Returns:
        ProcessSafeProgressBar: 进程安全进度条实例
    """
    return ProcessSafeProgressBar(total, description, bar_length, update_interval, enable_in_worker)


class MultiProcessProgressManager:
    """
    多进程进度条管理器

    专门用于管理多进程批量处理场景下的进度显示，
    确保主进程显示整体进度，工作进程不产生冲突。
    """

    def __init__(self):
        self._main_progress_bar: Optional[ProgressBar] = None
        self._lock = threading.Lock()
        self._completed_tasks = 0
        self._total_tasks = 0
        self._task_details: Dict[str, Any] = {}

    def start_batch_progress(self, total_files: int, description: str = "批量处理文件") -> ProgressBar:
        """
        启动批量处理的主进度条

        Args:
            total_files: 总文件数量
            description: 进度描述

        Returns:
            ProgressBar: 主进度条实例
        """
        with self._lock:
            if self._main_progress_bar and self._main_progress_bar.is_running:
                self._main_progress_bar.finish()

            self._total_tasks = total_files
            self._completed_tasks = 0
            self._task_details.clear()

            self._main_progress_bar = ProgressBar(
                total=total_files,
                description=description,
                bar_length=30,
                update_interval=0.2
            )
            self._main_progress_bar.start()

            return self._main_progress_bar

    def update_file_progress(self, file_name: str, status: str = "完成"):
        """
        更新单个文件的处理进度

        Args:
            file_name: 文件名
            status: 处理状态
        """
        with self._lock:
            if self._main_progress_bar and self._main_progress_bar.is_running:
                self._completed_tasks += 1
                self._task_details[file_name] = status

                # 更新主进度条
                self._main_progress_bar.update(self._completed_tasks)

    def finish_batch_progress(self, message: str = "批量处理完成"):
        """
        完成批量处理进度条

        Args:
            message: 完成消息
        """
        with self._lock:
            if self._main_progress_bar:
                success_count = len([v for v in self._task_details.values() if v == "完成"])
                error_count = len([v for v in self._task_details.values() if v == "失败"])
                final_message = f"{message}! 成功: {success_count}, 失败: {error_count}"

                self._main_progress_bar.finish(final_message)
                self._main_progress_bar = None

    def get_progress_stats(self) -> Dict[str, Any]:
        """
        获取进度统计信息

        Returns:
            Dict: 进度统计数据
        """
        with self._lock:
            return {
                'total_tasks': self._total_tasks,
                'completed_tasks': self._completed_tasks,
                'success_count': len([v for v in self._task_details.values() if v == "完成"]),
                'error_count': len([v for v in self._task_details.values() if v == "失败"]),
                'task_details': self._task_details.copy()
            }


# 全局多进程进度条管理器实例
multiprocess_progress_manager = MultiProcessProgressManager()


if __name__ == "__main__":
    """测试进度条功能"""
    import random
    
    print("进度条功能测试")
    print("=" * 50)
    
    # 测试1: 基本进度条
    print("\n测试1: 基本进度条")
    total_items = 1000
    progress = create_progress_bar(total_items, "基本测试")
    progress.start()
    
    for i in range(total_items):
        time.sleep(0.001)  # 模拟处理时间
        progress.update()
    
    progress.finish("基本测试完成！")
    
    # 测试2: 大数量进度条
    print("\n测试2: 大数量进度条")
    total_items = 1000000
    progress = create_progress_bar(total_items, "大数量测试")
    progress.start()
    
    for i in range(0, total_items, 10000):
        time.sleep(0.01)  # 模拟批处理
        progress.update(i + 10000)
    
    progress.finish("大数量测试完成！")
    
    # 测试3: 不规则更新
    print("\n测试3: 不规则更新")
    total_items = 100
    progress = create_progress_bar(total_items, "不规则测试")
    progress.start()
    
    current = 0
    while current < total_items:
        increment = random.randint(1, 5)
        current = min(current + increment, total_items)
        progress.update(current)
        time.sleep(0.05)
    
    progress.finish("不规则测试完成！")
    
    print("\n所有测试完成！")
