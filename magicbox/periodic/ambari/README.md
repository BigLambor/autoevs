# Ambari 集群清单采集脚本

## 功能概述

该脚本用于采集 Ambari 管理的集群完整清单信息，包括：
- 集群基本信息
- 服务和组件信息
- 主机详细信息
- 角色分类和映射关系

## 🆕 新功能：智能组件分类

### 自动学习功能
脚本现在支持从 Ambari API 自动学习组件角色分类，**无需手动配置**！

**工作原理：**
1. **从 Ambari 获取元数据**：读取服务组件的 `category` 和 `cardinality` 信息
2. **智能分类算法**：
   - `category=MASTER` → MASTER 角色
   - `category=SLAVE` → WORKER 角色  
   - `category=CLIENT` → CLIENT 角色
   - `cardinality=1,1-2,2` → 通常是 MASTER
   - `cardinality=1+,0+` → 通常是 WORKER
   - `cardinality=ALL` → 通常是 CLIENT
3. **关键词后备匹配**：基于组件名称进行智能推断
4. **配置文件优先**：手动配置的规则优先级更高

### 支持的分类方式

1. **完全自动** (推荐)
   ```bash
   python collect_ambari_inventory.py
   ```
   - 从 Ambari 自动学习所有组件分类
   - 与配置文件规则智能合并

2. **仅使用配置文件**
   ```bash
   python collect_ambari_inventory.py --disable-auto-learn
   ```
   - 禁用自动学习，仅使用 `config/ambari_service_rules.yaml`

3. **保存学习结果**
   ```bash
   python collect_ambari_inventory.py --save-learned-rules
   ```
   - 将学习到的规则保存到 `config/learned_ambari_rules_<集群名>.yaml`
   - 方便查看和后续手动配置

## 使用方法

### 基本使用
```bash
# 自动学习模式（推荐）
python collect_ambari_inventory.py --env prod

# 禁用自动学习
python collect_ambari_inventory.py --env prod --disable-auto-learn

# 保存学习规则到文件
python collect_ambari_inventory.py --env prod --save-learned-rules
```

### 命令行参数
- `--env`: 指定环境 (dev/test/prod)
- `--disable-auto-learn`: 禁用自动学习功能
- `--save-learned-rules`: 保存学习到的规则到文件

## 配置文件

### 主配置文件：`config/{env}/ambari_service_rules.yaml`
```yaml
service_component_rules:
  HDFS:
    master_components: ['NAMENODE', 'SECONDARY_NAMENODE', 'JOURNALNODE']
    worker_components: ['DATANODE']
    client_components: ['HDFS_CLIENT']
  # ... 更多服务配置

default_rules:
  master_keywords: ['MASTER', 'SERVER', 'MANAGER', 'COORDINATOR']
  worker_keywords: ['WORKER', 'NODE', 'EXECUTOR', 'DATANODE']
  client_keywords: ['CLIENT', 'GATEWAY']
```

### 自动生成的学习文件：`config/{env}/learned_ambari_rules_<集群名>.yaml`
```yaml
metadata:
  cluster_name: "my_cluster"
  generated_time: "2025-06-25 08:00:00"
  total_services: 8
  total_components: 25

service_component_rules:
  FLINK:
    master_components: ['FLINK_JOBMANAGER']
    worker_components: ['FLINK_TASKMANAGER']
    client_components: ['FLINK_CLIENT']
  # ... 自动学习的规则

component_metadata:
  FLINK.FLINK_JOBMANAGER:
    category: "MASTER"
    cardinality: "1"
    service_name: "FLINK"
  # ... 详细的组件元数据
```

## 数据存储

### 数据库表结构

#### ambari_cluster_inventory (集群清单表)
- 扁平化存储所有集群、服务、组件、主机信息
- 包含智能分类的角色信息 (`is_master`, `is_worker`, `role_category`)

#### ambari_cluster_stats (集群统计表)  
- 集群级别的统计信息
- 服务、主机、组件的数量和状态统计

## 智能分类示例

### 自动识别的服务组件

| 服务 | 组件 | Ambari元数据 | 自动分类 |
|-----|------|-------------|----------|
| HDFS | NAMENODE | category=MASTER, cardinality=1-2 | MASTER |
| HDFS | DATANODE | category=SLAVE, cardinality=1+ | WORKER |
| HDFS | HDFS_CLIENT | category=CLIENT, cardinality=ALL | CLIENT |
| Flink | FLINK_JOBMANAGER | category="", cardinality=1 | MASTER (基于名称) |
| Flink | FLINK_TASKMANAGER | category="", cardinality=1+ | WORKER (基于名称) |
| Kafka | KAFKA_BROKER | category=MASTER, cardinality=1+ | MASTER |

### 扩展新服务

当集群中部署了新服务（如 Pulsar、Presto 等），脚本会：

1. **自动发现**：从 Ambari API 获取新服务的组件信息
2. **智能分类**：基于元数据和名称自动分类
3. **动态合并**：将新规则与现有配置合并
4. **日志记录**：记录新发现的服务和组件

## 故障排除

### 常见问题

1. **Ambari 连接失败**
   - 检查 `config/<env>/ambari.yaml` 配置
   - 确认网络连接和认证信息

2. **MySQL 连接失败**  
   - 脚本会继续运行但不保存数据
   - 检查 `config/<env>/mysql.yaml` 配置

3. **组件分类不准确**
   - 使用 `--save-learned-rules` 查看学习结果
   - 在 `config/{env}/ambari_service_rules.yaml` 中手动调整
   - 手动配置的规则优先级更高

### 调试技巧

```bash
# 查看详细日志
tail -f logs/<env>/AmbariInventoryCollector.log

# 保存学习规则进行分析
python collect_ambari_inventory.py --save-learned-rules

# 禁用自动学习测试配置文件
python collect_ambari_inventory.py --disable-auto-learn
```

## 最佳实践

1. **首次运行**：使用 `--save-learned-rules` 查看自动学习结果
2. **生产环境**：验证分类准确性后再启用自动学习
3. **新服务部署**：重新运行脚本自动发现新组件
4. **定期检查**：定期查看日志中的"未配置服务组件"信息
5. **手动优化**：将常用的准确规则添加到配置文件中

## 技术优势

- ✅ **零配置启动**：无需手动配置即可运行
- ✅ **智能适应**：自动适应新服务和组件
- ✅ **向后兼容**：完全兼容现有配置文件
- ✅ **灵活控制**：支持启用/禁用自动学习
- ✅ **可视化结果**：可保存学习规则供分析
- ✅ **高准确性**：基于 Ambari 官方元数据分类

## 概述

本目录包含 Ambari 集群清单采集的相关脚本，用于采集 Ambari 管理的 Hadoop 集群中的所有服务、组件、主机信息，并存储到扁平化的数据库表中。

## 文件说明

### 脚本文件

- `collect_ambari_inventory.py` - 主要的数据采集脚本
- `test_ambari_connection.py` - 连接测试脚本，用于验证 Ambari API 连接

### 数据库表

相关的数据库建表语句位于 `sql/create_ambari_tables.sql`，包含：

- `ambari_cluster_inventory` - 集群清单详细信息表（扁平化）
- `ambari_cluster_stats` - 集群统计信息表

## 数据采集内容

### 集群清单信息 (ambari_cluster_inventory)

每条记录包含以下信息：
- **集群信息**: 集群名称、ID、版本、状态
- **服务信息**: 服务名称、状态、版本
- **组件信息**: 组件名称、状态、版本
- **主机信息**: 主机名、IP、操作系统、硬件配置、状态
- **角色映射**: Master/Worker角色分类

### 集群统计信息 (ambari_cluster_stats)

- 服务总数及各状态服务数量
- 主机总数及健康状态统计
- 组件总数及状态统计

## 使用方法

### 1. 前置条件

确保以下配置文件正确配置：
- `config/{env}/ambari.yaml` - Ambari 连接配置
- `config/{env}/mysql.yaml` - MySQL 数据库配置

### 2. 创建数据库表

```bash
# 在 MySQL 中执行建表语句
mysql -h your_host -u your_user -p your_database < sql/create_ambari_tables.sql
```

### 3. 测试连接

在运行正式采集之前，建议先运行测试脚本验证连接：

```bash
# 使用默认环境
python magicbox/periodic/ambari/test_ambari_connection.py

# 指定环境
python magicbox/periodic/ambari/test_ambari_connection.py --env dev
```

### 4. 运行采集脚本

```bash
# 使用默认环境
python magicbox/periodic/ambari/collect_ambari_inventory.py

# 指定环境
python magicbox/periodic/ambari/collect_ambari_inventory.py --env dev
```

## 配置说明

### Ambari 配置 (ambari.yaml)

```yaml
version: "2.7.5"
default_instance: "ambari"

common:
  base_url: "http://ambari-server:8080/api/v1"
  username: "admin"
  password: "admin"
  cluster_name: "your-cluster"
  timeout: 30
  verify_ssl: true
```

### MySQL 配置 (mysql.yaml)

```yaml
host: "mysql-server"
port: 3306
username: "mysql_user"
password: "mysql_password"
database: "your_database"
```

## 数据表结构

### ambari_cluster_inventory 表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| cluster_name | VARCHAR(100) | 集群名称 |
| service_name | VARCHAR(100) | 服务名称 |
| component_name | VARCHAR(100) | 组件名称 |
| host_name | VARCHAR(255) | 主机名 |
| host_ip | VARCHAR(50) | 主机IP |
| is_master | BOOLEAN | 是否为Master角色 |
| is_worker | BOOLEAN | 是否为Worker角色 |
| role_category | VARCHAR(50) | 角色类别 |

### ambari_cluster_stats 表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| cluster_name | VARCHAR(100) | 集群名称 |
| total_services | INT | 服务总数 |
| total_hosts | INT | 主机总数 |
| total_components | INT | 组件总数 |

## 角色分类规则

脚本会自动将组件分类为以下角色：

### Master 组件
- HDFS: NAMENODE, SECONDARY_NAMENODE, JOURNALNODE
- YARN: RESOURCEMANAGER, APP_TIMELINE_SERVER
- HIVE: HIVE_METASTORE, HIVE_SERVER
- HBASE: HBASE_MASTER
- ZOOKEEPER: ZOOKEEPER_SERVER

### Worker 组件
- HDFS: DATANODE
- YARN: NODEMANAGER
- HBASE: HBASE_REGIONSERVER

### Client 组件
- 其他所有组件

## 定时任务

可以将脚本配置为定时任务，建议的执行频率：
- **清单采集**: 每天1次（凌晨执行）
- **统计信息**: 每小时1次

示例 crontab 配置：
```bash
# 每天凌晨2点执行清单采集
0 2 * * * /path/to/python /path/to/collect_ambari_inventory.py --env prod

# 每小时执行一次统计采集（仅统计部分）
0 * * * * /path/to/python /path/to/collect_ambari_inventory.py --env prod
```

## 扩展说明

如需扩展更多数据采集功能，可以：

1. 在 `collect_ambari_inventory.py` 中添加新的采集方法
2. 修改数据库表结构以支持新字段
3. 更新角色分类规则以支持新的服务组件

## 支持的 Ambari 版本

- Ambari 2.6.x
- Ambari 2.7.x

建议使用最新版本的 Ambari 以获得最佳兼容性。 