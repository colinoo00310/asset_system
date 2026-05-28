"""地图功能 - 控制台版本（用于调试）"""
# -*- coding: utf-8 -*-

import sys
import os

# 首先处理路径
if getattr(sys, 'frozen', False):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if base_path not in sys.path:
    sys.path.insert(0, base_path)

print(f"[DEBUG] base_path: {base_path}")
print(f"[DEBUG] sys.path[0]: {sys.path[0]}")
print(f"[DEBUG] sys.executable: {sys.executable}")
print(f"[DEBUG] sys.frozen: {getattr(sys, 'frozen', False)}")
print(f"[DEBUG] sys._MEIPASS: {getattr(sys, '_MEIPASS', 'NOT SET')}")

# 测试导入
print("[DEBUG] 尝试导入 PyQt5...")
try:
    from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout
    print("[DEBUG] PyQt5 导入成功")
except Exception as e:
    print(f"[ERROR] PyQt5 导入失败: {e}")
    input("按回车退出...")
    sys.exit(1)

print("[DEBUG] 尝试导入项目模块...")
try:
    import json
    from config.database import Database
    from services.auth import AuthManager
    from gui.map.map_view import MapViewDialog
    print("[DEBUG] 项目模块导入成功")
except Exception as e:
    print(f"[ERROR] 项目模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    input("按回车退出...")
    sys.exit(1)

def main():
    print("[DEBUG] 读取参数文件...")
    if len(sys.argv) < 2:
        print("[ERROR] 没有参数文件")
        input("按回车退出...")
        return 1

    param_file = sys.argv[1]
    print(f"[DEBUG] 参数文件: {param_file}")

    try:
        with open(param_file, 'r', encoding='utf-8') as f:
            params = json.load(f)
        print(f"[DEBUG] 参数解析成功")
    except Exception as e:
        print(f"[ERROR] 参数解析失败: {e}")
        input("按回车退出...")
        return 1

    db_path = params.get('db_path', 'assets_pro.db')
    auth_data = params.get('auth_data', {})

    print(f"[DEBUG] 初始化数据库: {db_path}")
    try:
        db = Database(db_path)
        print("[DEBUG] 数据库初始化成功")
    except Exception as e:
        print(f"[ERROR] 数据库初始化失败: {e}")
        input("按回车退出...")
        return 1

    print("[DEBUG] 初始化认证...")
    auth = AuthManager(db)
    if auth_data.get('logged_in') and auth_data.get('user'):
        auth.current_user = auth_data.get('user')
        auth.user_permissions = auth_data.get('permissions', {})

    print("[DEBUG] 创建 QApplication...")
    app = QApplication(sys.argv)

    print("[DEBUG] 创建 MapViewDialog...")
    try:
        dialog = MapViewDialog(db, auth)
        print("[DEBUG] MapViewDialog 创建成功")
    except Exception as e:
        print(f"[ERROR] MapViewDialog 创建失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车退出...")
        return 1

    print("[DEBUG] 显示窗口...")
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()

    print("[DEBUG] 进入事件循环...")
    print("[DEBUG] 窗口应该正在显示!")
    exit_code = app.exec_()

    print(f"[DEBUG] 应用退出，代码: {exit_code}")
    return exit_code

if __name__ == "__main__":
    print("[DEBUG] 脚本开始执行")
    sys.exit(main())
