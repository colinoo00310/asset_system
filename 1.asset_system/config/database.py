import sqlite3
import os
import sys
import hashlib


def get_db_path(db_file):
    """获取数据库文件的绝对路径（兼容开发和打包环境）"""
    if os.path.isabs(db_file):
        return db_file

    if getattr(sys, 'frozen', False):
        # 打包环境：相对于 exe 所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 开发环境：相对于项目根目录
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, db_file)


class Database:
    def __init__(self, db_file="assets_pro.db"):
        self.db_file = get_db_path(db_file)
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        print(f"正在初始化数据库，文件路径: {os.path.abspath(self.db_file)}")

        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()

            # 部门表
            c.execute('''CREATE TABLE IF NOT EXISTS departments
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          address TEXT NOT NULL,
                          contact TEXT,
                          manager TEXT NOT NULL,
                          created_at TEXT)''')

            # 员工表 - 依赖于先创建的departments表
            c.execute('''CREATE TABLE IF NOT EXISTS employees
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          position TEXT,
                          department_id INTEGER NOT NULL,
                          contact TEXT,
                          created_at TEXT,
                          FOREIGN KEY(department_id) REFERENCES departments(id))''')

            # 检查是否有sort_order列
            c.execute("PRAGMA table_info(employees)")
            columns = [column[1] for column in c.fetchall()]
            if 'sort_order' not in columns:
                # 添加 sort_order 列
                c.execute("ALTER TABLE employees ADD COLUMN sort_order INTEGER DEFAULT 0")
                # 为现有数据设置排序号
                c.execute("UPDATE employees SET sort_order = id")

            # 现在创建users表 - 依赖于先创建的departments表
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE NOT NULL,
                          password TEXT NOT NULL,
                          role TEXT NOT NULL,
                          full_name TEXT,
                          department_id INTEGER,
                          FOREIGN KEY(department_id) REFERENCES departments(id))''')

            # 资产表
            c.execute('''CREATE TABLE IF NOT EXISTS assets
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          category TEXT NOT NULL,
                          management_type TEXT DEFAULT '自主管理',
                          asset_number TEXT NOT NULL,
                          quantity INTEGER DEFAULT 1,
                          model TEXT,
                          purchase_date TEXT,
                          market_value REAL,
                          responsible_person TEXT NOT NULL,
                          location TEXT NOT NULL,
                          status TEXT,
                          lease_start_date TEXT,
                          lease_end_date TEXT,
                          lease_reminder_days INTEGER DEFAULT 30,
                          tenant_name TEXT,
                          tenant_contact TEXT,
                          image_path1 TEXT,
                          image_path2 TEXT,
                          image_path3 TEXT,
                          notes TEXT,
                          created_by TEXT,
                          created_at TEXT,
                          department_id INTEGER,
                          FOREIGN KEY(department_id) REFERENCES departments(id))''')

            # 检查并添加房屋信息字段
            c.execute("PRAGMA table_info(assets)")
            columns = [column[1] for column in c.fetchall()]

            # 添加房屋信息字段
            house_info_fields = [
                ('certificate_status', 'TEXT'),
                ('property_unit', 'TEXT'),
                ('building_area', 'TEXT')
            ]

            for field_name, field_type in house_info_fields:
                if field_name not in columns:
                    c.execute(f"ALTER TABLE assets ADD COLUMN {field_name} {field_type}")
                    print(f"已添加 {field_name} 字段")

            # 添加托管信息字段
            trusteeship_fields = [
                ('trusteeship_contract_type', 'TEXT'),
                ('trusteeship_contract_amount', 'REAL'),
                ('trusteeship_counterparty', 'TEXT'),
                ('trusteeship_contract_number', 'TEXT'),
                ('trusteeship_start_date', 'TEXT'),
                ('trusteeship_end_date', 'TEXT'),
                ('trusteeship_sign_date', 'TEXT'),
                ('trusteeship_is_archived', 'TEXT'),
            ]

            # 获取现有字段列表
            c.execute("PRAGMA table_info(assets)")
            columns = [column[1] for column in c.fetchall()]

            # 添加托管管理字段
            for field_name, field_type in trusteeship_fields:
                if field_name not in columns:
                    c.execute(f"ALTER TABLE assets ADD COLUMN {field_name} {field_type}")
                    print(f"已添加 {field_name} 字段")

            # 添加租赁信息新字段
            lease_info_fields = [
                ('tenant_nature', 'TEXT'),
                ('tenant_purpose', 'TEXT'),
                ('rent_amount', 'REAL'),
                ('rent_payment_method', 'TEXT'),
                ('bidding_situation', 'TEXT')
            ]

            for field_name, field_type in lease_info_fields:
                if field_name not in columns:
                    c.execute(f"ALTER TABLE assets ADD COLUMN {field_name} {field_type}")
                    print(f"已添加 {field_name} 字段")

            # 添加地图经纬度字段
            map_fields = [
                ('longitude', 'REAL'),
                ('latitude', 'REAL'),
                ('coord_type', 'TEXT')
            ]

            for field_name, field_type in map_fields:
                if field_name not in columns:
                    c.execute(f"ALTER TABLE assets ADD COLUMN {field_name} {field_type}")
                    print(f"已添加 {field_name} 字段")

            # 修改租赁信息字段名
            try:
                c.execute("SELECT name FROM pragma_table_info('assets') WHERE name='lessor_name'")
                if c.fetchone():
                    c.execute("ALTER TABLE assets RENAME COLUMN lessor_name TO tenant_name")

                c.execute("SELECT name FROM pragma_table_info('assets') WHERE name='lessor_contact'")
                if c.fetchone():
                    c.execute("ALTER TABLE assets RENAME COLUMN lessor_contact TO tenant_contact")
            except Exception as e:
                print(f"字段重命名时出错: {e}")

                # 为现有资产数据设置默认部门ID
                c.execute('''UPDATE assets
                             SET department_id = (
                                 SELECT e.department_id
                                 FROM employees e
                                 WHERE e.name = assets.responsible_person
                                 LIMIT 1
                             )
                             WHERE department_id IS NULL''')

                # 如果没有找到对应的员工，设置为默认部门
                c.execute("SELECT id FROM departments ORDER BY id LIMIT 1")
                default_dept = c.fetchone()
                if default_dept:
                    c.execute("UPDATE assets SET department_id = ? WHERE department_id IS NULL", (default_dept[0],))

            # 权限表
            c.execute('''CREATE TABLE IF NOT EXISTS permissions
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          role TEXT NOT NULL,
                          module TEXT NOT NULL,
                          can_view INTEGER DEFAULT 0,
                          can_add INTEGER DEFAULT 0,
                          can_edit INTEGER DEFAULT 0,
                          can_delete INTEGER DEFAULT 0,
                          can_export INTEGER DEFAULT 0,
                          can_import INTEGER DEFAULT 0,
                          UNIQUE(role, module))''')

            # 初始化权限数据
            modules = ["assets", "departments"]
            for module in modules:
                # 管理员权限
                c.execute('''INSERT OR IGNORE INTO permissions
                            (role, module, can_view, can_add, can_edit, can_delete, can_export, can_import)
                            VALUES (?, ?, 1, 1, 1, 1, 1, 1)''',
                          ("admin", module))

                # 科长在资产管理的权限
                c.execute('''INSERT OR IGNORE INTO permissions
                            (role, module, can_view, can_add, can_edit, can_delete, can_export, can_import)
                            VALUES (?, ?, 1, 1, 1, 1, 1, 1)''',
                          ("section_chief", "assets"))

                # 科长在部门管理的权限
                c.execute('''INSERT OR IGNORE INTO permissions
                            (role, module, can_view, can_add, can_edit, can_delete, can_export, can_import)
                            VALUES (?, ?, 1, 0, 1, 0, 1, 0)''',
                          ("section_chief", "departments"))

                # 员工在资产管理的权限
                c.execute('''INSERT OR IGNORE INTO permissions
                            (role, module, can_view, can_add, can_edit, can_delete, can_export, can_import)
                            VALUES (?, ?, 1, 1, 1, 1, 1, 1)''',
                          ("staff", "assets"))

                # 员工在部门管理的权限
                c.execute('''INSERT OR IGNORE INTO permissions
                            (role, module, can_view, can_add, can_edit, can_delete, can_export, can_import)
                            VALUES (?, ?, 1, 0, 0, 0, 1, 0)''',
                          ("staff", "departments"))

            # 创建默认用户
            self.create_default_users(conn)

            conn.commit()
            print("数据库表初始化完成")

        except Exception as e:
            print(f"数据库初始化失败: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    def create_default_users(self, conn):
        """创建默认用户"""
        c = conn.cursor()

        try:
            # 确保至少有一个部门
            c.execute("SELECT COUNT(*) FROM departments")
            dept_count = c.fetchone()[0]

            if dept_count == 0:
                from datetime import datetime
                default_dept = {
                    'name': '默认部门',
                    'address': 'XXX有限公司',
                    'contact': '0571-123456',
                    'manager': '系统管理员'
                }

                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute('''INSERT INTO departments (name, address, contact, manager, created_at)
                             VALUES (?, ?, ?, ?, ?)''',
                          (default_dept['name'], default_dept['address'],
                           default_dept['contact'], default_dept['manager'], current_time))
                print("已创建默认部门")

            # 获取部门ID
            c.execute("SELECT id FROM departments ORDER BY id LIMIT 1")
            dept_result = c.fetchone()
            default_dept_id = dept_result[0] if dept_result else None

            # 检查是否已有用户
            c.execute("SELECT COUNT(*) FROM users")
            user_count = c.fetchone()[0]

            if user_count == 0:
                print("创建默认用户...")

                # 创建默认管理员账户
                default_admin = {
                    'username': 'admin',
                    'password': self.hash_password('admin123'),
                    'role': 'admin',
                    'full_name': '系统管理员',
                    'department_id': None
                }

                c.execute('''INSERT INTO users (username, password, role, full_name, department_id)
                             VALUES (?, ?, ?, ?, ?)''',
                          (default_admin['username'], default_admin['password'],
                           default_admin['role'], default_admin['full_name'], None))

                # 创建默认科长账户
                default_chief = {
                    'username': 'chief',
                    'password': self.hash_password('chief123'),
                    'role': 'section_chief',
                    'full_name': '默认科长',
                    'department_id': default_dept_id
                }

                c.execute('''INSERT INTO users (username, password, role, full_name, department_id)
                             VALUES (?, ?, ?, ?, ?)''',
                          (default_chief['username'], default_chief['password'],
                           default_chief['role'], default_chief['full_name'], default_dept_id))

                # 创建默认员工账户
                default_staff = {
                    'username': 'staff',
                    'password': self.hash_password('staff123'),
                    'role': 'staff',
                    'full_name': '普通员工',
                    'department_id': default_dept_id
                }

                c.execute('''INSERT INTO users (username, password, role, full_name, department_id)
                             VALUES (?, ?, ?, ?, ?)''',
                          (default_staff['username'], default_staff['password'],
                           default_staff['role'], default_staff['full_name'], default_dept_id))

                print("默认用户创建完成")
                print("管理员账号: admin / admin123")
                print("科长账号: chief / chief123")
                print("员工账号: staff / staff123")
            else:
                print("已有用户存在，跳过默认用户创建")

        except Exception as e:
            print(f"创建默认用户时出错: {e}")
            import traceback
            traceback.print_exc()

    def hash_password(self, password):
        """密码哈希处理"""
        return hashlib.sha256(password.encode()).hexdigest()

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_file)

    def table_exists(self, cursor, table_name):
        """检查表是否存在"""
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cursor.fetchone() is not None
