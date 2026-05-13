# 已处理文件列表功能说明

## 功能概述

为了避免重复处理相同的文件，系统新增了已处理文件列表功能。该功能会自动记录已成功处理的文件，在下次批量处理时自动跳过这些文件，提高处理效率。

## 配置说明

### 主配置文件 (config.json)

在 `config.json` 文件的 `batch_processing.processed_files` 配置项中：

```json
"processed_files": {
    "enable_skip_processed": true     // 是否启用跳过已处理文件功能
}
```

### 已处理文件列表 (processed_files.json)

已处理文件列表保存在项目根目录的 `processed_files.json` 文件中：

```json
{
    "files": [                        // 已处理文件列表
        "batch_split_001.parquet",
        "batch_split_002.parquet"
    ],
    "last_updated": "2025-08-08 14:52:22"  // 最后更新时间
}
```

这种设计的优势：
- 保持主配置文件简洁易读
- 避免因文件列表过长导致配置文件难以维护
- 文件列表可以独立管理和备份

## 自动功能

### 批量处理时的自动跳过

当运行批量处理时，如果 `enable_skip_processed` 为 `true`，系统会：

1. 在处理开始前显示处理状态统计
2. 自动过滤掉已处理的文件
3. 只处理未处理的文件
4. 处理成功后自动将文件添加到已处理列表

### 处理状态显示

系统会显示以下信息：
- 总可用文件数
- 已处理文件数
- 未处理文件数
- 完成率
- 跳过已处理文件状态
- 最后更新时间
- 未处理文件列表

## CLI 管理工具

提供了 `cli/processed_files_manager_cli.py` 工具来管理已处理文件列表：

### 查看处理状态
```bash
python cli/processed_files_manager_cli.py status
```

### 查看已处理文件列表
```bash
python cli/processed_files_manager_cli.py list
```

### 手动添加文件到已处理列表
```bash
python cli/processed_files_manager_cli.py add <filename>
```

### 从已处理列表移除文件
```bash
python cli/processed_files_manager_cli.py remove <filename>
```

### 清空已处理文件列表
```bash
python cli/processed_files_manager_cli.py clear
```

### 启用/禁用跳过功能
```bash
python cli/processed_files_manager_cli.py enable   # 启用跳过已处理文件
python cli/processed_files_manager_cli.py disable  # 禁用跳过已处理文件
```

## 使用场景

1. **大批量文件处理**：处理大量文件时，如果中途中断，重新运行时会自动跳过已处理的文件
2. **增量处理**：定期处理新增文件时，只处理新文件，跳过已处理的文件
3. **错误恢复**：处理过程中出现错误时，修复后重新运行只会处理失败的文件

## 注意事项

1. 只有成功处理完成的文件才会被添加到已处理列表
2. 如果需要重新处理某个文件，可以使用 CLI 工具将其从已处理列表中移除
3. 配置文件会自动保存，无需手动操作
4. 可以通过配置文件或 CLI 工具随时启用/禁用此功能