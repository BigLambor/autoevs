# Ambari 集群清单采集脚本

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

## 故障排除

### 常见问题

1. **连接失败**
   - 检查 Ambari 服务器地址和端口
   - 验证用户名密码
   - 确认网络连通性

2. **数据采集不完整**
   - 检查 Ambari API 权限
   - 查看日志中的警告信息
   - 验证集群服务状态

3. **数据库写入失败**
   - 检查 MySQL 连接配置
   - 确认数据库表已创建
   - 验证数据库权限

### 日志查看

脚本运行时会输出详细的日志信息，包括：
- 连接状态
- 数据采集进度
- 错误和警告信息
- 统计结果

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