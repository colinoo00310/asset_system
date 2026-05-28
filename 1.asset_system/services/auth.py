from config.database import Database


class AuthManager:
    def __init__(self, db: Database):
        self.db = db
        self.current_user = None
        self.user_permissions = {}

    def login(self, username, password):
        """用户登录"""
        conn = self.db.get_connection()
        c = conn.cursor()

        hashed_password = self.db.hash_password(password)

        c.execute("SELECT id, username, role, full_name, department_id FROM users WHERE username=? AND password=?",
                  (username, hashed_password))
        user = c.fetchone()
        conn.close()

        if user:
            self.current_user = {
                "id": user[0],
                "username": user[1],
                "role": user[2],
                "full_name": user[3],
                "department_id": user[4]
            }
            self.load_user_permissions(user[2])
            return True
        return False

    def load_user_permissions(self, role):
        """加载用户权限"""
        conn = self.db.get_connection()
        c = conn.cursor()

        c.execute(
            "SELECT module, can_view, can_add, can_edit, can_delete, can_export, can_import FROM permissions WHERE role=?",
            (role,))
        permissions = c.fetchall()

        self.user_permissions = {}
        for perm in permissions:
            module = perm[0]
            self.user_permissions[module] = {
                "view": bool(perm[1]),
                "add": bool(perm[2]),
                "edit": bool(perm[3]),
                "delete": bool(perm[4]),
                "export": bool(perm[5]),
                "import": bool(perm[6])
            }

        conn.close()

    def has_permission(self, module, action):
        """检查用户是否有特定权限"""
        if module in self.user_permissions:
            return self.user_permissions[module].get(action, False)
        return False

    def can_view_asset(self, asset_department_id=None):
        """检查用户是否有权限查看资产"""
        user = self.get_current_user()
        if user['role'] == 'admin':
            return True
        elif user['role'] == 'section_chief' or user['role'] == 'staff':
            return user.get('department_id') == asset_department_id
        return False

    def can_manage_asset(self, asset_department_id=None):
        """检查用户是否有权限管理资产"""
        user = self.get_current_user()
        if user['role'] == 'admin':
            return True
        elif user['role'] == 'section_chief' or user['role'] == 'staff':
            return user.get('department_id') == asset_department_id
        return False

    def can_add_asset(self, department_id=None):
        """检查用户是否可以添加资产"""
        user = self.get_current_user()

        if not self.has_permission("assets", "add"):
            return False

        if user['role'] == 'admin':
            return True
        elif user['role'] == 'section_chief' or user['role'] == 'staff':
            return user.get('department_id') == department_id
        return False

    def can_edit_asset(self, asset_department_id=None):
        """检查用户是否可以编辑资产"""
        user = self.get_current_user()

        if not self.has_permission("assets", "edit"):
            return False

        if user['role'] == 'admin':
            return True
        elif user['role'] == 'section_chief' or user['role'] == 'staff':
            return user.get('department_id') == asset_department_id
        return False

    def can_delete_asset(self, asset_department_id=None):
        """检查用户是否可以删除资产"""
        user = self.get_current_user()

        if not self.has_permission("assets", "delete"):
            return False

        if user['role'] == 'admin':
            return True
        elif user['role'] == 'section_chief' or user['role'] == 'staff':
            return user.get('department_id') == asset_department_id
        return False

    def can_edit_department(self, department_id=None):
        """检查用户是否可以编辑部门"""
        user = self.get_current_user()

        if not self.has_permission("departments", "edit"):
            return False

        if user['role'] == 'admin':
            return True
        elif user['role'] == 'section_chief':
            return user.get('department_id') == department_id
        elif user['role'] == 'staff':
            return False
        return False

    def logout(self):
        """用户登出"""
        self.current_user = None
        self.user_permissions = {}

    def get_current_user(self):
        """获取当前用户信息"""
        return self.current_user
