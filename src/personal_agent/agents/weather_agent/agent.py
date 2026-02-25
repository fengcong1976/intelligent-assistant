import re
import jwt
import time
import json
import gzip
import ssl
import asyncio
import urllib.request
import urllib.parse
import aiohttp
from abc import ABC, abstractmethod
from pathlib import Path
from loguru import logger
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..base import BaseAgent, Task

class WeatherDataSource(ABC):
    """天气数据源抽象类"""
    
    @abstractmethod
    async def get_current_weather(self, location: str) -> Optional[Dict]:
        """获取当前天气"""
        pass
    
    @abstractmethod
    async def get_forecast(self, location: str, days: int) -> Optional[Dict]:
        """获取天气预报"""
        pass

class QWeatherDataSource(WeatherDataSource):
    """和风天气数据源"""
    
    def __init__(self):
        self.domain = "https://mf436hnhdx.re.qweatherapi.com"
        self.key_id = "K7B825QRAU"
        self.project_id = "4F87M6VC92"
        self.private_key_file = Path(__file__).parent.parent.parent.parent.parent / "ed25519-private.pem"
        self._token = None
        self._token_expire = 0
    
    def _load_private_key(self) -> str:
        """加载和风天气私钥"""
        try:
            with open(self.private_key_file, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"加载私钥失败: {e}")
            return ""
    
    def _generate_token(self) -> str:
        """生成和风天气JWT Token"""
        if self._token and time.time() < self._token_expire - 60:
            return self._token
        
        private_key = self._load_private_key()
        if not private_key:
            return ""
        
        payload = {
            'sub': self.project_id,
            'iat': int(time.time()) - 30,
            'exp': int(time.time()) + 900
        }
        headers = {'kid': self.key_id}
        
        try:
            self._token = jwt.encode(payload, private_key, algorithm='EdDSA', headers=headers)
            self._token_expire = int(time.time()) + 900
            return self._token
        except Exception as e:
            logger.error(f"生成JWT Token失败: {e}")
            return ""
    
    async def _fetch_data(self, location: str, api_type: str = "now", retry_count: int = 2) -> Optional[Dict]:
        """从和风天气获取数据，支持重试机制"""
        token = self._generate_token()
        if not token:
            logger.error("和风天气API: 无法生成访问令牌")
            return None
        
        for attempt in range(retry_count + 1):
            try:
                if api_type == "geo":
                    url = f"{self.domain}/geo/v2/city/lookup?location={urllib.parse.quote(location)}"
                elif api_type == "now":
                    url = f"{self.domain}/v7/weather/now?location={urllib.parse.quote(location)}"
                elif api_type == "3d":
                    url = f"{self.domain}/v7/weather/3d?location={urllib.parse.quote(location)}"
                elif api_type == "7d":
                    url = f"{self.domain}/v7/weather/7d?location={urllib.parse.quote(location)}"
                else:
                    logger.warning(f"和风天气API: 不支持的API类型: {api_type}")
                    return None
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip',
                    'Authorization': f'Bearer {token}'
                }
                
                logger.debug(f"和风天气API请求: {api_type} for {location} (尝试 {attempt+1}/{retry_count+1})")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as response:
                        if response.status == 200:
                            data_bytes = await response.read()
                            try:
                                data_bytes = gzip.decompress(data_bytes)
                            except Exception as decompress_error:
                                logger.debug(f"和风天气API: 解压缩失败，使用原始数据: {decompress_error}")
                            
                            try:
                                data = json.loads(data_bytes.decode('utf-8'))
                                if data.get('code') == '200':
                                    logger.debug(f"和风天气API: 请求成功 ({api_type})")
                                    return data
                                else:
                                    error_code = data.get('code')
                                    logger.warning(f"和风天气API返回错误: {error_code} for {location}")
                                    if attempt < retry_count:
                                        logger.info(f"和风天气API: 将在 2 秒后重试...")
                                        await asyncio.sleep(2)
                                        continue
                                    return None
                            except json.JSONDecodeError as json_error:
                                logger.error(f"和风天气API: JSON解析失败: {json_error}")
                                if attempt < retry_count:
                                    logger.info(f"和风天气API: 将在 2 秒后重试...")
                                    await asyncio.sleep(2)
                                    continue
                                return None
                        else:
                            logger.warning(f"和风天气API: HTTP错误 {response.status} for {location}")
                            if attempt < retry_count:
                                logger.info(f"和风天气API: 将在 2 秒后重试...")
                                await asyncio.sleep(2)
                                continue
                            return None
            except asyncio.TimeoutError:
                logger.error(f"和风天气API: 请求超时 ({api_type} for {location})")
                if attempt < retry_count:
                    logger.info(f"和风天气API: 将在 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
            except Exception as e:
                logger.error(f"和风天气API请求失败: {e}")
                logger.exception("和风天气API: 详细错误信息:")
                if attempt < retry_count:
                    logger.info(f"和风天气API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
        
        logger.error(f"和风天气API: 所有尝试都失败了 ({api_type} for {location})")
        return None
    
    async def _get_city_location(self, city: str) -> Optional[str]:
        """获取城市Location ID，支持详细地址"""
        if city in CITY_CODES:
            return CITY_CODES[city]
        
        geo_data = await self._fetch_data(city, "geo")
        if geo_data and geo_data.get('location'):
            location = geo_data['location'][0]
            location_id = location.get('id')
            location_name = location.get('name', city)
            logger.info(f"和风天气地理编码: {city} -> {location_name} (ID: {location_id})")
            return location_id
        
        return None
    
    async def _get_city_location_with_name(self, city: str) -> tuple:
        """获取城市Location ID和名称，支持详细地址"""
        if city in CITY_CODES:
            return CITY_CODES[city], city
        
        geo_data = await self._fetch_data(city, "geo")
        if geo_data and geo_data.get('location'):
            location = geo_data['location'][0]
            location_id = location.get('id')
            location_name = location.get('name', city)
            adm1 = location.get('adm1', '')
            adm2 = location.get('adm2', '')
            full_name = f"{adm2}{location_name}" if adm2 and adm2 != location_name else location_name
            logger.info(f"和风天气地理编码: {city} -> {full_name} (ID: {location_id})")
            return location_id, full_name
        
        return None, city
    
    async def get_current_weather(self, location: str) -> Optional[Dict]:
        """获取当前天气"""
        location_id, location_name = await self._get_city_location_with_name(location)
        if not location_id:
            return None
        
        data = await self._fetch_data(location_id, "now")
        if data and data.get('now'):
            now = data['now']
            return {
                "city": location_name,
                "temp": int(now.get('temp', 0)),
                "feels_like": int(now.get('feelsLike', 0)),
                "weather": now.get('text', '未知'),
                "humidity": now.get('humidity', '--'),
                "wind_dir": now.get('windDir', '--'),
                "wind_speed": now.get('windSpeed', '--'),
                "pressure": now.get('pressure', '--'),
                "visibility": now.get('vis', '--'),
                "time": datetime.now().strftime("%H:%M"),
                "source": "和风天气"
            }
        return None
    
    async def get_forecast(self, location: str, days: int = 3) -> Optional[Dict]:
        """获取天气预报
        
        Args:
            location: 城市名称
            days: 预报天数（1=明天，2=后天，3=未来3天）
        """
        location_id, location_name = await self._get_city_location_with_name(location)
        if not location_id:
            return None
        
        api_type = "3d" if days <= 3 else "7d"
        data = await self._fetch_data(location_id, api_type)
        if data and data.get('daily'):
            daily = data['daily']
            forecast = []
            day_names = ["今天", "明天", "后天"]
            for i in range(days + 1):
                if i < len(daily):
                    day_data = daily[i]
                    forecast.append({
                        "date": day_data.get('fxDate', ''),
                        "day_name": day_names[i] if i < len(day_names) else f"{i}天后",
                        "weather": day_data.get('textDay', '未知'),
                        "temp_max": int(day_data.get('tempMax', 0)),
                        "temp_min": int(day_data.get('tempMin', 0)),
                        "wind_dir": day_data.get('windDirDay', '--'),
                        "wind_speed": day_data.get('windSpeedDay', '--')
                    })
            if days == 1:
                forecast = [forecast[1]] if len(forecast) > 1 else forecast
            elif days == 2:
                forecast = [forecast[1], forecast[2]] if len(forecast) > 2 else forecast[1:]
            return {
                "city": location,
                "forecast": forecast,
                "source": "和风天气"
            }
        return None

class WeatherCNDataSource(WeatherDataSource):
    """中国天气网数据源"""
    
    def __init__(self):
        self.domain = "http://www.weather.com.cn"
    
    async def _fetch_weathercn(self, city: str, days: int = 0, retry_count: int = 2) -> Optional[Dict]:
        """从中国天气网获取数据，支持重试机制"""
        city_code = CITY_CODES.get(city)
        if not city_code:
            logger.warning(f"中国天气网: 城市代码未找到 for {city}")
            return None
        
        for attempt in range(retry_count + 1):
            try:
                url = f"{self.domain}/weather/{city_code}.shtml"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://www.weather.com.cn/"
                }
                
                logger.debug(f"中国天气网API请求: {city} (code: {city_code}) (尝试 {attempt+1}/{retry_count+1})")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            try:
                                html = await response.text()
                                
                                weather_pattern = r'<li[^>]*class="sky[^"]*"[^>]*>(.*?)</li>'
                                matches = re.findall(weather_pattern, html, re.DOTALL)
                                
                                if matches and len(matches) > days:
                                    item = matches[days]
                                    
                                    date_match = re.search(r'<h1>([^<]+)</h1>', item)
                                    date_str = date_match.group(1).strip() if date_match else ""
                                    
                                    weather_desc_match = re.search(r'<p[^>]*class="wea"[^>]*>([^<]+)</p>', item)
                                    weather_desc = weather_desc_match.group(1).strip() if weather_desc_match else ""
                                    
                                    temp_section = re.search(r'<p class="tem">(.*?)</p>', item, re.DOTALL)
                                    temp_max = "--"
                                    temp_min = "--"
                                    if temp_section:
                                        temp_html = temp_section.group(1)
                                        high_match = re.search(r'<span>(-?\d+)</span>', temp_html)
                                        low_match = re.search(r'<i>(-?\d+)', temp_html)
                                        temp_max = high_match.group(1) if high_match else "--"
                                        temp_min = low_match.group(1) if low_match else "--"
                                    
                                    logger.debug(f"中国天气网API: 请求成功 for {city}")
                                    return {
                                        "city": city,
                                        "date": date_str,
                                        "weather": weather_desc or "未知",
                                        "temp_max": temp_max,
                                        "temp_min": temp_min,
                                        "source": "中国天气网"
                                    }
                                else:
                                    logger.warning(f"中国天气网API: 无匹配的天气数据 for {city}")
                                    if attempt < retry_count:
                                        logger.info(f"中国天气网API: 将在 2 秒后重试...")
                                        await asyncio.sleep(2)
                                        continue
                            except Exception as parse_error:
                                logger.error(f"中国天气网API: 解析错误: {parse_error}")
                                if attempt < retry_count:
                                    logger.info(f"中国天气网API: 将在 2 秒后重试...")
                                    await asyncio.sleep(2)
                                    continue
                        else:
                            logger.warning(f"中国天气网API: HTTP错误 {response.status} for {city}")
                            if attempt < retry_count:
                                logger.info(f"中国天气网API: 将在 2 秒后重试...")
                                await asyncio.sleep(2)
                                continue
            except asyncio.TimeoutError:
                logger.error(f"中国天气网API: 请求超时 for {city}")
                if attempt < retry_count:
                    logger.info(f"中国天气网API: 将在 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
            except Exception as e:
                logger.error(f"中国天气网API请求失败: {e}")
                logger.exception("中国天气网API: 详细错误信息:")
                if attempt < retry_count:
                    logger.info(f"中国天气网API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
        
        logger.error(f"中国天气网API: 所有尝试都失败了 for {city}")
        return None
    
    async def get_current_weather(self, location: str) -> Optional[Dict]:
        """获取当前天气"""
        return await self._fetch_weathercn(location, 0)
    
    async def get_forecast(self, location: str, days: int = 3) -> Optional[Dict]:
        """获取天气预报"""
        forecasts = []
        for day in range(days):
            forecast = await self._fetch_weathercn(location, day)
            if forecast:
                forecasts.append({
                    "date": forecast.get("date", ""),
                    "weather": forecast.get("weather", "未知"),
                    "temp_max": forecast.get("temp_max", "--"),
                    "temp_min": forecast.get("temp_min", "--")
                })
        
        if forecasts:
            return {
                "city": location,
                "forecast": forecasts,
                "source": "中国天气网"
            }
        return None

class OpenMeteoDataSource(WeatherDataSource):
    """Open-Meteo数据源"""
    
    def __init__(self):
        self.geocoding_domain = "https://geocoding-api.open-meteo.com"
        self.weather_domain = "https://api.open-meteo.com"
    
    async def _fetch_openmeteo(self, city: str, days: int = 0, retry_count: int = 2) -> Optional[Dict]:
        """从 Open-Meteo 获取天气数据，支持重试机制"""
        for attempt in range(retry_count + 1):
            try:
                geocoding_url = f"{self.geocoding_domain}/v1/search?name={urllib.parse.quote(city)}&count=1&language=zh"
                
                logger.debug(f"Open-Meteo API请求: 地理编码 for {city} (尝试 {attempt+1}/{retry_count+1})")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(geocoding_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                if data.get("results"):
                                    location = data["results"][0]
                                    lat = location["latitude"]
                                    lon = location["longitude"]
                                    city_name = location.get("name", city)
                                    
                                    if days == 0:
                                        weather_url = f"{self.weather_domain}/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&timezone=Asia/Shanghai"
                                        
                                        logger.debug(f"Open-Meteo API请求: 天气数据 for {city_name} (lat: {lat}, lon: {lon})")
                                        
                                        async with session.get(weather_url, timeout=aiohttp.ClientTimeout(total=5)) as weather_response:
                                            if weather_response.status == 200:
                                                try:
                                                    weather_data = await weather_response.json()
                                                    current = weather_data.get("current", {})
                                                    weather_code = current.get("weather_code", 0)
                                                    wind_dir = current.get("wind_direction_10m", 0)
                                                    
                                                    directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
                                                    wind_dir_name = directions[round(wind_dir / 45) % 8]
                                                    
                                                    logger.debug(f"Open-Meteo API: 请求成功 for {city_name}")
                                                    return {
                                                        "city": city_name,
                                                        "temp": int(current.get("temperature_2m", 0)),
                                                        "humidity": current.get("relative_humidity_2m", "--"),
                                                        "wind": f"{wind_dir_name}风 {int(current.get('wind_speed_10m', 0))} km/h",
                                                        "weather": WEATHER_CODE_MAP.get(weather_code, "未知"),
                                                        "time": datetime.now().strftime("%H:%M"),
                                                        "source": "Open-Meteo"
                                                    }
                                                except json.JSONDecodeError as json_error:
                                                    logger.error(f"Open-Meteo API: 天气数据JSON解析失败: {json_error}")
                                                    if attempt < retry_count:
                                                        logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                                        await asyncio.sleep(2)
                                                        continue
                                            else:
                                                logger.warning(f"Open-Meteo API: 天气数据HTTP错误 {weather_response.status}")
                                                if attempt < retry_count:
                                                    logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                                    await asyncio.sleep(2)
                                                    continue
                                else:
                                    logger.warning(f"Open-Meteo API: 无匹配位置 for {city}")
                                    if attempt < retry_count:
                                        logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                        await asyncio.sleep(2)
                                        continue
                            except json.JSONDecodeError as json_error:
                                logger.error(f"Open-Meteo API: 地理编码JSON解析失败: {json_error}")
                                if attempt < retry_count:
                                    logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                    await asyncio.sleep(2)
                                    continue
                        else:
                            logger.warning(f"Open-Meteo API: 地理编码HTTP错误 {response.status}")
                            if attempt < retry_count:
                                logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                await asyncio.sleep(2)
                                continue
            except asyncio.TimeoutError:
                logger.error(f"Open-Meteo API: 请求超时 for {city}")
                if attempt < retry_count:
                    logger.info(f"Open-Meteo API: 将在 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
            except Exception as e:
                logger.error(f"Open-Meteo API请求失败: {e}")
                logger.exception("Open-Meteo API: 详细错误信息:")
                if attempt < retry_count:
                    logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
        
        logger.error(f"Open-Meteo API: 所有尝试都失败了 for {city}")
        return None
    
    async def get_current_weather(self, location: str) -> Optional[Dict]:
        """获取当前天气"""
        return await self._fetch_openmeteo(location, 0)
    
    async def get_forecast(self, location: str, days: int = 3) -> Optional[Dict]:
        """获取天气预报"""
        # Open-Meteo 的天气预报需要不同的 API 调用，这里简化处理
        current = await self._fetch_openmeteo(location, 0)
        if current:
            return {
                "city": current.get("city", location),
                "forecast": [{
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "weather": current.get("weather", "未知"),
                    "temp_max": current.get("temp", "--"),
                    "temp_min": current.get("temp", "--")
                }],
                "source": "Open-Meteo"
            }
        return None


QWEATHER_KEY_ID = "K7B825QRAU"
QWEATHER_PROJECT_ID = "4F87M6VC92"
QWEATHER_PRIVATE_KEY_FILE = Path(__file__).parent.parent.parent.parent.parent / "ed25519-private.pem"
QWEATHER_DOMAIN = "https://mf436hnhdx.re.qweatherapi.com"

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

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


class WeatherAgent(BaseAgent):
    """
    天气查询智能体

    能力：
    - 实时天气查询
    - 天气预报（支持未来几天）
    - 基于位置的天气查询
    - 街道级精确定位
    - 多数据源支持（和风天气、中国天气网、Open-Meteo）
    - 自动容错和数据源切换
    - 上下文记忆（记住最近查询的城市）
    """
    
    PRIORITY: int = 5
    _last_city: str = ""

    KEYWORD_MAPPINGS: Dict[str, tuple] = {
        "天气": ("query", {}),
        "今天天气": ("query", {}),
        "今天天气怎么样": ("query", {}),
        "天气怎么样": ("query", {}),
        "明天天气": ("query", {"days": 1}),
        "后天天气": ("query", {"days": 2}),
        "天气预报": ("forecast", {}),
        "天气对比": ("compare", {}),
        "对比天气": ("compare", {}),
        "穿什么": ("clothing", {}),
        "穿什么合适": ("clothing", {}),
        "穿衣建议": ("clothing", {}),
        "出门要带伞吗": ("umbrella", {}),
        "要带伞吗": ("umbrella", {}),
        "会下雨吗": ("umbrella", {}),
    }

    def __init__(self):
        super().__init__(name="weather_agent", description="天气查询智能体 - 支持街道级精确定位，数据来源和风天气")
        self.data_sources = {
            "qweather": QWeatherDataSource(),
            "weathercn": WeatherCNDataSource(),
            "openmeteo": OpenMeteoDataSource()
        }
        self._load_keyword_config()
        
        self.register_capability(
            capability="get_weather",
            description="查询天气信息。支持街道级精确定位。返回当前天气和未来几天的天气预报。当用户询问天气相关问题时必须调用此工具。",
            aliases=[
                "查询天气", "查看天气", "天气查询", "天气信息",
                "今天天气", "今日天气", "当前天气", "现在天气",
                "明天天气", "明日天气", "后天天气", "大后天天气",
                "天气预报", "天气情况", "天气状况",
                "气温", "温度", "下雨吗", "会下雨吗", "晴天吗", "阴天吗",
                "北京天气", "上海天气", "广州天气", "深圳天气", "西安天气"
            ],
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如'北京'、'西安'。如果用户未指定城市，可留空，系统会使用上下文或默认城市"
                    },
                    "address": {
                        "type": "string",
                        "description": "详细地址（可选），如'新城区韩森寨街道'，用于街道级精度天气查询"
                    },
                    "days": {
                        "type": "integer",
                        "description": "预报天数，0表示今天，1表示明天，2表示后天，默认0",
                        "default": 0
                    }
                },
                "required": []
            },
            category="weather"
        )
    
    def _load_keyword_config(self):
        """从配置文件加载关键词配置"""
        config_file = Path(__file__).parent / "weather_agent" / "agent.json"
        self._keyword_patterns = {
            "time_words": ["今天", "明天", "明日", "后天", "大后天", "当前", "现在", "今日"],
            "days_mapping": {"明天": 1, "明日": 1, "后天": 2, "大后天": 3},
            "city_patterns": [
                r'([\u4e00-\u9fa5]{2,})(?:市|省)?(?:当前|现在|今天|今日|明日|明天|后天|大后天)?(?:的)?天气',
                r'(?:当前|现在|今天|今日|明日|明天|后天|大后天)([\u4e00-\u9fa5]{2,})(?:市|省)?(?:的)?天气',
                r'([\u4e00-\u9fa5]{2,})(?:市|省)?天气',
            ],
            "weather_keywords": ["天气", "气温", "温度", "下雨", "晴天", "阴天", "多云"]
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "keyword_patterns" in data:
                    self._keyword_patterns = data["keyword_patterns"]
                    logger.info(f"✅ 天气智能体关键词配置已加载")
            except Exception as e:
                logger.warning(f"加载关键词配置失败，使用默认配置: {e}")
    
    def reload_config(self):
        """热重载配置"""
        self._load_keyword_config()
        logger.info("✅ 天气智能体配置已热重载")
    
    def get_capabilities_description(self) -> str:
        """获取能力描述，用于LLM意图识别"""
        return """### weather_agent (天气查询智能体)
- 实时天气查询: 获取当前天气状况，action=get_current_weather, location=城市名称
- 天气预报: 获取未来几天的天气预报，action=get_forecast, location=城市名称, days=天数
- 基于位置的天气查询: 根据经纬度获取天气，action=get_weather_by_coords, lat=纬度, lon=经度
- 天气对比: 对比多个城市的天气，action=compare_weather, cities=城市列表
- 穿衣建议: 根据天气提供穿衣建议，action=get_clothing_advice, location=城市名称
- 雨伞建议: 根据天气提供是否需要带伞的建议，action=get_umbrella_advice, location=城市名称
- 示例: "北京今天天气怎么样" -> action=get_current_weather, location="北京"
- 示例: "上海明天天气" -> action=get_forecast, location="上海", days=1
- 示例: "广州后天天气" -> action=get_forecast, location="广州", days=2
"""
    
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """🌤️ 天气查询智能体

功能：
- 实时天气查询：获取当前天气状况
- 天气预报：获取未来几天的天气预报
- 基于位置的天气查询：根据经纬度获取天气
- 街道级精确定位：支持更精确的位置查询
- 多数据源支持：自动切换数据源，提高可靠性
- 天气对比：对比多个城市的天气
- 穿衣建议：根据天气提供穿衣建议
- 雨伞建议：根据天气提供是否需要带伞的建议

使用方法：
- "北京今天天气怎么样"
- "上海明天天气"
- "广州后天天气"
- "北京市朝阳区天气"
- "对比北京和上海的天气"
- "北京今天穿什么合适"
- "北京今天需要带伞吗"

参数说明：
- location: 城市名称或详细地址
- days: 预报天数（默认0，表示实时天气）
- lat: 纬度（可选，用于精确位置）
- lon: 经度（可选，用于精确位置）
- cities: 城市列表（用于天气对比）

数据源：
- 和风天气：提供街道级精确定位
- 中国天气网：提供全国天气数据
- Open-Meteo：作为备选数据源

注意：
- 支持街道级精确定位，可提供更准确的天气信息
- 当一个数据源不可用时，会自动切换到其他数据源
- 支持自然语言查询，如"明天北京天气"、"后天上海天气"等
"""

    def _load_private_key(self) -> str:
        """加载和风天气私钥"""
        try:
            with open(QWEATHER_PRIVATE_KEY_FILE, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"加载私钥失败: {e}")
            return ""

    def _generate_qweather_token(self) -> str:
        """生成和风天气JWT Token"""
        if self._qweather_token and time.time() < self._token_expire - 60:
            return self._qweather_token
        
        private_key = self._load_private_key()
        if not private_key:
            return ""
        
        payload = {
            'sub': QWEATHER_PROJECT_ID,
            'iat': int(time.time()) - 30,
            'exp': int(time.time()) + 900
        }
        headers = {'kid': QWEATHER_KEY_ID}
        
        try:
            self._qweather_token = jwt.encode(payload, private_key, algorithm='EdDSA', headers=headers)
            self._token_expire = int(time.time()) + 900
            return self._qweather_token
        except Exception as e:
            logger.error(f"生成JWT Token失败: {e}")
            return ""

    async def _fetch_qweather(self, location: str, api_type: str = "now", retry_count: int = 2) -> Optional[Dict]:
        """从和风天气获取数据，支持重试机制"""
        token = self._generate_qweather_token()
        if not token:
            logger.error("和风天气API: 无法生成访问令牌")
            return None
        
        for attempt in range(retry_count + 1):
            try:
                if api_type == "geo":
                    url = f"{QWEATHER_DOMAIN}/geo/v2/city/lookup?location={urllib.parse.quote(location)}"
                elif api_type == "now":
                    url = f"{QWEATHER_DOMAIN}/v7/weather/now?location={urllib.parse.quote(location)}"
                elif api_type == "3d":
                    url = f"{QWEATHER_DOMAIN}/v7/weather/3d?location={urllib.parse.quote(location)}"
                elif api_type == "7d":
                    url = f"{QWEATHER_DOMAIN}/v7/weather/7d?location={urllib.parse.quote(location)}"
                else:
                    logger.warning(f"和风天气API: 不支持的API类型: {api_type}")
                    return None
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip',
                    'Authorization': f'Bearer {token}'
                }
                
                logger.debug(f"和风天气API请求: {api_type} for {location} (尝试 {attempt+1}/{retry_count+1})")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as response:
                        if response.status == 200:
                            data_bytes = await response.read()
                            try:
                                data_bytes = gzip.decompress(data_bytes)
                            except Exception as decompress_error:
                                logger.debug(f"和风天气API: 解压缩失败，使用原始数据: {decompress_error}")
                            
                            try:
                                data = json.loads(data_bytes.decode('utf-8'))
                                if data.get('code') == '200':
                                    logger.debug(f"和风天气API: 请求成功 ({api_type})")
                                    return data
                                else:
                                    error_code = data.get('code')
                                    logger.warning(f"和风天气API返回错误: {error_code} for {location}")
                                    if attempt < retry_count:
                                        logger.info(f"和风天气API: 将在 2 秒后重试...")
                                        await asyncio.sleep(2)
                                        continue
                                    return None
                            except json.JSONDecodeError as json_error:
                                logger.error(f"和风天气API: JSON解析失败: {json_error}")
                                if attempt < retry_count:
                                    logger.info(f"和风天气API: 将在 2 秒后重试...")
                                    await asyncio.sleep(2)
                                    continue
                                return None
                        else:
                            logger.warning(f"和风天气API: HTTP错误 {response.status} for {location}")
                            if attempt < retry_count:
                                logger.info(f"和风天气API: 将在 2 秒后重试...")
                                await asyncio.sleep(2)
                                continue
                            return None
            except asyncio.TimeoutError:
                logger.error(f"和风天气API: 请求超时 ({api_type} for {location})")
                if attempt < retry_count:
                    logger.info(f"和风天气API: 将在 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
            except aiohttp.ClientError as client_error:
                logger.error(f"和风天气API: 客户端错误: {client_error}")
                if attempt < retry_count:
                    logger.info(f"和风天气API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
            except Exception as e:
                logger.error(f"和风天气API请求失败: {e}")
                logger.exception("和风天气API: 详细错误信息:")
                if attempt < retry_count:
                    logger.info(f"和风天气API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
        
        logger.error(f"和风天气API: 所有尝试都失败了 ({api_type} for {location})")
        return None

    async def _get_city_location(self, city: str) -> Optional[str]:
        """获取城市Location ID"""
        if city in CITY_CODES:
            return CITY_CODES[city]
        
        geo_data = await self._fetch_qweather(city, "geo")
        if geo_data and geo_data.get('location'):
            return geo_data['location'][0].get('id')
        
        return None

    async def _get_location_from_address(self, address: str) -> Optional[Dict]:
        """从详细地址获取精确位置信息（支持街道级精度）"""
        geo_data = await self._fetch_qweather(address, "geo")
        if geo_data and geo_data.get('location'):
            loc = geo_data['location'][0]
            return {
                "id": loc.get('id'),
                "name": loc.get('name'),
                "adm1": loc.get('adm1', ''),
                "adm2": loc.get('adm2', ''),
                "lat": float(loc.get('lat', 0)),
                "lon": float(loc.get('lon', 0))
            }
        return None

    async def _fetch_weather_from_qweather(self, city: str, days: int = 0) -> Optional[Dict]:
        """从和风天气获取天气数据"""
        location_id = await self._get_city_location(city)
        if not location_id:
            return None
        
        if days == 0:
            data = await self._fetch_qweather(location_id, "now")
            if data and data.get('now'):
                now = data['now']
                return {
                    "city": city,
                    "temp": int(now.get('temp', 0)),
                    "feels_like": int(now.get('feelsLike', 0)),
                    "weather": now.get('text', '未知'),
                    "humidity": now.get('humidity', '--'),
                    "wind_dir": now.get('windDir', '--'),
                    "wind_speed": now.get('windSpeed', '--'),
                    "pressure": now.get('pressure', '--'),
                    "visibility": now.get('vis', '--'),
                    "time": datetime.now().strftime("%H:%M"),
                    "source": "和风天气"
                }
        else:
            api_type = "3d" if days <= 3 else "7d"
            data = await self._fetch_qweather(location_id, api_type)
            if data and data.get('daily'):
                daily_list = data['daily']
                if len(daily_list) > days:
                    day_names = ["今天", "明天", "后天"]
                    day_data = daily_list[days]
                    return {
                        "city": city,
                        "day_name": day_names[days] if days < len(day_names) else f"{days}天后",
                        "date": day_data.get('fxDate', ''),
                        "weather": day_data.get('textDay', '未知'),
                        "weather_night": day_data.get('textNight', ''),
                        "temp_max": int(day_data.get('tempMax', 0)),
                        "temp_min": int(day_data.get('tempMin', 0)),
                        "humidity": day_data.get('humidity', '--'),
                        "wind_dir": day_data.get('windDirDay', '--'),
                        "wind_speed": day_data.get('windSpeedDay', '--'),
                        "source": "和风天气"
                    }
        
        return None

    async def _fetch_weather_from_qweather_coords(self, lat: float, lon: float, city_name: str = "") -> Optional[Dict]:
        """根据经纬度获取天气数据（街道级精度）"""
        location = f"{lon},{lat}"
        
        data = await self._fetch_qweather(location, "now")
        if data and data.get('now'):
            now = data['now']
            return {
                "city": city_name or f"经纬度({lat:.2f},{lon:.2f})",
                "temp": int(now.get('temp', 0)),
                "feels_like": int(now.get('feelsLike', 0)),
                "weather": now.get('text', '未知'),
                "humidity": now.get('humidity', '--'),
                "wind_dir": now.get('windDir', '--'),
                "wind_speed": now.get('windSpeed', '--'),
                "pressure": now.get('pressure', '--'),
                "visibility": now.get('vis', '--'),
                "time": datetime.now().strftime("%H:%M"),
                "source": "和风天气",
                "precision": "街道级"
            }
        
        return None

    async def _fetch_weather_forecast_by_location(self, location: str, city_name: str, days: int) -> Optional[Dict]:
        """根据位置ID获取未来天气预报（支持街道级精度）"""
        api_type = "3d" if days <= 3 else "7d"
        data = await self._fetch_qweather(location, api_type)
        if data and data.get('daily'):
            daily_list = data['daily']
            if len(daily_list) > days:
                day_names = ["今天", "明天", "后天"]
                day_data = daily_list[days]
                return {
                    "city": city_name,
                    "day_name": day_names[days] if days < len(day_names) else f"{days}天后",
                    "date": day_data.get('fxDate', ''),
                    "weather": day_data.get('textDay', '未知'),
                    "weather_night": day_data.get('textNight', ''),
                    "temp_max": int(day_data.get('tempMax', 0)),
                    "temp_min": int(day_data.get('tempMin', 0)),
                    "humidity": day_data.get('humidity', '--'),
                    "wind_dir": day_data.get('windDirDay', '--'),
                    "wind_speed": day_data.get('windSpeedDay', '--'),
                    "source": "和风天气"
                }
        return None

    async def _fetch_weather_from_weathercn(self, city: str, days: int = 0, retry_count: int = 2) -> Optional[Dict]:
        """从中国天气网获取天气数据（备用），支持重试机制"""
        city_code = CITY_CODES.get(city)
        if not city_code:
            logger.warning(f"中国天气网: 城市代码未找到 for {city}")
            return None
        
        for attempt in range(retry_count + 1):
            try:
                url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://www.weather.com.cn/"
                }
                
                logger.debug(f"中国天气网API请求: {city} (code: {city_code}) (尝试 {attempt+1}/{retry_count+1})")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            try:
                                html = await response.text()
                                
                                weather_pattern = r'<li[^>]*class="sky[^"]*"[^>]*>(.*?)</li>'
                                matches = re.findall(weather_pattern, html, re.DOTALL)
                                
                                if matches and len(matches) > days:
                                    item = matches[days]
                                    
                                    date_match = re.search(r'<h1>([^<]+)</h1>', item)
                                    date_str = date_match.group(1).strip() if date_match else ""
                                    
                                    weather_desc_match = re.search(r'<p[^>]*class="wea"[^>]*>([^<]+)</p>', item)
                                    weather_desc = weather_desc_match.group(1).strip() if weather_desc_match else ""
                                    
                                    temp_section = re.search(r'<p class="tem">(.*?)</p>', item, re.DOTALL)
                                    temp_max = "--"
                                    temp_min = "--"
                                    if temp_section:
                                        temp_html = temp_section.group(1)
                                        high_match = re.search(r'<span>(-?\d+)</span>', temp_html)
                                        low_match = re.search(r'<i>(-?\d+)', temp_html)
                                        temp_max = high_match.group(1) if high_match else "--"
                                        temp_min = low_match.group(1) if low_match else "--"
                                    
                                    logger.debug(f"中国天气网API: 请求成功 for {city}")
                                    return {
                                        "city": city,
                                        "date": date_str,
                                        "weather": weather_desc or "未知",
                                        "temp_max": temp_max,
                                        "temp_min": temp_min,
                                        "source": "中国天气网"
                                    }
                                else:
                                    logger.warning(f"中国天气网API: 无匹配的天气数据 for {city}")
                                    if attempt < retry_count:
                                        logger.info(f"中国天气网API: 将在 2 秒后重试...")
                                        await asyncio.sleep(2)
                                        continue
                            except Exception as parse_error:
                                logger.error(f"中国天气网API: 解析错误: {parse_error}")
                                if attempt < retry_count:
                                    logger.info(f"中国天气网API: 将在 2 秒后重试...")
                                    await asyncio.sleep(2)
                                    continue
                        else:
                            logger.warning(f"中国天气网API: HTTP错误 {response.status} for {city}")
                            if attempt < retry_count:
                                logger.info(f"中国天气网API: 将在 2 秒后重试...")
                                await asyncio.sleep(2)
                                continue
            except asyncio.TimeoutError:
                logger.error(f"中国天气网API: 请求超时 for {city}")
                if attempt < retry_count:
                    logger.info(f"中国天气网API: 将在 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
            except aiohttp.ClientError as client_error:
                logger.error(f"中国天气网API: 客户端错误: {client_error}")
                if attempt < retry_count:
                    logger.info(f"中国天气网API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
            except Exception as e:
                logger.error(f"中国天气网API请求失败: {e}")
                logger.exception("中国天气网API: 详细错误信息:")
                if attempt < retry_count:
                    logger.info(f"中国天气网API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
        
        logger.error(f"中国天气网API: 所有尝试都失败了 for {city}")
        return None

    async def _fetch_weather_from_openmeteo(self, city: str, days: int = 0, retry_count: int = 2) -> Optional[Dict]:
        """从 Open-Meteo 获取天气数据（备用），支持重试机制"""
        for attempt in range(retry_count + 1):
            try:
                geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=zh"
                
                logger.debug(f"Open-Meteo API请求: 地理编码 for {city} (尝试 {attempt+1}/{retry_count+1})")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(geocoding_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                if data.get("results"):
                                    location = data["results"][0]
                                    lat = location["latitude"]
                                    lon = location["longitude"]
                                    city_name = location.get("name", city)
                                    
                                    if days == 0:
                                        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&timezone=Asia/Shanghai"
                                        
                                        logger.debug(f"Open-Meteo API请求: 天气数据 for {city_name} (lat: {lat}, lon: {lon})")
                                        
                                        async with session.get(weather_url, timeout=aiohttp.ClientTimeout(total=5)) as weather_response:
                                            if weather_response.status == 200:
                                                try:
                                                    weather_data = await weather_response.json()
                                                    current = weather_data.get("current", {})
                                                    weather_code = current.get("weather_code", 0)
                                                    wind_dir = current.get("wind_direction_10m", 0)
                                                    
                                                    directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
                                                    wind_dir_name = directions[round(wind_dir / 45) % 8]
                                                    
                                                    logger.debug(f"Open-Meteo API: 请求成功 for {city_name}")
                                                    return {
                                                        "city": city_name,
                                                        "temp": int(current.get("temperature_2m", 0)),
                                                        "humidity": current.get("relative_humidity_2m", "--"),
                                                        "wind": f"{wind_dir_name}风 {int(current.get('wind_speed_10m', 0))} km/h",
                                                        "weather": WEATHER_CODE_MAP.get(weather_code, "未知"),
                                                        "time": datetime.now().strftime("%H:%M"),
                                                        "source": "Open-Meteo"
                                                    }
                                                except json.JSONDecodeError as json_error:
                                                    logger.error(f"Open-Meteo API: 天气数据JSON解析失败: {json_error}")
                                                    if attempt < retry_count:
                                                        logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                                        await asyncio.sleep(2)
                                                        continue
                                            else:
                                                logger.warning(f"Open-Meteo API: 天气数据HTTP错误 {weather_response.status}")
                                                if attempt < retry_count:
                                                    logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                                    await asyncio.sleep(2)
                                                    continue
                                else:
                                    logger.warning(f"Open-Meteo API: 无匹配位置 for {city}")
                                    if attempt < retry_count:
                                        logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                        await asyncio.sleep(2)
                                        continue
                            except json.JSONDecodeError as json_error:
                                logger.error(f"Open-Meteo API: 地理编码JSON解析失败: {json_error}")
                                if attempt < retry_count:
                                    logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                    await asyncio.sleep(2)
                                    continue
                        else:
                            logger.warning(f"Open-Meteo API: 地理编码HTTP错误 {response.status}")
                            if attempt < retry_count:
                                logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                                await asyncio.sleep(2)
                                continue
            except asyncio.TimeoutError:
                logger.error(f"Open-Meteo API: 请求超时 for {city}")
                if attempt < retry_count:
                    logger.info(f"Open-Meteo API: 将在 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
            except aiohttp.ClientError as client_error:
                logger.error(f"Open-Meteo API: 客户端错误: {client_error}")
                if attempt < retry_count:
                    logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
            except Exception as e:
                logger.error(f"Open-Meteo API请求失败: {e}")
                logger.exception("Open-Meteo API: 详细错误信息:")
                if attempt < retry_count:
                    logger.info(f"Open-Meteo API: 将在 2 秒后重试...")
                    await asyncio.sleep(2)
                    continue
        
        logger.error(f"Open-Meteo API: 所有尝试都失败了 for {city}")
        return None

    async def _query_weather(self, city: str, days: int = 0, lat: float = None, lon: float = None) -> Dict[str, Any]:
        """查询天气主函数"""
        city = city.replace("市", "").replace("省", "").strip() if city else ""
        
        logger.info(f"开始查询天气: {city} (days: {days}, lat: {lat}, lon: {lon})")
        
        if "明天" in city or "明日" in city:
            days = 1
            city = city.replace("明天", "").replace("明日", "").strip()
            logger.debug(f"解析为明天的天气查询，更新days=1, city={city}")
        elif "后天" in city:
            days = 2
            city = city.replace("后天", "").strip()
            logger.debug(f"解析为后天的天气查询，更新days=2, city={city}")
        
        if not city:
            try:
                from ...config import Settings
                settings = Settings()
                city = settings.user.city or ""
                address = settings.user.address or ""
                if address and city:
                    city = f"{city}{address}"
                    logger.info(f"使用用户设置的默认位置: {city}")
                elif city:
                    logger.info(f"使用用户设置的默认城市: {city}")
            except Exception as e:
                logger.warning(f"获取用户默认城市失败: {e}")
        
        if city:
            # 尝试不同的数据源获取天气数据
            for source_name, data_source in self.data_sources.items():
                try:
                    logger.info(f"尝试从 {source_name} 获取天气数据")
                    if days == 0:
                        data = await data_source.get_current_weather(city)
                    else:
                        data = await data_source.get_forecast(city, days)
                    
                    if data:
                        logger.info(f"从 {source_name} 获取天气数据成功")
                        return {"success": True, "data": data}
                    else:
                        logger.warning(f"从 {source_name} 获取天气数据失败")
                except Exception as e:
                    logger.error(f"从 {source_name} 获取天气数据异常: {e}")
                    logger.exception(f"详细错误信息:")
        
        error_msg = f"无法获取 {city or '该位置'} 的天气信息"
        logger.error(f"所有天气查询尝试都失败: {error_msg}")
        return {"success": False, "error": error_msg}

    def _format_weather_response(self, result: Dict[str, Any]) -> str:
        """格式化天气响应"""
        if not result.get("success"):
            return f"❌ {result.get('error', '查询失败')}"
        
        data = result["data"]
        source = data.get("source", "未知")
        precision = data.get("precision", "")
        precision_str = f" ({precision})" if precision else ""
        
        if "temp" in data and "feels_like" in data:
            return f"""🌤️ {data['city']}当前天气{precision_str} ({data.get('time', '')})

🌡️ 温度: {data['temp']}°C (体感{data.get('feels_like', data['temp'])}°C)
☁️ 天气: {data.get('weather', '--')}
💧 湿度: {data.get('humidity', '--')}%
🌬️ 风向风速: {data.get('wind_dir', '--')} {data.get('wind_speed', '--')} km/h
👁️ 能见度: {data.get('visibility', '--')} km
📊 气压: {data.get('pressure', '--')} hPa

📍 数据来源: {source}"""
        elif "temp" in data:
            return f"""🌤️ {data['city']}当前天气 ({data.get('time', '')})

🌡️ 温度: {data['temp']}°C
☁️ 天气: {data.get('weather', '--')}
💧 湿度: {data.get('humidity', '--')}%
🌬️ 风力: {data.get('wind', '--')}

📍 数据来源: {source}"""
        elif "forecast" in data:
            forecast_list = data['forecast']
            if not forecast_list:
                return f"❌ {data['city']}暂无天气预报数据"
            
            day_names = ["今天", "明天", "后天"]
            response_parts = [f"🌤️ {data['city']}天气预报 ({len(forecast_list)}天)"]
            
            for i, forecast in enumerate(forecast_list):
                day_name = forecast.get("day_name") or (day_names[i] if i < len(day_names) else f"{i}天后")
                weather_night = forecast.get("weather_night", "")
                weather_str = f"{forecast.get('weather', '--')}" + (f" 转{weather_night}" if weather_night else "")
                
                day_part = f"\n{day_name} ({forecast.get('date', '')})"
                day_part += f"\n🌡️ 温度: {forecast.get('temp_min', '--')}°C ~ {forecast.get('temp_max', '--')}°C"
                day_part += f"\n☁️ 天气: {weather_str}"
                if forecast.get('wind_dir') or forecast.get('wind_speed'):
                    day_part += f"\n🌬️ 风向风速: {forecast.get('wind_dir', '--')} {forecast.get('wind_speed', '--')} km/h"
                
                response_parts.append(day_part)
            
            response_parts.append(f"\n\n📍 数据来源: {source}")
            return "".join(response_parts)
        else:
            day_name = data.get("day_name", "")
            weather_night = data.get("weather_night", "")
            weather_str = f"{data.get('weather', '--')}" + (f" 转{weather_night}" if weather_night else "")
            return f"""🌤️ {data['city']}{day_name}天气 ({data.get('date', '')})

🌡️ 温度: {data.get('temp_min', '--')}°C ~ {data.get('temp_max', '--')}°C
☁️ 天气: {weather_str}
💧 湿度: {data.get('humidity', '--')}%
🌬️ 风向风速: {data.get('wind_dir', '--')} {data.get('wind_speed', '--')} km/h

📍 数据来源: {source}"""

    async def execute_task(self, task: Task) -> Any:
        import time
        start_time = time.time()
        
        if task.type == "action":
            result = await self._handle_action(task.params)
            logger.info(f"⏱️ [计时] WeatherAgent.execute_task 耗时: {time.time() - start_time:.2f}秒")
            return result
        elif task.type in ("current_weather", "get_weather"):
            city = task.params.get("city", "")
            lat = task.params.get("lat")
            lon = task.params.get("lon")
            text = task.params.get("original_text", "")
            days = task.params.get("days", 0)
            
            logger.info(f"current_weather task: city={city}, text={text}, days={days}")
            
            if "明天" in text or "明日" in text:
                days = 1
            elif "后天" in text:
                days = 2
            
            try:
                from ...config import Settings
                settings = Settings()
                user_city = settings.user.city or ""
                user_address = settings.user.address or ""
                
                if not city:
                    if user_city:
                        city = f"{user_city}{user_address}" if user_address else user_city
                        logger.info(f"使用用户默认位置: {city}")
                    elif WeatherAgent._last_city:
                        city = WeatherAgent._last_city
                        logger.info(f"使用上下文记忆的城市: {city}")
                elif city == user_city and user_address:
                    city = f"{city}{user_address}"
                    logger.info(f"添加详细地址: {city}")
            except Exception as e:
                logger.warning(f"获取用户配置失败: {e}")
            
            if days == 1:
                text = f"{city}明天天气" if city else "明天天气"
            elif days == 2:
                text = f"{city}后天天气" if city else "后天天气"
            else:
                text = f"{city}天气" if city else "天气"
            
            if city or (lat and lon):
                return await self._handle_action({"text": text, "lat": lat, "lon": lon})
            return self.cannot_handle("未提供城市名称或位置")
        elif task.type == "weather_query" or task.type == "weather_forecast":
            city = task.params.get("city", "")
            lat = task.params.get("lat")
            lon = task.params.get("lon")
            text = task.params.get("original_text", "")
            action = task.params.get("action", "")
            days = task.params.get("days", 0)
            
            logger.info(f"weather_query task: city={city}, text={text}, action={action}, days={days}")
            
            if "明天" in text or "明日" in text:
                days = 1
            elif "后天" in text:
                days = 2
            
            if days == 1:
                text = f"{city}明天天气" if city else "明天天气"
            elif days == 2:
                text = f"{city}后天天气" if city else "后天天气"
            else:
                if city:
                    text = f"{city}天气"
                elif text:
                    pass
                else:
                    text = "天气"
            
            logger.info(f"最终查询文本: '{text}', days={days}")
            
            result = await self._handle_action({"text": text, "lat": lat, "lon": lon})
            logger.info(f"⏱️ [计时] WeatherAgent.execute_task 耗时: {time.time() - start_time:.2f}秒")
            return result
        elif task.type == "general":
            text = task.params.get("text", task.content or "")
            if not text:
                return self.cannot_handle("未提供查询文本")
            
            intent_result = self.parse_weather_intent(text)
            
            if intent_result.get("is_weather_query", False):
                city = intent_result.get("city", "")
                days = intent_result.get("days", 0)
                
                if not city:
                    if WeatherAgent._last_city:
                        city = WeatherAgent._last_city
                        logger.info(f"使用上下文记忆的城市: {city}")
                    else:
                        try:
                            from ...config import Settings
                            settings = Settings()
                            city = settings.user.city or ""
                            address = settings.user.address or ""
                            if address and city:
                                city = f"{city}{address}"
                            elif city:
                                pass
                            else:
                                city = "北京"
                        except Exception as e:
                            logger.warning(f"获取用户默认城市失败: {e}")
                            city = "北京"
                
                if days == 1:
                    text = f"{city}明天天气"
                elif days == 2:
                    text = f"{city}后天天气"
                elif days == 3:
                    text = f"{city}大后天天气"
                else:
                    text = f"{city}天气"
                
                result = await self._handle_action({"text": text})
                logger.info(f"⏱️ [计时] WeatherAgent.execute_task 耗时: {time.time() - start_time:.2f}秒")
                return result
            
            if self._is_weather_related(text):
                result = await self._handle_action({"text": text})
                logger.info(f"⏱️ [计时] WeatherAgent.execute_task 耗时: {time.time() - start_time:.2f}秒")
                return result
            
            logger.info(f"⏱️ [计时] WeatherAgent.execute_task 耗时: {time.time() - start_time:.2f}秒")
            return self.cannot_handle("无法识别天气查询意图")
        logger.info(f"⏱️ [计时] WeatherAgent.execute_task 耗时: {time.time() - start_time:.2f}秒")
        return self.cannot_handle("未知操作")

    def _is_weather_related(self, text: str) -> bool:
        """判断文本是否与天气相关"""
        text_lower = text.lower()
        related_keywords = [
            "穿什么", "穿衣", "带伞", "下雨", "晴天", "阴天", "多云", 
            "气温", "温度", "风", "雨", "雪", "热", "冷", "凉快",
            "出门", "天气", "预报"
        ]
        return any(kw in text_lower for kw in related_keywords)

    async def _handle_action(self, params: Dict) -> str:
        text = params.get("text", "").strip()
        lat = params.get("lat")
        lon = params.get("lon")
        
        logger.info(f"_handle_action 收到文本: '{text}'")
        
        if not text:
            return self.cannot_handle("未提供查询文本")

        if "对比" in text:
            candidates = re.split(r"[，、\s]+", re.sub(r"^对比[：:]*", "", text).strip())
            candidates = [c.strip(" \u3000") for c in candidates if c.strip()]
            cities = [c for c in candidates[:5] if c and len(c) <= 10]
            
            if len(cities) < 2:
                return self.cannot_handle("多城市对比需指定2–5个城市")
            
            results = []
            for city in cities:
                result = await self._query_weather(city)
                if result["success"]:
                    results.append((city, result["data"]))
            
            if not results:
                return self.cannot_handle("未找到任何有效城市的天气数据")
            
            lines = ["📊 多城天气对比\n", "| 城市 | 温度 | 天气 | 来源 |", "|---|---|---|---|"]
            for city, data in results:
                if "temp" in data:
                    temp = f"{data['temp']}°C"
                else:
                    temp = f"{data['temp_min']}~{data['temp_max']}°C"
                lines.append(f"| {city} | {temp} | {data['weather']} | {data.get('source', '--')} |")
            
            return "\n".join(lines)

        city = self._extract_city_from_text(text)
        
        if not city and not (lat and lon):
            if "穿什么" in text or "穿衣" in text or "伞" in text:
                return "请问您所在的城市是？或者您计划前往哪个城市？"
            return self.cannot_handle("未识别到城市名称，请输入如'北京天气'或'对比上海和杭州'")

        days = 0
        if "明天" in text or "明日" in text:
            days = 1
        elif "后天" in text:
            days = 2

        result = await self._query_weather(city, days, lat, lon)
        
        if not result["success"]:
            return f"❌ {result.get('error', '查询失败')}，请确认城市名称是否正确"
        
        if city:
            WeatherAgent._last_city = city
            logger.info(f"已记住城市: {city}")

        if "穿" in text or "穿衣" in text or "伞" in text:
            data = result["data"]
            temp = data.get("temp", data.get("temp_max", 26))
            if isinstance(temp, str):
                temp = int(temp) if temp.isdigit() else 26
            weather = data.get("weather", "晴")
            
            advice = self._get_clothing_advice(temp, weather)
            return f"{self._format_weather_response(result)}\n\n👔 穿衣建议:\n{advice}"

        return self._format_weather_response(result)

    def _get_clothing_advice(self, temp: int, weather: str) -> str:
        """根据温度和天气给出穿衣建议"""
        if temp >= 30:
            advice = "👕 建议：短袖、短裤、裙子等清凉透气服装\n🧢 配饰：遮阳帽、墨镜、防晒霜\n⚠️ 提示：高温天气，注意防暑降温"
        elif temp >= 25:
            advice = "👕 建议：短袖T恤、薄衬衫、薄裙\n🧢 配饰：太阳镜、薄外套（室内空调）\n⚠️ 提示：天气炎热，注意防晒"
        elif temp >= 20:
            advice = "👕 建议：长袖衬衫、薄外套、休闲裤\n🧢 配饰：薄围巾（早晚温差）\n⚠️ 提示：温度适宜，穿着舒适"
        elif temp >= 15:
            advice = "👕 建议：薄毛衣、夹克、风衣\n🧢 配饰：薄围巾\n⚠️ 提示：早晚微凉，建议叠穿"
        elif temp >= 10:
            advice = "👕 建议：毛衣、厚外套、长裤\n🧢 配饰：围巾、帽子\n⚠️ 提示：天气转凉，注意保暖"
        elif temp >= 5:
            advice = "👕 建议：厚毛衣、羽绒服、保暖裤\n🧢 配饰：围巾、手套、帽子\n⚠️ 提示：天气寒冷，注意保暖"
        else:
            advice = "👕 建议：厚羽绒服、保暖内衣、棉裤\n🧢 配饰：围巾、手套、帽子、耳罩\n⚠️ 提示：严寒天气，尽量减少外出"

        if "雨" in weather:
            advice += "\n☔ 提示：有降雨，建议携带雨具"
        if "雪" in weather:
            advice += "\n❄️ 提示：有降雪，注意防滑"
        
        return advice
    
    def _extract_city_from_text(self, text: str) -> Optional[str]:
        """从文本中提取城市名称或详细地址"""
        text = text.replace("天气", "").replace("明天", "").replace("后天", "").strip()
        
        for known_city in CITY_CODES.keys():
            if known_city in text:
                idx = text.find(known_city)
                rest = text[idx:]
                for end_marker in ["今天", "明日", "今日", "当前", "现在"]:
                    if end_marker in rest:
                        rest = rest[:rest.find(end_marker)]
                if len(rest) > len(known_city) and ("区" in rest or "县" in rest or "镇" in rest):
                    return rest.strip()
                return known_city
        
        if "街道" in text or ("区" in text and len(text) > 5) or ("路" in text and len(text) > 5):
            for known_city in CITY_CODES.keys():
                if known_city in text:
                    return text
            return text
        
        if "市" in text:
            idx = text.find("市")
            city_candidate = text[:idx]
            if len(city_candidate) >= 2:
                return city_candidate
        
        for seg in re.split(r"[，、\s（）\[\]]+", text):
            seg = seg.strip()
            if seg and len(seg) >= 2 and len(seg) <= 10 and not seg.isdigit():
                if "区" in seg or "县" in seg or "街道" in seg or "路" in seg:
                    continue
                return seg
        
        if len(text) >= 2:
            return text[:min(len(text), 10)]
        
        return None

    def parse_weather_intent(self, text: str) -> Dict[str, Any]:
        """使用关键词解析天气查询意图"""
        text_lower = text.lower()
        
        config = self._keyword_patterns
        time_words = config.get("time_words", ["今天", "明天", "明日", "后天", "大后天", "当前", "现在", "今日"])
        days_mapping = config.get("days_mapping", {"明天": 1, "明日": 1, "后天": 2, "大后天": 3})
        city_patterns = config.get("city_patterns", [])
        weather_keywords = config.get("weather_keywords", ["天气", "气温", "温度", "下雨", "晴天", "阴天", "多云"])
        
        days = 0
        for word, day_value in days_mapping.items():
            if word in text:
                days = day_value
                break
        
        city = ""
        for pattern in city_patterns:
            match = re.search(pattern, text)
            if match:
                city = match.group(1)
                if city in time_words:
                    city = ""
                break
        
        is_weather = any(kw in text_lower for kw in weather_keywords)
        
        result = {
            "is_weather_query": is_weather,
            "city": city,
            "days": days,
            "confidence": 1.0 if is_weather else 0.0
        }
        logger.info(f"关键词解析天气意图: {result}")
        return result
