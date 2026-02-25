"""
Weather Query Skill Executor
直接从权威天气API获取数据，支持中国城市
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from datetime import datetime


CITY_CODES = {
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280101",
    "深圳": "101280601",
    "杭州": "101210101",
    "南京": "101190101",
    "成都": "101270101",
    "重庆": "101040100",
    "武汉": "101200101",
    "西安": "101110101",
    "天津": "101030100",
    "苏州": "101190401",
    "郑州": "101180101",
    "长沙": "101250101",
    "东莞": "101281601",
    "沈阳": "101070101",
    "青岛": "101120201",
    "合肥": "101220101",
    "佛山": "101281701",
    "宁波": "101210401",
    "昆明": "101290101",
    "福州": "101230101",
    "厦门": "101230201",
    "哈尔滨": "101050101",
    "济南": "101120101",
    "大连": "101070201",
    "长春": "101060101",
    "太原": "101100101",
    "贵阳": "101260101",
    "南宁": "101300101",
    "南昌": "101240101",
    "石家庄": "101090101",
    "兰州": "101160101",
    "银川": "101170101",
    "西宁": "101150101",
    "海口": "101310101",
    "三亚": "101310201",
    "拉萨": "101140101",
    "呼和浩特": "101080101",
    "乌鲁木齐": "101130101",
}


async def fetch_weather_from_weathercn(city: str, days: int = 0) -> Optional[Dict]:
    """从中国天气网(weather.com.cn)获取天气数据 - 更权威的中国数据源
    
    Args:
        city: 城市名称
        days: 0=今天, 1=明天, 2=后天
    """
    city_code = CITY_CODES.get(city)
    if not city_code:
        return None
    
    try:
        # 使用中国天气网API
        url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://www.weather.com.cn/"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    html = await response.text()
                    import re
                    
                    # 查找7天天气预报数据 - 每个li包含一天
                    weather_pattern = r'<li[^>]*class="sky[^"]*"[^>]*>(.*?)</li>'
                    matches = re.findall(weather_pattern, html, re.DOTALL)
                    
                    if matches and len(matches) > days:
                        item = matches[days]
                        
                        # 提取日期
                        date_match = re.search(r'<h1>([^<]+)</h1>', item)
                        date_str = date_match.group(1).strip() if date_match else ""
                        
                        # 提取天气类型代码和描述
                        weather_match = re.search(r'class="([dn]\d+)"', item)
                        weather_type = weather_match.group(1) if weather_match else "d00"
                        
                        # 提取天气描述（如"小雨转阴"）
                        weather_desc_match = re.search(r'<p[^>]*class="wea"[^>]*>([^<]+)</p>', item)
                        weather_desc_from_html = weather_desc_match.group(1).strip() if weather_desc_match else ""
                        
                        # 提取温度 - 中国天气网格式: <span>最高温</span>/<i>最低温℃</i>
                        temp_section = re.search(r'<p class="tem">(.*?)</p>', item, re.DOTALL)
                        temp_max = "--"
                        temp_min = "--"
                        if temp_section:
                            temp_html = temp_section.group(1)
                            # 最高温在 <span> 中
                            high_match = re.search(r'<span>(-?\d+)</span>', temp_html)
                            # 最低温在 <i> 中
                            low_match = re.search(r'<i>(-?\d+)', temp_html)
                            temp_max = high_match.group(1) if high_match else "--"
                            temp_min = low_match.group(1) if low_match else "--"
                        
                        # 天气类型映射
                        # 优先使用HTML中的天气描述（如"小雨转阴"）
                        if weather_desc_from_html:
                            weather_desc = weather_desc_from_html
                        else:
                            weather_map = {
                                "d00": "晴", "n00": "晴",
                                "d01": "多云", "n01": "多云",
                                "d02": "阴", "n02": "阴",
                                "d03": "阵雨", "n03": "阵雨",
                                "d04": "雷阵雨", "n04": "雷阵雨",
                                "d07": "小雨", "n07": "小雨",
                                "d08": "中雨", "n08": "中雨",
                                "d09": "大雨", "n09": "大雨",
                                "d10": "暴雨", "n10": "暴雨",
                                "d13": "小雪", "n13": "小雪",
                                "d14": "中雪", "n14": "中雪",
                                "d15": "大雪", "n15": "大雪",
                            }
                            weather_desc = weather_map.get(weather_type, "未知")
                        
                        return {
                            "city": city,
                            "daily": {
                                "time": date_str,
                                "weather_code": weather_type,
                                "weather_desc": weather_desc,
                                "temp_max": temp_max,
                                "temp_min": temp_min,
                                "wind_speed": "--"
                            },
                            "days": days,
                            "source": "中国天气网"
                        }
    except Exception as e:
        print(f"Weather.com.cn API error: {e}")
    
    return None


async def fetch_weather_from_openmeteo(city: str, days: int = 0) -> Optional[Dict]:
    """从 Open-Meteo 获取天气数据（免费、无需API Key）
    
    Args:
        city: 城市名称
        days: 0=今天, 1=明天, 2=后天, etc.
    """
    import urllib.parse
    
    geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=zh"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(geocoding_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("results"):
                        location = data["results"][0]
                        lat = location["latitude"]
                        lon = location["longitude"]
                        city_name = location.get("name", city)
                        
                        if days == 0:
                            # 当前天气
                            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&timezone=Asia/Shanghai"
                            
                            async with session.get(weather_url, timeout=aiohttp.ClientTimeout(total=5)) as weather_response:
                                if weather_response.status == 200:
                                    weather_data = await weather_response.json()
                                    return {
                                        "city": city_name,
                                        "current": weather_data.get("current", {}),
                                        "timezone": weather_data.get("timezone", "Asia/Shanghai"),
                                        "days": 0
                                    }
                        else:
                            # 未来天气预报
                            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weather_code,temperature_2m_max,temperature_2m_min,wind_speed_10m_max&timezone=Asia/Shanghai&forecast_days={days+1}"
                            
                            async with session.get(weather_url, timeout=aiohttp.ClientTimeout(total=5)) as weather_response:
                                if weather_response.status == 200:
                                    weather_data = await weather_response.json()
                                    daily = weather_data.get("daily", {})
                                    if daily and len(daily.get("time", [])) > days:
                                        return {
                                            "city": city_name,
                                            "daily": {
                                                "time": daily["time"][days],
                                                "weather_code": daily["weather_code"][days],
                                                "temp_max": daily["temperature_2m_max"][days],
                                                "temp_min": daily["temperature_2m_min"][days],
                                                "wind_speed": daily["wind_speed_10m_max"][days]
                                            },
                                            "timezone": weather_data.get("timezone", "Asia/Shanghai"),
                                            "days": days
                                        }
    except Exception as e:
        print(f"Open-Meteo API error: {e}")
    
    return None


WEATHER_CODE_MAP = {
    0: "晴",
    1: "大部晴朗",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "霜雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}


def get_wind_direction(degrees: int) -> str:
    """将风向角度转换为中文方向"""
    directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    index = round(degrees / 45) % 8
    return directions[index]


def parse_openmeteo_weather(data: Dict) -> Dict[str, Any]:
    """解析天气数据（支持 Open-Meteo 和中国天气网）"""
    days = data.get("days", 0)
    source = data.get("source", "")
    
    if days == 0:
        # 当前天气
        current = data.get("current", {})
        weather_code = current.get("weather_code", 0)
        wind_dir = current.get("wind_direction_10m", 0)
        
        return {
            "city": data.get("city", "未知"),
            "temp": str(int(current.get("temperature_2m", 0))),
            "humidity": f"{current.get('relative_humidity_2m', '--')}%",
            "wind": f"{get_wind_direction(wind_dir)}风 {int(current.get('wind_speed_10m', 0))} km/h",
            "weather": WEATHER_CODE_MAP.get(weather_code, "未知"),
            "time": datetime.now().strftime("%H:%M"),
            "type": "current"
        }
    else:
        # 未来天气
        daily = data.get("daily", {})
        
        # 检查是否来自中国天气网（有 weather_desc 字段）
        if "weather_desc" in daily:
            # 中国天气网数据
            return {
                "city": data.get("city", "未知"),
                "day_name": "",
                "date": daily.get("time", ""),
                "temp_max": daily.get("temp_max", "--"),
                "temp_min": daily.get("temp_min", "--"),
                "wind": "--",
                "weather": daily.get("weather_desc", "未知"),
                "type": "forecast"
            }
        else:
            # Open-Meteo 数据
            weather_code = daily.get("weather_code", 0)
            
            day_names = ["今天", "明天", "后天"]
            day_name = day_names[days] if days < len(day_names) else f"{days}天后"
            
            return {
                "city": data.get("city", "未知"),
                "day_name": day_name,
                "date": daily.get("time", ""),
                "temp_max": str(int(daily.get("temp_max", 0))),
                "temp_min": str(int(daily.get("temp_min", 0))),
                "wind": f"{int(daily.get('wind_speed', 0))} km/h",
                "weather": WEATHER_CODE_MAP.get(weather_code, "未知"),
                "type": "forecast"
            }


async def query_weather(city: str, days: int = 0) -> Dict[str, Any]:
    """查询天气主函数
    
    Args:
        city: 城市名称
        days: 0=今天, 1=明天, 2=后天
    """
    city = city.replace("市", "").replace("省", "").strip()
    
    # 解析天数（如果用户说"明天"、"后天"）
    if "明天" in city or "明日" in city:
        days = 1
        city = city.replace("明天", "").replace("明日", "").strip()
    elif "后天" in city:
        days = 2
        city = city.replace("后天", "").strip()
    
    # 优先使用中国天气网（更权威的中国数据源）
    data = await fetch_weather_from_weathercn(city, days)
    if data:
        source = data.pop("source", "中国天气网")
        return {
            "success": True,
            "source": source,
            "data": parse_openmeteo_weather(data)
        }
    
    # 备用：使用 Open-Meteo
    data = await fetch_weather_from_openmeteo(city, days)
    if data:
        return {
            "success": True,
            "source": "Open-Meteo",
            "data": parse_openmeteo_weather(data)
        }
    
    return {
        "success": False,
        "error": f"无法获取 {city} 的天气信息，请确认城市名称是否正确"
    }


def format_weather_response(result: Dict[str, Any]) -> str:
    """格式化天气响应"""
    if not result.get("success"):
        return f"❌ {result.get('error', '查询失败')}"
    
    data = result["data"]
    source = result.get("source", "未知")
    
    if data.get("type") == "forecast":
        # 未来天气预报
        response = f"""🌤️ {data['city']}{data['day_name']}天气 ({data['date']})

🌡️ 温度: {data['temp_min']}°C ~ {data['temp_max']}°C
☁️ 天气: {data['weather']}
🌬️ 最大风力: {data['wind']}

📍 数据来源: {source}"""
    else:
        # 当前天气
        response = f"""🌤️ {data['city']}当前天气 ({data['time']})

🌡️ 温度: {data['temp']}°C
☁️ 天气: {data['weather']}
💧 湿度: {data['humidity']}
🌬️ 风力: {data['wind']}

📍 数据来源: {source}"""
    
    return response


async def execute(city: str = "北京", days: int = 0, **kwargs) -> Dict[str, Any]:
    """
    主入口函数
    
    Args:
        city: 城市名称（支持中文，可包含"明天"、"后天"）
        days: 0=今天, 1=明天, 2=后天
    
    Returns:
        天气查询结果
    """
    if not city:
        return {
            "success": False,
            "error": "请提供城市名称"
        }
    
    result = await query_weather(city, days)
    
    if result["success"]:
        result["message"] = format_weather_response(result)
    
    return result


if __name__ == "__main__":
    async def test():
        # 测试当前天气
        print("=== 当前天气 ===")
        for city in ["北京", "上海", "西安"]:
            result = await execute(city=city)
            print(f"\n{'='*40}")
            print(result.get("message", result.get("error")))
        
        # 测试明天天气
        print("\n\n=== 明天天气 ===")
        for city in ["西安明天", "北京明天"]:
            result = await execute(city=city)
            print(f"\n{'='*40}")
            print(result.get("message", result.get("error")))
    
    asyncio.run(test())
