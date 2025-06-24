# AutoEVS

AutoEVS 是一个专注于大数据平台的自动化运维工具集，提供YARN、HDFS、Hive等组件的监控、数据采集和管理功能。

## 🚀 功能特点

- **YARN 监控**：应用状态采集、资源管理、队列监控、应用快照
- **HDFS 监控**：存储概览、NameNode状态、容量分析、文件统计
- **Hive 监控**：表存储检查、分区健康、数据质量、查询性能、元数据管理
- **多环境支持**：dev/test/prod环境配置管理
- **Kerberos 支持**：安全认证集成
- **统一配置**：YAML配置文件，支持多实例
- **完善日志**：结构化日志，自动轮转
- **批量执行**：一键执行所有监控任务

## 📋 系统要求

- **Python**: 3.8+
- **操作系统**: Linux/Unix（推荐），macOS
- **内存**: 至少 4GB
- **磁盘空间**: 至少 1GB 可用空间
- **网络**: 能访问Hadoop集群各组件的REST API

## ⚡ 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd autoevs

# 创建并激活虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置文件设置

```bash
# 查看配置文件结构
ls config/prod/

# 编辑配置文件（根据实际环境修改）
vim config/prod/hive.yaml
vim config/prod/yarn.yaml
vim config/prod/hdfs.yaml
vim config/prod/mysql.yaml
```

**配置文件说明**：
- `hive.yaml` - Hive连接配置
- `yarn.yaml` - YARN ResourceManager配置
- `hdfs.yaml` - HDFS NameNode配置
- `mysql.yaml` - MySQL数据库配置
- `ambari.yaml` - Ambari管理配置

### 3. 数据库初始化

```bash
# 创建数据库表结构
mysql -u your_user -p your_database < sql/create_yarn_tables.sql
mysql -u your_user -p your_database < sql/create_hdfs_storage.sql
```

### 4. 运行示例

```bash
# 运行Hive完整监控
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod

# 采集YARN应用状态
python3 -m magicbox.periodic.yarn.collect_yarn_apps --cluster_name=hadoop-cluster --env=prod

# 采集HDFS存储信息
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=hadoop-cluster --ns_name=ns1 --env=prod

# 一键执行所有任务
./run_all_magicbox.sh --cluster hadoop-cluster
```

## 📁 项目结构

```
autoevs/
├── config/                    # 配置文件目录
│   ├── dev/                  # 开发环境配置
│   ├── test/                 # 测试环境配置
│   └── prod/                 # 生产环境配置
│       ├── hive.yaml         # Hive配置
│       ├── yarn.yaml         # YARN配置
│       ├── hdfs.yaml         # HDFS配置
│       ├── mysql.yaml        # MySQL配置
│       └── ambari.yaml       # Ambari配置
├── lib/                      # 核心库目录
│   ├── config/               # 配置管理
│   ├── hive/                 # Hive客户端
│   ├── yarn/                 # YARN客户端
│   ├── hdfs/                 # HDFS客户端
│   ├── mysql/                # MySQL客户端
│   ├── ambari/               # Ambari客户端
│   ├── http/                 # HTTP客户端
│   ├── os/                   # 操作系统客户端
│   ├── kerberos/             # Kerberos认证
│   └── logger/               # 日志管理
├── magicbox/                 # 功能模块目录
│   ├── monitor/              # 监控模块
│   │   └── hive/             # Hive监控
│   └── periodic/             # 定期任务模块
│       ├── yarn/             # YARN数据采集
│       └── hdfs/             # HDFS数据采集
├── sql/                      # 数据库脚本
│   ├── create_yarn_tables.sql
│   └── create_hdfs_storage.sql
├── logs/                     # 日志文件目录（运行时生成）
├── run_all_magicbox.sh       # 批量执行脚本
├── clean_project.sh          # 项目清理脚本
├── magicbox_commands.md      # 命令参考文档
├── requirements.txt          # Python依赖
└── README.md                 # 项目文档
```

## 🔧 核心模块说明

### 监控模块 (magicbox/monitor/)
- **Hive监控** (`hive_monitor.py`)：表存储检查、分区健康、数据质量、查询性能

### 定期任务模块 (magicbox/periodic/)
- **YARN采集**：
  - `collect_yarn_apps.py` - 应用状态统计
  - `collect_yarn_app_snapshots.py` - 应用详细快照
  - `collect_yarn_queues.py` - 队列资源信息
  - `collect_yarn_resources.py` - 集群资源管理
- **HDFS采集**：
  - `collect_hdfs_overview.py` - HDFS存储概览
  - `collect_hive_storage.py` - Hive数据库存储

### 客户端库 (lib/)
- **统一接口**：为各大数据组件提供统一的Python客户端接口
- **配置管理**：支持多环境、多实例配置
- **错误处理**：统一的异常处理和重试机制
- **认证支持**：支持Kerberos安全认证

## 📚 使用文档

### 快速命令参考
详见 [magicbox_commands.md](magicbox_commands.md)

### 常用命令

```bash
# 查看帮助
./run_all_magicbox.sh --help

# 使用默认配置（prod环境，hadoop-cluster集群，ns1命名空间）
./run_all_magicbox.sh

# 自定义集群名称
./run_all_magicbox.sh --cluster production-cluster

# 完全自定义
./run_all_magicbox.sh --env prod --cluster my-cluster --ns ns2

# 单独执行Hive监控
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod --debug

# 单独执行YARN监控
python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=hadoop-cluster --env=prod
```

## 🔧 开发指南

### 添加新的监控功能

1. **继承ScriptTemplate基类**：
```python
from magicbox.script_template import ScriptTemplate

class MyMonitor(ScriptTemplate):
    def __init__(self, env=None):
        super().__init__(env=env)
        # 初始化代码
```

2. **使用配置管理**：
```python
# 获取组件配置
config = self.get_component_config("component_name")
# 获取所有实例
instances = self.get_all_instances("component_name")
```

3. **使用客户端库**：
```python
from lib.hive.hive_client import HiveClient
from lib.yarn.yarn_client import YARNClient

# 创建客户端
hive_client = HiveClient(config)
yarn_client = YARNClient(config)
```

### 配置文件格式

```yaml
# 组件配置示例
version: "1.0"
default_instance: "default"

# 公共配置
common:
  timeout: 300
  retry_times: 3

# 实例配置
instances:
  default:
    host: "localhost"
    port: 8080
    username: "admin"
  
  instance2:
    host: "remote-host"
    port: 8080
```

### 代码规范

- **遵循PEP 8**：使用标准Python代码风格
- **类型注解**：为函数参数和返回值添加类型注解
- **错误处理**：使用try-except处理异常，记录详细错误信息
- **日志记录**：使用self.logger记录操作日志
- **文档字符串**：为类和函数添加docstring

### 测试

```bash
# 运行清理脚本
./clean_project.sh

# 测试单个功能
python3 -m magicbox.monitor.hive.hive_monitor --run=create_test_table --env=dev --debug

# 检查日志
tail -f logs/prod/HiveMonitor.log
```

## 🛠️ 运维部署

### 生产环境部署

1. **环境变量设置**：
```bash
export HADOOP_CONF_DIR=/etc/hadoop/conf
export HIVE_CONF_DIR=/etc/hive/conf
export AUTOEVS_ENV=prod
```

2. **Crontab定时任务**：
```bash
# 每小时执行一次完整监控
0 * * * * cd /path/to/autoevs && ./run_all_magicbox.sh --cluster production-cluster

# 每5分钟执行YARN监控
*/5 * * * * cd /path/to/autoevs && python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=production-cluster --env=prod
```

3. **监控脚本**：
```bash
# 检查进程状态
ps aux | grep magicbox

# 检查日志
tail -f logs/prod/*.log

# 磁盘清理
./clean_project.sh
```

### Docker部署（可选）

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x run_all_magicbox.sh

CMD ["./run_all_magicbox.sh"]
```

## 🐛 故障排除

### 常见问题

1. **连接失败**：
   - 检查网络连接和防火墙设置
   - 验证配置文件中的主机名和端口
   - 确认服务是否正常运行

2. **认证失败**：
   - 检查Kerberos票据：`klist`
   - 重新获取票据：`kinit username`
   - 验证配置文件中的认证信息

3. **权限不足**：
   - 确认用户有访问HDFS/Hive的权限
   - 检查MySQL用户权限
   - 验证文件系统权限

4. **配置错误**：
   - 使用`--debug`参数查看详细日志
   - 检查配置文件语法
   - 验证必需的配置项

5. **执行引擎问题**：
   - 确认集群支持指定的执行引擎（mr/tez/spark）
   - 检查执行引擎设置：`--run=check_execution_engine`
   - 如果Tez有问题，可以强制使用MapReduce：`--engine=mr`

### 日志分析

```bash
# 查看错误日志
grep -i error logs/prod/*.log

# 查看特定时间的日志
grep "2024-01-20 10:" logs/prod/HiveMonitor.log

# 实时监控日志
tail -f logs/prod/*.log | grep -i error
```

## 📈 性能优化

- **并发执行**：使用批量脚本可以并发执行多个任务
- **数据库优化**：合理设置连接池大小和超时时间
- **缓存机制**：配置信息会被缓存，减少重复读取
- **日志轮转**：自动日志轮转，避免日志文件过大

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 创建Pull Request

### 开发环境设置

```bash
# 使用开发环境配置
export AUTOEVS_ENV=dev

# 运行测试
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=dev --debug
```

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 📞 支持

- **问题反馈**：通过 GitHub Issues 提交问题
- **功能建议**：欢迎提出改进建议
- **文档改进**：帮助完善文档

---

**快速开始示例**：
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库连接
vim config/prod/mysql.yaml

# 3. 一键运行
./run_all_magicbox.sh --cluster your-cluster-name
``` 