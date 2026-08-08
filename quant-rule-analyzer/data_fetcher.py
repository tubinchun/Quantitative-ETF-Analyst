#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易数据获取模块
基于 akshare 免费开源库，为 quant-rule-analyzer 技能集提供实时市场数据获取能力。

数据源：
- ETF历史K线: ak.fund_etf_hist_em()  (东方财富)
- ETF最新净值: ak.fund_etf_spot_ths() (同花顺)
- 全球财经新闻: ak.stock_info_global_em() (东方财富)
- ETF份额规模: ak.fund_etf_scale_sse/szse() (交易所)

用法:
    from data_fetcher import QuantDataFetcher
    fetcher = QuantDataFetcher()
    data = fetcher.fetch_etf_full_data('159770')
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

import pandas as pd
import numpy as np
import requests

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


# ============================================================
# 代理绕过工具
# ============================================================
def _create_direct_session() -> requests.Session:
    """创建绕过系统代理的requests session"""
    session = requests.Session()
    session.trust_env = False
    session.proxies = {}
    return session


@contextmanager
def _bypass_proxy():
    """临时绕过系统代理的上下文管理器，用于akshare调用"""
    original_init = requests.Session.__init__

    def patched_init(self):
        original_init(self)
        self.trust_env = False
        self.proxies = {}

    requests.Session.__init__ = patched_init
    try:
        yield
    finally:
        requests.Session.__init__ = original_init


# ============================================================
# 缓存管理
# ============================================================
class DataCache:
    """简单的文件缓存，避免重复请求"""

    def __init__(self, cache_dir='reports/.cache', ttl_seconds=3600):
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, key):
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f'{key_hash}.json')

    def get(self, key):
        path = self._cache_path(key)
        if not os.path.exists(path):
            return None
        mtime = os.path.getmtime(path)
        if time.time() - mtime > self.ttl:
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def set(self, key, value):
        path = self._cache_path(key)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, default=str)
        except Exception:
            pass


# ============================================================
# 技术指标计算
# ============================================================
class TechnicalIndicator:
    """基于K线数据计算V9.3策略所需的技术指标"""

    @staticmethod
    def calc_rsi(closes: List[float], period: int = 14) -> float:
        """计算RSI(14)"""
        if len(closes) < period + 1:
            return 50.0
        closes_arr = np.array(closes, dtype=float)
        deltas = np.diff(closes_arr)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi), 2)

    @staticmethod
    def calc_ma(closes: List[float], period: int = 20) -> float:
        """计算移动平均线"""
        if len(closes) < period:
            return float(closes[-1]) if closes else 0.0
        return round(float(np.mean(closes[-period:])), 4)

    @staticmethod
    def calc_bias(current_price: float, ma_value: float) -> float:
        """计算乖离率"""
        if ma_value == 0:
            return 0.0
        return round(((current_price - ma_value) / ma_value) * 100, 2)

    @staticmethod
    def calc_drawback(high: float, current: float) -> float:
        """计算回撤幅度（百分比，正值表示回撤）"""
        if high == 0:
            return 0.0
        return round(((high - current) / high) * 100, 2)

    @staticmethod
    def calc_volume_ratio(volumes: List[float]) -> float:
        """计算量比（当日成交量 / 近5日均量）"""
        if len(volumes) < 6:
            return 1.0
        avg_vol_5 = np.mean(volumes[-6:-1])
        if avg_vol_5 == 0:
            return 1.0
        return round(float(volumes[-1] / avg_vol_5), 2)

    @staticmethod
    def analyze_trend(closes: List[float]) -> Dict[str, Any]:
        """综合趋势分析"""
        if len(closes) < 20:
            return {'trend': '数据不足', 'ma20': None, 'bias': None, 'rsi': None}

        current = float(closes[-1])
        ma5 = TechnicalIndicator.calc_ma(closes, 5)
        ma20 = TechnicalIndicator.calc_ma(closes, 20)
        rsi = TechnicalIndicator.calc_rsi(closes, 14)
        bias = TechnicalIndicator.calc_bias(current, ma20)
        high_20 = float(max(closes[-20:]))
        drawback = TechnicalIndicator.calc_drawback(high_20, current)

        # 近3日/5日涨幅
        gain_3d = round(((closes[-1] - closes[-4]) / closes[-4]) * 100, 2) if len(closes) >= 4 else 0
        gain_5d = round(((closes[-1] - closes[-6]) / closes[-6]) * 100, 2) if len(closes) >= 6 else 0

        # F90分类器判定
        f90_class = '观望区'
        f90_reason = ''
        if current > ma20 * 1.05 or gain_3d > 5 or gain_5d > 8:
            f90_class = '追涨区'
            f90_reason = '正乖离>5%或短期涨幅过大'
        elif current < ma20 * 0.97 or gain_5d < -3 or rsi < 45:
            f90_class = '抄底区'
            f90_reason = '负乖离>3%或近5日跌幅>3%或RSI<45'

        # F73红线检测
        f73_violations = []
        if gain_3d > 5:
            f73_violations.append(f'红线二: 近3日涨幅{gain_3d}%>5%')
        if bias > 5:
            f73_violations.append(f'红线三(不可豁免): 乖离率{bias}%>+5%')

        return {
            'current_price': current,
            'ma5': ma5,
            'ma20': ma20,
            'bias_ma20': bias,
            'rsi14': rsi,
            'drawback_20d': drawback,
            'gain_3d': gain_3d,
            'gain_5d': gain_5d,
            'high_20d': high_20,
            'f90_classification': f90_class,
            'f90_reason': f90_reason,
            'f73_violations': f73_violations,
            'is_oversold': rsi < 35,
            'is_overbought': rsi > 70,
        }


# ============================================================
# 数据获取主类
# ============================================================
class QuantDataFetcher:
    """量化交易数据获取器"""

    # 常见ETF代码与名称映射
    ETF_MAPPING = {
        '159770': '机器人ETF天弘',
        '560770': '机器人ETF招商',
        '159039': '机器人ETF华安',
        '512010': '医药ETF',
        '159992': '创新药ETF',
        '515170': '白酒ETF',
        '512690': '酒ETF',
        '512480': '半导体ETF',
        '588000': '科创50ETF',
        '510300': '沪深300ETF',
        '510050': '上证50ETF',
        '510500': '中证500ETF',
        '159915': '创业板ETF',
        '512660': '军工ETF',
        '515790': '光伏ETF',
        '516160': '新能源ETF',
        '512800': '银行ETF',
        '518880': '黄金ETF',
        '511260': '十年国债ETF',
    }

    def __init__(self, cache_ttl=3600):
        self.cache = DataCache(ttl_seconds=cache_ttl)
        self.available = AKSHARE_AVAILABLE
        if not self.available:
            print('警告: akshare 未安装，数据获取功能不可用。请运行: pip install akshare')

    def _safe_call(self, func, *args, **kwargs):
        """安全的API调用，带重试和延迟，自动绕过系统代理"""
        max_retries = 3
        for i in range(max_retries):
            try:
                with _bypass_proxy():
                    result = func(*args, **kwargs)
                time.sleep(0.8)
                return result
            except Exception as e:
                if i < max_retries - 1:
                    wait = (i + 1) * 2
                    print(f'  [重试 {i+1}/{max_retries}] {func.__name__} 失败，{wait}秒后重试: {str(e)[:80]}')
                    time.sleep(wait)
                else:
                    print(f'  [API调用失败] {func.__name__}: {str(e)[:100]}')
                    return None

    # ========================================
    # 1. ETF行情数据
    # ========================================
    def get_etf_history(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        """获取ETF历史K线数据（新浪API优先，akshare备用）"""
        if not self.available:
            return None

        cache_key = f'etf_hist_{symbol}_{days}'
        cached = self.cache.get(cache_key)
        if cached:
            return pd.DataFrame(cached)

        # 方案1: 新浪财经API（最稳定）
        df = self._fetch_kline_sina(symbol, days)

        # 方案2: akshare 东方财富接口（备用）
        if df is None or df.empty:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days + 30)).strftime('%Y%m%d')
            df = self._safe_call(
                ak.fund_etf_hist_em,
                symbol=symbol, period='daily',
                start_date=start_date, end_date=end_date, adjust='qfq'
            )

        if df is None or df.empty:
            return None

        # 统一列名
        if 'day' in df.columns:
            df = df.rename(columns={
                'day': '日期', 'open': '开盘', 'high': '最高',
                'low': '最低', 'close': '收盘', 'volume': '成交量'
            })

        # 计算涨跌幅（如果不存在）
        if '涨跌幅' not in df.columns and '收盘' in df.columns:
            closes = df['收盘'].astype(float)
            df['涨跌幅'] = (closes.pct_change() * 100).round(2).fillna(0)

        # 缓存
        self.cache.set(cache_key, df.to_dict('records'))
        return df

    def _fetch_kline_sina(self, symbol: str, datalen: int = 90) -> Optional[pd.DataFrame]:
        """通过新浪财经API获取K线数据（最稳定的数据源，绕过系统代理）"""
        session = _create_direct_session()

        if symbol.startswith('5'):
            sina_symbol = f'sh{symbol}'
        else:
            sina_symbol = f'sz{symbol}'

        url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {
            'symbol': sina_symbol,
            'scale': '240',
            'ma': 'no',
            'datalen': str(datalen),
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://finance.sina.com.cn/',
        }

        try:
            resp = session.get(url, params=params, headers=headers, timeout=15)
            import json as json_lib
            data = json_lib.loads(resp.text)
            if not data:
                return None
            df = pd.DataFrame(data)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            return df
        except Exception as e:
            print(f'  [新浪API失败] {symbol}: {str(e)[:80]}')
            return None

    def get_etf_latest_quote(self, symbol: str) -> Optional[Dict]:
        """获取ETF最新净值/行情（同花顺优先，东方财富备用）"""
        if not self.available:
            return None

        cache_key = f'etf_quote_{symbol}'
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        df = self._safe_call(ak.fund_etf_spot_ths)
        if df is not None and not df.empty:
            row = df[df['基金代码'] == symbol]
            if not row.empty:
                record = row.iloc[0].to_dict()
                result = {
                    'symbol': symbol,
                    'name': record.get('基金名称', ''),
                    'unit_nav': float(record.get('当前-单位净值', 0)),
                    'accum_nav': float(record.get('当前-累计净值', 0)),
                    'prev_nav': float(record.get('前一日-单位净值', 0)),
                    'growth_value': float(record.get('增长值', 0)),
                    'growth_rate': float(record.get('增长率', 0)),
                    'latest_trade_date': str(record.get('最新-交易日', '')),
                    'fund_type': record.get('基金类型', ''),
                    'query_date': str(record.get('查询日期', '')),
                }
                self.cache.set(cache_key, result)
                return result

        # 东方财富备用
        em_data = self._fetch_etf_quote_em(symbol)
        if em_data:
            self.cache.set(cache_key, em_data)
            return em_data

        return None

    def _fetch_etf_quote_em(self, symbol: str) -> Optional[Dict]:
        """通过东方财富API获取单只ETF行情"""
        session = _create_direct_session()
        url = 'https://88.push2.eastmoney.com/api/qt/clist/get'
        params = {
            'pn': 1, 'pz': 2000, 'po': 1, 'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2, 'invt': 2,
            'wbp2u': '|0|0|0|web',
            'fid': 'f12',
            'fs': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024,b:MK0827',
            'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f8,f15,f16,f17,f18',
        }
        try:
            resp = session.get(url, params=params, timeout=15)
            data = resp.json()
            items = data.get('data', {}).get('diff', [])
            for item in items:
                if str(item.get('f12', '')) == symbol:
                    return {
                        'symbol': symbol,
                        'name': item.get('f14', ''),
                        'unit_nav': item.get('f2', 0),
                        'growth_rate': item.get('f3', 0),
                        'growth_value': item.get('f4', 0),
                        'high': item.get('f15', 0),
                        'low': item.get('f16', 0),
                        'open': item.get('f17', 0),
                        'prev_close': item.get('f18', 0),
                        'source': 'eastmoney',
                    }
        except Exception as e:
            print(f'  [东方财富单ETF查询失败] {symbol}: {str(e)[:80]}')
        return None

    def get_etf_list(self) -> Optional[pd.DataFrame]:
        """获取全市场ETF列表（同花顺优先，东方财富备用）"""
        if not self.available:
            return None

        cache_key = 'etf_list_all'
        cached = self.cache.get(cache_key)
        if cached:
            return pd.DataFrame(cached)

        df = self._safe_call(ak.fund_etf_spot_ths)
        if df is not None and not df.empty:
            self.cache.set(cache_key, df.to_dict('records'))
            return df

        # 东方财富备用
        print('  同花顺接口不可用，尝试东方财富备用接口...')
        df = self._fetch_etf_list_em()
        if df is not None and not df.empty:
            self.cache.set(cache_key, df.to_dict('records'))
            return df

        return None

    def _fetch_etf_list_em(self) -> Optional[pd.DataFrame]:
        """通过东方财富API获取全市场ETF列表"""
        session = _create_direct_session()
        all_items = []
        page_size = 2000

        for page in range(1, 5):
            url = 'https://88.push2.eastmoney.com/api/qt/clist/get'
            params = {
                'pn': page, 'pz': page_size, 'po': 1, 'np': 1,
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': 2, 'invt': 2,
                'wbp2u': '|0|0|0|web',
                'fid': 'f12',
                'fs': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024,b:MK0827',
                'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f8,f15,f16,f17,f18',
            }
            try:
                resp = session.get(url, params=params, timeout=15)
                data = resp.json()
                items = data.get('data', {}).get('diff', [])
                if not items:
                    break
                all_items.extend(items)
                total = data.get('data', {}).get('total', 0)
                if len(all_items) >= total:
                    break
                time.sleep(0.5)
            except Exception as e:
                print(f'  [东方财富ETF列表第{page}页失败]: {str(e)[:80]}')
                break

        if not all_items:
            return None

        records = []
        for item in all_items:
            records.append({
                '基金代码': str(item.get('f12', '')),
                '基金名称': str(item.get('f14', '')),
                '当前-单位净值': item.get('f2', 0),
                '增长率': item.get('f3', 0),
                '增长值': item.get('f4', 0),
                '最高': item.get('f15', 0),
                '最低': item.get('f16', 0),
                '今开': item.get('f17', 0),
                '昨收': item.get('f18', 0),
                '振幅': item.get('f7', 0),
                '换手率': item.get('f8', 0),
                '最新-交易日': datetime.now().strftime('%Y-%m-%d'),
                '基金类型': 'ETF',
                '查询日期': datetime.now().strftime('%Y-%m-%d'),
            })

        df = pd.DataFrame(records)
        print(f'  [东方财富] 获取到 {len(df)} 只ETF')
        return df

    # ========================================
    # 2. 技术指标分析
    # ========================================
    def get_technical_analysis(self, symbol: str) -> Dict:
        """获取ETF的完整技术分析（基于V9.3策略指标）"""
        hist = self.get_etf_history(symbol, days=90)
        if hist is None or len(hist) < 20:
            return {'error': f'无法获取{symbol}的足够历史数据'}

        closes = hist['收盘'].astype(float).tolist()
        volumes = hist['成交量'].astype(float).tolist() if '成交量' in hist.columns else []

        trend = TechnicalIndicator.analyze_trend(closes)

        result = {
            'symbol': symbol,
            'name': self.ETF_MAPPING.get(symbol, symbol),
            'data_date': str(hist['日期'].iloc[-1]) if '日期' in hist.columns else '',
            'data_points': len(closes),
            'technical': trend,
            'volume_ratio': TechnicalIndicator.calc_volume_ratio(volumes) if volumes else None,
            'latest_bar': {
                'date': str(hist['日期'].iloc[-1]),
                'open': float(hist['开盘'].iloc[-1]),
                'close': float(hist['收盘'].iloc[-1]),
                'high': float(hist['最高'].iloc[-1]),
                'low': float(hist['最低'].iloc[-1]),
                'volume': float(hist['成交量'].iloc[-1]) if '成交量' in hist.columns else 0,
                'amount': float(hist['成交额'].iloc[-1]) if '成交额' in hist.columns else 0,
                'change_pct': float(hist['涨跌幅'].iloc[-1]) if '涨跌幅' in hist.columns else 0,
            }
        }

        # 近5日走势
        if len(hist) >= 5:
            result['recent_5d'] = []
            for _, row in hist.tail(5).iterrows():
                result['recent_5d'].append({
                    'date': str(row['日期']),
                    'close': float(row['收盘']),
                    'change_pct': float(row['涨跌幅']) if '涨跌幅' in row else 0,
                    'volume': float(row['成交量']) if '成交量' in row else 0,
                })

        return result

    # ========================================
    # 3. 新闻与事件数据
    # ========================================
    def get_latest_news(self, count: int = 50) -> List[Dict]:
        """获取最新全球财经新闻"""
        if not self.available:
            return []

        cache_key = f'global_news_{count}'
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        df = self._safe_call(ak.stock_info_global_em)
        if df is None or df.empty:
            return []

        news_list = []
        for _, row in df.head(count).iterrows():
            news_list.append({
                'title': str(row.get('标题', '')),
                'summary': str(row.get('摘要', '')),
                'time': str(row.get('发布时间', '')),
                'url': str(row.get('链接', '')),
            })

        self.cache.set(cache_key, news_list)
        return news_list

    def get_sector_news(self, keywords: List[str], count: int = 20) -> List[Dict]:
        """按关键词筛选板块相关新闻"""
        all_news = self.get_latest_news(200)
        if not all_news:
            return []

        filtered = []
        for news in all_news:
            text = news['title'] + news['summary']
            if any(kw in text for kw in keywords):
                filtered.append(news)
                if len(filtered) >= count:
                    break

        return filtered

    # ========================================
    # 4. 综合数据获取
    # ========================================
    def fetch_etf_full_data(self, symbol: str, sector_keywords: List[str] = None) -> Dict:
        """一次性获取ETF的全部数据（行情+技术+新闻）"""
        print(f'正在获取 {symbol} ({self.ETF_MAPPING.get(symbol, "")}) 的最新数据...')

        result = {
            'symbol': symbol,
            'name': self.ETF_MAPPING.get(symbol, symbol),
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_source': 'akshare (东方财富/同花顺)',
        }

        # 1. 最新行情
        quote = self.get_etf_latest_quote(symbol)
        result['latest_quote'] = quote

        # 2. 技术分析
        tech = self.get_technical_analysis(symbol)
        result['technical_analysis'] = tech

        # 3. 板块相关新闻
        if sector_keywords:
            news = self.get_sector_news(sector_keywords, count=10)
            result['sector_news'] = news
            result['news_count'] = len(news)

        return result

    def fetch_sector_data(self, sector_name: str, etf_codes: List[str],
                          keywords: List[str] = None) -> Dict:
        """获取板块级数据（多只ETF + 新闻）"""
        print(f'\n=== 获取板块数据: {sector_name} ===')

        result = {
            'sector_name': sector_name,
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'etfs': [],
            'sector_news': [],
        }

        # 获取每只ETF数据
        for code in etf_codes:
            etf_data = self.fetch_etf_full_data(code, keywords)
            result['etfs'].append(etf_data)
            time.sleep(0.5)  # 避免请求过快

        # 板块新闻
        if keywords:
            result['sector_news'] = self.get_sector_news(keywords, count=15)

        return result

    def fetch_multi_sectors(self, sector_configs: List[Dict]) -> Dict:
        """批量获取多板块数据
        sector_configs: [{'sector_name': '机器人', 'etf_codes': ['159770','560770'], 'keywords': ['机器人','人形机器人']}, ...]
        """
        print(f'开始获取 {len(sector_configs)} 个板块的最新数据...')
        result = {
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_source': 'akshare (东方财富/同花顺)',
            'sectors': []
        }

        for config in sector_configs:
            sector_data = self.fetch_sector_data(
                config['sector_name'],
                config.get('etf_codes', []),
                config.get('keywords', [])
            )
            result['sectors'].append(sector_data)

        print(f'\n数据获取完成，共 {len(result["sectors"])} 个板块')
        return result


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行测试入口"""
    import sys

    fetcher = QuantDataFetcher(cache_ttl=300)  # 5分钟缓存

    if len(sys.argv) < 2:
        print('用法:')
        print('  python data_fetcher.py etf <代码>          # 获取单只ETF数据')
        print('  python data_fetcher.py news [数量]         # 获取最新新闻')
        print('  python data_fetcher.py sector <板块名>      # 获取板块数据')
        print('  python data_fetcher.py demo                # 演示三大板块')
        return

    cmd = sys.argv[1]

    if cmd == 'etf':
        symbol = sys.argv[2] if len(sys.argv) > 2 else '159770'
        data = fetcher.fetch_etf_full_data(symbol, ['机器人', '人形机器人'])
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    elif cmd == 'news':
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        news = fetcher.get_latest_news(count)
        print(f'获取到 {len(news)} 条新闻:')
        for n in news[:10]:
            print(f'  [{n["time"]}] {n["title"]}')

    elif cmd == 'demo':
        # 演示：三大板块数据获取
        configs = [
            {
                'sector_name': '机器人',
                'etf_codes': ['159770', '560770', '159039'],
                'keywords': ['机器人', '人形机器人', '宇树', '特斯拉']
            },
            {
                'sector_name': '创新药',
                'etf_codes': ['159992', '512010'],
                'keywords': ['创新药', '医药', '生物', '药品']
            },
            {
                'sector_name': '白酒',
                'etf_codes': ['515170', '512690'],
                'keywords': ['白酒', '茅台', '五粮液', '酒类']
            },
        ]

        data = fetcher.fetch_multi_sectors(configs)

        # 保存到JSON
        output_file = 'reports/latest_market_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f'\n数据已保存到: {output_file}')

        # 打印摘要
        print('\n=== 数据摘要 ===')
        for sector in data['sectors']:
            print(f'\n【{sector["sector_name"]}】')
            for etf in sector['etfs']:
                tech = etf.get('technical_analysis', {})
                latest = tech.get('latest_bar', {})
                ta = tech.get('technical', {})
                print(f'  {etf["symbol"]} {etf["name"]}: '
                      f'收盘{latest.get("close", "—")} '
                      f'涨跌{latest.get("change_pct", "—")}% '
                      f'RSI={ta.get("rsi14", "—")} '
                      f'F90={ta.get("f90_classification", "—")} '
                      f'乖离={ta.get("bias_ma20", "—")}%')
            print(f'  相关新闻: {len(sector.get("sector_news", []))} 条')


if __name__ == '__main__':
    main()
