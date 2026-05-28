"""
独立的地图启动器
使用独立进程来避免 Qt 和 Tkinter 的冲突
"""

import subprocess
import sys
import os
import json
import tempfile


def launch_map_view_as_process(db_path, auth_data):
    """
    使用独立进程启动地图窗口
    :param db_path: 数据库文件路径
    :param auth_data: 认证信息（JSON格式）
    """
    temp_dir = tempfile.gettempdir()
    param_file = os.path.join(temp_dir, "map_launch_params.json")

    params = {
        'db_path': db_path,
        'auth_data': auth_data
    }

    with open(param_file, 'w', encoding='utf-8') as f:
        json.dump(params, f)

    # 打包环境下，使用 exe 所在目录
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        project_dir = exe_dir
    else:
        # 开发环境
        current_file = os.path.abspath(__file__)
        gui_dir = os.path.dirname(current_file)  # gui/map
        gui_parent = os.path.dirname(gui_dir)     # gui
        project_dir = os.path.dirname(gui_parent) # 项目根目录

    map_script = os.path.join(project_dir, "gui", "map", "map_standalone.py")

    # 使用当前 Python 解释器
    python_exe = sys.executable

    # 使用 CREATE_NO_WINDOW 避免弹出黑色控制台窗口
    try:
        creation_flags = 0x08000000  # CREATE_NO_WINDOW
        process = subprocess.Popen(
            [python_exe, map_script, param_file],
            creationflags=creation_flags,
            cwd=project_dir  # 设置工作目录
        )
        print(f"[DEBUG] 地图进程已启动, PID: {process.pid}")
    except Exception as e:
        print(f"启动地图进程失败: {e}")
        import traceback
        traceback.print_exc()
