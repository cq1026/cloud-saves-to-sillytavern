# SillyTavern 云备份系统

为 SillyTavern 提供基于 Git 和 GitHub 的自动化云备份解决方案。

## ✨ 特性

- 🔄 **自动定时备份**：每天自动备份到 GitHub 私有仓库
- 📦 **增量备份**：使用 Git 版本控制，仅上传变更部分
- 🔙 **版本恢复**：支持恢复到任意历史版本
- 🐳 **Docker 友好**：支持 Docker 和 Systemd 两种部署方式
- 🔒 **安全隔离**：不污染 SillyTavern 目录，仅读不写
- ⚙️ **灵活配置**：支持环境变量和配置文件两种配置方式
- 🚀 **GitHub Actions**：支持手动触发 Docker 镜像构建

## 📦 仓库架构

**重要**：本项目需要**两个独立的 GitHub 仓库**：

### 仓库 1: cloud-saves（项目代码仓库）- 当前仓库
- **用途**：存放备份系统的源代码
- **内容**：Python 代码、Dockerfile、GitHub Actions workflow
- **访问**：公开或私有均可

### 仓库 2: sillytavern-backup（数据备份仓库）- 需单独创建
- **用途**：存放 SillyTavern 的 data 目录备份
- **内容**：characters/、chats/、settings.json 等 ST 数据
- **访问**：**必须是私有仓库**（包含个人数据）
- **配置**：在 `.env` 中设置 `GITHUB_REMOTE_URL` 指向此仓库

```
cloud-saves 仓库 (代码)           sillytavern-backup 仓库 (数据)
      ↓                                    ↑
   部署到 VPS                         自动推送备份
      ↓                                    ↑
   运行备份程序  ──────────────────────────┘
```

## 📋 前置要求

### VPS 环境
- Debian/Ubuntu Linux（或其他支持 Docker 的系统）
- Python 3.11+（非 Docker 部署需要）
- Git（已安装）

### GitHub 准备

**创建两个仓库**：

1. **cloud-saves 仓库**（项目代码）- 你正在看的这个仓库
2. **sillytavern-backup 仓库**（数据备份）- 需要新建：
   - 进入 GitHub → New repository
   - 名称：`sillytavern-backup`（可自定义）
   - **重要**：设置为 **Private**（私有）
   - 不要添加 README、.gitignore 等文件（保持空仓库）

**配置 SSH 密钥认证**：

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your_email@example.com"

# 查看公钥并添加到 GitHub Settings > SSH Keys
cat ~/.ssh/id_ed25519.pub

# 测试连接
ssh -T git@github.com
```

## 🚀 快速开始

### 方式 1：Docker 部署（推荐）

```bash
# 1. 克隆项目
cd /opt
git clone <this-repo-url> cloud-saves
cd cloud-saves

# 2. 复制 .env 模板并编辑
cp .env.example .env
nano .env

# 修改以下配置：
#   - ST_DATA_PATH: SillyTavern 数据目录路径
#   - GITHUB_REMOTE_URL: 你的 GitHub 仓库地址

# 3. 启动容器
docker-compose up -d

# 4. 查看日志
docker logs -f sillytavern-backup
```

### 方式 2：Systemd 服务

```bash
# 1. 克隆项目
cd /opt
git clone <this-repo-url> cloud-saves
cd cloud-saves

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 复制配置文件示例并编辑
cp config.json.example config.json
nano config.json

# 4. 安装 systemd 服务
sudo cp cloud-saves.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cloud-saves
sudo systemctl start cloud-saves

# 5. 查看状态
sudo systemctl status cloud-saves
```

## ⚙️ 配置说明

### 环境变量（Docker 推荐）

复制 `.env.example` 为 `.env` 并编辑：

```bash
# .env 文件
ST_DATA_PATH=/var/sillytavern/data
BACKUP_REPO_PATH=/backup
GITHUB_REMOTE_URL=git@github.com:username/sillytavern-backup.git
BACKUP_TIME=03:00
AUTO_BACKUP_ENABLED=true
MAX_LOG_SIZE_MB=10
```

Docker Compose 会自动读取 `.env` 文件中的环境变量。

### 配置文件（Systemd 推荐）

编辑 `config.json`：

```json
{
  "sillytavern_data_path": "/var/sillytavern/data",
  "backup_repo_path": "/var/backups/sillytavern-backup",
  "github_remote_url": "git@github.com:username/sillytavern-backup.git",
  "backup_time": "03:00",
  "max_log_size_mb": 10,
  "enable_auto_backup": true
}
```

> **注意**：环境变量优先级高于配置文件

## 📖 使用指南

### 手动备份

```bash
# Docker 部署
docker exec sillytavern-backup python backup.py

# Systemd 部署
cd /opt/cloud-saves
python3 backup.py
```

### 手动恢复

```bash
# Docker 部署
docker exec -it sillytavern-backup python restore.py

# Systemd 部署
cd /opt/cloud-saves
python3 restore.py
```

恢复流程会：
1. 列出所有可用的历史版本
2. 让你选择要恢复的版本
3. 自动备份当前数据到 `/tmp/st-backup-<timestamp>`
4. 将选定版本恢复到 SillyTavern data 目录

### 查看日志

```bash
# Docker 部署
docker logs -f sillytavern-backup
tail -f logs/backup.log

# Systemd 部署
sudo journalctl -u cloud-saves -f
tail -f /opt/cloud-saves/logs/backup.log
```

### 查看备份历史

```bash
# Docker 部署
docker exec sillytavern-backup sh -c "cd /backup && git log --oneline"

# Systemd 部署
cd /var/backups/sillytavern-backup
git log --oneline --graph
```

## 🔧 高级操作

### 更改备份时间

**Docker**：
```bash
# 编辑 docker-compose.yml
nano docker-compose.yml
# 修改 BACKUP_TIME 环境变量

# 重启容器
docker-compose restart
```

**Systemd**：
```bash
# 编辑配置文件
nano /opt/cloud-saves/config.json
# 修改 backup_time 字段

# 重启服务
sudo systemctl restart cloud-saves
```

### 禁用自动备份

**Docker**：
```yaml
environment:
  - AUTO_BACKUP_ENABLED=false
```

**Systemd**：
```json
{
  "enable_auto_backup": false
}
```

### 停止服务

```bash
# Docker
docker-compose down

# Systemd
sudo systemctl stop cloud-saves
sudo systemctl disable cloud-saves
```

### 使用 GitHub Actions 构建镜像

如果你不想在本地构建 Docker 镜像，可以使用 GitHub Actions：

1. **手动触发构建**：
   - 进入 GitHub 仓库 → Actions 标签
   - 选择 "构建 Docker 镜像" workflow
   - 点击 "Run workflow"
   - 选择是否推送到 GitHub Container Registry

2. **使用预构建镜像**：
   ```yaml
   # docker-compose.yml
   services:
     cloud-saves:
       image: ghcr.io/USERNAME/cloud-saves:latest  # 使用预构建镜像
       # build: .  # 注释掉本地构建
   ```

详细说明见 [.github/ACTIONS.md](.github/ACTIONS.md)

## ❓ 常见问题

### 1. GitHub 推送失败（认证错误）

**问题**：`Permission denied (publickey)` 或 `Authentication failed`

**解决**：
```bash
# 检查 SSH 密钥
ssh -T git@github.com

# 如果失败，重新配置 SSH 密钥
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub  # 添加到 GitHub
```

### 2. Docker 容器无法访问 SillyTavern 数据

**问题**：`源目录不存在`

**解决**：检查 `docker-compose.yml` 中的卷挂载路径是否正确：
```yaml
volumes:
  - /var/sillytavern/data:/data:ro  # 确保左侧路径正确
```

### 3. 单个文件超过 100MB

**问题**：GitHub 限制单个文件最大 100MB

**解决**：
- 检查 SillyTavern data 目录，删除不必要的大文件
- 或使用 Git LFS（需额外配置）

### 4. 如何更换 GitHub 仓库？

```bash
# Docker：编辑 docker-compose.yml 的 GITHUB_REMOTE_URL
# Systemd：编辑 config.json 的 github_remote_url

# 然后删除旧的备份仓库重新初始化
rm -rf /var/backups/sillytavern-backup  # Systemd
docker volume rm cloud-saves_backup-repo  # Docker
```

## 🔒 安全说明

### 本项目的安全特性

- ✅ **无端口监听**：仅进行出站连接（连接 GitHub）
- ✅ **无攻击面**：不运行 Web 服务器，无网络风险
- ✅ **只读挂载**：SillyTavern 数据以只读方式挂载
- ✅ **私有仓库**：备份存储在 GitHub 私有仓库
- ✅ **SSH 认证**：使用 SSH 密钥，不存储密码

### 文件权限建议

```bash
# 保护配置文件（仅所有者可读写）
chmod 600 config.json

# 保护 SSH 私钥（自动设置）
chmod 600 ~/.ssh/id_ed25519
```

### .gitignore 保护

项目已配置 `.gitignore`，避免意外提交敏感文件：
- `config.json`（实际配置）
- `logs/`（日志文件）
- `backup-repo/`（本地备份仓库）

## 📁 项目结构

```
cloud-saves/
├── .github/
│   ├── workflows/
│   │   └── docker-build.yml # GitHub Actions workflow
│   └── ACTIONS.md           # Actions 使用说明
├── main.py                  # 主程序（守护进程）
├── backup.py                # 备份模块
├── restore.py               # 恢复模块
├── config.py                # 配置管理
├── logger.py                # 日志管理
├── requirements.txt         # Python 依赖
├── config.json.example      # 配置模板（Systemd 用）
├── .env.example             # 环境变量模板（Docker 用）
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # Docker Compose 配置
├── cloud-saves.service      # Systemd 服务配置
├── .gitignore               # Git 忽略文件
├── .dockerignore            # Docker 忽略文件
└── README.md                # 本文件
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
