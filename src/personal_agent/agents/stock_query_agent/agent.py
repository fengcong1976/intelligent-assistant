"""
stock_query_agent - 股票查询智能体 - 使用 Tushare 查询股票实时价格、历史数据和K线图
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from ..base import BaseAgent, Task


INDEX_MAP = {
    "上证指数": "000001.SH",
    "上证": "000001.SH",
    "沪市": "000001.SH",
    "大盘": "000001.SH",
    "沪指": "000001.SH",
    "深证成指": "399001.SZ",
    "深证": "399001.SZ",
    "深成指": "399001.SZ",
    "深指": "399001.SZ",
    "创业板指": "399006.SZ",
    "创业板": "399006.SZ",
    "沪深300": "000300.SH",
    "上证50": "000016.SH",
    "中证500": "000905.SH",
    "科创50": "000688.SH",
    "北证50": "899050.BJ",
}


class StockQueryAgent(BaseAgent):
    """股票查询智能体 - 使用 Tushare 查询股票实时价格、历史数据和K线图"""
    
    PRIORITY = 5
    KEYWORD_MAPPINGS = {
        "股票": ("query_price", {}),
        "股价": ("query_price", {}),
        "股票价格": ("query_price", {}),
        "查询股票": ("query_price", {}),
        "股票行情": ("query_price", {}),
        "K线": ("query_kline", {}),
        "K线图": ("query_kline", {}),
        "股票走势": ("query_kline", {}),
        "大盘": ("query_index", {}),
        "指数": ("query_index", {}),
        "上证指数": ("query_index", {}),
        "深证成指": ("query_index", {}),
        "创业板指": ("query_index", {}),
    }
    
    def __init__(self):
        super().__init__(
            name="stock_query_agent",
            description="股票查询智能体 - 使用 Tushare 查询股票实时价格、历史数据和K线图"
        )
        
        self.register_capability(
            capability="query_stock",
            description="查询股票行情信息。支持股票代码（如'000001'）或公司名称（如'平安银行'、'美的集团'）。返回股票的实时价格、涨跌幅等信息。",
            aliases=[
                "股票行情", "股票价格", "股票查询", "查股票", "股票信息",
                "股价", "股票走势", "股票涨跌", "股票涨跌幅",
                "实时股价", "实时行情", "股票实时价格"
            ],
            parameters={
                "type": "object",
                "properties": {
                    "stock_code": {
                        "type": "string",
                        "description": "股票代码（如'000001'）或公司名称（如'平安银行'、'美的集团'、'伊利股份'、'中国人寿'）。支持中文公司名称和股票代码。"
                    }
                },
                "required": ["stock_code"]
            },
            category="stock"
        )
        
        self.register_capability(
            capability="query_index",
            description="""查询大盘指数行情。

**重要**：当用户问"大盘指数"、"大盘"、"指数行情"时，只需调用一次，会自动返回上证指数、深证成指、创业板指三个指数的行情。不要分别调用三次！

**单个指数查询**：
- 上证指数 / 沪指 / 大盘
- 深证成指 / 深成指
- 创业板指 / 创业板
- 沪深300 / 上证50 / 中证500 / 科创50""",
            aliases=[
                "大盘指数", "大盘行情", "指数行情", "股市指数", "股票指数",
                "上证指数", "上证综指", "沪指", "上证",
                "深证成指", "深证指数", "深成指", "深证",
                "创业板指", "创业板指数", "创业板",
                "沪深300", "上证50", "中证500", "科创50"
            ],
            parameters={
                "type": "object",
                "properties": {
                    "index_name": {
                        "type": "string",
                        "description": "指数名称。当用户问'大盘指数'、'大盘'、'指数'时，留空或填'大盘'会返回三个主要指数。单个指数可填：上证指数、深证成指、创业板指等",
                        "default": "大盘"
                    }
                },
                "required": []
            },
            category="stock"
        )
        
        self.register_capability("query_price", "查询股票价格")
        self.register_capability("query_kline", "查询K线图")
        
        logger.info("✅ stock_query_agent 已初始化")
    
    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params
        logger.info(f"🔧 {self.name} 执行任务: {task_type}, 参数: {params}")
        
        if not HAS_TUSHARE:
            return "❌ 股票查询功能需要 tushare 库，请运行 pip install tushare"
        
        if not HAS_PANDAS:
            return "❌ 股票查询功能需要 pandas 库，请运行 pip install pandas numpy"
        
        if task_type == "query_index":
            index_input = params.get("index_name") or params.get("stock_code") or params.get("stock_name")
            if not index_input:
                index_input = "上证指数"
            result = await self._handle_query_index(index_input)
            if result and "未找到" in result:
                task.no_retry = True
            return result
        
        if task_type in ["query_stock", "query_price", "stock_query", "general"]:
            index_input = params.get("index_name")
            if index_input:
                result = await self._handle_query_index(index_input)
                if result and "未找到" in result:
                    task.no_retry = True
                return result
            
            stock_input = params.get("stock_code") or params.get("stock_name") or params.get("text", "")
            if not stock_input:
                return self._get_help()
            
            stock_input = self._extract_stock_code(stock_input)
            
            if self._is_index_query(stock_input):
                result = await self._handle_query_index(stock_input)
                if result and "未找到" in result:
                    task.no_retry = True
                return result
            
            result = await self._handle_query_price(stock_input)
            if result and "未找到" in result:
                task.no_retry = True
            return result
        
        elif task_type == "query_kline":
            stock_input = params.get("stock_code") or params.get("stock_name")
            period = params.get("period", "day").lower()
            if not stock_input:
                return self._get_help()
            if period not in ["day", "week", "month"]:
                return "❌ 错误：不支持的周期，仅支持 day/week/month"
            result = await self._handle_query_kline(stock_input, period)
            if result and "未找到" in result:
                task.no_retry = True
            return result
        elif task_type == "agent_help":
            return self._get_help()
        else:
            return self._get_help()
    
    def _is_index_query(self, text: str) -> bool:
        """判断是否为大盘指数查询"""
        text_lower = text.lower()
        index_keywords = ["大盘", "上证", "深证", "创业板", "指数", "沪指", "深指"]
        return any(kw in text_lower for kw in index_keywords) or text in INDEX_MAP
    
    def _extract_stock_code(self, text: str) -> str:
        """从文本中提取股票代码或名称"""
        import re
        
        text = text.strip()
        
        code_patterns = [
            r'^(\d{6})$',
            r'(\d{6})(?:股票|行情|股价)?',
            r'股票[：:]?\s*(\d{6})',
        ]
        
        for pattern in code_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        result = text
        if result.startswith('查询'):
            result = result[2:].strip()
        
        suffixes = ['股票行情', '股票股价', '股票', '行情', '股价', '股份']
        for suffix in suffixes:
            if result.endswith(suffix):
                result = result[:-len(suffix)].strip()
                break
        
        if result:
            return result
        
        return text
    
    def _get_help(self) -> str:
        """返回帮助信息"""
        help_text = """📈 股票查询智能体使用帮助

🔍 查询股票价格：
   • 直接输入股票名称：伊利股份、美的集团、贵州茅台
   • 输入股票代码：600887、000333、600519
   • 输入完整代码：600887.SH、000333.SZ

📊 查询大盘指数：
   • 大盘 / 上证指数 / 沪指
   • 深证成指 / 深成指
   • 创业板指 / 创业板
   • 沪深300 / 上证50 / 中证500

📈 查询K线图：
   • 日K线：某某股票 日K
   • 周K线：某某股票 周K
   • 月K线：某某股票 月K

💡 示例：
   • 伊利股份
   • 600887
   • 今天大盘怎么样
   • 上证指数
   • 创业板

⚠️ 注意：
   • 当前仅支持A股查询
   • 需要配置 Tushare Token"""
        return help_text
    
    def _get_realtime_tencent(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        使用腾讯财经接口获取实时行情 (速度快,优先使用)
        
        Args:
            stock_code: 股票代码，格式如 600887.SH 或 000001.SH
        
        Returns:
            包含实时行情数据的字典，如果失败返回 None
        """
        if not HAS_REQUESTS:
            logger.warning("⚠️ requests 库未安装，无法使用腾讯财经接口")
            return None
        
        try:
            # 判断交易所
            if stock_code.endswith('.SH') or (len(stock_code) == 6 and stock_code.startswith('6')):
                prefix = 'sh'
            elif stock_code.endswith('.SZ') or (len(stock_code) == 6 and (stock_code.startswith('0') or stock_code.startswith('3'))):
                prefix = 'sz'
            elif stock_code.endswith('.BJ') or (len(stock_code) == 6 and stock_code.startswith('8')):
                prefix = 'bj'
            else:
                prefix = 'sh'
            
            # 提取代码数字
            code_num = stock_code.replace('.SH', '').replace('.SZ', '').replace('.BJ', '').zfill(6)
            
            # 构建URL
            url = f"http://qt.gtimg.cn/q={prefix}{code_num}"
            
            # 请求腾讯财经接口（超时1秒）
            response = requests.get(url, timeout=1)
            
            if response.status_code == 200:
                text = response.text.strip()
                
                # 检查数据格式
                if not '~' in text:
                    return None
                
                # 解析腾讯返回的数据格式: v_sh600519="1~贵州茅台~600519~1755.00~..."
                data = text.split('"')[1].split('~')
                
                if len(data) < 10:
                    return None
                
                # 构建返回数据 (腾讯接口字段索引)
                # 1=名称, 3=现价, 4=昨收, 5=今开, 6=成交量, 31=涨跌额, 32=涨跌幅,
                # 33=最高, 34=最低, 37=成交额(万元), 38=换手率,
                # 39=动态市盈率, 44=总市值(亿元), 45=流通市值(亿元),
                # 52=市净率, 53=市盈率TTM
                result = {
                    'name': data[1] if len(data) > 1 else '',
                    'open': float(data[5]) if len(data) > 5 and data[5] else 0,
                    'pre_close': float(data[4]) if len(data) > 4 and data[4] else 0,
                    'close': float(data[3]) if len(data) > 3 and data[3] else 0,
                    'high': float(data[33]) if len(data) > 33 and data[33] else 0,
                    'low': float(data[34]) if len(data) > 34 and data[34] else 0,
                    'vol': float(data[6]) if len(data) > 6 and data[6] else 0,
                    'amount': float(data[37]) if len(data) > 37 and data[37] else 0,
                    'pct_chg': float(data[32]) if len(data) > 32 and data[32] else 0,
                    'change': float(data[31]) if len(data) > 31 and data[31] else 0,
                    'turnover_rate': float(data[38]) if len(data) > 38 and data[38] else 0,
                    'pe_ttm': float(data[53]) if len(data) > 53 and data[53] else 0,
                    'pb': float(data[52]) if len(data) > 52 and data[52] else 0,
                    'total_mv': float(data[44]) if len(data) > 44 and data[44] else 0,
                    'circ_mv': float(data[45]) if len(data) > 45 and data[45] else 0,
                }
                
                # 如果腾讯接口没有涨跌幅，则计算
                if result['pct_chg'] == 0 and result['pre_close'] > 0:
                    result['change'] = result['close'] - result['pre_close']
                    result['pct_chg'] = (result['change'] / result['pre_close'] * 100)
                
                logger.info(f"📊 腾讯财经接口获取成功: {stock_code}")
                return result
            
            return None
        except Exception as e:
            logger.warning(f"📊 腾讯财经接口获取失败: {e}")
            return None
    
    def _get_pro_api(self):
        """获取 Tushare API 实例"""
        from ...config import settings
        tushare_token = settings.user.tushare_token
        if not tushare_token:
            raise ValueError("Tushare Token 未配置，请在设置中配置 TUSHARE_TOKEN")
        return ts.pro_api(tushare_token)
    
    def _get_latest_trade_date(self, pro) -> str:
        """获取最近的交易日"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=today, is_open='1')
            
            if df is not None and not df.empty:
                df = df.sort_values('cal_date', ascending=False)
                latest_date = df.iloc[0]['cal_date']
                logger.info(f"📅 最近交易日: {latest_date}")
                return latest_date
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
        
        return None
    
    def _resolve_index_code(self, index_input: str) -> Tuple[str, str]:
        """解析指数代码"""
        if not index_input:
            return "000001.SH", "上证指数"
        
        for name, code in INDEX_MAP.items():
            if name in index_input or index_input in name:
                return code, name
        
        if index_input.upper().replace('.', '') in ['000001SH', '000001']:
            return "000001.SH", "上证指数"
        if index_input.upper().replace('.', '') in ['399001SZ', '399001']:
            return "399001.SZ", "深证成指"
        if index_input.upper().replace('.', '') in ['399006SZ', '399006']:
            return "399006.SZ", "创业板指"
        
        return "000001.SH", "上证指数"
    
    async def _handle_query_index(self, index_input: str) -> str:
        """查询指数行情"""
        try:
            # 检查是否需要查询多个大盘指数
            if any(keyword in index_input for keyword in ["大盘指数", "大盘", "指数"]):
                return await self._handle_multi_index_query()
            
            # 单个指数查询
            ts_code, index_name = self._resolve_index_code(index_input)
            
            # 判断是否在交易时段
            now = datetime.now()
            is_trading_hours = now.weekday() < 5 and (
                (9 <= now.hour < 11 and now.minute >= 30) or 
                (13 <= now.hour < 15) or 
                (now.hour == 11 and now.minute <= 30)
            )
            
            # 优先使用腾讯财经接口获取实时数据
            realtime_data = self._get_realtime_tencent(ts_code)
            
            if realtime_data is not None:
                # 使用腾讯财经接口的实时数据
                logger.info(f"📊 使用腾讯财经接口的实时数据")
                
                close = realtime_data['close']
                pct_chg = realtime_data['pct_chg']
                pre_close = realtime_data['pre_close']
                high = realtime_data['high']
                low = realtime_data['low']
                vol = realtime_data['vol']
                amount = realtime_data['amount']
                
                status_hint = " 🟢 交易中" if is_trading_hours else " ⚠️ 已收盘"
                
                result = f"📊 {index_name}（{ts_code.split('.')[0]}）\n"
                result += f"💰 现点位: {close:.2f}"
                
                if pct_chg > 0:
                    result += f" 🔴+{pct_chg:.2f}%"
                elif pct_chg < 0:
                    result += f" 🟢{pct_chg:.2f}%"
                else:
                    result += f" ⚪{pct_chg:.2f}%"
                
                result += status_hint
                
                if pre_close:
                    result += f"\n📊 昨收: {pre_close:.2f}"
                if high and low:
                    result += f" | 最高: {high:.2f} | 最低: {low:.2f}"
                if vol:
                    result += f"\n📊 成交量: {vol/100000000:.2f}亿手"
                if amount:
                    result += f" | 成交额: {amount/100000:.2f}亿"
                
                return result
            
            # 腾讯财经接口失败，使用 Tushare 历史数据
            logger.info(f"📊 腾讯财经接口失败，使用 Tushare 历史数据")
            
            pro = self._get_pro_api()
            
            df = None
            
            # 如果在交易时段，优先查询当天的数据
            if is_trading_hours:
                today = datetime.now().strftime('%Y%m%d')
                logger.info(f"📊 在交易时段，尝试查询当天数据: {today}")
                df = pro.index_daily(ts_code=ts_code, trade_date=today)
                
                if df is not None and not df.empty:
                    logger.info(f"📊 当天数据获取成功")
                else:
                    logger.info(f"📊 当天数据暂无，尝试查询最近交易日")
            
            # 如果当天数据为空，尝试用最近交易日查询
            if df is None or df.empty:
                latest_trade_date = self._get_latest_trade_date(pro)
                if latest_trade_date:
                    df = pro.index_daily(ts_code=ts_code, trade_date=latest_trade_date)
            
            # 如果查询不到数据，就查询最近30天的数据
            if df is None or df.empty:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"📊 查询不到数据，改查 {start_date} - {end_date}")
                df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                return f"❌ 指数 {ts_code} 暂无数据"
            
            latest = df.iloc[0]
            
            close = float(latest['close'])
            pct_chg = float(latest['pct_chg']) if 'pct_chg' in latest else None
            pre_close = float(latest['pre_close']) if 'pre_close' in latest else None
            high = float(latest['high']) if 'high' in latest else None
            low = float(latest['low']) if 'low' in latest else None
            vol = float(latest['vol']) if 'vol' in latest else None
            amount = float(latest['amount']) if 'amount' in latest else None
            trade_date = latest['trade_date']
            
            status_hint = " 🟢 交易中" if is_trading_hours else " ⚠️ 已收盘"
            
            result = f"📊 {index_name}（{ts_code.split('.')[0]}）\n"
            result += f"📅 交易日: {trade_date}\n"
            result += f"📈 收盘点位: {close:.2f}"
            
            if pct_chg is not None:
                if pct_chg > 0:
                    result += f" 🔴+{pct_chg:.2f}%"
                elif pct_chg < 0:
                    result += f" 🟢{pct_chg:.2f}%"
                else:
                    result += f" ⚪{pct_chg:.2f}%"
            
            result += status_hint
            
            if pre_close:
                result += f"\n📊 昨收: {pre_close:.2f}"
            if high and low:
                result += f" | 最高: {high:.2f} | 最低: {low:.2f}"
            if vol:
                result += f"\n📊 成交量: {vol/100000000:.2f}亿手"
            if amount:
                result += f" | 成交额: {amount/100000:.2f}亿"
            
            logger.info(f"✅ 指数查询成功: {index_name}")
            return result
            
        except ValueError as e:
            return f"❌ {str(e)}"
        except Exception as e:
            logger.exception(f"查询指数时发生错误 {index_input}: {e}")
            return f"❌ 查询失败: {str(e)}"
    
    async def _handle_multi_index_query(self) -> str:
        """查询多个主要大盘指数"""
        try:
            # 主要指数列表
            main_indices = [
                ("000001.SH", "上证指数"),
                ("399001.SZ", "深证成指"),
                ("399006.SZ", "创业板指")
            ]
            
            # 判断是否在交易时段
            now = datetime.now()
            is_trading_hours = now.weekday() < 5 and (
                (9 <= now.hour < 11 and now.minute >= 30) or 
                (13 <= now.hour < 15) or 
                (now.hour == 11 and now.minute <= 30)
            )
            
            # 优先使用腾讯财经接口获取实时数据
            results = []
            all_success = True
            
            for ts_code, index_name in main_indices:
                realtime_data = self._get_realtime_tencent(ts_code)
                
                if realtime_data is not None:
                    # 使用腾讯财经接口的实时数据
                    close = realtime_data['close']
                    pct_chg = realtime_data['pct_chg']
                    pre_close = realtime_data['pre_close']
                    high = realtime_data['high']
                    low = realtime_data['low']
                    vol = realtime_data['vol']
                    amount = realtime_data['amount']
                    
                    status_hint = " 🟢 交易中" if is_trading_hours else " ⚠️ 已收盘"
                    
                    result = f"📊 {index_name}（{ts_code.split('.')[0]}）\n"
                    result += f"💰 现点位: {close:.2f}"
                    
                    if pct_chg > 0:
                        result += f" 🔴+{pct_chg:.2f}%"
                    elif pct_chg < 0:
                        result += f" 🟢{pct_chg:.2f}%"
                    else:
                        result += f" ⚪{pct_chg:.2f}%"
                    
                    result += status_hint
                    
                    if pre_close:
                        result += f"\n📊 昨收: {pre_close:.2f}"
                    if high and low:
                        result += f" | 最高: {high:.2f} | 最低: {low:.2f}"
                    if vol:
                        result += f"\n📊 成交量: {vol/100000000:.2f}亿手"
                    if amount:
                        result += f" | 成交额: {amount/100000:.2f}亿"
                    
                    results.append(result)
                else:
                    all_success = False
                    break
            
            # 如果所有指数都获取成功，直接返回
            if all_success and results:
                final_result = "📈 大盘指数行情（实时）\n" + "\n" + "\n".join(results)
                logger.info("✅ 大盘指数实时查询成功")
                return final_result
            
            # 腾讯财经接口失败，使用 Tushare 历史数据
            logger.info(f"📊 腾讯财经接口失败，使用 Tushare 历史数据")
            
            pro = self._get_pro_api()
            latest_trade_date = self._get_latest_trade_date(pro)
            
            results = []
            
            for ts_code, index_name in main_indices:
                df = None
                
                # 先尝试用最近交易日查询
                if latest_trade_date:
                    df = pro.index_daily(ts_code=ts_code, trade_date=latest_trade_date)
                
                # 如果查询不到数据，就查询最近30天的数据
                if df is None or df.empty:
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                    logger.info(f"📊 {index_name} 查询不到 {latest_trade_date} 的数据，改查 {start_date} - {end_date}")
                    df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                
                logger.info(f"📊 查询指数: {index_name} ({ts_code}), 数据行数: {len(df) if df is not None else 0}")
                
                if df is None or df.empty:
                    results.append(f"📊 {index_name}（{ts_code.split('.')[0]}）\n❌ 暂无数据")
                    continue
                
                latest = df.iloc[0]
                logger.info(f"📊 {index_name} 最新数据: {latest.to_dict()}")
                
                close = float(latest['close'])
                pct_chg = float(latest['pct_chg']) if 'pct_chg' in latest else None
                trade_date = latest['trade_date']
                
                status_hint = " 🟢 交易中" if is_trading_hours else " ⚠️ 已收盘"
                
                result = f"📊 {index_name}（{ts_code.split('.')[0]}）\n"
                result += f"📅 交易日: {trade_date}\n"
                result += f"📈 收盘点位: {close:.2f}"
                
                if pct_chg is not None:
                    if pct_chg > 0:
                        result += f" 🔴+{pct_chg:.2f}%"
                    elif pct_chg < 0:
                        result += f" 🟢{pct_chg:.2f}%"
                    else:
                        result += f" ⚪{pct_chg:.2f}%"
                
                result += status_hint
                results.append(result)
            
            # 合并结果
            final_result = "📈 大盘指数行情\n" + "\n" + "\n".join(results)
            logger.info("✅ 大盘指数查询成功")
            return final_result
            
        except ValueError as e:
            return f"❌ {str(e)}"
        except Exception as e:
            logger.exception(f"查询大盘指数时发生错误: {e}")
            return f"❌ 查询失败: {str(e)}"
    
    async def _resolve_stock_code(self, stock_input: str) -> Tuple[str, str]:
        """将股票名称或代码转换为 ts_code 和股票名称
        
        Returns:
            tuple: (ts_code, stock_name) 或 (None, None)
        """
        if not stock_input:
            return None, None
        
        if stock_input in INDEX_MAP:
            return INDEX_MAP[stock_input], stock_input
        
        if '.' in stock_input and len(stock_input.split('.')) == 2:
            code, market = stock_input.split('.')
            market = market.upper()
            if market in ['SH', 'SZ', 'HK']:
                return f"{code}.{market}", None
            return stock_input, None
        
        if stock_input.isdigit():
            if len(stock_input) == 6:
                if stock_input.startswith('6'):
                    ts_code = f"{stock_input}.SH"
                else:
                    ts_code = f"{stock_input}.SZ"
                # 尝试获取股票名称
                try:
                    pro = self._get_pro_api()
                    df = pro.query('stock_basic', exchange='', list_status='L', fields='ts_code,name')
                    if df is not None and not df.empty:
                        stock_data = df[df['ts_code'] == ts_code]
                        if not stock_data.empty:
                            stock_name = stock_data.iloc[0]['name']
                            logger.info(f"🔍 通过代码获取股票名称: {ts_code} -> {stock_name}")
                            return ts_code, stock_name
                except Exception as e:
                    logger.error(f"获取股票名称失败: {e}")
                return ts_code, None
            elif len(stock_input) == 5:
                return f"{stock_input}.HK", None
        
        try:
            pro = self._get_pro_api()
            df = pro.query('stock_basic', exchange='', list_status='L', fields='ts_code,symbol,name')
            
            if df is not None and not df.empty:
                exact_match = df[df['symbol'] == stock_input]
                if not exact_match.empty:
                    row = exact_match.iloc[0]
                    logger.info(f"🔍 精确匹配股票代码: {stock_input} -> {row['ts_code']}")
                    return row['ts_code'], row['name']
                
                name_match = df[df['name'] == stock_input]
                if not name_match.empty:
                    row = name_match.iloc[0]
                    logger.info(f"🔍 名称匹配股票: {stock_input} -> {row['ts_code']} ({row['name']})")
                    return row['ts_code'], row['name']
                
                partial_match = df[df['name'].str.contains(stock_input, na=False)]
                if not partial_match.empty:
                    row = partial_match.iloc[0]
                    logger.info(f"🔍 模糊匹配股票: {stock_input} -> {row['ts_code']} ({row['name']})")
                    return row['ts_code'], row['name']
                
                logger.warning(f"🔍 未找到股票: {stock_input}")
        except Exception as e:
            logger.error(f"查询股票代码失败: {e}")
        
        return None, None
    
    async def _handle_query_price(self, stock_input: str) -> str:
        try:
            ts_code, stock_name = await self._resolve_stock_code(stock_input)
            
            if ts_code is None:
                return f"❌ 未找到股票: {stock_input}，请检查股票代码或名称是否正确"
            
            if ts_code in INDEX_MAP.values():
                return await self._handle_query_index(stock_input)
            
            # 判断是否在交易时段
            now = datetime.now()
            is_trading_hours = now.weekday() < 5 and (
                (9 <= now.hour < 11 and now.minute >= 30) or 
                (13 <= now.hour < 15) or 
                (now.hour == 11 and now.minute <= 30)
            )
            
            # 优先使用腾讯财经接口获取实时数据
            realtime_data = self._get_realtime_tencent(ts_code)
            
            if realtime_data is not None:
                # 使用腾讯财经接口的实时数据
                logger.info(f"📊 使用腾讯财经接口的实时数据")
                
                price = realtime_data['close']
                change_pct = realtime_data['pct_chg']
                pre_close = realtime_data['pre_close']
                volume = realtime_data['vol']
                amount = realtime_data['amount']
                
                if stock_name is None:
                    stock_name = realtime_data['name'] or ts_code.split('.')[0]
                
                status_hint = " 🟢 交易中" if is_trading_hours else " ⚠️ 已收盘"
                
                result = f"📈 {stock_name}（{ts_code.split('.')[0]}）\n"
                result += f"💰 现价: ¥{price:.2f}"
                
                if change_pct > 0:
                    result += f" 🔴+{change_pct:.2f}%"
                elif change_pct < 0:
                    result += f" 🟢{change_pct:.2f}%"
                else:
                    result += f" ⚪{change_pct:.2f}%"
                
                result += status_hint
                
                if pre_close:
                    result += f"\n📊 昨收: ¥{pre_close:.2f}"
                if volume:
                    result += f" | 成交量: {volume/10000:.1f}万手"
                if amount:
                    result += f" | 成交额: {amount/10000:.1f}亿元"
                
                # 添加估值指标
                if realtime_data['pe_ttm'] > 0:
                    result += f"\n📊 市盈率(TTM): {realtime_data['pe_ttm']:.2f}"
                if realtime_data['pb'] > 0:
                    result += f" | 市净率: {realtime_data['pb']:.2f}"
                if realtime_data['total_mv'] > 0:
                    result += f" | 总市值: {realtime_data['total_mv']:.1f}亿元"
                
                return result
            
            # 腾讯财经接口失败，使用 Tushare 历史数据
            logger.info(f"📊 腾讯财经接口失败，使用 Tushare 历史数据")
            
            pro = self._get_pro_api()
            
            is_hk = ts_code.endswith('.HK')
            is_us = not ts_code.endswith('.SH') and not ts_code.endswith('.SZ') and not ts_code.endswith('.HK')
            
            if is_hk or is_us:
                return f"❌ 暂不支持港股/美股查询，当前仅支持 A 股查询"
            
            latest_trade_date = self._get_latest_trade_date(pro)
            
            df = None
            
            # 如果在交易时段，优先查询当天的数据
            if is_trading_hours:
                today = datetime.now().strftime('%Y%m%d')
                logger.info(f"📊 在交易时段，尝试查询当天数据: {today}")
                df = pro.daily(ts_code=ts_code, trade_date=today)
                
                if df is not None and not df.empty:
                    logger.info(f"📊 当天数据获取成功")
                else:
                    logger.info(f"📊 当天数据暂无，尝试查询最近交易日")
            
            # 如果当天数据为空，尝试用最近交易日查询
            if df is None or df.empty:
                if latest_trade_date:
                    df = pro.daily(ts_code=ts_code, trade_date=latest_trade_date)
            
            # 如果查询不到数据，就查询最近30天的数据
            if df is None or df.empty:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"📊 查询不到数据，改查 {start_date} - {end_date}")
                df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                logger.warning(f"📊 股票 {ts_code} 暂无数据")
                return f"❌ 股票 {ts_code} 暂无数据"
            
            latest = df.iloc[0]
            
            logger.info(f"📊 获取到数据，交易日: {latest['trade_date']}")
            
            price = float(latest['close'])
            change_pct = float(latest['pct_chg']) if 'pct_chg' in latest else None
            pre_close = float(latest['pre_close']) if 'pre_close' in latest else None
            volume = float(latest['vol']) if 'vol' in latest else None
            amount = float(latest['amount']) if 'amount' in latest else None
            trade_date = latest['trade_date']
            
            if stock_name is None:
                stock_name = ts_code.split('.')[0]
            
            status_hint = " 🟢 交易中" if is_trading_hours else " ⚠️ 已收盘"
            
            result = f"📈 {stock_name}（{ts_code.split('.')[0]}）\n"
            result += f"📅 交易日: {trade_date}\n"
            result += f"💰 收盘价: ¥{price:.2f}"
            
            if change_pct is not None:
                if change_pct > 0:
                    result += f" 🔴+{change_pct:.2f}%"
                elif change_pct < 0:
                    result += f" 🟢{change_pct:.2f}%"
                else:
                    result += f" ⚪{change_pct:.2f}%"
            
            result += status_hint
            
            if pre_close:
                result += f"\n📊 昨收: ¥{pre_close:.2f}"
            if volume:
                result += f" | 成交量: {volume/10000:.1f}万手"
            if amount:
                result += f" | 成交额: {amount/10000:.1f}万"
            
            logger.info(f"✅ 股票查询成功: {stock_name}")
            return result
            
        except ValueError as e:
            logger.error(f"❌ ValueError: {e}")
            return f"❌ {str(e)}"
        except Exception as e:
            logger.exception(f"查询股价时发生错误 {stock_input}: {e}")
            return f"❌ 查询失败: {str(e)}"
    
    async def _handle_query_kline(self, stock_input: str, period: str) -> str:
        if not HAS_MATPLOTLIB:
            return "❌ 无法生成K线图：缺少 matplotlib 库，请运行 pip install matplotlib 安装"
        
        try:
            ts_code, stock_name = await self._resolve_stock_code(stock_input)
            
            if ts_code is None:
                return f"❌ 未找到股票: {stock_input}，请检查股票代码或名称是否正确"
            
            pro = self._get_pro_api()
            
            is_index = ts_code in INDEX_MAP.values()
            
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            
            if is_index:
                if period == 'day':
                    df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                else:
                    df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            else:
                is_hk = ts_code.endswith('.HK')
                is_us = not ts_code.endswith('.SH') and not ts_code.endswith('.SZ') and not ts_code.endswith('.HK')
                
                if is_hk or is_us:
                    return f"❌ 暂不支持港股/美股K线查询，当前仅支持 A 股查询"
                
                if period == 'day':
                    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                elif period == 'week':
                    df = pro.weekly(ts_code=ts_code, start_date=start_date, end_date=end_date)
                elif period == 'month':
                    df = pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date)
                else:
                    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                return f"❌ 股票 {ts_code} 暂无K线数据"
            
            df = df.sort_values('trade_date')
            
            if stock_name is None:
                stock_name = ts_code.split('.')[0]
            
            output_dir = Path.cwd() / "output" / "kline"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{stock_name}_{period}_kline.png"
            
            plt.figure(figsize=(12, 6))
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            
            dates = range(len(df))
            plt.plot(dates, df['close'].values, label='收盘价', linewidth=1.5)
            plt.fill_between(dates, df['low'].values, df['high'].values, alpha=0.3, label='波动区间')
            
            period_names = {'day': '日K', 'week': '周K', 'month': '月K'}
            plt.title(f"{stock_name} ({ts_code}) {period_names.get(period, '日K')}线图")
            plt.xlabel('交易日')
            plt.ylabel('价格 (元)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            tick_step = max(1, len(df) // 10)
            tick_positions = range(0, len(df), tick_step)
            tick_labels = [df['trade_date'].iloc[i] for i in tick_positions]
            plt.xticks(tick_positions, tick_labels, rotation=45)
            
            plt.tight_layout()
            plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
            plt.close()
            
            latest_price = float(df['close'].iloc[-1])
            latest_date = df['trade_date'].iloc[-1]
            
            result = f"📊 {stock_name}（{ts_code.split('.')[0]}）{period_names.get(period, '日K')}线图已生成\n"
            result += f"📅 最新交易日: {latest_date}\n"
            result += f"💰 最新收盘价: ¥{latest_price:.2f}\n"
            result += f"📁 保存位置: {output_path}"
            
            return result
            
        except ValueError as e:
            return f"❌ {str(e)}"
        except Exception as e:
            logger.exception(f"生成K线图时发生错误 {stock_input}: {e}")
            return f"❌ K线图生成失败: {str(e)}"
