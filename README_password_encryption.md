# 配置文件密码加密 - 快速开始

> 🔐 使用 `ENCRYPTED:` 前缀 + 种子加密的安全方案

## 问题解决

✅ **解决配置文件明文密码问题**  
✅ **通过安全扫描检查**  
✅ **应用代码零修改**  
✅ **支持多环境管理**

## 5分钟快速上手

### 1️⃣ 安装依赖
```bash
pip install cryptography>=41.0.0
```

### 2️⃣ 生成种子
```bash
# 为当前环境生成种子
python tools/seed_generator.py

# 输出示例：
# ✅ 种子生成完成
# 📁 环境文件: .env.dev
# 🔑 种子变量: AUTOEVS_CRYPTO_SEED
# ⚠️  请确保 .env.dev 不被提交到版本控制系统
```

### 3️⃣ 加密密码
```bash
# 加密单个密码
python tools/encrypt_passwords.py --mode single

# 输出示例：
# 🔐 密码加密工具
# 输入要加密的密码：[输入你的密码]
# ✅ 加密完成
# 📋 密文: ENCRYPTED:gAAAAABhZ1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0
# 💡 请将此密文复制到配置文件中
```

### 4️⃣ 更新配置文件
```yaml
# 原配置文件 config/dev/mysql.yaml
instances:
  mysql:
    host: "mysql.example.com"
    port: 3306
    user: "root"
    password: "dev123"  # 明文密码
    database: "autoevs_dev"

# 更新后的配置文件
instances:
  mysql:
    host: "mysql.example.com"
    port: 3306
    user: "root"
    password: "ENCRYPTED:gAAAAABhZ1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0"
    database: "autoevs_dev"
```

### 5️⃣ 应用代码无需修改
```python
# 原有代码继续工作，密码自动解密
from lib.config.config_manager import ConfigManager

config_manager = ConfigManager(env='dev')
mysql_config = config_manager.get_component_config('mysql')

# password 字段已自动解密为明文 "dev123"
print(mysql_config['password'])  # 输出: dev123
```

## 批量加密示例

```bash
# 预览所有需要加密的密码
python tools/encrypt_passwords.py --mode batch --dry-run

# 批量加密所有配置文件
python tools/encrypt_passwords.py --mode batch

# 只加密生产环境配置
python tools/encrypt_passwords.py --mode batch --pattern "config/prod/*.yaml"
```

## 多环境使用

```bash
# 开发环境
export AUTOEVS_ENV=dev
python tools/seed_generator.py

# 生产环境
export AUTOEVS_ENV=prod
python tools/seed_generator.py

# 使用不同环境的配置
python -c "
from lib.config.config_manager import ConfigManager
config = ConfigManager(env='prod').get_component_config('mysql')
print('生产环境MySQL密码已解密')
"
```

## 测试验证

```bash
# 运行完整测试
python tools/test_encryption.py

# 输出示例：
# 🧪 AutoEVS 加密解密功能测试
# ==================================================
# 🔧 测试加密解密核心功能...
# ✅ 成功
# 
# 📊 测试结果汇总:
# 加密解密核心功能: ✅ 通过
# 字段检测功能: ✅ 通过
# 配置管理器: ✅ 通过
# 集成测试: ✅ 通过
# 🎉 所有测试通过！加密解密功能正常工作
```

## 核心特性

### 🎯 智能字段识别
自动识别以下密码字段：
- `password`, `passwd`, `secret`, `key`, `token`
- `admin_password`, `metastore_password`, `mysql_password`
- 任何包含 "password" 的字段名

### 🛡️ 安全排除
自动排除以下非密码字段：
- `password_policy`, `password_length`
- `key_id`, `key_type`, `public_key`
- `token_type`, `token_expiry`

### 🔄 向后兼容
- 支持明文和加密密码混合使用
- 渐进式迁移，无需一次性全部加密
- 现有应用代码零修改

### 🌍 多环境支持
- 不同环境使用不同种子
- 环境隔离，提高安全性
- 自动环境检测和配置加载

## 文件结构

加密功能完成后，项目结构如下：

```
autoevs/
├── lib/security/           # 安全模块
│   ├── crypto_utils.py     # 加密解密核心
│   ├── field_detector.py   # 字段识别
│   └── __init__.py
├── tools/                  # 工具脚本
│   ├── seed_generator.py   # 种子生成器
│   ├── encrypt_passwords.py # 密码加密工具
│   └── test_encryption.py  # 测试工具
├── config/                 # 配置文件
│   ├── dev/               # 开发环境（可能包含加密密码）
│   ├── test/              # 测试环境
│   └── prod/              # 生产环境
├── .env.dev               # 开发环境种子文件
├── .env.test              # 测试环境种子文件
├── .env.prod              # 生产环境种子文件
└── docs/
    └── password_encryption_guide.md  # 详细使用指南
```

## 注意事项

⚠️ **重要提醒**：
1. 种子文件 `.env.*` 绝不能提交到版本控制
2. 加密前请备份原配置文件
3. 种子丢失将导致所有密码无法解密
4. 生产环境建议设置文件权限 `chmod 600 .env.prod`

## 下一步

1. 📖 查看详细文档：`docs/password_encryption_guide.md`
2. 🧪 运行完整测试：`python tools/test_encryption.py`
3. 🚀 开始加密你的配置文件！

---

*通过这个方案，您的配置文件将通过所有安全扫描，同时保持应用的正常运行。* 