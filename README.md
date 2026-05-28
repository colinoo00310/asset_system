# asset_system
基于Python Thinker+SQLite完成的资产管理系统，主要功能包括：资产管理、部门管理、用户管理、资产地图展示功能

项目整体结构：
asset_system2/
├── main.py                         # 主程序入口
│
├── config/                         # 配置模块
│   ├── __init__.py
│   ├── database.py                 # 数据库操作
│   └── map_config.py               # 地图API配置
│
├── models/                        # 数据模型
│   └── __init__.py
│
├── services/                       # 业务服务
│   ├── __init__.py
│   ├── auth.py                    # 认证和权限管理
│   └── geocoding.py               # 地理编码服务
│
├── utils/                          # 工具函数
│   ├── __init__.py
│   └── utils.py
│
├── gui/                            # GUI界面模块
│   ├── __init__.py
│   ├── login.py                   # 登录界面
│   ├── main_window.py             # 主窗口
│   ├── home.py                    # 系统首页
│   ├── assets.py                  # 资产管理
│   ├── departments.py             # 部门管理
│   ├── users.py                  # 用户管理
│   └── map/                       # 地图子模块
│       ├── __init__.py
│       ├── map_view.py            # 地图展示
│       ├── map_launcher.py        # 地图启动器
│       ├── map_standalone.py       # 地图独立进程
│       └── location_picker.py      # 位置选择器

桌面端exe打包终端命令：pyinstaller main.spec
注意：assets pro.db为数据库文件，不可随意删除，否则会导致数据丢失！！
dist文件夹要放在英文路径下，否则“地图展示”功能易失效！！

默认管理员账号:admin 密码：admin123
