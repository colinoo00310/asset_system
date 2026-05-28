"""
独立运行的地图窗口
用于从主程序外部启动地图展示功能
"""

import sys
import os
import json
import tempfile
import ctypes
from ctypes import wintypes


def get_short_path_name(long_path):
    """
    将长路径转换为短路径（8.3格式）
    用于处理中文路径问题
    """
    try:
        GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
        GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        GetShortPathNameW.restype = wintypes.DWORD

        # 首先获取需要的缓冲区大小
        buffer_size = GetShortPathNameW(long_path, None, 0)
        if buffer_size == 0:
            return long_path

        # 获取短路径
        buffer = ctypes.create_unicode_buffer(buffer_size)
        result = GetShortPathNameW(long_path, buffer, buffer_size)
        if result > 0:
            return buffer.value
        return long_path
    except Exception:
        return long_path


def safe_path(path):
    """确保路径不包含非ASCII字符"""
    # 如果路径包含非ASCII字符，尝试转换为短路径
    try:
        path.encode('ascii')
        return path  # 已经是ASCII
    except UnicodeEncodeError:
        # 包含中文字符
        return get_short_path_name(path)


# 设置日志函数，用于调试
def log_message(message):
    """写入日志文件"""
    try:
        log_dir = os.path.join(tempfile.gettempdir(), 'asset_system_logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'map_debug.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"[{datetime.now()}] {message}\n")
    except:
        pass


def find_project_root():
    """找到项目根目录"""
    log_message(f"find_project_root called, frozen={getattr(sys, 'frozen', False)}")
    log_message(f"sys.executable = {sys.executable}")
    log_message(f"sys._MEIPASS = {getattr(sys, '_MEIPASS', 'NOT SET')}")

    if getattr(sys, 'frozen', False):
        # 打包环境：使用 exe 所在目录
        exe_dir = os.path.dirname(sys.executable)
        exe_dir_safe = safe_path(exe_dir)
        log_message(f"Original exe_dir: {exe_dir}")
        log_message(f"Short exe_dir: {exe_dir_safe}")

        if hasattr(sys, '_MEIPASS'):
            meipass = sys._MEIPASS
            meipass_safe = safe_path(meipass)
            log_message(f"Original _MEIPASS: {meipass}")
            log_message(f"Short _MEIPASS: {meipass_safe}")
            return meipass_safe
        else:
            log_message(f"Using exe dir fallback: {exe_dir_safe}")
            return exe_dir_safe

    # 正常模式
    current_file = os.path.abspath(__file__)
    current_file_safe = safe_path(current_file)
    gui_map_dir = os.path.dirname(current_file_safe)
    gui_dir = os.path.dirname(gui_map_dir)
    project_dir = os.path.dirname(gui_dir)
    log_message(f"Using dev mode path: {project_dir}")
    return project_dir


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        return 1

    param_file = sys.argv[1]
    # 确保参数文件路径安全
    param_file_safe = safe_path(param_file)
    log_message(f"Original param_file: {param_file}")
    log_message(f"Short param_file: {param_file_safe}")

    try:
        with open(param_file_safe, 'r', encoding='utf-8') as f:
            params = json.load(f)
    except Exception as e:
        log_message(f"读取参数文件失败: {e}")
        print(f"读取参数文件失败: {e}")
        return 1

    db_path = params.get('db_path', 'assets_pro.db')
    auth_data = params.get('auth_data', {})

    # 确保数据库路径安全
    db_path_safe = safe_path(db_path)
    if db_path != db_path_safe:
        log_message(f"Converted db_path: {db_path} -> {db_path_safe}")
        db_path = db_path_safe

    # 找到项目根目录
    project_dir = find_project_root()
    project_dir_safe = safe_path(project_dir)
    log_message(f"Project dir: {project_dir_safe}")

    # 添加到 sys.path
    if project_dir_safe not in sys.path:
        sys.path.insert(0, project_dir_safe)

    # 确保工作目录正确
    os.chdir(project_dir_safe)

    # 导入依赖
    log_message("=== Starting imports ===")
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        log_message("PyQt5 imported successfully")
    except ImportError as e:
        log_message(f"PyQt5 导入失败: {e}")
        import traceback
        log_message(traceback.format_exc())
        print(f"PyQt5 导入失败: {e}")
        return 1

    try:
        from config.database import Database
        log_message(f"Database module loaded, db_path={db_path}")
        from services.auth import AuthManager
        from gui.map.map_view import MapViewDialog
        log_message("All modules imported successfully")
    except ImportError as e:
        log_message(f"模块导入失败: {e}")
        import traceback
        log_message(traceback.format_exc())
        print(f"模块导入失败: {e}")
        return 1

    # 初始化数据库
    log_message("Initializing database...")
    db = Database(db_path)

    # 初始化认证
    auth = AuthManager(db)
    if auth_data.get('logged_in') and auth_data.get('user'):
        auth.current_user = auth_data.get('user')
        auth.user_permissions = auth_data.get('permissions', {})

    # 创建 Qt 应用
    log_message("Creating QApplication...")
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setQuitOnLastWindowClosed(True)
    log_message("QApplication created")

    # 创建并显示地图对话框
    log_message("Creating MapViewDialog...")
    dialog = MapViewDialog(db, auth)
    log_message("MapViewDialog created")

    # 设置窗口大小
    screen = app.primaryScreen()
    if screen:
        geometry = screen.availableGeometry()
        width = int(geometry.width() * 0.9)
        height = int(geometry.height() * 0.85)
        x = (geometry.width() - width) // 2
        y = (geometry.height() - height) // 2
        dialog.setGeometry(x, y, width, height)
        log_message(f"Dialog geometry set: {width}x{height} at ({x},{y})")

    dialog.setWindowTitle("资产地图展示")
    log_message("Showing dialog...")
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    dialog.setFocus()
    log_message("Dialog shown and raised")

    # 处理事件队列确保窗口显示
    app.processEvents()
    log_message("Events processed")

    # 运行应用
    log_message("Entering exec loop...")
    exit_code = app.exec_()
    log_message(f"App exited with code: {exit_code}")

    # 清理
    try:
        os.remove(param_file_safe)
    except:
        pass

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
