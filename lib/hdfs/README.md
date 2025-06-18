# HDFS客户端

## 概述

HDFS客户端是一个用于与Hadoop分布式文件系统(HDFS)交互的Python库。与传统的`hdfs`库不同，这个客户端不依赖`InsecureClient`，而是直接通过`OSClient`调用`hdfs`命令来执行各种操作。

## 主要特性

- **无依赖**: 不依赖`hdfs`库的`InsecureClient`
- **命令驱动**: 直接调用`hdfs dfs`命令执行操作
- **错误处理**: 完善的异常处理和日志记录
- **灵活配置**: 支持自定义OS客户端和HDFS配置
- **功能完整**: 支持文件、目录的所有基本操作

## 安装要求

1. **HDFS客户端工具**: 确保系统已安装HDFS客户端工具
   ```bash
   # 检查hdfs命令是否可用
   which hdfs
   hdfs version
   ```

2. **Python依赖**: 
   - `lib.os.os_client`: 用于执行系统命令
   - 标准库: `typing`, `logging`, `re`, `json`, `datetime`

## 使用方法

### 基本用法

```python
from lib.hdfs.hdfs_client import HDFSClient
from lib.os.os_client import OSClient

# 创建OS客户端
os_client = OSClient({
    'timeout': 300,
    'work_dir': '/tmp'
})

# 创建HDFS客户端
hdfs_config = {
    'namenode_url': 'hdfs://localhost:8020',
    'username': 'hdfs'
}

hdfs_client = HDFSClient(hdfs_config, os_client=os_client)
```

### 常用操作

#### 1. 检查路径是否存在
```python
exists = hdfs_client.exists("/path/to/check")
print(f"路径存在: {exists}")
```

#### 2. 列出目录内容
```python
items = hdfs_client.list_dir("/path/to/list")
for item in items:
    print(f"{item['name']} - {item['size']} bytes")
```

#### 3. 创建目录
```python
hdfs_client.mkdir("/path/to/create", permission="755")
```

#### 4. 删除文件或目录
```python
# 删除文件
hdfs_client.delete("/path/to/file")

# 递归删除目录
hdfs_client.delete("/path/to/directory", recursive=True)
```

#### 5. 复制文件
```python
hdfs_client.copy("/source/path", "/destination/path", overwrite=True)
```

#### 6. 移动文件
```python
hdfs_client.move("/source/path", "/destination/path")
```

#### 7. 上传文件
```python
hdfs_client.upload("/local/path", "/hdfs/path")
```

#### 8. 下载文件
```python
hdfs_client.download("/hdfs/path", "/local/path")
```

#### 9. 读取文件内容
```python
content = hdfs_client.read("/path/to/file")
print(content.decode('utf-8'))
```

#### 10. 写入文件内容
```python
data = b"Hello, HDFS!"
hdfs_client.write("/path/to/file", data, overwrite=True)
```

#### 11. 获取文件状态
```python
status = hdfs_client.get_file_status("/path/to/file")
print(f"权限: {status['permission']}")
print(f"所有者: {status['owner']}")
print(f"大小: {status['size']}")
```

#### 12. 获取目录摘要
```python
summary = hdfs_client.get_content_summary("/path/to/directory")
print(f"目录数: {summary['dir_count']}")
print(f"文件数: {summary['file_count']}")
print(f"总大小: {summary['content_size']}")
```

## 配置参数

### HDFS配置
- `namenode_url`: NameNode URL (例如: `hdfs://localhost:8020`)
- `username`: HDFS用户名 (可选)

### OS客户端配置
- `timeout`: 命令执行超时时间 (秒)
- `work_dir`: 工作目录

## 错误处理

客户端提供了完善的错误处理机制：

```python
try:
    hdfs_client.list_dir("/path")
except Exception as e:
    print(f"操作失败: {str(e)}")
```

常见错误：
- **返回码127**: HDFS命令未找到，请检查HDFS客户端工具是否安装
- **返回码1**: 权限不足或路径不存在
- **返回码2**: 命令参数错误

## 日志记录

客户端使用Python标准库的`logging`模块记录日志：

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 客户端会自动记录操作日志
hdfs_client.list_dir("/path")
```

## 性能考虑

1. **命令执行**: 每次操作都会执行一个独立的`hdfs`命令，对于大量小文件操作可能较慢
2. **网络延迟**: 命令执行时间受网络延迟影响
3. **并发限制**: 建议避免同时执行大量并发操作

## 安全注意事项

1. **权限管理**: 确保HDFS用户有足够的权限执行所需操作
2. **路径验证**: 在用户输入路径时进行验证，避免路径遍历攻击
3. **敏感信息**: 避免在日志中记录敏感信息

## 示例

完整的使用示例请参考 `examples/hdfs_client_example.py`。

## 与采集脚本的集成

HDFS客户端已集成到以下采集脚本中：

- `magicbox/periodic/hdfs/collect_hdfs_storage.py`: HDFS存储采集
- `magicbox/periodic/hdfs/collect_hive_storage.py`: Hive存储采集

这些脚本使用HDFS客户端来获取存储信息和统计数据。

## 故障排除

### 常见问题

1. **HDFS命令未找到**
   ```
   错误: 返回码: 127
   解决: 安装HDFS客户端工具
   ```

2. **权限不足**
   ```
   错误: 返回码: 1
   解决: 检查HDFS用户权限
   ```

3. **网络连接问题**
   ```
   错误: 连接超时
   解决: 检查网络连接和NameNode配置
   ```

### 调试技巧

1. 启用详细日志：
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. 测试基本命令：
   ```bash
   hdfs dfs -ls /
   hdfs dfs -pwd
   ```

3. 检查环境变量：
   ```bash
   echo $HADOOP_HOME
   echo $PATH
   ``` 