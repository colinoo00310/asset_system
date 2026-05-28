"""
地理编码服务模块
用于将地址转换为经纬度坐标
支持：高德地图、百度地图
"""

import requests
import json
import time
import sqlite3


class GeocodingService:
    """地理编码服务类"""

    AMAP_API_KEY = ""
    BAIDU_API_KEY = ""

    def __init__(self, db):
        self.db = db
        self.cache = {}

    def set_amap_key(self, api_key):
        """设置高德地图 API Key"""
        self.AMAP_API_KEY = api_key

    def set_baidu_key(self, api_key):
        """设置百度地图 API Key"""
        self.BAIDU_API_KEY = api_key

    def geocode_amap(self, address):
        """使用高德地图进行地理编码"""
        if not self.AMAP_API_KEY:
            return None, None

        if address in self.cache:
            return self.cache[address]

        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": self.AMAP_API_KEY,
            "address": address,
            "city": "杭州",
            "output": "JSON"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get("status") == "1" and data.get("geocodes"):
                location = data["geocodes"][0]["location"]
                lng, lat = location.split(",")
                result = (float(lng), float(lat))
                self.cache[address] = result
                return result
        except Exception as e:
            print(f"高德地图API调用失败: {e}")

        return None, None

    def geocode_baidu(self, address):
        """使用百度地图进行地理编码"""
        if not self.BAIDU_API_KEY:
            return None, None

        if address in self.cache:
            return self.cache[address]

        url = "https://api.map.baidu.com/geocoding/v3/"
        params = {
            "address": address,
            "ak": self.BAIDU_API_KEY,
            "output": "json"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get("status") == 0 and data.get("result"):
                location = data["result"]["location"]
                result = (location["lng"], location["lat"])
                self.cache[address] = result
                return result
        except Exception as e:
            print(f"百度地图API调用失败: {e}")

        return None, None

    def geocode(self, address, provider="amap"):
        """通用地理编码方法"""
        if not address:
            return None, None

        address = address.strip()

        if address in self.cache:
            return self.cache[address]

        if provider == "amap":
            result = self.geocode_amap(address)
        elif provider == "baidu":
            result = self.geocode_baidu(address)
        else:
            result = self.geocode_amap(address)
            if result[0] is None:
                result = self.geocode_baidu(address)

        if result[0] is not None:
            self.cache[address] = result

        return result

    def batch_geocode(self, addresses, provider="amap"):
        """批量地理编码"""
        results = {}

        for address in addresses:
            if address:
                result = self.geocode(address, provider)
                results[address] = result
                time.sleep(0.2)

        return results

    def save_coordinates_to_db(self, asset_id, lng, lat):
        """保存坐标到数据库"""
        if lng is None or lat is None:
            return False

        conn = self.db.get_connection()
        c = conn.cursor()

        try:
            c.execute("""
                UPDATE assets
                SET longitude = ?, latitude = ?
                WHERE id = ?
            """, (lng, lat, asset_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"保存坐标失败: {e}")
            return False
        finally:
            conn.close()

    def get_all_assets_with_coordinates(self):
        """获取所有已有坐标的资产"""
        conn = self.db.get_connection()
        c = conn.cursor()

        try:
            c.execute("""
                SELECT id, name, location, longitude, latitude
                FROM assets
                WHERE longitude IS NOT NULL AND latitude IS NOT NULL
            """)
            return c.fetchall()
        finally:
            conn.close()

    def get_assets_without_coordinates(self):
        """获取所有没有坐标的资产"""
        conn = self.db.get_connection()
        c = conn.cursor()

        try:
            c.execute("""
                SELECT id, name, location
                FROM assets
                WHERE (longitude IS NULL OR latitude IS NULL)
                AND location IS NOT NULL
                AND location != ''
            """)
            return c.fetchall()
        finally:
            conn.close()

    def auto_geocode_all(self, provider="amap"):
        """自动为所有没有坐标的资产进行地理编码"""
        assets = self.get_assets_without_coordinates()
        success_count = 0

        for asset_id, name, location in assets:
            print(f"正在处理: {name} - {location}")
            lng, lat = self.geocode(location, provider)

            if lng is not None and lat is not None:
                if self.save_coordinates_to_db(asset_id, lng, lat):
                    success_count += 1
                    print(f"  成功: ({lng}, {lat})")
                else:
                    print(f"  保存失败")
            else:
                print(f"  地理编码失败")

            time.sleep(0.3)

        return success_count
