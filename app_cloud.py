"""
商品资料查询工具 - 云端版本
支持用户登录认证
"""
import streamlit as st
import pandas as pd
import io
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from database_manager_cloud import DatabaseManager
from matcher import ColorMatcher
from auth import (
    authenticate_user, create_user, list_users, delete_user,
    reset_password, check_permission, init_default_users
)

# 页面配置
st.set_page_config(
    page_title="商品资料查询工具",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化默认用户（如果没有用户）
init_default_users()

# 初始化 session state
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False


def login_page():
    """登录页面"""
    st.title("📦 商品资料查询工具")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 用户登录")
        
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            
            col_login, col_space = st.columns([1, 2])
            with col_login:
                submitted = st.form_submit_button("登录", type="primary", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("请输入用户名和密码")
                else:
                    success, result = authenticate_user(username, password)
                    if success:
                        st.session_state['user'] = result
                        st.session_state['logged_in'] = True
                        st.success(f"✅ 欢迎回来，{result['username']}！")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
        
        st.markdown("---")
        st.caption("💡 默认管理员账号：邹宏 / 123456")


def logout():
    """登出"""
    st.session_state['user'] = None
    st.session_state['logged_in'] = False
    st.rerun()


def sidebar_user_info():
    """侧边栏用户信息"""
    with st.sidebar:
        st.title("📦 商品查询系统")
        st.markdown("---")
        
        if st.session_state['user']:
            user = st.session_state['user']
            st.write(f"👤 **{user['username']}**")
            st.write(f"🎭 角色: {user['role']}")
            st.markdown("---")
            
            if st.button("🚪 退出登录", use_container_width=True):
                logout()


def user_management():
    """用户管理页面（仅管理员）"""
    st.subheader("👥 用户管理")
    
    if not check_permission("admin"):
        st.error("❌ 只有管理员可以管理用户")
        return
    
    # 创建新用户
    with st.expander("➕ 创建新用户"):
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("用户名")
                new_password = st.text_input("密码", type="password")
            with col2:
                new_email = st.text_input("邮箱")
                new_role = st.selectbox("角色", ["user", "admin"])
            
            if st.form_submit_button("创建用户", type="primary"):
                if new_username and new_password:
                    success, msg = create_user(new_username, new_password, new_email, new_role)
                    if success:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.error("请填写用户名和密码")
    
    # 用户列表
    st.markdown("---")
    st.write("### 用户列表")
    
    users = list_users()
    if users:
        users_df = pd.DataFrame(users)
        st.dataframe(users_df, use_container_width=True)
        
        # 重置密码
        with st.expander("🔄 重置用户密码"):
            col1, col2 = st.columns(2)
            with col1:
                reset_user = st.selectbox("选择用户", [u['username'] for u in users])
            with col2:
                new_pass = st.text_input("新密码", type="password")
            
            if st.button("重置密码", type="primary"):
                if new_pass:
                    success, msg = reset_password(reset_user, new_pass)
                    if success:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.error("请输入新密码")
        
        # 删除用户
        with st.expander("🗑️ 删除用户"):
            delete_username = st.selectbox("选择要删除的用户", [u['username'] for u in users])
            
            if st.button("删除用户", type="primary"):
                if delete_username == st.session_state['user']['username']:
                    st.error("❌ 不能删除当前登录的用户")
                else:
                    success, msg = delete_user(delete_username)
                    if success:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
    else:
        st.info("暂无用户数据")


# 主应用
@st.cache_resource
def get_database():
    """获取数据库连接（缓存）"""
    db = DatabaseManager()
    db.connect()
    return db


def init_database():
    """初始化数据库"""
    try:
        db = get_database()
        db.init_database()
        return db
    except Exception as e:
        st.error(f"❌ 数据库连接失败: {e}")
        return None


# 登录检查
if not st.session_state['logged_in']:
    login_page()
else:
    # 侧边栏
    sidebar_user_info()
    
    # 主内容区
    st.title("📦 商品资料查询工具")
    st.markdown("根据款式编码和颜色规格查询供应商款号")
    
    # 初始化数据库
    db = init_database()
    
    if db:
        try:
            stats = db.get_stats()
            st.success(f"✅ 数据库连接成功！共 {stats['total']:,} 条记录")
        except Exception as e:
            st.error(f"❌ 获取统计信息失败: {e}")
            db = None
    
    if db:
        # 初始化颜色匹配器
        if 'color_matcher' not in st.session_state:
            st.session_state['colors'] = db.get_all_colors()
            st.session_state['color_matcher'] = ColorMatcher(st.session_state['colors'])
        
        color_matcher = st.session_state['color_matcher']
        
        # 创建标签页
        tabs = ["🔍 单条查询", "📊 批量查询"]
        
        # 根据权限添加标签页
        if check_permission("user"):
            tabs.append("➕ 数据管理")
        if check_permission("admin"):
            tabs.append("👥 用户管理")
        
        tab_objects = st.tabs(tabs)
        
        # 单条查询
        with tab_objects[0]:
            st.subheader("单条商品查询")
            
            col1, col2 = st.columns(2)
            
            with col1:
                style_code = st.text_input(
                    "款式编码",
                    placeholder="例如: CCLTPXKWF2620",
                    help="支持带后缀的编码，系统会自动取前13个字符"
                )
            
            with col2:
                color_spec = st.text_input(
                    "颜色及规格",
                    placeholder="例如: 红色;L 或 白色 白色;M",
                    help="格式：颜色;规格，支持颜色模糊匹配。组合商品用空格分隔颜色"
                )
            
            if st.button("🔍 查询", type="primary"):
                if style_code and color_spec:
                    with st.spinner("查询中..."):
                        from app import match_product, parse_color_spec, check_length_attrs_match, match_product_with_candidates
                        
                        start_time = time.time()
                        result = match_product(style_code, color_spec)
                        elapsed_time = time.time() - start_time
                        
                        if result is None:
                            st.warning("⚠️ 未找到匹配的商品")
                            
                            standard_code = str(style_code)[:13]
                            st.info(f"款式编码（前13位）: `{standard_code}`")
                            
                            candidates = db.query_by_style_code(style_code)
                            if candidates:
                                st.markdown("**该款式编码下的可用颜色：**")
                                unique_colors = list(set([c['颜色'] for c in candidates]))
                                st.write(", ".join([f"`{c}`" for c in unique_colors[:20]]))
                        else:
                            st.success(f"✅ 查询成功！耗时 {elapsed_time:.3f} 秒")
                            
                            if '匹配商品编码' in result:
                                st.info(f"📦 匹配商品编码: `{result['匹配商品编码']}`")
                            
                            if '颜色匹配详情' in result:
                                st.caption(f"颜色匹配: {result['颜色匹配详情']}")
                            
                            display_df = pd.DataFrame([result])
                            display_cols = ['款式编码', '匹配商品编码', '商品编码', '颜色及规格', '颜色', '规格']
                            available_cols = [c for c in display_cols if c in display_df.columns]
                            st.dataframe(display_df[available_cols], use_container_width=True)
                else:
                    st.warning("请填写款式编码和颜色及规格")
        
        # 批量查询
        with tab_objects[1]:
            st.subheader("批量查询")
            st.markdown("""
            **上传文件格式要求：**
            - 文件类型：Excel (.xlsx) 或 CSV (.csv)
            - 必须包含列：`款式编码`、`颜色及规格`
            """)
            
            uploaded_file = st.file_uploader(
                "上传查询文件",
                type=['xlsx', 'csv'],
                help="上传包含款式编码和颜色及规格的Excel或CSV文件"
            )
            
            if uploaded_file:
                try:
                    file_name = uploaded_file.name
                    file_size = uploaded_file.size / 1024
                    
                    st.info(f"📄 文件名: {file_name} ({file_size:.1f} KB)")
                    
                    if file_name.lower().endswith('.csv'):
                        query_df = pd.read_csv(uploaded_file)
                    else:
                        query_df = pd.read_excel(uploaded_file)
                    
                    if query_df.empty:
                        st.error("❌ 文件为空")
                    else:
                        st.success(f"✅ 成功读取文件，共 {len(query_df)} 行数据")
                        
                        with st.expander("📋 数据预览"):
                            st.dataframe(query_df.head(10), use_container_width=True)
                        
                        required_cols = ['款式编码', '颜色及规格']
                        missing_cols = [c for c in required_cols if c not in query_df.columns]
                        
                        if missing_cols:
                            st.error(f"❌ 缺少必要的列: {', '.join(missing_cols)}")
                        else:
                            if st.button("🚀 开始批量查询", type="primary"):
                                with st.spinner("正在批量查询..."):
                                    from app import match_product_with_candidates
                                    
                                    start_time = time.time()
                                    total = len(query_df)
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    # 预加载数据
                                    unique_style_codes = query_df['款式编码'].apply(lambda x: str(x)[:13]).unique()
                                    style_code_cache = {}
                                    
                                    for i, style_code in enumerate(unique_style_codes):
                                        style_code_cache[style_code] = db.query_by_style_code(style_code)
                                        if i % 10 == 0:
                                            progress_bar.progress(min((i + 1) / len(unique_style_codes) * 0.3, 0.3))
                                    
                                    # 批量查询
                                    results_list = []
                                    for idx, row in query_df.iterrows():
                                        style_code = row['款式编码']
                                        color_spec = row['颜色及规格']
                                        standard_code = str(style_code)[:13]
                                        candidates = style_code_cache.get(standard_code, [])
                                        
                                        result = match_product_with_candidates(style_code, color_spec, candidates)
                                        
                                        if result:
                                            result_row = result.copy()
                                            result_row['查询款式编码'] = style_code
                                            result_row['查询颜色及规格'] = color_spec
                                            result_row['匹配状态'] = '成功'
                                        else:
                                            result_row = {
                                                '查询款式编码': style_code,
                                                '查询颜色及规格': color_spec,
                                                '款式编码_标准': standard_code,
                                                '匹配状态': '未找到'
                                            }
                                        
                                        results_list.append(result_row)
                                        
                                        if idx % 50 == 0:
                                            progress = 0.3 + 0.7 * (idx + 1) / total
                                            progress_bar.progress(min(progress, 1.0))
                                            status_text.text(f"处理进度: {progress*100:.1f}% ({idx+1}/{total})")
                                    
                                    progress_bar.empty()
                                    status_text.empty()
                                    
                                    elapsed_time = time.time() - start_time
                                    results_df = pd.DataFrame(results_list)
                                    
                                    success_count = len(results_df[results_df['匹配状态']=='成功'])
                                    st.success(f"✅ 查询完成！成功匹配 {success_count} 条，耗时 {elapsed_time:.2f} 秒")
                                    
                                    st.subheader("查询结果")
                                    st.dataframe(results_df, use_container_width=True)
                                    
                                    # 下载按钮
                                    excel_buffer = io.BytesIO()
                                    results_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                                    excel_buffer.seek(0)
                                    
                                    st.download_button(
                                        label="📥 下载Excel结果",
                                        data=excel_buffer,
                                        file_name="查询结果.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                except Exception as e:
                    st.error(f"❌ 文件读取失败: {e}")
        
        # 数据管理（仅 user 及以上权限）
        if check_permission("user") and len(tab_objects) > 2:
            with tab_objects[2]:
                st.subheader("➕ 数据管理")
                
                # 追加数据
                st.write("### 追加商品数据")
                append_file = st.file_uploader(
                    "上传要追加的数据文件",
                    type=['xlsx', 'csv'],
                    key="append_uploader"
                )
                
                if append_file:
                    try:
                        if append_file.name.endswith('.csv'):
                            new_data_df = pd.read_csv(append_file)
                        else:
                            new_data_df = pd.read_excel(append_file)
                        
                        st.success(f"✅ 成功读取文件，共 {len(new_data_df)} 行数据")
                        
                        with st.expander("📋 数据预览"):
                            st.dataframe(new_data_df.head(10), use_container_width=True)
                        
                        required_cols = ['款式编码', '商品编码', '颜色及规格']
                        missing_cols = [c for c in required_cols if c not in new_data_df.columns]
                        
                        if missing_cols:
                            st.error(f"❌ 缺少必要的列: {', '.join(missing_cols)}")
                        else:
                            if st.button("📥 追加到数据库", type="primary"):
                                with st.spinner("正在追加数据..."):
                                    progress_bar = st.progress(0)
                                    
                                    def update_progress(pct):
                                        progress_bar.progress(min(pct, 1.0))
                                    
                                    added, skipped, total = db.append_data(new_data_df, update_progress)
                                    
                                    progress_bar.empty()
                                    st.success(f"✅ 追加完成！新增 {added} 条，跳过 {skipped} 条")
                                    
                                    # 刷新颜色匹配器
                                    st.session_state['colors'] = db.get_all_colors()
                                    st.session_state['color_matcher'] = ColorMatcher(st.session_state['colors'])
                    except Exception as e:
                        st.error(f"❌ 文件读取失败: {e}")
                
                # 删除数据
                st.markdown("---")
                st.write("### 🗑️ 删除商品数据")
                
                delete_mode = st.radio(
                    "选择删除模式",
                    ["按商品编码删除", "按款式编码删除"],
                    horizontal=True
                )
                
                required_col = "商品编码" if delete_mode == "按商品编码删除" else "款式编码"
                
                delete_file = st.file_uploader(
                    f"上传要删除的{required_col}列表",
                    type=['xlsx', 'csv'],
                    key="delete_uploader"
                )
                
                if delete_file:
                    try:
                        if delete_file.name.endswith('.csv'):
                            delete_df = pd.read_csv(delete_file)
                        else:
                            delete_df = pd.read_excel(delete_file)
                        
                        st.success(f"✅ 成功读取文件，共 {len(delete_df)} 行数据")
                        
                        if required_col not in delete_df.columns:
                            st.error(f"❌ 缺少必要的列: {required_col}")
                        else:
                            unique_codes = delete_df[required_col].drop_duplicates()
                            st.info(f"📊 待删除数据包含 {len(unique_codes)} 个唯一的{required_col}")
                            
                            st.warning("⚠️ 警告：此操作将永久删除数据库中的数据！")
                            
                            confirm_delete = st.checkbox("我已确认要删除这些数据")
                            
                            if st.button("🗑️ 执行删除", type="primary", disabled=not confirm_delete):
                                if confirm_delete:
                                    with st.spinner("正在删除数据..."):
                                        progress_bar = st.progress(0)
                                        
                                        def update_progress(pct):
                                            progress_bar.progress(min(pct, 1.0))
                                        
                                        codes_list = unique_codes.tolist()
                                        if delete_mode == "按商品编码删除":
                                            deleted, not_found, total = db.delete_by_product_codes(codes_list, update_progress)
                                        else:
                                            deleted, not_found, total = db.delete_by_style_codes(codes_list, update_progress)
                                        
                                        progress_bar.empty()
                                        st.success(f"✅ 删除完成！删除 {deleted} 条，未找到 {not_found} 条")
                                        
                                        # 刷新颜色匹配器
                                        st.session_state['colors'] = db.get_all_colors()
                                        st.session_state['color_matcher'] = ColorMatcher(st.session_state['colors'])
                    except Exception as e:
                        st.error(f"❌ 文件读取失败: {e}")
                
                # 数据库统计
                st.markdown("---")
                st.write("### 📊 当前数据库统计")
                
                stats = db.get_stats()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总记录数", f"{stats['total']:,}")
                with col2:
                    st.metric("款式编码数", f"{stats['styles']:,}")
                with col3:
                    st.metric("商品编码数", f"{stats['products']:,}")
        
        # 用户管理（仅管理员）
        if check_permission("admin") and len(tab_objects) > 3:
            with tab_objects[3]:
                user_management()
    
    # 页脚
    st.markdown("---")
    st.caption("💡 提示：款式编码会自动截取前13个字符进行匹配，颜色支持模糊匹配")
