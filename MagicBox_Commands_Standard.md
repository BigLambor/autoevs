# MagicBox 脚本标准化命令参考

## 📋 概述

所有命令默认配置：
- **Python解释器**：`python3`
- **环境**：`prod`  
- **命名空间**：`ns1`

## 🔍 监控脚本 (Monitor)

### 1. Hive 监控脚本
**路径**: `magicbox/monitor/hive/hive_monitor.py`

#### 基本命令格式
```bash
python3 -m magicbox.monitor.hive.hive_monitor --run=<函数名> [选项]
```

#### 执行引擎支持
支持指定Hive执行引擎，提高查询性能：
- `mr`: MapReduce引擎（默认，稳定性好）
- `tez`: Tez引擎（性能较好，适合复杂查询）
- `spark`: Spark引擎（内存计算，适合迭代计算）

#### 可用函数及标准命令
```bash
# 创建测试表
python3 -m magicbox.monitor.hive.hive_monitor --run=create_test_table --env=prod

# 删除测试表
python3 -m magicbox.monitor.hive.hive_monitor --run=drop_test_table --env=prod

# 添加测试分区
python3 -m magicbox.monitor.hive.hive_monitor --run=add_test_partition --env=prod

# 加载测试数据
python3 -m magicbox.monitor.hive.hive_monitor --run=load_test_data --env=prod

# 统计测试数据
python3 -m magicbox.monitor.hive.hive_monitor --run=count_test_data --env=prod

# 检查表存储格式
python3 -m magicbox.monitor.hive.hive_monitor --run=check_table_storage --env=prod

# 检查分区健康状态
python3 -m magicbox.monitor.hive.hive_monitor --run=check_partition_health --env=prod

# 检查数据质量
python3 -m magicbox.monitor.hive.hive_monitor --run=check_data_quality --env=prod

# 检查查询性能
python3 -m magicbox.monitor.hive.hive_monitor --run=check_query_performance --env=prod

# 检查执行引擎设置
python3 -m magicbox.monitor.hive.hive_monitor --run=check_execution_engine --env=prod

# 检查表元数据
python3 -m magicbox.monitor.hive.hive_monitor --run=check_table_metadata --env=prod

# 运行所有检查
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod

# 启用调试模式
python3 -m magicbox.monitor.hive.hive_monitor --run=check_table_storage --env=prod --debug

# 指定执行引擎示例
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod --engine=tez
python3 -m magicbox.monitor.hive.hive_monitor --run=check_query_performance --env=prod --engine=spark
python3 -m magicbox.monitor.hive.hive_monitor --run=check_table_storage --env=prod --engine=mr
```

#### 参数说明
- `--run`: 要执行的函数名（必需）
- `--env`: 环境名称，可选值：dev/test/prod（可选，默认prod）
- `--engine`: Hive执行引擎，可选值：mr/tez/spark（可选）
- `--debug`: 启用调试模式（可选）

---

## 📊 定期任务脚本 (Periodic Tasks)

### 2. YARN 应用状态采集
**路径**: `magicbox/periodic/yarn/collect_yarn_apps.py`

#### 标准命令
```bash
# 生产环境采集
python3 -m magicbox.periodic.yarn.collect_yarn_apps --cluster_name=hadoop-cluster --env=prod

# 自定义集群名称
python3 -m magicbox.periodic.yarn.collect_yarn_apps --cluster_name=my-hadoop-cluster --env=prod
```

#### 参数说明
- `--cluster_name`: 集群名称（必需）
- `--env`: 环境名称（可选，默认prod）

---

### 3. YARN 应用快照采集
**路径**: `magicbox/periodic/yarn/collect_yarn_app_snapshots.py`

#### 标准命令
```bash
# 采集所有状态的应用
python3 -m magicbox.periodic.yarn.collect_yarn_app_snapshots --cluster_name=hadoop-cluster --env=prod

# 采集指定状态的应用
python3 -m magicbox.periodic.yarn.collect_yarn_app_snapshots --cluster_name=hadoop-cluster --env=prod --states=RUNNING,FINISHED

# 采集失败应用
python3 -m magicbox.periodic.yarn.collect_yarn_app_snapshots --cluster_name=hadoop-cluster --env=prod --states=FAILED,KILLED
```

#### 参数说明
- `--cluster_name`: 集群名称（必需）
- `--env`: 环境名称（可选，默认prod）
- `--states`: 要采集的应用状态，多个状态用逗号分隔（可选）
  - 可用状态：NEW, NEW_SAVING, SUBMITTED, ACCEPTED, RUNNING, FINISHED, FAILED, KILLED

---

### 4. YARN 队列资源采集
**路径**: `magicbox/periodic/yarn/collect_yarn_queues.py`

#### 标准命令
```bash
# 采集队列资源信息
python3 -m magicbox.periodic.yarn.collect_yarn_queues --cluster_name=hadoop-cluster --env=prod

# 指定不同集群
python3 -m magicbox.periodic.yarn.collect_yarn_queues --cluster_name=spark-cluster --env=prod
```

#### 参数说明
- `--cluster_name`: 集群名称（必需）
- `--env`: 环境名称（可选，默认prod）

---

### 5. YARN 资源管理采集
**路径**: `magicbox/periodic/yarn/collect_yarn_resources.py`

#### 标准命令
```bash
# 采集YARN管理资源信息
python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=hadoop-cluster --env=prod

# 指定不同集群
python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=my-cluster --env=prod
```

#### 参数说明
- `--cluster_name`: 集群名称（必需）
- `--env`: 环境名称（可选，默认prod）

---

### 6. HDFS 概览信息采集
**路径**: `magicbox/periodic/hdfs/collect_hdfs_overview.py`

#### 标准命令
```bash
# 标准采集（使用默认ns1）
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=hadoop-cluster --ns_name=ns1 --env=prod

# 指定不同命名空间
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=hadoop-cluster --ns_name=ns2 --env=prod

# 指定不同集群和命名空间
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=prod-cluster --ns_name=ns1 --env=prod
```

#### 参数说明
- `--cluster_name`: 集群名称（必需）
- `--ns_name`: 命名空间名称（必需，默认ns1）
- `--env`: 环境名称（可选，默认prod）

---

### 7. Hive 存储信息采集
**路径**: `magicbox/periodic/hdfs/collect_hive_storage.py`

#### 标准命令
```bash
# 标准采集（使用默认ns1）
python3 -m magicbox.periodic.hdfs.collect_hive_storage --cluster_name=hadoop-cluster --ns_name=ns1 --env=prod

# 指定不同命名空间
python3 -m magicbox.periodic.hdfs.collect_hive_storage --cluster_name=hadoop-cluster --ns_name=ns2 --env=prod

# 指定不同集群
python3 -m magicbox.periodic.hdfs.collect_hive_storage --cluster_name=prod-cluster --ns_name=ns1 --env=prod
```

#### 参数说明
- `--cluster_name`: 集群名称（必需）
- `--ns_name`: 命名空间名称（必需，默认ns1）
- `--env`: 环境名称（可选，默认prod）

---

## 🔄 批量执行脚本

### 标准批量执行脚本
```bash
#!/bin/bash
# run_all_magicbox.sh - 批量执行所有MagicBox定期任务

# 默认配置
ENV="prod"
CLUSTER_NAME="hadoop-cluster"
NS_NAME="ns1"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --env)
      ENV="$2"
      shift 2
      ;;
    --cluster)
      CLUSTER_NAME="$2"
      shift 2
      ;;
    --ns)
      NS_NAME="$2"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      echo "用法: $0 [--env prod] [--cluster hadoop-cluster] [--ns ns1]"
      exit 1
      ;;
  esac
done

echo "=== MagicBox 批量执行开始 ==="
echo "环境: $ENV"
echo "集群: $CLUSTER_NAME"
echo "命名空间: $NS_NAME"
echo "==============================="

# YARN 相关采集
echo "🔄 执行 YARN 相关采集任务..."
python3 -m magicbox.periodic.yarn.collect_yarn_apps --cluster_name=$CLUSTER_NAME --env=$ENV
python3 -m magicbox.periodic.yarn.collect_yarn_app_snapshots --cluster_name=$CLUSTER_NAME --env=$ENV
python3 -m magicbox.periodic.yarn.collect_yarn_queues --cluster_name=$CLUSTER_NAME --env=$ENV
python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=$CLUSTER_NAME --env=$ENV

# HDFS 相关采集
echo "🔄 执行 HDFS 相关采集任务..."
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=$CLUSTER_NAME --ns_name=$NS_NAME --env=$ENV
python3 -m magicbox.periodic.hdfs.collect_hive_storage --cluster_name=$CLUSTER_NAME --ns_name=$NS_NAME --env=$ENV

# Hive 监控
echo "🔄 执行 Hive 监控任务..."
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=$ENV

echo "✅ 所有任务执行完成！"
```

### 使用批量脚本
```bash
# 使用默认配置（prod环境，hadoop-cluster集群，ns1命名空间）
chmod +x run_all_magicbox.sh
./run_all_magicbox.sh

# 自定义配置
./run_all_magicbox.sh --env prod --cluster my-cluster --ns ns2

# 仅指定集群名称
./run_all_magicbox.sh --cluster production-cluster
```

---

## 🛠️ 常用组合命令

### 完整的系统健康检查
```bash
# 1. HDFS健康检查
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=hadoop-cluster --ns_name=ns1 --env=prod

# 2. YARN资源检查
python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=hadoop-cluster --env=prod

# 3. Hive健康检查
python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=prod
```

### 应用监控组合
```bash
# 1. 采集当前运行的应用
python3 -m magicbox.periodic.yarn.collect_yarn_app_snapshots --cluster_name=hadoop-cluster --env=prod --states=RUNNING

# 2. 采集应用统计
python3 -m magicbox.periodic.yarn.collect_yarn_apps --cluster_name=hadoop-cluster --env=prod

# 3. 采集队列状态
python3 -m magicbox.periodic.yarn.collect_yarn_queues --cluster_name=hadoop-cluster --env=prod
```

### 存储分析组合
```bash
# 1. HDFS整体存储
python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=hadoop-cluster --ns_name=ns1 --env=prod

# 2. Hive数据库存储详情
python3 -m magicbox.periodic.hdfs.collect_hive_storage --cluster_name=hadoop-cluster --ns_name=ns1 --env=prod
```

---

## 📝 注意事项

1. **环境变量**：确保相关的Hadoop、Hive环境变量已正确设置
2. **权限**：确保执行用户有足够的权限访问HDFS、YARN和Hive
3. **Kerberos**：如果启用了Kerberos认证，确保票据有效
4. **网络**：确保能够访问相关的服务端点
5. **配置文件**：确保`config/prod/`目录下的配置文件正确配置

## 🔍 故障排除

### 常见错误和解决方案
```bash
# 查看详细日志
python3 -m magicbox.monitor.hive.hive_monitor --run=check_table_storage --env=prod --debug

# 检查配置文件
ls -la config/prod/

# 验证网络连接
curl -k https://your-yarn-rm:8088/ws/v1/cluster/info

# 检查Kerberos票据
klist
```

### 日志位置
- 日志目录：`logs/prod/`
- 日志命名：`<ClassName>.log`
- 日志轮转：10MB/文件，保留5个备份 