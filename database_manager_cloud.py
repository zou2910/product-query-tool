"""
数据库管理器 - 云端版本
支持 SQLite（本地开发）和 PostgreSQL（云端部署）
"""
import pandas as pd
import sqlite3
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import streamlit as st


class DatabaseManager:
    """数据库管理器 - 支持 SQLite 和 PostgreSQL"""
    
    def __init__(self, db_path='product_database.db', excel_path='IT编码.xlsx'):
        self.db_path = db_path
        self.excel_path = excel_path
        self.conn = None
        self.cursor = None
        self.engine = None
        self.is_postgres = False
        
        # 检查是否有 PostgreSQL 连接字符串
        self.db_url = st.secrets.get("DATABASE_URL", "")
        
        if self.db_url and self.db_url.startswith("postgresql"):
            self.is_postgres = True
            print("🔌 使用 PostgreSQL 数据库")
        else:
            print("📁 使用 SQLite 数据库")
    
    def connect(self):
        """连接数据库"""
        if self.is_postgres:
            # PostgreSQL 连接
            self.engine = create_engine(
                self.db_url,
                poolclass=NullPool,
                connect_args={'connect_timeout': 10}
            )
            self.conn = self.engine.connect()
        else:
            # SQLite 连接
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
        
        return self
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def init_database(self):
        """初始化数据库表"""
        if self.is_postgres:
            # PostgreSQL 表结构
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    款式编码 VARCHAR(50) NOT NULL,
                    款式编码_标准 VARCHAR(50) NOT NULL,
                    商品编码 VARCHAR(100) NOT NULL UNIQUE,
                    颜色及规格 VARCHAR(200),
                    颜色 VARCHAR(100),
                    规格 VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            self.conn.execute(text(create_table_sql))
            
            # 创建索引
            self.conn.execute(text("CREATE INDEX IF NOT EXISTS idx_style_code ON products(款式编码_标准)"))
            self.conn.execute(text("CREATE INDEX IF NOT EXISTS idx_product_code ON products(商品编码)"))
            self.conn.execute(text("CREATE INDEX IF NOT EXISTS idx_color ON products(颜色)"))
            
            self.conn.commit()
        else:
            # SQLite 表结构
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    款式编码 TEXT NOT NULL,
                    款式编码_标准 TEXT NOT NULL,
                    商品编码 TEXT NOT NULL UNIQUE,
                    颜色及规格 TEXT,
                    颜色 TEXT,
                    规格 TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_style_code ON products(款式编码_标准)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_code ON products(商品编码)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_color ON products(颜色)')
            
            self.conn.commit()
        
        print("✅ 数据库初始化完成")
    
    def import_from_excel(self, excel_file=None):
        """从 Excel 导入数据"""
        if excel_file is None:
            excel_file = self.excel_path
        
        if not os.path.exists(excel_file):
            print(f"❌ 找不到文件: {excel_file}")
            return
        
        print(f"📊 正在从 {excel_file} 导入数据...")
        
        # 读取 Excel 文件
        df = pd.read_excel(excel_file)
        total_rows = len(df)
        print(f"  共 {total_rows:,} 行数据")
        
        # 数据处理
        df['款式编码_标准'] = df['款式编码'].astype(str).str[:13]
        
        # 分离颜色和规格
        split_result = df['颜色及规格'].str.split(';', expand=True)
        df['颜色'] = split_result[0].fillna('')
        df['规格'] = split_result[1].fillna('') if len(split_result.columns) > 1 else ''
        
        # 分批插入数据
        batch_size = 5000
        total_imported = 0
        
        for i in range(0, total_rows, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            if self.is_postgres:
                # PostgreSQL 批量插入
                data_to_insert = []
                for _, row in batch.iterrows():
                    data_to_insert.append({
                        '款式编码': row['款式编码'],
                        '款式编码_标准': row['款式编码_标准'],
                        '商品编码': row['商品编码'],
                        '颜色及规格': row['颜色及规格'],
                        '颜色': row['颜色'],
                        '规格': row['规格']
                    })
                
                if data_to_insert:
                    insert_sql = """
                        INSERT INTO products (款式编码, 款式编码_标准, 商品编码, 颜色及规格, 颜色, 规格)
                        VALUES (:款式编码, :款式编码_标准, :商品编码, :颜色及规格, :颜色, :规格)
                        ON CONFLICT (商品编码) DO NOTHING
                    """
                    self.conn.execute(text(insert_sql), data_to_insert)
                    self.conn.commit()
            else:
                # SQLite 批量插入
                for _, row in batch.iterrows():
                    try:
                        self.cursor.execute('''
                            INSERT OR IGNORE INTO products 
                            (款式编码, 款式编码_标准, 商品编码, 颜色及规格, 颜色, 规格)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            row['款式编码'],
                            row['款式编码_标准'],
                            row['商品编码'],
                            row['颜色及规格'],
                            row['颜色'],
                            row['规格']
                        ))
                    except Exception as e:
                        print(f"插入失败: {e}")
                
                self.conn.commit()
            
            total_imported += len(batch)
            if i % 50000 == 0:
                print(f"  已导入: {total_imported:,} / {total_rows:,} 条 ({total_imported/total_rows*100:.1f}%)")
        
        print(f"✅ 导入完成！共导入 {total_imported:,} 条记录")
    
    def append_data(self, new_data_df, progress_callback=None):
        """追加新数据"""
        total = len(new_data_df)
        added = 0
        skipped = 0
        batch_size = 5000
        
        # 准备数据
        data_to_insert = []
        for idx, row in new_data_df.iterrows():
            try:
                style_code = str(row['款式编码'])
                style_code_std = style_code[:13]
                product_code = str(row['商品编码'])
                color_spec = str(row['颜色及规格'])
                
                if ';' in color_spec:
                    color, size = color_spec.split(';', 1)
                else:
                    color = color_spec
                    size = ''
                
                data_to_insert.append({
                    '款式编码': style_code,
                    '款式编码_标准': style_code_std,
                    '商品编码': product_code,
                    '颜色及规格': color_spec,
                    '颜色': color,
                    '规格': size
                })
                
            except Exception as e:
                print(f"数据处理失败: {e}")
                skipped += 1
        
        if progress_callback:
            progress_callback(0.1)
        
        # 批量插入
        total_batches = (len(data_to_insert) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(data_to_insert))
            batch = data_to_insert[start_idx:end_idx]
            
            try:
                if self.is_postgres:
                    insert_sql = """
                        INSERT INTO products (款式编码, 款式编码_标准, 商品编码, 颜色及规格, 颜色, 规格)
                        VALUES (:款式编码, :款式编码_标准, :商品编码, :颜色及规格, :颜色, :规格)
                        ON CONFLICT (商品编码) DO NOTHING
                    """
                    result = self.conn.execute(text(insert_sql), batch)
                    self.conn.commit()
                    added += result.rowcount
                    skipped += len(batch) - result.rowcount
                else:
                    cursor = self.conn.cursor()
                    cursor.executemany('''
                        INSERT OR IGNORE INTO products 
                        (款式编码, 款式编码_标准, 商品编码, 颜色及规格, 颜色, 规格)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', [
                        (d['款式编码'], d['款式编码_标准'], d['商品编码'], 
                         d['颜色及规格'], d['颜色'], d['规格']) for d in batch
                    ])
                    added += cursor.rowcount
                    skipped += len(batch) - cursor.rowcount
                    cursor.close()
                    self.conn.commit()
                
                if progress_callback:
                    progress = 0.1 + 0.9 * (batch_idx + 1) / total_batches
                    progress_callback(min(progress, 0.99))
                    
            except Exception as e:
                print(f"批量插入失败: {e}")
                skipped += len(batch)
        
        if progress_callback:
            progress_callback(1.0)
        
        return added, skipped, total
    
    def query_by_style_code(self, style_code):
        """根据款式编码查询"""
        style_code_std = str(style_code)[:13]
        
        if self.is_postgres:
            sql = "SELECT * FROM products WHERE 款式编码_标准 = :style_code"
            result = self.conn.execute(text(sql), {'style_code': style_code_std})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        else:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM products WHERE 款式编码_标准 = ?', (style_code_std,))
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return results
    
    def get_all_colors(self):
        """获取所有颜色"""
        if self.is_postgres:
            sql = "SELECT DISTINCT 颜色 FROM products WHERE 颜色 IS NOT NULL AND 颜色 != ''"
            result = self.conn.execute(text(sql))
            return [row[0] for row in result.fetchall()]
        else:
            cursor = self.conn.cursor()
            cursor.execute('SELECT DISTINCT 颜色 FROM products WHERE 颜色 != ""')
            results = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return results
    
    def get_stats(self):
        """获取统计信息"""
        if self.is_postgres:
            total = self.conn.execute(text("SELECT COUNT(*) FROM products")).fetchone()[0]
            styles = self.conn.execute(text("SELECT COUNT(DISTINCT 款式编码_标准) FROM products")).fetchone()[0]
            products = self.conn.execute(text("SELECT COUNT(DISTINCT 商品编码) FROM products")).fetchone()[0]
        else:
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM products')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT 款式编码_标准) FROM products')
            styles = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT 商品编码) FROM products')
            products = cursor.fetchone()[0]
            
            cursor.close()
        
        return {"total": total, "styles": styles, "products": products}
    
    def delete_by_product_codes(self, product_codes, progress_callback=None):
        """根据商品编码批量删除"""
        total = len(product_codes)
        deleted = 0
        not_found = 0
        batch_size = 1000
        
        codes_list = [str(code).strip() for code in product_codes]
        total_batches = (total + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total)
            batch_codes = codes_list[start_idx:end_idx]
            
            try:
                if self.is_postgres:
                    placeholders = ','.join([f':code{i}' for i in range(len(batch_codes))])
                    params = {f'code{i}': code for i, code in enumerate(batch_codes)}
                    
                    # 查询存在数量
                    count_sql = f"SELECT COUNT(*) FROM products WHERE 商品编码 IN ({placeholders})"
                    existing_count = self.conn.execute(text(count_sql), params).fetchone()[0]
                    
                    # 删除
                    delete_sql = f"DELETE FROM products WHERE 商品编码 IN ({placeholders})"
                    result = self.conn.execute(text(delete_sql), params)
                    self.conn.commit()
                    
                    batch_deleted = result.rowcount
                else:
                    placeholders = ','.join(['?' for _ in batch_codes])
                    cursor = self.conn.cursor()
                    
                    cursor.execute(f'SELECT COUNT(*) FROM products WHERE 商品编码 IN ({placeholders})', batch_codes)
                    existing_count = cursor.fetchone()[0]
                    
                    cursor.execute(f'DELETE FROM products WHERE 商品编码 IN ({placeholders})', batch_codes)
                    batch_deleted = cursor.rowcount
                    cursor.close()
                    
                    self.conn.commit()
                
                deleted += batch_deleted
                not_found += len(batch_codes) - existing_count
                
                if progress_callback:
                    progress = (batch_idx + 1) / total_batches
                    progress_callback(min(progress, 1.0))
                    
            except Exception as e:
                print(f"批量删除失败: {e}")
                not_found += len(batch_codes)
        
        return deleted, not_found, total
    
    def delete_by_style_codes(self, style_codes, progress_callback=None):
        """根据款式编码批量删除"""
        total = len(style_codes)
        deleted = 0
        not_found = 0
        batch_size = 500
        
        codes_list = [str(code)[:13].strip() for code in style_codes]
        total_batches = (total + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total)
            batch_codes = codes_list[start_idx:end_idx]
            
            try:
                if self.is_postgres:
                    placeholders = ','.join([f':code{i}' for i in range(len(batch_codes))])
                    params = {f'code{i}': code for i, code in enumerate(batch_codes)}
                    
                    count_sql = f"SELECT COUNT(*) FROM products WHERE 款式编码_标准 IN ({placeholders})"
                    existing_count = self.conn.execute(text(count_sql), params).fetchone()[0]
                    
                    delete_sql = f"DELETE FROM products WHERE 款式编码_标准 IN ({placeholders})"
                    result = self.conn.execute(text(delete_sql), params)
                    self.conn.commit()
                    
                    batch_deleted = result.rowcount
                else:
                    placeholders = ','.join(['?' for _ in batch_codes])
                    cursor = self.conn.cursor()
                    
                    cursor.execute(f'SELECT COUNT(*) FROM products WHERE 款式编码_标准 IN ({placeholders})', batch_codes)
                    existing_count = cursor.fetchone()[0]
                    
                    cursor.execute(f'DELETE FROM products WHERE 款式编码_标准 IN ({placeholders})', batch_codes)
                    batch_deleted = cursor.rowcount
                    cursor.close()
                    
                    self.conn.commit()
                
                deleted += batch_deleted
                not_found += len(batch_codes) - existing_count if existing_count == 0 else 0
                
                if progress_callback:
                    progress = (batch_idx + 1) / total_batches
                    progress_callback(min(progress, 1.0))
                    
            except Exception as e:
                print(f"批量删除失败: {e}")
                not_found += len(batch_codes)
        
        return deleted, not_found, total


# 保持向后兼容
if __name__ == "__main__":
    db = DatabaseManager()
    db.connect()
    db.init_database()
    
    # 如果数据库为空，从 Excel 导入
    stats = db.get_stats()
    if stats['total'] == 0:
        print("数据库为空，开始从 Excel 导入...")
        db.import_from_excel()
    
    # 显示统计
    stats = db.get_stats()
    print(f"\n数据库统计:")
    print(f"  总记录数: {stats['total']:,}")
    print(f"  款式编码数: {stats['styles']:,}")
    print(f"  商品编码数: {stats['products']:,}")
    
    db.close()
