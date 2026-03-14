# 📦 商品资料查询工具 - 云端版

基于 Streamlit 的商品资料查询系统，支持用户登录认证，可部署到云端免费使用。

## ✨ 功能特性

- 🔐 **用户认证**：支持多用户登录，角色权限管理
- 🔍 **单条查询**：输入款式编码和颜色规格快速查询
- 📊 **批量查询**：上传 Excel/CSV 文件批量处理
- ➕ **数据管理**：追加、删除商品数据（需权限）
- 👥 **用户管理**：管理员可创建/删除用户（仅管理员）
- 🎯 **智能匹配**：款式编码自动取前13个字符，颜色支持模糊匹配
- ☁️ **云端部署**：支持 Streamlit Cloud 免费部署

## 🚀 快速开始

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run app_cloud.py
```

访问 http://localhost:8501

### 默认登录账号

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| 邹宏 | 123456 | admin | 所有功能 |
| test | 123456 | user | 查询+数据管理 |

## 🌐 云端部署

查看 [DEPLOY.md](DEPLOY.md) 获取详细的云端部署指南。

### 免费服务

- **Streamlit Cloud**: 免费托管 Web 应用
- **Neon**: 免费 PostgreSQL 数据库 (500MB)
- **GitHub**: 免费代码托管

**总费用：¥0/月**

## 📁 项目结构

```
.
├── app_cloud.py              # 主应用（带登录功能）
├── database_manager_cloud.py # 数据库模块（支持SQLite+PostgreSQL）
├── auth.py                   # 用户认证模块
├── matcher.py                # 颜色匹配器
├── requirements.txt          # Python 依赖
├── .streamlit/
│   ├── config.toml          # Streamlit 配置
│   └── secrets.toml         # 本地密钥配置（不提交到Git）
├── DEPLOY.md                # 部署指南
└── README_CLOUD.md          # 本文件
```

## 🔐 权限说明

- **admin（管理员）**：所有功能，包括用户管理
- **user（普通用户）**：查询功能 + 数据管理
- **guest（访客）**：仅单条查询（预留）

## 🛠️ 技术栈

- **前端**: Streamlit
- **后端**: Python
- **数据库**: SQLite（本地）/ PostgreSQL（云端）
- **认证**: JWT + bcrypt
- **部署**: Streamlit Cloud

## 📝 注意事项

1. **首次使用**：登录后需要导入商品数据（IT编码.xlsx）
2. **数据备份**：定期从数据库导出数据备份
3. **云端限制**：免费版适合小团队使用（建议10人以内）

## 📞 支持

如有问题，请联系开发者。

---

**版本**: v2.0 - 云端版  
**更新日期**: 2026-03-14
