# AutoEVS - 大数据平台自动化运维工具

AutoEVS 是一个企业级的大数据平台自动化运维工具集，专注于 Hadoop 生态系统的监控、数据采集和运维管理。项目采用模块化架构设计，支持多环境部署，提供统一的配置管理和安全的密码加密机制。

## 🚀 核心特性

### 📊 全面监控
- **YARN 监控**：应用状态统计、应用快照采集、队列资源监控、集群资源管理
- **HDFS 监控**：存储概览、NameNode状态、容量分析、Hive存储统计
- **Hive 监控**：表存储检查、分区健康、数据质量、查询性能、元数据管理
- **Ambari 监控**：集群清单采集、服务状态统计、主机健康监控

### 🏗️ 企业级架构
- **模板化设计**：统一的脚本基类，标准化开发模式
- **多环境支持**：dev/test/prod 环境完全隔离
- **多实例配置**：支持同一组件的多个实例管理
- **统一配置管理**：YAML 格式配置，支持配置继承和合并

### 🔒 安全与稳定
- **密码加密**：支持敏感信息加密存储，自动解密机制
- **Kerberos 集成**：支持安全认证，企业级安全保障
- **完善日志**：轮转日志机制，结构化日志输出
- **错误处理**：统一异常处理，重试机制，优雅降级

### ⚡ 运维友好
- **批量执行**：一键执行所有监控任务
- **命令标准化**：统一的命令行接口和参数规范
- **灵活调度**：支持 Crontab 定时任务，适配各种调度系统
- **数据持久化**：MySQL 数据存储，完整的表结构设计

## 📋 系统要求

### 基础环境
- **Python**: 3.8+ （推荐 3.9+）
- **操作系统**: Linux/Unix（CentOS 7+, Ubuntu 18+），macOS
- **内存**: 至少 4GB （推荐 8GB+）
- **磁盘空间**: 至少 2GB 可用空间
- **数据库**: MySQL 5.7+ 或 8.0+

### 网络访问
- Hadoop 集群各组件的 REST API 端口
- MySQL 数据库连接端口
- 如启用 Kerberos，需访问 KDC 服务

### Hadoop 生态版本兼容性
- **Hadoop**: 2.7+, 3.x
- **Hive**: 2.3+, 3.x
- **HBase**: 1.4+, 2.x
- **Ambari**: 2.7+

## ⚡ 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd autoevs

# 创建并激活虚拟环境（强烈推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 密码加密（推荐）

```bash
# 生成加密种子
python3 tools/generate_seed.py

# 设置环境变量（建议加入 ~/.bashrc）
export AUTOEVS_CRYPTO_SEED='your_generated_seed'

# 加密配置文件中的密码
python3 tools/encrypt_passwords.py --config config/prod/mysql.yaml --dry-run
python3 tools/encrypt_passwords.py --config config/prod/mysql.yaml
```

### 3. 配置文件设置

```bash
# 复制并编辑配置文件
cp config/prod/mysql.yaml.example config/prod/mysql.yaml  # 如果有示例文件
vim config/prod/mysql.yaml

# 配置各组件连接信息
vim config/prod/hive.yaml
vim config/prod/yarn.yaml
vim config/prod/hdfs.yaml
vim config/prod/ambari.yaml
```

**关键配置文件说明**：
```yaml
# mysql.yaml - MySQL数据库配置
host: "mysql-server"
port: 3306
username: "autoevs_user"
password: "encrypted_password_here"  # 使用加密工具加密
database: "autoevs"

# hive.yaml - Hive连接配置（支持多实例）
version: "3.1.3"
default_instance: "hive"
instances:
  hive:
    host: "hive-server"
    port: 10000
    metastore_host: "metastore-server"
    metastore_port: 9083
```

### 4. 数据库初始化

```bash
# 创建数据库和用户
mysql -u root -p << EOF
CREATE DATABASE autoevs DEFAULT CHARACTER SET utf8mb4;
CREATE USER 'autoevs_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON autoevs.* TO 'autoevs_user'@'%';
FLUSH PRIVILEGES;
EOF

# 创建表结构
mysql -u autoevs_user -p autoevs < sql/create_yarn_tables.sql
mysql -u autoevs_user -p autoevs < sql/create_hdfs_storage.sql
mysql -u autoevs_user -p autoevs < sql/create_ambari_tables.sql
```

### 5. 验证安装

```bash
# 测试 Hive 连接
python3 -m magicbox.monitor.hive.hive_monitor --run=check_execution_engine --env=prod --debug

# 测试 YARN 连接
python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=test-cluster --env=prod

# 一键执行所有任务（使用默认配置）
./run_all_magicbox.sh --cluster hadoop-cluster
```

## 📁 项目架构

```
autoevs/
├── 📂 config/                    # 多环境配置文件
│   ├── dev/                     # 开发环境配置
│   ├── test/                    # 测试环境配置
│   └── prod/                    # 生产环境配置
│       ├── hive.yaml           # Hive 多实例配置
│       ├── yarn.yaml           # YARN ResourceManager 配置
│       ├── hdfs.yaml           # HDFS NameNode 配置
│       ├── mysql.yaml          # MySQL 数据库配置
│       ├── ambari.yaml         # Ambari 管理平台配置
│       ├── hbase.yaml          # HBase 配置
│       └── kerberos.yaml.example # Kerberos 认证配置示例
│
├── 📂 lib/                       # 核心库模块
│   ├── config/                  # 统一配置管理
│   │   └── config_manager.py   # 配置管理器（支持加密解密）
│   ├── security/                # 安全模块
│   │   ├── crypto_utils.py     # 密码加密解密工具
│   │   └── field_detector.py   # 智能密码字段检测
│   ├── hive/                    # Hive 客户端
│   ├── yarn/                    # YARN 客户端  
│   ├── hdfs/                    # HDFS 客户端
│   ├── mysql/                   # MySQL 数据库客户端
│   ├── ambari/                  # Ambari REST API 客户端
│   ├── http/                    # 通用 HTTP 客户端
│   ├── os/                      # 操作系统命令执行
│   ├── kerberos/                # Kerberos 认证集成
│   └── logger/                  # 日志管理模块
│
├── 📂 magicbox/                  # 功能模块
│   ├── script_template.py       # 脚本基类模板
│   ├── monitor/                 # 监控模块
│   │   └── hive/               # Hive 深度监控
│   │       └── hive_monitor.py # 表健康、性能、质量检查
│   ├── periodic/                # 定期采集任务
│   │   ├── yarn/               # YARN 数据采集
│   │   │   ├── collect_yarn_apps.py          # 应用状态统计
│   │   │   ├── collect_yarn_app_snapshots.py # 应用详细快照
│   │   │   ├── collect_yarn_queues.py        # 队列资源信息
│   │   │   └── collect_yarn_resources.py     # 集群资源管理
│   │   ├── hdfs/               # HDFS 数据采集
│   │   │   ├── collect_hdfs_overview.py      # HDFS 存储概览
│   │   │   └── collect_hive_storage.py       # Hive 存储统计
│   │   └── ambari/             # Ambari 集群管理
│   │       ├── collect_ambari_inventory.py   # 集群清单采集
│   │       └── README.md       # Ambari 模块详细说明
│   └── trigger/                 # 触发器模块（预留扩展）
│
├── 📂 sql/                       # 数据库脚本
│   ├── create_yarn_tables.sql   # YARN 监控表结构
│   ├── create_hdfs_storage.sql  # HDFS 存储表结构
│   └── create_ambari_tables.sql # Ambari 管理表结构
│
├── 📂 tools/                     # 运维工具
│   ├── encrypt_passwords.py     # 密码加密工具
│   └── generate_seed.py         # 加密种子生成器
│
├── 📂 logs/                      # 运行时日志目录
│   ├── dev/                     # 开发环境日志
│   ├── test/                    # 测试环境日志
│   └── prod/                    # 生产环境日志
│
├── run_all_magicbox.sh          # 批量执行脚本
├── clean_project.sh             # 项目清理脚本
├── magicbox_commands.md         # 详细命令参考
├── MagicBox_Commands_Standard.md # 标准化命令手册
├── README_password_encryption.md # 密码加密使用指南
├── requirements.txt             # Python 依赖包
└── README.md                    # 项目文档
```

## 🔧 核心功能模块

### 监控模块 (magicbox/monitor/)

#### Hive 深度监控 (`hive_monitor.py`)
- **表存储检查**：存储格式、压缩方式、文件格式验证
- **分区健康检查**：分区完整性、数据分布、异常分区检测
- **数据质量检查**：数据一致性、空值检测、重复数据分析
- **查询性能检查**：执行引擎性能对比、查询优化建议
- **元数据管理**：表结构变更跟踪、权限检查

```bash
# 支持多种执行引擎
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod --engine=tez
python3 -m magicbox.monitor.hive.hive_monitor --run=check_query_performance --env=prod --engine=spark
```

### 定期任务模块 (magicbox/periodic/)

#### YARN 数据采集
- **应用状态统计** (`collect_yarn_apps.py`)：各状态应用数量统计
- **应用详细快照** (`collect_yarn_app_snapshots.py`)：应用完整信息采集
- **队列资源监控** (`collect_yarn_queues.py`)：队列配置和使用情况
- **集群资源管理** (`collect_yarn_resources.py`)：节点状态、资源利用率

#### HDFS 存储分析
- **存储概览采集** (`collect_hdfs_overview.py`)：集群容量、使用率统计
- **Hive 存储统计** (`collect_hive_storage.py`)：数据库级别存储分析

#### Ambari 集群管理
- **集群清单采集** (`collect_ambari_inventory.py`)：
  - 自动学习组件角色分类
  - 主机和服务映射关系
  - 集群健康状态统计
  - 支持自定义分类规则

### 客户端库 (lib/)

#### 统一架构设计
- **配置管理** (`config/config_manager.py`)：
  - 多环境配置隔离
  - 多实例配置支持
  - 配置继承和合并
  - 自动密码解密
- **安全模块** (`security/`)：
  - 密码加密解密 (`crypto_utils.py`)
  - 智能字段检测 (`field_detector.py`)
- **统一错误处理**：标准化异常处理和重试机制
- **Kerberos 认证**：企业级安全认证集成

## 📚 使用指南

### 命令行界面

所有脚本都遵循统一的命令行规范：

```bash
# 基本格式
python3 -m <模块路径> --参数名=参数值 [--选项]

# 常用参数
--env=prod          # 环境名称（dev/test/prod）
--cluster_name=集群名 # 集群标识
--debug             # 调试模式
--help              # 帮助信息
```

### 快速命令参考

```bash
# =============================================================================
# 🔍 监控检查命令
# =============================================================================

# Hive 完整健康检查
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod

# 指定执行引擎的性能检查
python3 -m magicbox.monitor.hive.hive_monitor --run=check_query_performance --env=prod --engine=tez

# 表存储格式检查
python3 -m magicbox.monitor.hive.hive_monitor --run=check_table_storage --env=prod --debug

# =============================================================================
# 📊 数据采集命令
# =============================================================================

# YARN 应用状态采集
python3 -m magicbox.periodic.yarn.collect_yarn_apps --cluster_name=hadoop-cluster --env=prod

# YARN 资源管理采集
python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=hadoop-cluster --env=prod

# HDFS 存储概览采集
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=hadoop-cluster --ns_name=ns1 --env=prod

# Ambari 集群清单采集
python3 -m magicbox.periodic.ambari.collect_ambari_inventory --env=prod

# =============================================================================
# 🚀 批量执行命令
# =============================================================================

# 使用默认配置执行所有任务
./run_all_magicbox.sh

# 指定集群执行
./run_all_magicbox.sh --cluster production-cluster

# 完全自定义配置
./run_all_magicbox.sh --env prod --cluster my-cluster --ns ns2

# 查看执行帮助
./run_all_magicbox.sh --help
```

### 配置文件管理

#### 多环境配置
```bash
# 环境配置结构
config/
├── dev/     # 开发环境：连接测试集群，调试日志级别
├── test/    # 测试环境：连接预发布集群，完整功能测试
└── prod/    # 生产环境：连接生产集群，优化性能配置
```

#### 多实例配置示例
```yaml
# hive.yaml
version: "3.1.3"
default_instance: "hive_primary"

common:
  timeout: 300
  retry_times: 3
  
instances:
  hive_primary:
    host: "hive-primary.company.com"
    port: 10000
    metastore_host: "metastore-primary.company.com"
    metastore_port: 9083
    
  hive_backup:
    host: "hive-backup.company.com"
    port: 10000
    metastore_host: "metastore-backup.company.com"
    metastore_port: 9083
```

### 密码安全管理

#### 加密密码流程
```bash
# 1. 生成加密种子（只需执行一次）
python3 tools/generate_seed.py

# 2. 设置环境变量
export AUTOEVS_CRYPTO_SEED='your_production_seed'

# 3. 预览要加密的字段
python3 tools/encrypt_passwords.py --config config/prod/mysql.yaml --dry-run

# 4. 加密配置文件
python3 tools/encrypt_passwords.py --config config/prod/mysql.yaml

# 5. 批量加密所有配置
python3 tools/encrypt_passwords.py --pattern "config/prod/*.yaml"
```

## 🛠️ 运维部署

### 生产环境部署

#### 1. 环境变量配置
```bash
# ~/.bashrc 或 ~/.profile
export AUTOEVS_ENV=prod
export AUTOEVS_CRYPTO_SEED='your_production_seed'
export HADOOP_CONF_DIR=/etc/hadoop/conf
export HIVE_CONF_DIR=/etc/hive/conf

# Kerberos 环境（如果需要）
export KRB5_CONFIG=/etc/krb5.conf
```

#### 2. 系统服务配置
```bash
# 创建系统用户
sudo useradd -r -m -s /bin/bash autoevs

# 部署代码
sudo cp -r autoevs /opt/
sudo chown -R autoevs:autoevs /opt/autoevs

# 创建日志目录
sudo mkdir -p /var/log/autoevs
sudo chown autoevs:autoevs /var/log/autoevs
```

#### 3. Crontab 定时任务
```bash
# 编辑 autoevs 用户的 crontab
sudo -u autoevs crontab -e

# 添加定时任务
# 每小时执行一次完整监控
0 * * * * cd /opt/autoevs && ./run_all_magicbox.sh --cluster production-cluster >> /var/log/autoevs/cron.log 2>&1

# 每15分钟执行 YARN 资源监控
*/15 * * * * cd /opt/autoevs && python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=production-cluster --env=prod

# 每天凌晨2点执行 Ambari 集群清单采集
0 2 * * * cd /opt/autoevs && python3 -m magicbox.periodic.ambari.collect_ambari_inventory --env=prod

# 每周日凌晨3点执行日志清理
0 3 * * 0 cd /opt/autoevs && ./clean_project.sh
```

#### 4. 监控和告警
```bash
# 健康检查脚本
#!/bin/bash
# health_check.sh

LOG_DIR="/var/log/autoevs"
ERROR_COUNT=$(grep -c "ERROR\|CRITICAL" $LOG_DIR/prod/*.log)

if [ $ERROR_COUNT -gt 0 ]; then
    echo "发现 $ERROR_COUNT 个错误，请检查日志"
    # 发送告警邮件或钉钉消息
fi

# 检查磁盘空间
DISK_USAGE=$(df /opt/autoevs | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "磁盘使用率超过80%: ${DISK_USAGE}%"
fi
```

### Docker 部署（可选）

```dockerfile
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    default-mysql-client \
    krb5-user \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p logs/prod

# 设置执行权限
RUN chmod +x run_all_magicbox.sh clean_project.sh

# 环境变量
ENV AUTOEVS_ENV=prod

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "from lib.config.config_manager import ConfigManager; ConfigManager()" || exit 1

# 默认命令
CMD ["./run_all_magicbox.sh"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  autoevs:
    build: .
    environment:
      - AUTOEVS_ENV=prod
      - AUTOEVS_CRYPTO_SEED=${AUTOEVS_CRYPTO_SEED}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - /etc/hadoop/conf:/etc/hadoop/conf:ro
      - /etc/hive/conf:/etc/hive/conf:ro
    depends_on:
      - mysql
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=autoevs
      - MYSQL_USER=autoevs_user
      - MYSQL_PASSWORD=autoevs_password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./sql:/docker-entrypoint-initdb.d
    restart: unless-stopped

volumes:
  mysql_data:
```

## 🔧 开发指南

### 添加新的监控功能

#### 1. 继承脚本模板基类
```python
from magicbox.script_template import ScriptTemplate

class MyCustomMonitor(ScriptTemplate):
    def __init__(self, env=None):
        super().__init__(env=env)
        # 自定义初始化逻辑
        self.my_client = self._create_client()
    
    def _create_client(self):
        """创建客户端连接"""
        config = self.get_component_config("my_component")
        # 返回客户端实例
        
    def check_something(self, **kwargs):
        """自定义检查功能"""
        self.logger.info("开始执行自定义检查")
        try:
            # 实现检查逻辑
            result = {"status": "success", "data": "检查结果"}
            self.logger.info("检查完成")
            return result
        except Exception as e:
            self.logger.error(f"检查失败: {str(e)}")
            raise
```

#### 2. 配置文件设计
```yaml
# config/prod/my_component.yaml
version: "1.0"
default_instance: "primary"

common:
  timeout: 300
  retry_times: 3
  
instances:
  primary:
    host: "component-server"
    port: 8080
    username: "admin"
    password: "encrypted_password"
```

#### 3. 命令行接口
```python
def parse_args():
    parser = argparse.ArgumentParser(description='自定义监控脚本')
    parser.add_argument('--run', required=True, help='执行的函数名')
    parser.add_argument('--env', choices=['dev', 'test', 'prod'], help='环境')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    return parser.parse_args()

def main():
    args = parse_args()
    script = MyCustomMonitor(env=args.env)
    
    if args.debug:
        script.logger.setLevel(logging.DEBUG)
    
    result = script.run_function(args.run)
    script.logger.info(f"执行结果: {result}")

if __name__ == "__main__":
    main()
```

### 数据库表设计规范

```sql
-- 表命名规范：{组件}_{功能}_{类型}
CREATE TABLE IF NOT EXISTS my_component_monitor_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    cluster_name VARCHAR(100) NOT NULL COMMENT '集群名称',
    collect_time DATETIME NOT NULL COMMENT '数据采集时间',
    insert_time DATETIME NOT NULL COMMENT '数据插入时间',
    
    -- 业务字段
    metric_name VARCHAR(100) NOT NULL COMMENT '指标名称',
    metric_value DECIMAL(15,2) NOT NULL COMMENT '指标值',
    
    -- 索引设计
    INDEX idx_cluster_collect_time (cluster_name, collect_time),
    INDEX idx_metric_name (metric_name),
    INDEX idx_insert_time (insert_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自定义组件监控统计表';
```

### 代码规范和最佳实践

#### 1. 日志记录规范
```python
# 标准日志级别使用
self.logger.debug("调试信息：变量值为 {value}")
self.logger.info("正常操作：开始执行某项任务")
self.logger.warning("警告信息：配置项缺失，使用默认值")
self.logger.error("错误信息：操作失败，错误原因")
self.logger.critical("严重错误：系统无法继续运行")

# 包含上下文信息
self.logger.info(f"开始处理集群 {cluster_name} 的 {component} 组件")
```

#### 2. 异常处理规范
```python
def robust_operation(self):
    """健壮的操作示例"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 执行操作
            result = self._do_operation()
            self.logger.info("操作执行成功")
            return result
        except ConnectionError as e:
            self.logger.warning(f"连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                self.logger.error("所有重试都失败，放弃操作")
                raise
            time.sleep(2 ** attempt)  # 指数退避
        except Exception as e:
            self.logger.error(f"未预期的错误: {str(e)}")
            raise
```

#### 3. 配置验证
```python
def validate_and_get_config(self):
    """配置验证示例"""
    required_keys = ['host', 'port', 'username', 'password']
    
    if not self.validate_config('my_component', required_keys):
        raise ValueError("配置验证失败")
    
    config = self.get_component_config('my_component')
    
    # 额外的业务验证
    if config['port'] < 1 or config['port'] > 65535:
        raise ValueError(f"无效的端口号: {config['port']}")
    
    return config
```

## 🐛 故障排除

### 常见问题诊断

#### 1. 连接问题
```bash
# 检查网络连通性
telnet yarn-resourcemanager 8088
curl -k "https://ambari-server:8080/api/v1/clusters"

# 检查 Kerberos 认证
klist -v
kinit username@REALM

# 检查 Hadoop 配置
hadoop classpath
hdfs dfsadmin -report
```

#### 2. 配置问题
```bash
# 验证配置文件语法
python3 -c "
import yaml
with open('config/prod/hive.yaml') as f:
    config = yaml.safe_load(f)
    print('配置文件语法正确')
    print(f'配置内容: {config}')
"

# 检查密码解密
python3 -c "
from lib.config.config_manager import ConfigManager
cm = ConfigManager('prod')
config = cm.get_component_config('mysql')
print('MySQL配置加载成功')
"
```

#### 3. 权限问题
```bash
# 检查文件权限
ls -la config/prod/
ls -la logs/prod/

# 检查数据库权限
mysql -u autoevs_user -p -e "SHOW GRANTS FOR CURRENT_USER;"

# 检查 HDFS 权限
hdfs dfs -ls /user/$(whoami)
```

### 调试技巧

#### 1. 启用详细日志
```bash
# 单个脚本调试
python3 -m magicbox.monitor.hive.hive_monitor --run=check_table_storage --env=dev --debug

# 修改日志级别
export AUTOEVS_LOG_LEVEL=DEBUG
```

#### 2. 逐步验证
```bash
# 1. 验证基础连接
python3 -c "
from lib.hive.hive_client import HiveClient
from lib.config.config_manager import ConfigManager

cm = ConfigManager('prod')
config = cm.get_component_config('hive')
client = HiveClient(config)
print('Hive 连接测试成功')
"

# 2. 验证 SQL 执行
python3 -c "
# ... 连接代码 ...
result = client.execute_sql('SHOW DATABASES')
print(f'数据库列表: {result}')
"
```

#### 3. 性能分析
```bash
# 使用 time 命令测量执行时间
time python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod

# 使用 cProfile 进行性能分析
python3 -m cProfile -o profile.stats -m magicbox.monitor.hive.hive_monitor --run=check_query_performance --env=prod

# 分析性能结果
python3 -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"
```

### 日志分析

#### 1. 快速错误检查
```bash
# 查看最近的错误
grep -i "error\|exception\|failed" logs/prod/*.log | tail -20

# 按时间过滤错误
grep -i error logs/prod/HiveMonitor.log | grep "$(date '+%Y-%m-%d')"

# 统计错误类型
grep -i error logs/prod/*.log | cut -d':' -f3- | sort | uniq -c | sort -nr
```

#### 2. 性能监控
```bash
# 查看执行时间
grep "执行时间\|execution time" logs/prod/*.log

# 监控内存使用
grep -i "memory\|内存" logs/prod/*.log

# 实时监控日志
tail -f logs/prod/*.log | grep -i "error\|warning\|info"
```

## 📈 性能优化

### 1. 数据库优化
```sql
-- 添加必要的索引
CREATE INDEX idx_collect_time_cluster ON yarn_application_stats(collect_time, cluster_name);
CREATE INDEX idx_application_id_collect_time ON yarn_application_snapshots(application_id, collect_time);

-- 定期清理历史数据
DELETE FROM yarn_application_snapshots WHERE collect_time < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 优化表结构
OPTIMIZE TABLE yarn_application_stats;
ANALYZE TABLE yarn_application_snapshots;
```

### 2. 应用级优化
```python
# 连接池配置
mysql_config = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_pre_ping': True,
    'pool_recycle': 3600
}

# 批量插入优化
def batch_insert_data(self, table_name, data_list, batch_size=1000):
    """批量插入数据"""
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i + batch_size]
        self.mysql_client.batch_insert(table_name, batch)
```

### 3. 系统级优化
```bash
# 调整 Python 垃圾回收
export PYTHONHASHSEED=0
export PYTHONDONTWRITEBYTECODE=1

# 增加文件描述符限制
ulimit -n 65536

# 优化 MySQL 连接数
# my.cnf
[mysqld]
max_connections = 500
innodb_buffer_pool_size = 2G
query_cache_size = 128M
```

## 🤝 贡献指南

### 开发环境设置
```bash
# 1. Fork 项目并克隆
git clone https://github.com/your-username/autoevs.git
cd autoevs

# 2. 创建开发分支
git checkout -b feature/new-feature

# 3. 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如果有开发依赖

# 4. 配置开发环境
cp config/dev/mysql.yaml.example config/dev/mysql.yaml
# 编辑配置文件...

# 5. 运行测试
python3 -m pytest tests/  # 如果有测试用例
```

### 代码提交规范
```bash
# 提交信息格式
git commit -m "类型(范围): 简短描述

详细描述（可选）

关联问题: #123"

# 类型说明
feat:     新功能
fix:      Bug 修复
docs:     文档更新
style:    代码格式调整
refactor: 重构
test:     测试相关
chore:    构建/工具链相关
```

### Pull Request 流程
1. 确保代码通过所有测试
2. 更新相关文档
3. 添加变更日志条目
4. 创建 Pull Request
5. 等待代码审查

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持与社区

### 获取帮助
- **GitHub Issues**: [提交问题和 Bug 报告](https://github.com/your-org/autoevs/issues)
- **讨论区**: [功能建议和使用讨论](https://github.com/your-org/autoevs/discussions)
- **Wiki**: [详细文档和FAQ](https://github.com/your-org/autoevs/wiki)

### 快速链接
- 📖 [详细命令参考](magicbox_commands.md)
- 🔒 [密码加密指南](README_password_encryption.md)
- 🚀 [标准化命令手册](MagicBox_Commands_Standard.md)
- 🔧 [Ambari 模块说明](magicbox/periodic/ambari/README.md)

---

## 🎯 快速开始总结

```bash
# 🚀 30秒快速启动
git clone <repository-url> && cd autoevs
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 📝 配置数据库连接
vim config/prod/mysql.yaml

# 🗄️ 初始化数据库
mysql -u user -p database < sql/create_yarn_tables.sql

# ▶️ 执行监控任务
./run_all_magicbox.sh --cluster your-cluster-name

# 🎉 开始监控您的大数据平台！
```

**AutoEVS** - 让大数据平台运维更简单、更智能、更可靠！ 