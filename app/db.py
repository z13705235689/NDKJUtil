import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Optional


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        # 数据库文件放在项目根目录下
        self.project_root = Path(__file__).parent.parent
        self.db_path = self.project_root / 'mes.db'
        
        # 确保项目目录存在
        self.project_root.mkdir(exist_ok=True)
        
        print(f"数据库路径: {self.db_path}")
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        try:
            # 如果数据库文件不存在，创建它
            if not self.db_path.exists():
                print(f"创建新数据库: {self.db_path}")
                self.db_path.touch()
            
            # 连接数据库并创建表
            with self.get_conn() as conn:
                # 读取schema.sql文件
                schema_file = Path(__file__).parent / 'schema.sql'
                if schema_file.exists():
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # 执行schema
                    conn.executescript(schema_sql)
                    print("数据库表结构创建完成")
                else:
                    print(f"警告: 找不到schema文件 {schema_file}")
                
                # 检查并更新数据库版本
                self._check_and_update_schema(conn)
                
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            raise
    
    def _check_and_update_schema(self, conn):
        """检查并更新数据库结构"""
        try:
            # 检查是否存在版本表
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_version'")
            version_table_exists = cursor.fetchone() is not None
            
            if not version_table_exists:
                # 创建版本表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS db_version (
                        version_id INTEGER PRIMARY KEY,
                        version_number TEXT NOT NULL,
                        applied_date DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 读取并执行完整的schema.sql
                schema_file = Path(__file__).parent / 'schema.sql'
                if schema_file.exists():
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # 执行建表语句
                    conn.executescript(schema_sql)
                    
                    # 记录版本
                    conn.execute("INSERT INTO db_version (version_number) VALUES (?)", ("1.0.0",))
                    conn.commit()
                    print("数据库初始化完成，版本：1.0.0")
            else:
                # 检查当前版本
                cursor = conn.execute("SELECT version_number FROM db_version ORDER BY version_id DESC LIMIT 1")
                current_version = cursor.fetchone()
                
                if current_version and current_version[0] == "1.0.0":
                    print("数据库已是最新版本：1.0.0")
                else:
                    # 需要更新数据库结构
                    self._update_database_schema(conn)
                    
        except Exception as e:
            print(f"数据库初始化错误: {e}")
            # 如果出错，尝试删除数据库文件重新创建
            try:
                conn.close()
                if self.db_path.exists():
                    self.db_path.unlink()
                print("数据库文件已删除，将重新创建")
                # 重新初始化
                self._init_db()
            except Exception as cleanup_error:
                print(f"清理数据库文件失败: {cleanup_error}")
                raise e
    
    def _update_database_schema(self, conn):
        """更新数据库结构"""
        try:
            # 检查并添加缺失的列
            self._add_missing_columns(conn)
            
            # 更新版本号
            conn.execute("INSERT INTO db_version (version_number) VALUES (?)", ("1.0.0",))
            conn.commit()
            print("数据库结构更新完成，版本：1.0.0")
            
        except Exception as e:
            print(f"更新数据库结构失败: {e}")
            raise e
    
    def _add_missing_columns(self, conn):
        """添加缺失的列"""
        try:
            # 检查Items表是否存在
            cursor = conn.execute("PRAGMA table_info(Items)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # 定义需要添加的列
            missing_columns = [
                ('ItemSpec', 'TEXT'),
                ('ItemType', 'TEXT NOT NULL DEFAULT "物资"'),
                ('Unit', 'TEXT NOT NULL DEFAULT "个"'),
                ('Quantity', 'REAL NOT NULL DEFAULT 1.0'),
                ('SafetyStock', 'REAL NOT NULL DEFAULT 0'),
                ('ParentItemId', 'INTEGER'),
                ('IsActive', 'BOOLEAN NOT NULL DEFAULT 1')
            ]
            
            # 添加缺失的列
            for column_name, column_def in missing_columns:
                if column_name not in existing_columns:
                    if column_name == 'ItemType':
                        # 特殊处理ItemType列，为现有数据设置默认值
                        conn.execute(f"ALTER TABLE Items ADD COLUMN {column_name} {column_def}")
                        # 更新现有数据，将旧类型映射到新类型
                        conn.execute("""
                            UPDATE Items SET ItemType = CASE 
                                WHEN ItemType = 'FG' THEN '成品'
                                WHEN ItemType = 'SFG' THEN '半成品'
                                WHEN ItemType = 'RM' THEN '原材料'
                                WHEN ItemType = 'PKG' THEN '包装'
                                ELSE '物资'
                            END
                        """)
                    else:
                        conn.execute(f"ALTER TABLE Items ADD COLUMN {column_name} {column_def}")
            
            # 添加外键约束
            try:
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_items_parent 
                    ON Items(ParentItemId)
                """)
            except:
                pass  # 索引可能已存在
                
        except Exception as e:
            print(f"添加列时出错: {e}")
            raise
    
    def _create_missing_table(self, conn, table_name):
        """创建缺失的表"""
        # 这里可以根据需要添加具体的建表语句
        # 为了简化，我们只创建基本的表结构
        table_definitions = {
            "Suppliers": """
                CREATE TABLE Suppliers (
                    SupplierId INTEGER PRIMARY KEY AUTOINCREMENT,
                    SupplierCode TEXT UNIQUE NOT NULL,
                    SupplierName TEXT NOT NULL,
                    ContactPerson TEXT,
                    Phone TEXT,
                    Email TEXT,
                    Address TEXT,
                    TaxNo TEXT,
                    BankAccount TEXT,
                    PaymentTerms TEXT,
                    CreditLimit REAL,
                    IsActive BOOLEAN DEFAULT 1,
                    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "WorkCenters": """
                CREATE TABLE WorkCenters (
                    WorkCenterId INTEGER PRIMARY KEY AUTOINCREMENT,
                    WorkCenterCode TEXT UNIQUE NOT NULL,
                    WorkCenterName TEXT NOT NULL,
                    WorkCenterType TEXT,
                    Capacity REAL,
                    Efficiency REAL DEFAULT 1.0,
                    SetupTime REAL DEFAULT 0,
                    IsActive BOOLEAN DEFAULT 1,
                    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "Customers": """
                CREATE TABLE Customers (
                    CustomerId INTEGER PRIMARY KEY AUTOINCREMENT,
                    CustomerCode TEXT UNIQUE NOT NULL,
                    CustomerName TEXT NOT NULL,
                    ContactPerson TEXT,
                    Phone TEXT,
                    Email TEXT,
                    Address TEXT,
                    TaxNo TEXT,
                    CreditLimit REAL,
                    PaymentTerms TEXT,
                    IsActive BOOLEAN DEFAULT 1,
                    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        if table_name in table_definitions:
            try:
                conn.execute(table_definitions[table_name])
                print(f"已创建表: {table_name}")
            except Exception as e:
                print(f"创建表 {table_name} 失败: {e}")
    
    @contextmanager
    def get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果支持列名访问
        
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def execute_query(self, sql: str, params: tuple = ()) -> list:
        """执行查询语句"""
        with self.get_conn() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()
    
    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """执行更新语句，返回最后插入行的ID或影响的行数"""
        with self.get_conn() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            # 如果是INSERT语句，返回lastrowid；否则返回影响的行数
            if sql.strip().upper().startswith('INSERT'):
                return cursor.lastrowid
            else:
                return cursor.rowcount
    
    def get_last_rowid(self) -> int:
        """获取最后插入行的ID"""
        # 这个方法现在不需要了，因为execute_update已经返回了正确的ID
        return 0
    
    def execute_many(self, sql: str, params_list: list) -> int:
        """批量执行语句"""
        with self.get_conn() as conn:
            cursor = conn.executemany(sql, params_list)
            conn.commit()
            return cursor.rowcount
    
    def get_last_rowid(self) -> int:
        """获取最后插入行的ID"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            return cursor.lastrowid


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_conn():
    """获取数据库连接的便捷函数"""
    return db_manager.get_conn()


def init_db():
    """初始化数据库"""
    db_manager._init_db()


# 便捷的数据库操作函数
def query_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """查询单条记录"""
    with get_conn() as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchone()


def query_all(sql: str, params: tuple = ()) -> list:
    """查询多条记录"""
    return db_manager.execute_query(sql, params)


def execute(sql: str, params: tuple = ()) -> int:
    """执行SQL语句"""
    return db_manager.execute_update(sql, params)


def get_last_id() -> int:
    """获取最后插入的ID"""
    return db_manager.get_last_rowid()


def execute_many(sql: str, params_list: list) -> int:
    """批量执行SQL语句"""
    return db_manager.execute_many(sql, params_list)
