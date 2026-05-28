"""地图功能诊断工具 - 用于测试地图子进程是否能正常启动"""

import sys
import os
import tempfile
import json

def log(msg):
    """写入诊断日志"""
    log_dir = os.path.join(tempfile.gettempdir(), 'asset_system_logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'map_diagnose.log')
    with open(log_file, 'a', encoding='utf-8') as f:
        from datetime import datetime
        f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

def main():
    log("=" * 50)
    log("地图诊断开始")
    log("=" * 50)

    # 1. 检查环境
    log(f"Python: {sys.executable}")
    log(f"sys.frozen: {getattr(sys, 'frozen', False)}")
    log(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'NOT SET')}")
    log(f"sys.executable: {sys.executable}")
    log(f"__file__: {__file__}")
    log(f"os.getcwd(): {os.getcwd()}")

    # 2. 检查参数文件
    if len(sys.argv) < 2:
        log("错误: 没有参数文件")
        input("按回车退出...")
        return 1

    param_file = sys.argv[1]
    log(f"参数文件: {param_file}")
    log(f"参数文件存在: {os.path.exists(param_file)}")

    if not os.path.exists(param_file):
        log("错误: 参数文件不存在!")
        input("按回车退出...")
        return 1

    try:
        with open(param_file, 'r', encoding='utf-8') as f:
            params = json.load(f)
        log(f"参数解析成功: {list(params.keys())}")
    except Exception as e:
        log(f"参数解析失败: {e}")
        input("按回车退出...")
        return 1

    # 3. 检查 PyQt5
    log("尝试导入 PyQt5...")
    try:
        from PyQt5.QtWidgets import QApplication, QDialog
        from PyQt5.QtCore import Qt
        log("PyQt5 导入成功")
    except Exception as e:
        log(f"PyQt5 导入失败: {e}")
        import traceback
        log(traceback.format_exc())
        input("按回车退出...")
        return 1

    # 4. 检查项目模块
    log("检查项目根目录...")
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            project_root = sys._MEIPASS
        else:
            project_root = os.path.dirname(sys.executable)
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    log(f"项目根目录: {project_root}")
    log(f"项目根目录存在: {os.path.exists(project_root)}")

    # 检查关键文件
    files_to_check = [
        os.path.join(project_root, 'config', 'database.py'),
        os.path.join(project_root, 'services', 'auth.py'),
        os.path.join(project_root, 'gui', 'map', 'map_view.py'),
    ]

    for f in files_to_check:
        log(f"  {f}: {'存在' if os.path.exists(f) else '不存在'}")

    # 5. 添加到 sys.path 并导入
    log("添加到 sys.path...")
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    log("导入 config.database...")
    try:
        from config.database import Database
        log("导入成功")
    except Exception as e:
        log(f"导入 config.database 失败: {e}")
        import traceback
        log(traceback.format_exc())
        input("按回车退出...")
        return 1

    log("导入 services.auth...")
    try:
        from services.auth import AuthManager
        log("导入成功")
    except Exception as e:
        log(f"导入 services.auth 失败: {e}")
        input("按回车退出...")
        return 1

    log("导入 gui.map.map_view...")
    try:
        from gui.map.map_view import MapViewDialog
        log("导入成功")
    except Exception as e:
        log(f"导入 gui.map.map_view 失败: {e}")
        import traceback
        log(traceback.format_exc())
        input("按回车退出...")
        return 1

    # 6. 初始化数据库
    log("初始化数据库...")
    db_path = params.get('db_path', 'assets_pro.db')
    log(f"数据库路径: {db_path}")
    try:
        db = Database(db_path)
        log("数据库初始化成功")
    except Exception as e:
        log(f"数据库初始化失败: {e}")
        input("按回车退出...")
        return 1

    # 7. 创建应用和窗口
    log("创建 QApplication...")
    try:
        app = QApplication(sys.argv)
        log("QApplication 创建成功")
    except Exception as e:
        log(f"QApplication 创建失败: {e}")
        input("按回车退出...")
        return 1

    log("创建 MapViewDialog...")
    try:
        auth = AuthManager(db)
        dialog = MapViewDialog(db, auth)
        log("MapViewDialog 创建成功")
    except Exception as e:
        log(f"MapViewDialog 创建失败: {e}")
        import traceback
        log(traceback.format_exc())
        input("按回车退出...")
        return 1

    # 8. 显示窗口
    log("显示窗口...")
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    log("窗口已显示!")

    log("进入事件循环...")
    log("=" * 50)
    log("诊断完成，窗口应该正在显示")
    log("关闭窗口后会自动退出")
    log("=" * 50)

    exit_code = app.exec_()
    log(f"应用退出，代码: {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
