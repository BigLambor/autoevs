# AutoEVS

AutoEVS 是一个自动化运维工具集，专注于大数据平台的监控、管理和维护。

## 功能特点

- Hive 监控和管理
- 自动化运维任务
- 配置管理
- 日志管理
- 性能监控
- 故障诊断

## 系统要求

- Python 3.8+
- 操作系统：Linux/Unix（推荐），Windows（部分功能可能受限）
- 内存：至少 4GB
- 磁盘空间：至少 1GB 可用空间

## 快速开始

### 1. 安装

```bash
# 克隆代码库
git clone https://github.com/your-org/autoevs.git
cd autoevs

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制配置文件模板
cp config/dev/hive.yaml.example config/dev/hive.yaml

# 编辑配置文件
vim config/dev/hive.yaml
```

### 3. 运行

```bash
# 运行 Hive 监控
python -m magicbox.monitor.hive.hive_monitor --run=check_table_storage --env=dev

# 查看帮助
python -m magicbox.monitor.hive.hive_monitor --help
```

## 项目结构

```
autoevs/
├── config/           # 配置文件
│   ├── dev/         # 开发环境配置
│   ├── test/        # 测试环境配置
│   └── prod/        # 生产环境配置
├── magicbox/        # 核心功能模块
│   ├── monitor/     # 监控模块
│   ├── triggertask/ # 触发任务
│   └── periodictask/# 定期任务
├── lib/             # 公共库
│   ├── hive/        # Hive 相关
│   ├── os/          # 操作系统相关
│   └── logger/      # 日志相关
├── tests/           # 测试文件
├── docs/            # 文档
└── scripts/         # 工具脚本
```

## 文档

- [API 文档](docs/api/README.md)
- [部署指南](docs/deployment/README.md)
- [故障排除](docs/troubleshooting/README.md)
- [最佳实践](docs/best_practices/README.md)

## 主要功能

### Hive 监控

- 表存储检查
- 分区健康检查
- 数据质量检查
- 查询性能监控
- 元数据管理

### 自动化运维

- 定时任务
- 触发任务
- 告警管理
- 日志分析

### 配置管理

- 环境配置
- 组件配置
- 实例管理
- 配置验证

## 开发指南

### 代码风格

- 遵循 PEP 8 规范
- 使用类型注解
- 编写单元测试
- 保持代码简洁

### 提交规范

- 使用语义化提交信息
- 保持提交粒度适中
- 添加必要的注释
- 更新相关文档

### 测试规范

- 编写单元测试
- 编写集成测试
- 保持测试覆盖率
- 定期运行测试

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 版本历史

- v1.0.0 (2024-01-20)
  - 初始版本
  - 基础功能实现
  - 文档完善

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 联系方式

- 技术支持：support@example.com
- 问题报告：issues@example.com
- 文档更新：docs@example.com

## 致谢

感谢所有为本项目做出贡献的开发者。 