import streamlit as st
import pandas as pd
import io
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from database_manager import DatabaseManager
from matcher import ColorMatcher

st.set_page_config(
    page_title="商品资料查询工具",
    page_icon="📦",
    layout="wide"
)

st.title("📦 商品资料查询工具")
st.markdown("根据款式编码和颜色规格查询供应商款号")

# 初始化数据库
def init_database(max_retries=3):
    for attempt in range(max_retries):
        try:
            db = DatabaseManager()
            db.connect()
            return db
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise e

@st.cache_resource
def get_database():
    return init_database()

try:
    with st.spinner("正在连接数据库..."):
        db = get_database()
        stats = db.get_stats()
    st.success(f"✅ 数据库连接成功！共 {stats['total']:,} 条记录")
except Exception as e:
    st.error(f"❌ 数据库连接失败: {e}")
    st.stop()

# 初始化颜色匹配器
if 'color_matcher' not in st.session_state:
    st.session_state['colors'] = db.get_all_colors()
    st.session_state['color_matcher'] = ColorMatcher(st.session_state['colors'])

color_matcher = st.session_state['color_matcher']

# 创建标签页
tab1, tab2, tab3 = st.tabs(["🔍 单条查询", "📊 批量查询", "➕ 数据管理"])

# 单条查询
with tab1:
    st.subheader("单条商品查询")
    col1, col2 = st.columns(2)
    
    with col1:
        style_code = st.text_input("款式编码", placeholder="例如: CCLTPXKWF2620")
    
    with col2:
        color_spec = st.text_input("颜色及规格", placeholder="例如: 红色;L")
    
    if st.button("🔍 查询", type="primary"):
        if style_code and color_spec:
            st.info("查询功能已部署")
        else:
            st.warning("请填写款式编码和颜色及规格")

# 批量查询
with tab2:
    st.subheader("批量查询")
    st.markdown("上传Excel文件进行批量查询")
    uploaded_file = st.file_uploader("上传查询文件", type=['xlsx', 'csv'])

# 数据管理
with tab3:
    st.subheader("➕ 数据管理")
    stats = db.get_stats()
    st.metric("总记录数", f"{stats['total']:,}")
