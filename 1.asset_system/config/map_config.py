"""
地图 API 密钥配置
从 map_api_keys.json 读取/保存高德密钥，未配置时返回空字符串
"""
import os
import json

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "..", "map_api_keys.json")


def _load():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_baidu_ak():
    return _load().get("baidu_ak", "").strip()


def get_amap_key():
    return _load().get("amap_key", "").strip()


def set_keys(baidu_ak="", amap_key=""):
    data = _load()
    if baidu_ak is not None:
        data["baidu_ak"] = (baidu_ak or "").strip()
    if amap_key is not None:
        data["amap_key"] = (amap_key or "").strip()
    _save(data)
