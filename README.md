# SillyTavern 云备份

自动备份 SillyTavern 数据到 GitHub 私有仓库。

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> cloud-saves
cd cloud-saves

# 2. 配置环境变量
cp .env.example .env
nano .env  # 修改配置

# 3. 启动
docker-compose up -d
```

## 配置说明

编辑 `.env` 文件：

```bash
ST_DATA_PATH=/path/to/sillytavern/data  # ST 数据目录
GITHUB_REMOTE_URL=https://github.com/user/repo.git  # 备份仓库（需私有）
GITHUB_TOKEN=ghp_xxxxx  # GitHub Token
BACKUP_TIME=03:00  # 备份时间
```

## 使用

```bash
# 交互式菜单
docker exec -it sillytavern-backup python menu.py

# 手动备份
docker exec sillytavern-backup python backup.py

# 查看日志
docker logs -f sillytavern-backup
```

## 菜单功能

1. 执行手动备份（支持自定义描述）
2. 列出并拉取备份版本
3. 修改存档描述
4. 删除云端存档
5. 比较存档差异（支持备份间对比）

## 注意事项

- ⚠️ 备份仓库必须设为**私有**
- 🔒 使用 GitHub Token 认证（HTTPS）
- 📦 数据只读，不会修改 ST 源文件
- 🔄 恢复时拉取到本地，需手动复制到 ST 目录

## 许可证

MIT
