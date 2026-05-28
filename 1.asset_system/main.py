"""
主程序入口
使用 Tkinter + PyQt5 混合架构
Tkinter 负责主界面，PyQt5 负责地图展示
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os
import tempfile

# 添加项目根目录到路径
def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        else:
            return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

project_root = get_project_root()
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def log_to_file(message):
    """写入日志文件"""
    try:
        log_dir = os.path.join(tempfile.gettempdir(), 'asset_system_logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'main_debug.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"[{datetime.now()}] {message}\n")
    except:
        pass


from gui.login import LoginWindow


def main():
    """程序入口"""
    log_to_file(f"=== Program Start ===")
    log_to_file(f"sys.frozen = {getattr(sys, 'frozen', False)}")
    log_to_file(f"sys.executable = {sys.executable}")
    log_to_file(f"sys._MEIPASS = {getattr(sys, '_MEIPASS', 'NOT SET')}")
    log_to_file(f"sys.argv = {sys.argv}")
    log_to_file(f"project_root = {project_root}")

    # 检查是否是地图模式（从独立进程启动）
    if len(sys.argv) > 2 and sys.argv[1] == '--map-mode':
        # 地图独立模式
        # sys.argv = ['exe_path', '--map-mode', 'param_file_path']
        param_file = sys.argv[2]

        log_to_file(f"=== Map Mode ===")
        log_to_file(f"param_file = {param_file}")

        # 在打包环境中，需要添加 _internal 到路径
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, '_internal')

        log_to_file(f"exe_dir = {exe_dir}")
        log_to_file(f"internal_dir = {internal_dir}")
        log_to_file(f"internal exists = {os.path.exists(internal_dir)}")

        # 确保 _internal 目录在 sys.path 中
        if os.path.exists(internal_dir) and internal_dir not in sys.path:
            sys.path.insert(0, internal_dir)
            log_to_file(f"Added internal_dir to sys.path")

        # 尝试导入模块
        try:
            from gui.map.map_standalone import main as map_main
            log_to_file(f"Imported map_standalone.main successfully")
            # 重新组织 sys.argv，让 map_standalone 以为只有参数文件
            sys.argv = [sys.argv[0], param_file]
            log_to_file(f"Calling map_main()")
            sys.exit(map_main())
        except Exception as e:
            log_to_file(f"[ERROR] 导入 map_standalone 失败: {e}")
            import traceback
            traceback.print_exc()
            log_to_file(traceback.format_exc())
            # 写入日志文件
            log_dir = os.path.join(os.environ.get('TEMP', ''), 'asset_system_logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'map_launch_error.log')
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"exe_dir: {exe_dir}\n")
                f.write(f"internal_dir: {internal_dir}\n")
                f.write(f"internal exists: {os.path.exists(internal_dir)}\n")
                f.write(f"sys.argv: {sys.argv}\n")
                f.write(f"\n{traceback.format_exc()}\n")
            sys.exit(1)

    try:
        log_to_file("Starting Tkinter mainloop")
        root = tk.Tk()
        app = LoginWindow(root)
        root.mainloop()
    except KeyboardInterrupt:
        print("程序正常退出")
    except Exception as e:
        log_to_file(f"[ERROR] 程序异常: {e}")
        import traceback
        log_to_file(traceback.format_exc())
        with open("error.log", "a", encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"{datetime.now()} - 程序异常: {str(e)}\n")


if __name__ == "__main__":
    main()
