"""
用户认证模块
支持本地 YAML 文件存储用户数据（适合 Streamlit Cloud 免费版）
"""
import yaml
import bcrypt
import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta
import jwt
import secrets

# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "config.yaml"

# JWT 密钥（从环境变量获取或使用默认值）
JWT_SECRET = st.secrets.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def load_config():
    """加载配置文件"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    return {
        'credentials': {
            'usernames': {}
        },
        'cookie': {
            'name': 'product_query_auth',
            'key': secrets.token_hex(32),
            'expiry_days': 1
        }
    }


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False, allow_unicode=True)


def hash_password(password: str) -> str:
    """密码加密"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_user(username: str, password: str, email: str = None, role: str = "user"):
    """创建新用户"""
    config = load_config()
    
    if username in config['credentials']['usernames']:
        return False, "用户名已存在"
    
    config['credentials']['usernames'][username] = {
        'password': hash_password(password),
        'email': email or f"{username}@example.com",
        'role': role,
        'created_at': datetime.now().isoformat(),
        'last_login': None
    }
    
    save_config(config)
    return True, "用户创建成功"


def authenticate_user(username: str, password: str):
    """验证用户登录"""
    config = load_config()
    
    if username not in config['credentials']['usernames']:
        return False, "用户名或密码错误"
    
    user = config['credentials']['usernames'][username]
    
    if not verify_password(password, user['password']):
        return False, "用户名或密码错误"
    
    # 更新最后登录时间
    user['last_login'] = datetime.now().isoformat()
    save_config(config)
    
    # 生成 JWT token
    token = generate_token(username, user['role'])
    
    return True, {
        'username': username,
        'email': user['email'],
        'role': user['role'],
        'token': token
    }


def generate_token(username: str, role: str) -> str:
    """生成 JWT token"""
    payload = {
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str):
    """验证 JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Token 已过期"
    except jwt.InvalidTokenError:
        return False, "无效的 Token"


def get_user_role(username: str) -> str:
    """获取用户角色"""
    config = load_config()
    user = config['credentials']['usernames'].get(username)
    return user['role'] if user else None


def list_users():
    """列出所有用户"""
    config = load_config()
    users = []
    for username, data in config['credentials']['usernames'].items():
        users.append({
            'username': username,
            'email': data.get('email', ''),
            'role': data.get('role', 'user'),
            'created_at': data.get('created_at', ''),
            'last_login': data.get('last_login', '从未登录')
        })
    return users


def delete_user(username: str):
    """删除用户"""
    config = load_config()
    
    if username not in config['credentials']['usernames']:
        return False, "用户不存在"
    
    # 不能删除最后一个管理员
    admin_count = sum(1 for u in config['credentials']['usernames'].values() if u.get('role') == 'admin')
    if config['credentials']['usernames'][username].get('role') == 'admin' and admin_count <= 1:
        return False, "不能删除最后一个管理员"
    
    del config['credentials']['usernames'][username]
    save_config(config)
    return True, "用户删除成功"


def change_password(username: str, old_password: str, new_password: str):
    """修改密码"""
    config = load_config()
    
    if username not in config['credentials']['usernames']:
        return False, "用户不存在"
    
    user = config['credentials']['usernames'][username]
    
    if not verify_password(old_password, user['password']):
        return False, "原密码错误"
    
    user['password'] = hash_password(new_password)
    save_config(config)
    return True, "密码修改成功"


def reset_password(username: str, new_password: str):
    """管理员重置密码"""
    config = load_config()
    
    if username not in config['credentials']['usernames']:
        return False, "用户不存在"
    
    config['credentials']['usernames'][username]['password'] = hash_password(new_password)
    save_config(config)
    return True, "密码重置成功"


def init_default_users():
    """初始化默认用户"""
    config = load_config()
    
    # 如果没有任何用户，创建默认管理员
    if not config['credentials']['usernames']:
        # 创建管理员账号
        create_user(
            username="邹宏",
            password="123456",
            email="admin@example.com",
            role="admin"
        )
        print("✅ 已创建默认管理员账号: 邹宏 / 123456")
        
        # 创建测试普通用户
        create_user(
            username="test",
            password="123456",
            email="test@example.com",
            role="user"
        )
        print("✅ 已创建测试用户账号: test / 123456")


def check_permission(required_role: str = "user"):
    """检查用户权限"""
    if 'user' not in st.session_state:
        return False
    
    user_role = st.session_state['user'].get('role', 'user')
    
    # 权限等级：admin > user > guest
    role_levels = {'admin': 3, 'user': 2, 'guest': 1}
    
    return role_levels.get(user_role, 0) >= role_levels.get(required_role, 0)


# 初始化默认用户
if __name__ == "__main__":
    init_default_users()
    print("\n当前用户列表：")
    for user in list_users():
        print(f"  - {user['username']} ({user['role']}) - {user['email']}")
