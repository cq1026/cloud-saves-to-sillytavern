# 如何获取 GitHub Personal Access Token

## 方法步骤

1. **登录 GitHub**
   - 访问 https://github.com

2. **进入 Settings**
   - 点击右上角头像 → **Settings**

3. **进入 Developer settings**
   - 左侧菜单滚动到底部 → **Developer settings**

4. **创建 Personal Access Token**
   - 左侧选择 **Personal access tokens** → **Tokens (classic)**
   - 点击右上角 **Generate new token** → **Generate new token (classic)**

5. **配置 Token**
   - **Note**（备注）：填写 `SillyTavern Backup`
   - **Expiration**（过期时间）：建议选择 `No expiration`（永不过期）
   - **Select scopes**（权限）：
     - ✅ 勾选 **repo**（完整仓库权限）
       - 这会自动勾选所有子选项

6. **生成 Token**
   - 点击底部绿色按钮 **Generate token**

7. **复制 Token**
   - ⚠️ **重要**：Token 只会显示一次！
   - Token 格式：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - 立即复制并保存到安全的地方

## 使用 Token

将 Token 添加到 `.env` 文件：

```bash
GITHUB_TOKEN=ghp_你复制的完整Token
```

## 安全提示

- ❌ **不要**将 Token 提交到 Git 仓库
- ❌ **不要**在公开场合分享 Token
- ✅ Token 已在 `.gitignore` 中排除
- ✅ 如果 Token 泄露，及时在 GitHub 上删除并重新生成

## 权限说明

勾选 **repo** 权限后，Token 可以：
- ✅ 读取私有仓库
- ✅ 推送到私有仓库
- ✅ 创建和删除仓库（本项目不需要）

如果只需要备份，**repo** 权限已足够。
