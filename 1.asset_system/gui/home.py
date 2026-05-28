import os
import tkinter as tk
from tkinter import ttk
import textwrap
import random
import sys

# 添加项目根目录到路径
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


class HomePage:
    def __init__(self, parent, db, auth):
        self.parent = parent
        self.db = db
        self.auth = auth
        self.utils = Utils()
        self.home_images = []

        self.clear_content()
        self.create_home_page()

    def clear_content(self):
        """清除内容区域"""
        for widget in self.parent.winfo_children():
            widget.destroy()

    def create_home_page(self):
        """创建首页内容"""
        home_frame = ttk.Frame(self.parent, padding=20)
        home_frame.pack(fill="both", expand=True)

        # 公司图片
        company_photo = None
        try:
            # 添加更多可能的图片路径
            possible_paths = [
                self.utils.resource_path("images/company_image.png"),
                self.utils.resource_path("company_image.png"),
                "images/company_image.png",
                "company_image.png"
            ]

            company_image_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    company_image_path = path
                    break

            if company_image_path:
                from PIL import Image, ImageTk
                img = Image.open(company_image_path)
                img = img.resize((50, 50), Image.LANCZOS)
                company_photo = ImageTk.PhotoImage(img)
                self.home_images.append(company_photo)
            else:
                print("未找到图片文件，尝试以下路径:")
                for path in possible_paths:
                    print(f"  {path}")
        except Exception as e:
            print(f"加载公司图片失败: {e}")

        # 公司标题
        title_frame = ttk.Frame(home_frame)
        title_frame.pack(pady=(0, 10))

        title_inner_frame = tk.Frame(title_frame, bg="white")
        title_inner_frame.pack()

        if company_photo:
            image_label = tk.Label(title_inner_frame, image=company_photo, bg="white")
            image_label.image = company_photo
            image_label.pack(side="left", padx=(0, 10))
        else:
            # 添加占位符或默认图片
            placeholder = tk.Label(title_inner_frame, text="[图片]", bg="white", fg="gray")
            placeholder.pack(side="left", padx=(0, 10))

        title_label = tk.Label(title_inner_frame, text="XXX有限公司",
                               font=('微软雅黑', 20, 'bold'), fg="#2c3e50", bg="white")
        title_label.pack(side="left")


        # 主内容框架
        main_content_frame = ttk.Frame(home_frame)
        main_content_frame.pack(fill="both", expand=True)

        # 上部分区域
        top_frame = ttk.Frame(main_content_frame)
        top_frame.pack(fill="both", expand=True, pady=(0, 10))

        paned_window = tk.PanedWindow(top_frame, orient=tk.HORIZONTAL, sashwidth=4)
        paned_window.pack(fill="both", expand=True)

        # 左侧统计框架
        left_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(left_frame, minsize=400, width=400)

        # 右侧简介框架
        right_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(right_frame, minsize=400)

        # 系统统计
        self.create_stats_section(left_frame)

        # 公司简介
        self.create_intro_section(right_frame)

        # 联系我们
        bottom_frame = ttk.Frame(main_content_frame)
        bottom_frame.pack(fill="x")

        self.create_contact_section(bottom_frame)

    def create_stats_section(self, parent):
        """创建统计区域"""
        stats_frame = tk.LabelFrame(parent, text="系统统计", font=('微软雅黑', 13, 'bold'), padx=15, pady=10)
        stats_frame.pack(fill="both", expand=True)

        # 获取当前用户信息
        current_user = self.auth.get_current_user()

        # 初始化统计变量
        asset_count = 0
        own_asset_count = 0
        lease_asset_count = 0
        trusteeship_asset_count = 0

        # 获取统计数据
        conn = self.db.get_connection()
        c = conn.cursor()

        try:
            # 获取部门数量（只统计有员工的部门）
            c.execute("""
                SELECT COUNT(DISTINCT d.id) FROM departments d
                INNER JOIN employees e ON d.id = e.department_id
            """)
            dept_result = c.fetchone()
            dept_count = dept_result[0] if dept_result else 0

            # 获取用户数量
            c.execute("SELECT COUNT(*) FROM users")
            user_result = c.fetchone()
            user_count = user_result[0] if user_result else 0

            # 资产统计（根据权限区分）
            if current_user['role'] == 'admin':
                # 管理员查看所有资产
                c.execute("SELECT COUNT(*) FROM assets")
                result = c.fetchone()
                asset_count = result[0] if result else 0

                c.execute("SELECT COUNT(*) FROM assets WHERE management_type='自主管理'")
                result = c.fetchone()
                own_asset_count = result[0] if result else 0

                c.execute("SELECT COUNT(*) FROM assets WHERE management_type='租赁管理'")
                result = c.fetchone()
                lease_asset_count = result[0] if result else 0  # 改名为 lease_asset_count

                c.execute("SELECT COUNT(*) FROM assets WHERE management_type='托管管理'")  # 新增
                result = c.fetchone()
                trusteeship_asset_count = result[0] if result else 0  # 新增

            else:
                # 科长和员工只查看本部门的资产
                dept_id = current_user.get('department_id')

                if dept_id:
                    c.execute("SELECT COUNT(*) FROM assets WHERE department_id=?", (dept_id,))
                    result = c.fetchone()
                    asset_count = result[0] if result else 0

                    c.execute("SELECT COUNT(*) FROM assets WHERE department_id=? AND management_type='自主管理'",
                              (dept_id,))
                    result = c.fetchone()
                    own_asset_count = result[0] if result else 0

                    c.execute("SELECT COUNT(*) FROM assets WHERE department_id=? AND management_type='租赁管理'",
                              (dept_id,))
                    result = c.fetchone()
                    lease_asset_count = result[0] if result else 0  # 改名为 lease_asset_count

                    c.execute("SELECT COUNT(*) FROM assets WHERE department_id=? AND management_type='托管管理'",  # 新增
                              (dept_id,))
                    result = c.fetchone()
                    trusteeship_asset_count = result[0] if result else 0  # 新增
                else:
                    lease_asset_count = 0  # 新增
                    trusteeship_asset_count = 0  # 新增

            # 资产分类统计
            asset_categories = {}
            if current_user['role'] == 'admin':
                c.execute("SELECT category, COUNT(*) FROM assets GROUP BY category")
                categories = c.fetchall()
            else:
                dept_id = current_user.get('department_id')
                if dept_id:
                    c.execute("SELECT category, COUNT(*) FROM assets WHERE department_id=? GROUP BY category",
                              (dept_id,))
                    categories = c.fetchall()
                else:
                    categories = []

            for category, count in categories:
                asset_categories[category] = count

            # 获取用户部门名称
            dept_name = "无"
            dept_id = current_user.get('department_id')
            if dept_id:
                c.execute("SELECT name FROM departments WHERE id=?", (dept_id,))
                result = c.fetchone()
                dept_name = result[0] if result else "未知部门"

        except Exception as e:
            print(f"获取统计数据时出错: {e}")
            error_label = tk.Label(stats_frame, text=f"数据加载出错: {str(e)}",
                                   font=('微软雅黑', 10), fg="red")
            error_label.pack()
            conn.close()
            return

        finally:
            conn.close()

        # 显示统计信息
        if current_user['role'] == 'admin':
            stats_text = f"""
        系统全局统计：
        • 资产总数：{asset_count} 个
            - 自主管理：{own_asset_count} 个
            - 租赁管理：{lease_asset_count} 个  
            - 托管管理：{trusteeship_asset_count} 个  
        • 部门数量：{dept_count} 个  
        • 用户数量：{user_count} 个
            """
        else:
            stats_text = f"""
        部门资产统计（{dept_name}）：
        • 资产总数：{asset_count} 个
            - 自主管理：{own_asset_count} 个
            - 租赁管理：{lease_asset_count} 个
            - 托管管理：{trusteeship_asset_count} 个  

        系统全局：
        • 部门数量：{dept_count} 个
        • 用户数量：{user_count} 个
            """

        stats_label = tk.Label(stats_frame, text=stats_text, justify="left", font=('微软雅黑', 11))
        stats_label.pack(anchor="w", pady=(0, 5))

        # 资产分类饼状图
        if asset_categories:
            chart_container = ttk.Frame(stats_frame)
            chart_container.pack(fill="x", pady=(10, 0))

            # 显示标题
            if current_user['role'] == 'admin':
                title_label = ttk.Label(chart_container, text="系统资产分类统计",
                                        font=('微软雅黑', 11, 'bold'))
                title_label.pack(anchor="w")
            else:
                title_label = ttk.Label(chart_container, text=f"【{dept_name}】资产分类统计",
                                        font=('微软雅黑', 11, 'bold'))
                title_label.pack(anchor="w")

            # 创建饼状图
            self.create_simple_pie_chart(chart_container, asset_categories)
        else:
            print("没有资产分类数据")
            if current_user['role'] == 'admin':
                no_data_label = tk.Label(stats_frame, text="暂无资产分类数据",
                                         font=('微软雅黑', 10), fg="gray")
            else:
                no_data_label = tk.Label(stats_frame,
                                         text=f"【{dept_name}】暂无资产分类数据",
                                         font=('微软雅黑', 10), fg="gray")
            no_data_label.pack(pady=(10, 0))

    def create_simple_pie_chart(self, parent, asset_categories):
        """创建简单的饼状图"""
        pie_frame = ttk.Frame(parent)
        pie_frame.pack(pady=10)

        canvas_size = 150
        canvas = tk.Canvas(pie_frame, width=canvas_size, height=canvas_size,
                           bg='white', highlightthickness=0)
        canvas.pack()

        total_assets = sum(asset_categories.values())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F9A826', '#6A0572', '#98D8AA', '#FF9A76']


        # 单类资产直接画一个完整的圆
        if len(asset_categories) == 1:
            category, count = list(asset_categories.items())[0]
            color = colors[0] if colors else '#FF6B6B'

            canvas.create_oval(10, 10, canvas_size - 10, canvas_size - 10,
                               fill=color, outline='white', width=2)

        else:
            # 多类资产的情况
            start_angle = 0
            for i, (category, count) in enumerate(asset_categories.items()):
                if i >= len(colors):
                    color = f"#{random.randint(0, 0xFFFFFF):06x}"
                else:
                    color = colors[i]

                extent = 360 * (count / total_assets)

                # 最后一个部分，确保总和为360
                if i == len(asset_categories) - 1:
                    extent = 360 - start_angle

                canvas.create_arc(10, 10, canvas_size - 10, canvas_size - 10,
                                  start=start_angle, extent=extent,
                                  fill=color, outline='white', width=1)
                start_angle += extent

        # 图例
        legend_frame = ttk.Frame(parent)
        legend_frame.pack(fill="x", pady=(5, 0))

        for i, (category, count) in enumerate(asset_categories.items()):
            if i >= len(colors):
                color = f"#{random.randint(0, 0xFFFFFF):06x}"
            else:
                color = colors[i]

            percentage = (count / total_assets) * 100

            legend_item = ttk.Frame(legend_frame)
            legend_item.pack(fill="x", pady=2)

            color_canvas = tk.Canvas(legend_item, width=20, height=20, highlightthickness=0)
            color_canvas.pack(side="left")
            color_canvas.create_rectangle(2, 2, 18, 18, fill=color, outline='gray')

            info_text = f"{category}: {count}个 ({percentage:.1f}%)"
            ttk.Label(legend_item, text=info_text, font=('微软雅黑', 9)).pack(side="left", padx=5)

    def show_lease_reminders(self):
        """显示租赁提醒"""
        conn = self.db.get_connection()
        c = conn.cursor()

        # 查询即将到期的租赁资产
        c.execute('''
            SELECT a.name, a.lease_end_date, a.responsible_person, a.location, a.tenant_name  # 改为tenant_name
            FROM assets a
            WHERE a.management_type = '租赁管理'
            AND a.lease_end_date IS NOT NULL
            AND date(a.lease_end_date) <= date('now', '+' || COALESCE(a.lease_reminder_days, 30) || ' days')
            ORDER BY a.lease_end_date
        ''')

        reminders = c.fetchall()
        conn.close()

        if not reminders:
            from tkinter import messagebox
            messagebox.showinfo("租赁提醒", "没有即将到期的租赁资产")
            return

        # 创建提醒对话框
        from tkinter import Toplevel
        from datetime import datetime

        reminder_dialog = Toplevel(self.parent)
        reminder_dialog.title("租赁到期提醒")
        reminder_dialog.geometry("800x400")

        self.utils.center_window(reminder_dialog)

        # 创建表格显示提醒信息
        tree_frame = ttk.Frame(reminder_dialog)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(tree_frame, columns=("资产名称", "到期日期", "剩余天数", "责任人", "位置", "出租方"),
                            show="headings")

        columns = {
            "资产名称": {"width": 150, "anchor": "center"},
            "到期日期": {"width": 100, "anchor": "center"},
            "剩余天数": {"width": 80, "anchor": "center"},
            "责任人": {"width": 80, "anchor": "center"},
            "位置": {"width": 120, "anchor": "center"},
            "出租方": {"width": 100, "anchor": "center"}
        }

        for col, settings in columns.items():
            tree.column(col, **settings)
            tree.heading(col, text=col)

        # 添加滚动条
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 填充数据
        today = datetime.now().date()
        for reminder in reminders:
            try:
                end_date = datetime.strptime(reminder[1], "%Y-%m-%d").date()
                days_left = (end_date - today).days

                status_color = ""
                if days_left < 0:
                    status_text = f"已过期{abs(days_left)}天"
                    status_color = "red"
                elif days_left <= 7:
                    status_text = f"剩余{days_left}天"
                    status_color = "orange"
                else:
                    status_text = f"剩余{days_left}天"
                    status_color = "green"

                tree.insert("", "end", values=(
                    reminder[0], reminder[1], status_text,
                    reminder[2], reminder[3], reminder[4] or "未知"
                ), tags=(status_color,))

            except:
                tree.insert("", "end", values=(
                    reminder[0], reminder[1], "日期格式错误",
                    reminder[2], reminder[3], reminder[4] or "未知"
                ))

        # 设置颜色
        tree.tag_configure("red", foreground="red")
        tree.tag_configure("orange", foreground="orange")
        tree.tag_configure("green", foreground="green")

        # 关闭按钮
        ttk.Button(reminder_dialog, text="关闭", command=reminder_dialog.destroy).pack(pady=10)

    def create_intro_section(self, parent):
        """创建公司简介区域"""
        intro_frame = tk.LabelFrame(parent, text="公司简介", font=('微软雅黑', 13, 'bold'), padx=15, pady=10)
        intro_frame.pack(fill="both", expand=True)

        # 获取当前用户信息
        current_user = self.auth.get_current_user()

        # 显示欢迎信息和用户信息
        welcome_frame = ttk.Frame(intro_frame)
        welcome_frame.pack(fill="x", pady=(0, 15))

        # 角色显示映射
        role_mapping = {
            'admin': '管理员',
            'section_chief': '科长',
            'staff': '员工'
        }

        role_display = role_mapping.get(current_user['role'], current_user['role'])
        full_name = current_user['full_name'] or current_user['username']

        # 欢迎信息
        welcome_label = tk.Label(welcome_frame,
                                 text=f"👋 欢迎您进入系统，{role_display}：{full_name}",
                                 font=('微软雅黑', 12, 'bold'),
                                 fg="#2c3e50")
        welcome_label.pack(anchor="w")

        # 用户名信息
        username_label = tk.Label(welcome_frame,
                                  text=f"👤 当前用户名为：{current_user['username']}",
                                  font=('微软雅黑', 12, 'bold'),
                                  fg="#2c3e50")
        username_label.pack(anchor="w", pady=(5, 0))

        # 添加分隔线
        separator = ttk.Separator(intro_frame, orient='horizontal')
        separator.pack(fill='x', pady=(0, 15))

        intro_text = textwrap.dedent("""\
        XXXX有限公司成立于XXX年X月X日，...

        公司主营业务包括：
        • XXX
        • XXX
        """).strip()

        # 创建可滚动的文本框
        text_frame = ttk.Frame(intro_frame)
        text_frame.pack(fill="both", expand=True)

        intro_text_widget = tk.Text(text_frame, wrap="char", font=('微软雅黑', 11),
                                    bg=intro_frame.cget('bg'), relief="flat",
                                    borderwidth=0, padx=5, pady=5, height=10)  # 限制高度
        intro_text_widget.insert("1.0", intro_text)
        intro_text_widget.config(state="disabled")

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=intro_text_widget.yview)
        intro_text_widget.configure(yscrollcommand=scrollbar.set)

        intro_text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        intro_frame.grid_rowconfigure(0, weight=1)
        intro_frame.grid_columnconfigure(0, weight=1)

    def create_contact_section(self, parent):
        """创建联系我们区域"""
        contact_frame = tk.LabelFrame(parent, text="联系我们", font=('微软雅黑', 13, 'bold'), padx=15, pady=10)
        contact_frame.pack(fill="x")

        contact_text = """🏣 地址：XXX
📞 电话：XXX
📧 邮箱：XXX"""

        contact_label = tk.Label(contact_frame, text=contact_text, justify="left", font=('微软雅黑', 11))
        contact_label.pack(anchor="w", pady=5)

    def create_pie_chart(self, parent, asset_categories, show_title=False):
        """创建饼状图
        Args:
            parent: 父容器
            asset_categories: 资产分类数据字典
            show_title: 是否显示标题
        """
        chart_frame = ttk.Frame(parent)
        chart_frame.pack(fill="x", pady=(5, 0))  # 减少上边距

        # 只有当外部要求显示标题时才显示
        if show_title:
            if hasattr(self, 'auth'):
                current_user = self.auth.get_current_user()
                if current_user['role'] == 'admin':
                    ttk.Label(chart_frame, text="系统资产分类统计",
                              font=('微软雅黑', 11, 'bold')).pack(anchor="w")
                else:
                    ttk.Label(chart_frame, text="资产分类统计",
                              font=('微软雅黑', 11, 'bold')).pack(anchor="w")

        # 创建饼状图画布
        canvas_frame = ttk.Frame(chart_frame)
        canvas_frame.pack(pady=(0, 10))

        pie_frame = ttk.Frame(canvas_frame)
        pie_frame.pack(pady=10)

        canvas_size = 150
        canvas = tk.Canvas(pie_frame, width=canvas_size, height=canvas_size, bg='white', highlightthickness=0)
        canvas.pack()

        total_assets = sum(asset_categories.values())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F9A826', '#6A0572', '#98D8AA', '#FF9A76']

        start_angle = 0
        for i, (category, count) in enumerate(asset_categories.items()):
            if i >= len(colors):
                color = f"#{random.randint(0, 0xFFFFFF):06x}"
            else:
                color = colors[i]

            extent = 360 * (count / total_assets)
            canvas.create_arc(10, 10, canvas_size - 10, canvas_size - 10,
                              start=start_angle, extent=extent, fill=color, outline='white')
            start_angle += extent

        # 图例
        legend_frame = ttk.Frame(canvas_frame)
        legend_frame.pack(fill="x", pady=10)

        for i, (category, count) in enumerate(asset_categories.items()):
            if i >= len(colors):
                color = f"#{random.randint(0, 0xFFFFFF):06x}"
            else:
                color = colors[i]

            percentage = (count / total_assets) * 100

            legend_item = ttk.Frame(legend_frame)
            legend_item.pack(fill="x", pady=2)

            color_canvas = tk.Canvas(legend_item, width=20, height=20, highlightthickness=0)
            color_canvas.pack(side="left")
            color_canvas.create_rectangle(2, 2, 18, 18, fill=color, outline='gray')

            info_text = f"{category}: {count}个 ({percentage:.1f}%)"
            ttk.Label(legend_item, text=info_text, font=('微软雅黑', 9)).pack(side="left", padx=5)
