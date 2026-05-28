import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import sys
import os

# 添加项目根目录到路径（兼容开发和打包环境）
def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        else:
            return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

project_root = get_project_root()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.utils import Utils

class UserManagement:
    def __init__(self, parent, db, auth):
        self.parent = parent
        self.db = db
        self.auth = auth
        self.utils = Utils()

        self.clear_content()
        self.create_user_interface()
        self.load_users()

    def clear_content(self):
        """清除内容区域"""
        for widget in self.parent.winfo_children():
            widget.destroy()

    def create_user_interface(self):
        """创建用户管理界面"""
        # 工具栏
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill="x", pady=5)

        # 获取当前用户角色
        current_user_role = self.auth.get_current_user()['role']

        if current_user_role == 'admin':
            # admin用户显示所有功能
            ttk.Button(toolbar, text="添加用户", command=lambda: self.user_dialog("添加用户")).pack(side="left", padx=5)
            ttk.Button(toolbar, text="编辑用户", command=lambda: self.edit_selected_user()).pack(side="left", padx=5)
            ttk.Button(toolbar, text="删除用户", command=self.delete_user).pack(side="left", padx=5)
            ttk.Button(toolbar, text="刷新", command=self.load_users).pack(side="left", padx=5)
        else:
            # staff用户只显示刷新功能
            ttk.Button(toolbar, text="刷新", command=self.load_users).pack(side="left", padx=5)

        # 用户表格
        tree_frame = ttk.Frame(self.parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.user_tree = ttk.Treeview(tree_frame, columns=("ID", "用户名", "角色", "姓名"), show="headings")

        # 设置列
        columns = {
            "ID": {"width": 50, "anchor": "center"},
            "用户名": {"width": 150, "anchor": "center"},
            "角色": {"width": 100, "anchor": "center"},
            "姓名": {"width": 150, "anchor": "center"}
        }

        for col, settings in columns.items():
            self.user_tree.column(col, **settings)
            self.user_tree.heading(col, text=col)

        # 滚动条
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.user_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.user_tree.xview)
        self.user_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.user_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 状态栏
        status_bar = ttk.Frame(self.parent, height=25)
        status_bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar()
        self.status_var.set(
            f"欢迎, {self.auth.get_current_user()['full_name'] or self.auth.get_current_user()['username']} | 角色: {self.auth.get_current_user()['role']}")
        ttk.Label(status_bar, textvariable=self.status_var, relief="sunken", padding=2).pack(fill="x")

    def load_users(self):
        """加载用户数据"""
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)

        conn = self.db.get_connection()
        c = conn.cursor()

        # 按照角色排序，先按照admin、section_chief、staff排序，再按ID排序
        c.execute("""
            SELECT id, username, role, full_name 
            FROM users 
            ORDER BY 
                CASE role
                    WHEN 'admin' THEN 0
                    WHEN 'section_chief' THEN 1
                    WHEN 'staff' THEN 2
                    ELSE 3
                END,
                id
        """)

        rows = c.fetchall()
        conn.close()

        # 重新编号显示序号，不改变数据库ID
        display_id = 1
        for row in rows:
            # 使用显示序号而不是数据库ID
            display_values = (display_id, row[1], row[2], row[3])
            self.user_tree.insert("", "end", values=display_values, tags=(f"user_{row[0]}",))
            display_id += 1

        self.status_var.set(f"共加载 {len(rows)} 条用户信息")

    def user_dialog(self, title, data=None):
        """用户添加/编辑对话框"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(title)
        dialog.grab_set()

        # 居中显示
        self.utils.center_window(dialog)

        # 主容器
        main_frame = ttk.Frame(dialog, padding=15)
        main_frame.pack()

        # 获取部门列表
        conn = self.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM departments ORDER BY name")
        departments = c.fetchall()
        conn.close()

        department_choices = ["无"] + [dept[1] for dept in departments]
        department_ids = {dept[1]: dept[0] for dept in departments}

        # 表单字段
        fields = ["用户名", "密码", "确认密码", "角色", "部门", "姓名"]
        entries = {}

        for i, field in enumerate(fields):
            ttk.Label(main_frame, text=field + ":").grid(row=i, column=0, padx=5, pady=5, sticky="e")

            if field in ["密码", "确认密码"]:
                entry = ttk.Entry(main_frame, width=30, show="*")
            elif field == "角色":
                entry = ttk.Combobox(main_frame, width=28, values=["admin", "section_chief", "staff"], state="readonly")
                entry.set("staff")
            elif field == "部门":
                entry = ttk.Combobox(main_frame, width=28, values=department_choices, state="readonly")
                entry.set("无")
            else:
                entry = ttk.Entry(main_frame, width=30)

            entry.grid(row=i, column=1, padx=5, pady=5)
            entries[field] = entry

        # 在编辑模式填充数据时
        if data:
            # 获取真实的数据库ID
            selected_item = self.user_tree.selection()[0]
            tags = self.user_tree.item(selected_item, "tags")
            db_id = int(tags[0].split("_")[1]) if tags else None

            if db_id:
                conn = self.db.get_connection()
                c = conn.cursor()

                # 确保查询包含 department_id
                c.execute("SELECT username, role, full_name, department_id FROM users WHERE id=?", (db_id,))
                user_data = c.fetchone()
                conn.close()

                if user_data:
                    entries["用户名"].insert(0, user_data[0])
                    entries["用户名"].config(state="disabled")
                    entries["角色"].set(user_data[1])
                    entries["姓名"].insert(0, user_data[2] if user_data[2] else "")

                    # 设置部门
                    if user_data[3]:  # department_id
                        # 根据department_id获取部门名称
                        conn = self.db.get_connection()
                        c = conn.cursor()
                        c.execute("SELECT name FROM departments WHERE id=?", (user_data[3],))
                        dept_name = c.fetchone()
                        conn.close()

                        if dept_name:
                            entries["部门"].set(dept_name[0])
                    else:
                        entries["部门"].set("无")

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=(10, 0))

        ttk.Button(btn_frame, text="保存",
                   command=lambda: self.save_user(dialog, entries, data, department_ids)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="left", padx=5)

    def save_user(self, dialog, entries, data=None, department_ids=None):
        """保存用户信息"""
        username = entries["用户名"].get().strip()
        password = entries["密码"].get().strip()
        confirm_pwd = entries["确认密码"].get().strip()
        role = entries["角色"].get().strip()
        department_name = entries["部门"].get().strip()
        full_name = entries["姓名"].get().strip()

        # 验证输入
        if not username:
            messagebox.showerror("错误", "用户名不能为空")
            return

        if not data and not password:
            messagebox.showerror("错误", "密码不能为空")
            return

        if password and password != confirm_pwd:
            messagebox.showerror("错误", "两次输入的密码不一致")
            return

        if not role:
            messagebox.showerror("错误", "必须选择角色")
            return

        # 处理部门ID
        department_id = None
        if department_name != "无" and department_ids and department_name in department_ids:
            department_id = department_ids[department_name]

        # 保存到数据库
        conn = self.db.get_connection()
        c = conn.cursor()

        try:
            if data:  # 更新用户
                # 获取真实的数据库ID
                selected_item = self.user_tree.selection()[0]
                tags = self.user_tree.item(selected_item, "tags")
                user_id = int(tags[0].split("_")[1]) if tags else None

                if user_id:
                    if password:  # 更新密码
                        hashed_pwd = self.db.hash_password(password)
                        c.execute("UPDATE users SET password=?, role=?, department_id=?, full_name=? WHERE id=?",
                                  (hashed_pwd, role, department_id, full_name, user_id))
                    else:  # 不更新密码
                        c.execute("UPDATE users SET role=?, department_id=?, full_name=? WHERE id=?",
                                  (role, department_id, full_name, user_id))
            else:  # 新增用户
                hashed_pwd = self.db.hash_password(password)
                c.execute(
                    "INSERT INTO users (username, password, role, department_id, full_name) VALUES (?, ?, ?, ?, ?)",
                    (username, hashed_pwd, role, department_id, full_name))

            conn.commit()
            messagebox.showinfo("成功", "用户信息已保存")
            dialog.destroy()

            # 刷新用户列表
            self.load_users()
        except sqlite3.IntegrityError:
            messagebox.showerror("错误", "用户名已存在")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
        finally:
            conn.close()

    def edit_selected_user(self):
        """编辑选中用户"""
        selected_item = self.user_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个用户")
            return

        item_data = self.user_tree.item(selected_item)["values"]
        self.user_dialog("编辑用户", item_data)

    def delete_user(self):
        """删除用户"""
        selected_item = self.user_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个用户")
            return

        # 获取真实的数据库ID
        tags = self.user_tree.item(selected_item, "tags")
        user_id = int(tags[0].split("_")[1]) if tags else None

        if not user_id:
            messagebox.showerror("错误", "无法获取用户ID")
            return

        username = self.user_tree.item(selected_item)["values"][1]

        if username == self.auth.get_current_user()["username"]:
            messagebox.showerror("错误", "不能删除当前登录的用户")
            return

        if messagebox.askyesno("确认", f"确定要删除用户 '{username}' 吗？"):
            conn = self.db.get_connection()
            c = conn.cursor()

            try:
                # 删除用户
                c.execute("DELETE FROM users WHERE id=?", (user_id,))

                # 更新自增序列
                c.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM users) WHERE name='users'")

                conn.commit()
                messagebox.showinfo("成功", "用户已删除")
                self.load_users()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("错误", f"删除失败: {str(e)}")
            finally:
                conn.close()
