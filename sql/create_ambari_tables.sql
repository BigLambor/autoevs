-- Ambari集群清单信息表
CREATE TABLE IF NOT EXISTS ambari_cluster_inventory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    -- 采集元数据
    collect_time DATETIME NOT NULL COMMENT '数据采集时间',
    insert_time DATETIME NOT NULL COMMENT '数据插入时间',
    
    -- 集群信息
    cluster_name VARCHAR(100) NOT NULL COMMENT '集群名称',
    cluster_id VARCHAR(100) DEFAULT NULL COMMENT '集群ID',
    cluster_version VARCHAR(50) DEFAULT NULL COMMENT '集群版本',
    cluster_state VARCHAR(50) DEFAULT NULL COMMENT '集群状态',
    
    -- 服务信息
    service_name VARCHAR(100) NOT NULL COMMENT '服务名称',
    service_state VARCHAR(50) DEFAULT NULL COMMENT '服务状态',
    service_version VARCHAR(50) DEFAULT NULL COMMENT '服务版本',
    
    -- 组件信息
    component_name VARCHAR(100) NOT NULL COMMENT '组件名称',
    component_state VARCHAR(50) DEFAULT NULL COMMENT '组件状态',
    component_version VARCHAR(50) DEFAULT NULL COMMENT '组件版本',
    
    -- 主机信息
    host_name VARCHAR(255) NOT NULL COMMENT '主机名',
    host_ip VARCHAR(50) DEFAULT NULL COMMENT '主机IP地址',
    host_os VARCHAR(100) DEFAULT NULL COMMENT '操作系统',
    host_cpu_count INT DEFAULT NULL COMMENT 'CPU核心数',
    host_memory_mb BIGINT DEFAULT NULL COMMENT '内存大小(MB)',
    host_disk_gb BIGINT DEFAULT NULL COMMENT '磁盘大小(GB)',
    host_state VARCHAR(50) DEFAULT NULL COMMENT '主机状态',
    
    -- 角色映射信息
    is_master BOOLEAN DEFAULT FALSE COMMENT '是否为Master角色',
    is_worker BOOLEAN DEFAULT FALSE COMMENT '是否为Worker角色',
    role_category VARCHAR(50) DEFAULT NULL COMMENT '角色类别',
    
    -- 索引设计
    INDEX idx_cluster_name (cluster_name) COMMENT '集群名称索引',
    INDEX idx_collect_time (collect_time) COMMENT '采集时间索引',
    INDEX idx_service_component (service_name, component_name) COMMENT '服务组件索引',
    INDEX idx_host_name (host_name) COMMENT '主机名索引',
    INDEX idx_cluster_collect_time (cluster_name, collect_time) COMMENT '集群采集时间复合索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Ambari集群清单信息表';

-- Ambari集群服务统计表
CREATE TABLE IF NOT EXISTS ambari_cluster_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    cluster_name VARCHAR(100) NOT NULL COMMENT '集群名称',
    collect_time DATETIME NOT NULL COMMENT '数据采集时间',
    insert_time DATETIME NOT NULL COMMENT '数据插入时间',
    
    -- 统计信息
    total_services INT NOT NULL DEFAULT 0 COMMENT '服务总数',
    running_services INT NOT NULL DEFAULT 0 COMMENT '运行中服务数',
    stopped_services INT NOT NULL DEFAULT 0 COMMENT '停止的服务数',
    total_hosts INT NOT NULL DEFAULT 0 COMMENT '主机总数',
    healthy_hosts INT NOT NULL DEFAULT 0 COMMENT '健康主机数',
    unhealthy_hosts INT NOT NULL DEFAULT 0 COMMENT '不健康主机数',
    total_components INT NOT NULL DEFAULT 0 COMMENT '组件总数',
    started_components INT NOT NULL DEFAULT 0 COMMENT '已启动组件数',
    installed_components INT NOT NULL DEFAULT 0 COMMENT '已安装组件数',
    
    -- 索引
    INDEX idx_cluster_collect_time (cluster_name, collect_time) COMMENT '集群采集时间索引',
    UNIQUE KEY uk_cluster_collect_time (cluster_name, collect_time) COMMENT '集群采集时间唯一约束'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Ambari集群服务统计表'; 