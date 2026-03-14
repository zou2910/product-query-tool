# 🚀 Streamlit Cloud 部署指南

## 📋 部署前准备

### 1. 注册必要账号

- **GitHub**: https://github.com (已有账号: 523217860@qq.com)
- **Streamlit Cloud**: https://streamlit.io/cloud
- **Neon** (免费 PostgreSQL): https://neon.tech

---

## 🗄️ 第一步：创建 Neon 数据库

1. 访问 https://neon.tech 并注册账号
2. 创建新项目
3. 创建数据库（名称建议: `product_db`）
4. 复制数据库连接字符串，格式如下：
   ```
   postgresql://username:password@hostname/database?sslmode=require
   ```

---

## 📦 第二步：准备 GitHub 仓库

### 2.1 创建新仓库

1. 登录 GitHub
2. 点击右上角 "+" → "New repository"
3. 仓库名称: `product-query-tool`
4. 选择 "Public" 或 "Private"
5. 点击 "Create repository"

### 2.2 上传代码

在本地项目目录执行：

```bash
# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: Cloud version with auth"

# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/product-query-tool.git

# 推送代码
git branch -M main
git push -u origin main
```

---

## ☁️ 第三步：部署到 Streamlit Cloud

### 3.1 连接 GitHub

1. 访问 https://streamlit.io/cloud
2. 使用 GitHub 账号登录
3. 点击 "New app"
4. 选择仓库: `product-query-tool`
5. 分支: `main`
6. 主文件路径: `app_cloud.py`

### 3.2 配置 Secrets

在 Streamlit Cloud 界面中：

1. 点击 "Advanced settings"
2. 找到 "Secrets" 部分
3. 添加以下配置：

```toml
JWT_SECRET = "your-random-secret-key-here-min-32-characters"
DATABASE_URL = "postgresql://username:password@hostname/database?sslmode=require"
```

> ⚠️ **重要**: 
> - `JWT_SECRET` 使用随机生成的长字符串（至少32位）
> - `DATABASE_URL` 使用 Neon 提供的连接字符串

### 3.3 部署

点击 "Deploy" 按钮，等待部署完成。

---

## 🔧 第四步：初始化数据库

部署完成后，首次访问应用时：

1. 使用默认管理员账号登录：
   - 用户名: `邹宏`
   - 密码: `123456`

2. 进入 "➕ 数据管理" 标签页

3. 上传你的 `IT编码.xlsx` 文件导入数据

---

## 📊 费用说明

| 服务 | 费用 | 免费额度 |
|------|------|---------|
| GitHub | 免费 | 无限公共仓库 |
| Streamlit Cloud | 免费 | 1GB内存，无限流量 |
| Neon PostgreSQL | 免费 | 500MB存储 |
| **总计** | **¥0/月** | - |

---

## 🔐 默认账号

部署后可以使用以下账号登录：

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| 邹宏 | 123456 | admin | 所有功能 |
| test | 123456 | user | 查询+数据管理 |

---

## 🛠️ 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 本地运行（使用 SQLite）
streamlit run app_cloud.py
```

---

## 📝 注意事项

1. **数据备份**: 定期从 Neon 控制台导出数据
2. **休眠机制**: Streamlit Cloud 长时间不访问会休眠，首次访问需等待约30秒唤醒
3. **文件上传**: 临时文件存储在内存中，重启会清空
4. **并发限制**: 免费版适合小团队使用（建议10人以内）

---

## 🆘 常见问题

### Q1: 部署失败怎么办？

检查以下几点：
- requirements.txt 是否包含所有依赖
- app_cloud.py 是否在仓库根目录
- Secrets 是否正确配置

### Q2: 数据库连接失败？

- 检查 DATABASE_URL 格式是否正确
- 确认 Neon 数据库是否允许外部连接
- 检查 SSL 模式设置

### Q3: 如何更新代码？

```bash
git add .
git commit -m "Update"
git push origin main
```

Streamlit Cloud 会自动重新部署。

---

## 📞 技术支持

如有问题，请联系开发者。
