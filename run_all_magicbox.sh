#!/bin/bash
# run_all_magicbox.sh - 批量执行所有MagicBox定期任务
# 默认配置：python3, env=prod, ns=ns1

# 默认配置
ENV="prod"
CLUSTER_NAME="hadoop-cluster"
NS_NAME="ns1"

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --env ENV         设置环境名称 (默认: prod)"
    echo "  --cluster NAME    设置集群名称 (默认: hadoop-cluster)"
    echo "  --ns NAME         设置命名空间名称 (默认: ns1)"
    echo "  --help, -h        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                                    # 使用默认配置"
    echo "  $0 --cluster production-cluster      # 指定集群名称"
    echo "  $0 --env prod --cluster my-cluster --ns ns2  # 完全自定义"
    echo ""
}

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
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "错误: 未知参数 '$1'"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 验证参数
if [[ -z "$CLUSTER_NAME" ]]; then
    echo "错误: 集群名称不能为空"
    exit 1
fi

if [[ -z "$NS_NAME" ]]; then
    echo "错误: 命名空间名称不能为空"
    exit 1
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 执行命令的函数
execute_command() {
    local cmd="$1"
    local description="$2"
    
    log_info "执行: $description"
    log_info "命令: $cmd"
    
    if eval "$cmd"; then
        log_success "$description 执行成功"
        return 0
    else
        log_error "$description 执行失败"
        return 1
    fi
}

# 开始执行
echo "=============================================="
echo "🚀 MagicBox 批量任务执行器"
echo "=============================================="
echo "环境配置:"
echo "  Python版本: python3"
echo "  环境: $ENV"
echo "  集群: $CLUSTER_NAME"
echo "  命名空间: $NS_NAME"
echo "=============================================="

# 记录开始时间
START_TIME=$(date +%s)

# 任务计数器
TOTAL_TASKS=0
SUCCESS_TASKS=0
FAILED_TASKS=0

# YARN 相关采集任务
echo ""
log_info "📊 开始执行 YARN 相关采集任务..."

# 1. YARN 应用状态采集
TOTAL_TASKS=$((TOTAL_TASKS + 1))
if execute_command "python3 -m magicbox.periodic.yarn.collect_yarn_apps --cluster_name=$CLUSTER_NAME --env=$ENV" "YARN 应用状态采集"; then
    SUCCESS_TASKS=$((SUCCESS_TASKS + 1))
else
    FAILED_TASKS=$((FAILED_TASKS + 1))
fi

# 2. YARN 应用快照采集
TOTAL_TASKS=$((TOTAL_TASKS + 1))
if execute_command "python3 -m magicbox.periodic.yarn.collect_yarn_app_snapshots --cluster_name=$CLUSTER_NAME --env=$ENV" "YARN 应用快照采集"; then
    SUCCESS_TASKS=$((SUCCESS_TASKS + 1))
else
    FAILED_TASKS=$((FAILED_TASKS + 1))
fi

# 3. YARN 队列资源采集
TOTAL_TASKS=$((TOTAL_TASKS + 1))
if execute_command "python3 -m magicbox.periodic.yarn.collect_yarn_queues --cluster_name=$CLUSTER_NAME --env=$ENV" "YARN 队列资源采集"; then
    SUCCESS_TASKS=$((SUCCESS_TASKS + 1))
else
    FAILED_TASKS=$((FAILED_TASKS + 1))
fi

# 4. YARN 资源管理采集
TOTAL_TASKS=$((TOTAL_TASKS + 1))
if execute_command "python3 -m magicbox.periodic.yarn.collect_yarn_resources --cluster_name=$CLUSTER_NAME --env=$ENV" "YARN 资源管理采集"; then
    SUCCESS_TASKS=$((SUCCESS_TASKS + 1))
else
    FAILED_TASKS=$((FAILED_TASKS + 1))
fi

# HDFS 相关采集任务
echo ""
log_info "🗂️  开始执行 HDFS 相关采集任务..."

# 5. HDFS 概览信息采集
TOTAL_TASKS=$((TOTAL_TASKS + 1))
if execute_command "python3 -m magicbox.periodic.hdfs.collect_hdfs_overview --cluster_name=$CLUSTER_NAME --ns_name=$NS_NAME --env=$ENV" "HDFS 概览信息采集"; then
    SUCCESS_TASKS=$((SUCCESS_TASKS + 1))
else
    FAILED_TASKS=$((FAILED_TASKS + 1))
fi

# 6. Hive 存储信息采集
TOTAL_TASKS=$((TOTAL_TASKS + 1))
if execute_command "python3 -m magicbox.periodic.hdfs.collect_hive_storage --cluster_name=$CLUSTER_NAME --ns_name=$NS_NAME --env=$ENV" "Hive 存储信息采集"; then
    SUCCESS_TASKS=$((SUCCESS_TASKS + 1))
else
    FAILED_TASKS=$((FAILED_TASKS + 1))
fi

# Hive 监控任务
echo ""
log_info "🔍 开始执行 Hive 监控任务..."

# 7. Hive 完整监控
TOTAL_TASKS=$((TOTAL_TASKS + 1))
if execute_command "python3 -m magicbox.monitor.hive.hive_monitor --run=run_all --env=$ENV" "Hive 完整监控检查"; then
    SUCCESS_TASKS=$((SUCCESS_TASKS + 1))
else
    FAILED_TASKS=$((FAILED_TASKS + 1))
fi

# 计算执行时间
END_TIME=$(date +%s)
EXECUTION_TIME=$((END_TIME - START_TIME))

# 执行结果报告
echo ""
echo "=============================================="
echo "📈 执行结果报告"
echo "=============================================="
echo "总任务数: $TOTAL_TASKS"
echo -e "成功任务: ${GREEN}$SUCCESS_TASKS${NC}"
echo -e "失败任务: ${RED}$FAILED_TASKS${NC}"
echo "执行时间: ${EXECUTION_TIME}秒"
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"

if [[ $FAILED_TASKS -eq 0 ]]; then
    echo ""
    log_success "🎉 所有任务执行成功！"
    echo "=============================================="
    exit 0
else
    echo ""
    log_warning "⚠️  有 $FAILED_TASKS 个任务执行失败，请检查日志"
    echo "日志位置: logs/$ENV/"
    echo "=============================================="
    exit 1
fi 