-- Hive数据库存储信息表
CREATE TABLE IF NOT EXISTS hive_db_storage (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    cluster_name VARCHAR(100) NOT NULL COMMENT '集群名称',
    ns_name VARCHAR(100) NOT NULL COMMENT '命名空间名称',
    db_name VARCHAR(100) NOT NULL COMMENT '数据库名称',
    collect_time DATETIME NOT NULL COMMENT '数据采集时间(命令执行时间)',
    insert_time DATETIME NOT NULL COMMENT '数据插入时间(写入数据库时间)',
    storage_size BIGINT NOT NULL COMMENT '存储大小(字节)',
    dir_count BIGINT NOT NULL COMMENT '目录数量',
    file_count BIGINT NOT NULL COMMENT '文件数量',
    INDEX idx_cluster_ns_db (cluster_name, ns_name, db_name) COMMENT '集群、命名空间和数据库索引',
    INDEX idx_collect_time (collect_time) COMMENT '采集时间索引',
    INDEX idx_insert_time (insert_time) COMMENT '插入时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hive数据库存储信息表';

-- 创建HDFS NameNode状态表
CREATE TABLE IF NOT EXISTS hdfs_namenode_status (
    cluster_name VARCHAR(64) NOT NULL COMMENT '集群名称',
    ns_name VARCHAR(64) NOT NULL COMMENT '命名空间名称',
    collect_time DATETIME NOT NULL COMMENT '采集时间',
    insert_time DATETIME NOT NULL COMMENT '插入时间',
    live_datanodes INT NOT NULL COMMENT '存活的DataNode数量',
    dead_datanodes INT NOT NULL COMMENT '死亡的DataNode数量',
    bad_blocks INT NOT NULL COMMENT '坏块数量',
    blocks INT NOT NULL COMMENT '总块数',
    configured_capacity BIGINT NOT NULL COMMENT '配置的总容量(字节)',
    dfs_used BIGINT NOT NULL COMMENT 'DFS已使用容量(字节)',
    dfs_remaining BIGINT NOT NULL COMMENT 'DFS剩余容量(字节)',
    PRIMARY KEY (cluster_name, ns_name, collect_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='HDFS NameNode状态表';

-- 创建HDFS集群存储表
CREATE TABLE IF NOT EXISTS hdfs_cluster_storage (
    cluster_name VARCHAR(64) NOT NULL COMMENT '集群名称',
    ns_name VARCHAR(64) NOT NULL COMMENT '命名空间名称',
    collect_time DATETIME NOT NULL COMMENT '采集时间',
    insert_time DATETIME NOT NULL COMMENT '插入时间',
    total_capacity BIGINT NOT NULL COMMENT '总容量(字节)',
    used_capacity BIGINT NOT NULL COMMENT '已使用容量(字节)',
    remaining_capacity BIGINT NOT NULL COMMENT '剩余容量(字节)',
    used_percentage DECIMAL(5,2) NOT NULL COMMENT '使用率(%)',
    total_dirs INT NOT NULL COMMENT '总目录数',
    total_files INT NOT NULL COMMENT '总文件数',
    PRIMARY KEY (cluster_name, ns_name, collect_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='HDFS集群存储表'; 