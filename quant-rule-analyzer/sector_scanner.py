#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
板块全盘扫描模块
自动扫描全市场ETF，按板块分类，按V9.3规则筛选有交易机会的板块。
支持用户指定板块名称进行特定分析。

用法:
    # 全盘扫描所有板块（自动筛选有交易机会的板块）
    python sector_scanner.py scan

    # 全盘扫描，显示所有板块（不筛选）
    python sector_scanner.py scan --all

    # 分析指定板块
    python sector_scanner.py analyze 机器人 创新药 白酒

    # 扫描并自动生成报告
    python sector_scanner.py scan --report

    # 分析指定板块并生成报告
    python sector_scanner.py analyze 机器人 创新药 --report
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加技能目录到路径
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

from data_fetcher import QuantDataFetcher, TechnicalIndicator


# ============================================================
# 板块分类映射表（按优先级排序，避免重叠）
# ============================================================
SECTOR_KEYWORD_MAP = [
    # 科技类
    {'sector': '机器人', 'keywords': ['机器人'], 'etf_codes': ['159770', '560770', '159039']},
    {'sector': '人工智能', 'keywords': ['人工智能', 'AI', '智算'], 'etf_codes': []},
    {'sector': '半导体', 'keywords': ['半导体', '芯片'], 'etf_codes': ['512480', '159995']},
    {'sector': '科技', 'keywords': ['科技'], 'etf_codes': []},
    {'sector': '通信', 'keywords': ['通信', '5G'], 'etf_codes': []},
    {'sector': '计算机', 'keywords': ['计算机', '软件', '云计算'], 'etf_codes': []},
    # 医药类
    {'sector': '创新药', 'keywords': ['创新药'], 'etf_codes': ['159992']},
    {'sector': '医药', 'keywords': ['医药', '医疗', '生物'], 'etf_codes': ['512010']},
    # 消费类
    {'sector': '白酒', 'keywords': ['酒'], 'etf_codes': ['515170', '512690']},
    {'sector': '食品饮料', 'keywords': ['食品', '饮料'], 'etf_codes': ['515710']},
    {'sector': '消费', 'keywords': ['消费'], 'etf_codes': []},
    {'sector': '家电', 'keywords': ['家电'], 'etf_codes': []},
    {'sector': '旅游', 'keywords': ['旅游', '出行'], 'etf_codes': []},
    # 新能源类
    {'sector': '光伏', 'keywords': ['光伏'], 'etf_codes': ['515790']},
    {'sector': '新能源', 'keywords': ['新能源'], 'etf_codes': ['516160']},
    {'sector': '新能源车', 'keywords': ['汽车', '车联网', '智能车'], 'etf_codes': []},
    {'sector': '电池', 'keywords': ['电池', '锂电池'], 'etf_codes': []},
    # 金融类
    {'sector': '银行', 'keywords': ['银行'], 'etf_codes': ['512800']},
    {'sector': '证券', 'keywords': ['证券', '券商'], 'etf_codes': []},
    {'sector': '金融', 'keywords': ['金融'], 'etf_codes': []},
    # 周期类
    {'sector': '军工', 'keywords': ['军工', '国防'], 'etf_codes': ['512660']},
    {'sector': '黄金', 'keywords': ['黄金'], 'etf_codes': ['518880']},
    {'sector': '有色金属', 'keywords': ['有色', '金属'], 'etf_codes': []},
    {'sector': '煤炭', 'keywords': ['煤炭', '能源'], 'etf_codes': []},
    {'sector': '钢铁', 'keywords': ['钢铁'], 'etf_codes': []},
    {'sector': '电力', 'keywords': ['电力'], 'etf_codes': []},
    {'sector': '基建', 'keywords': ['基建', '工程'], 'etf_codes': []},
    {'sector': '房地产', 'keywords': ['房地产', '地产'], 'etf_codes': []},
    # 其他
    {'sector': '央企', 'keywords': ['央企'], 'etf_codes': []},
    {'sector': '红利', 'keywords': ['红利', '股息'], 'etf_codes': []},
    {'sector': '环保', 'keywords': ['环保', '低碳'], 'etf_codes': []},
    {'sector': '传媒', 'keywords': ['传媒', '游戏', '动漫'], 'etf_codes': []},
    {'sector': '农业', 'keywords': ['农业', '种业'], 'etf_codes': []},
    {'sector': '央企科技', 'keywords': ['央企科技'], 'etf_codes': []},
    # 宽基指数
    {'sector': '科创50', 'keywords': ['科创50'], 'etf_codes': ['588000']},
    {'sector': '沪深300', 'keywords': ['沪深300'], 'etf_codes': ['510300']},
    {'sector': '创业板', 'keywords': ['创业板'], 'etf_codes': ['159915']},
    {'sector': '中证500', 'keywords': ['中证500'], 'etf_codes': ['510500']},
    {'sector': '中证1000', 'keywords': ['中证1000'], 'etf_codes': []},
    {'sector': '上证50', 'keywords': ['上证50'], 'etf_codes': ['510050']},
]


# ============================================================
# 板块扫描器
# ============================================================
class SectorScanner:
    """板块全盘扫描器"""

    def __init__(self, cache_ttl=600):
        self.fetcher = QuantDataFetcher(cache_ttl=cache_ttl)
        self.etf_list = None

    def _load_etf_list(self):
        """加载全市场ETF列表"""
        if self.etf_list is not None:
            return self.etf_list

        df = self.fetcher.get_etf_list()
        if df is None or df.empty:
            print('警告: 无法获取ETF列表')
            return pd.DataFrame()

        self.etf_list = df
        return df

    def classify_etfs_by_sector(self) -> Dict[str, List[Dict]]:
        """将全市场ETF按板块分类（失败时回退到预设ETF代码）"""
        import pandas as pd
        df = self._load_etf_list()

        if df is None or df.empty:
            print('ETF列表不可用，使用预设ETF代码进行扫描...')
            return self._classify_from_preset()

        name_col = '基金名称'
        code_col = '基金代码'

        sector_etfs = {}
        matched_codes = set()

        for sector_info in SECTOR_KEYWORD_MAP:
            sector_name = sector_info['sector']
            keywords = sector_info['keywords']

            matched = df[df[name_col].apply(
                lambda x: any(kw in str(x) for kw in keywords) if pd.notna(x) else False
            )]

            if matched.empty:
                continue

            etfs = []
            for _, row in matched.iterrows():
                code = str(row[code_col])
                etfs.append({
                    'code': code,
                    'name': str(row[name_col]),
                    'nav': float(row.get('当前-单位净值', 0)),
                    'growth_rate': float(row.get('增长率', 0)),
                    'trade_date': str(row.get('最新-交易日', '')),
                })
                matched_codes.add(code)

            sector_etfs[sector_name] = etfs

        # 补充预设ETF中未被匹配的板块
        for sector_info in SECTOR_KEYWORD_MAP:
            sector_name = sector_info['sector']
            if sector_name not in sector_etfs and sector_info.get('etf_codes'):
                etfs = []
                for code in sector_info['etf_codes']:
                    etfs.append({
                        'code': code,
                        'name': self.fetcher.ETF_MAPPING.get(code, code),
                        'nav': 0,
                        'growth_rate': 0,
                        'trade_date': '',
                    })
                sector_etfs[sector_name] = etfs

        return sector_etfs

    def _classify_from_preset(self) -> Dict[str, List[Dict]]:
        """使用预设ETF代码构建板块分类"""
        sector_etfs = {}
        for sector_info in SECTOR_KEYWORD_MAP:
            sector_name = sector_info['sector']
            etf_codes = sector_info.get('etf_codes', [])
            if not etf_codes:
                # 无预设代码的板块跳过
                continue
            etfs = []
            for code in etf_codes:
                etfs.append({
                    'code': code,
                    'name': self.fetcher.ETF_MAPPING.get(code, code),
                    'nav': 0,
                    'growth_rate': 0,
                    'trade_date': '',
                })
            sector_etfs[sector_name] = etfs
        return sector_etfs

    def select_representative_etfs(self, sector_name: str, etfs: List[Dict], max_count: int = 3) -> List[str]:
        """为板块选择代表ETF（优先选预定义的，否则选增长率绝对值最大的）"""
        # 查找预定义的ETF代码
        for sector_info in SECTOR_KEYWORD_MAP:
            if sector_info['sector'] == sector_name and sector_info.get('etf_codes'):
                predefined = sector_info['etf_codes']
                available = [e['code'] for e in etfs if e['code'] in predefined]
                if available:
                    return available[:max_count]

        # 没有预定义的，选增长率绝对值最大的
        sorted_etfs = sorted(etfs, key=lambda x: abs(x.get('growth_rate', 0)), reverse=True)
        return [e['code'] for e in sorted_etfs[:max_count]]

    def scan_all_sectors(self, filter_rule=True, max_sectors=10) -> List[Dict]:
        """全盘扫描所有板块，按V9.3规则筛选

        Args:
            filter_rule: 是否按V9.3规则筛选（True=只保留有交易机会的，False=全部）
            max_sectors: 最大返回板块数
        """
        print('=== 开始全盘扫描所有板块 ===')
        sector_etfs = self.classify_etfs_by_sector()
        print(f'共发现 {len(sector_etfs)} 个板块')

        results = []
        for sector_name, etfs in sector_etfs.items():
            rep_codes = self.select_representative_etfs(sector_name, etfs)
            if not rep_codes:
                continue

            print(f'\n扫描板块: {sector_name} (代表ETF: {", ".join(rep_codes)})')

            # 获取第一只代表ETF的技术分析
            tech_data = self.fetcher.get_technical_analysis(rep_codes[0])
            if 'error' in tech_data:
                print(f'  跳过: {tech_data["error"]}')
                continue

            tech = tech_data.get('technical', {})
            f90_class = tech.get('f90_classification', '观望区')

            # 按规则筛选
            if filter_rule:
                # 只保留抄底区和观望区（有交易机会的）
                if f90_class == '追涨区':
                    print(f'  跳过: F90={f90_class}（追涨区不推荐）')
                    continue

            # 获取板块相关新闻
            sector_info = next((s for s in SECTOR_KEYWORD_MAP if s['sector'] == sector_name), {})
            keywords = sector_info.get('keywords', [sector_name])
            news = self.fetcher.get_sector_news(keywords, count=5)

            result = {
                'sector_name': sector_name,
                'sector_id': f'SE{len(results) + 1}',
                'representative_etfs': [f"{e['name']}({e['code']})" for e in etfs if e['code'] in rep_codes],
                'representative_codes': rep_codes,
                'etf_count': len(etfs),
                'technical': tech,
                'f90_classification': f90_class,
                'sector_news': news,
                'market_context': {
                    'july_trend': f"最新交易日{tech_data.get('data_date', '')}收盘{tech.get('current_price', '—')}，"
                                  f"近5日涨幅{tech.get('gain_5d', '—')}%，RSI={tech.get('rsi14', '—')}",
                    'etf_flows': f"板块共{len(etfs)}只ETF",
                    'valuation': '需结合基本面数据',
                    'key_catalysts': [n['title'] for n in news[:3]],
                    'institution_views': '—',
                },
            }
            results.append(result)

            if len(results) >= max_sectors:
                break

        # 按F90分类和RSI排序：抄底区优先
        results.sort(key=lambda x: (
            0 if x['f90_classification'] == '抄底区' else 1,
            x['technical'].get('rsi14', 50)
        ))

        print(f'\n=== 扫描完成，共筛选出 {len(results)} 个板块 ===')
        return results

    def analyze_specific_sectors(self, sector_names: List[str]) -> List[Dict]:
        """分析用户指定的板块"""
        print(f'=== 分析指定板块: {", ".join(sector_names)} ===')
        sector_etfs = self.classify_etfs_by_sector()

        results = []
        for sector_name in sector_names:
            # 模糊匹配板块名
            matched_sector = None
            for s in sector_etfs.keys():
                if sector_name in s or s in sector_name:
                    matched_sector = s
                    break

            if not matched_sector:
                print(f'  未找到板块: {sector_name}，尝试直接用关键词搜索ETF...')
                # 直接用关键词搜索
                matched_sector = sector_name
                sector_etfs[sector_name] = []

            etfs = sector_etfs.get(matched_sector, [])
            rep_codes = self.select_representative_etfs(matched_sector, etfs) if etfs else []

            if not rep_codes:
                # 尝试用板块名作为关键词搜索
                print(f'  板块{matched_sector}无匹配ETF，跳过')
                continue

            print(f'\n分析板块: {matched_sector} (代表ETF: {", ".join(rep_codes)})')

            # 获取技术分析
            tech_data = self.fetcher.get_technical_analysis(rep_codes[0])
            if 'error' in tech_data:
                print(f'  跳过: {tech_data["error"]}')
                continue

            tech = tech_data.get('technical', {})

            # 获取新闻
            sector_info = next((s for s in SECTOR_KEYWORD_MAP if s['sector'] == matched_sector), {})
            keywords = sector_info.get('keywords', [matched_sector])
            news = self.fetcher.get_sector_news(keywords, count=10)

            result = {
                'sector_name': matched_sector,
                'sector_id': f'SE{len(results) + 1}',
                'representative_etfs': [f"{e['name']}({e['code']})" for e in etfs if e['code'] in rep_codes],
                'representative_codes': rep_codes,
                'etf_count': len(etfs),
                'technical': tech,
                'f90_classification': tech.get('f90_classification', '观望区'),
                'sector_news': news,
                'market_context': {
                    'july_trend': f"最新交易日{tech_data.get('data_date', '')}收盘{tech.get('current_price', '—')}，"
                                  f"近5日涨幅{tech.get('gain_5d', '—')}%，RSI={tech.get('rsi14', '—')}",
                    'etf_flows': f"板块共{len(etfs)}只ETF",
                    'valuation': '需结合基本面数据',
                    'key_catalysts': [n['title'] for n in news[:5]],
                    'institution_views': '—',
                },
            }
            results.append(result)

        print(f'\n=== 分析完成，共 {len(results)} 个板块 ===')
        return results

    # ========================================
    # 生成报告JSON
    # ========================================
    def generate_report_json(self, sectors: List[Dict], output_path: str, target_period: str = None):
        """生成符合 generate_sector_report.py 格式的JSON"""
        if not target_period:
            target_period = f"下周（{datetime.now().strftime('%Y-%m-%d')}起）"

        # 为每个板块生成ST和LT评分
        sector_analysis = []
        for s in sectors:
            tech = s.get('technical', {})
            f90 = s.get('f90_classification', '观望区')
            rsi = tech.get('rsi14', 50)
            bias = tech.get('bias_ma20', 0)
            gain_3d = tech.get('gain_3d', 0)
            gain_5d = tech.get('gain_5d', 0)
            drawback = tech.get('drawback_20d', 0)

            # ST五维评分（基于技术指标自动推导）
            s1_score = self._calc_st_s1(rsi, f90)
            s2_score = self._calc_st_s2(s.get('sector_news', []))
            s3_score = self._calc_st_s3(s.get('sector_news', []))
            s4_score = self._calc_st_s4(rsi, bias, gain_3d, gain_5d, f90)
            s5_score = self._calc_st_s5(bias, drawback)

            st_total = round(s1_score * 0.25 + s2_score * 0.20 + s3_score * 0.20 + s4_score * 0.20 + s5_score * 0.15, 2)
            st_af = self._calc_st_af(f90, rsi)
            st_final = round(st_total + st_af, 2)

            # LT六维评分（基于技术指标+新闻自动推导）
            d1_score = self._calc_lt_d1(bias, drawback)
            d2_score = self._calc_lt_d2(s.get('sector_news', []))
            d3_score = 5.0  # 盈利质量需基本面数据，默认中值
            d4_score = self._calc_lt_d4(rsi, f90)
            d5_score = self._calc_lt_d5(s.get('sector_news', []))
            d6_score = self._calc_lt_d6(rsi, bias, f90)

            lt_total = round(d1_score * 0.35 + d2_score * 0.30 + d3_score * 0.15 + d4_score * 0.10 + d5_score * 0.05 + d6_score * 0.05, 2)
            lt_rating = self._lt_rating(lt_total)
            lt_position = self._lt_position(lt_rating)

            # F73红线检测
            f73_violations = tech.get('f73_violations', [])
            f73_check = '安全' if not f73_violations else '；'.join(f73_violations)

            # F86-V2阶段
            if f90 == '抄底区':
                f86_stage = '阶段二待确认（需连续3日不创新低确认止跌）'
            elif f90 == '追涨区':
                f86_stage = '阶段三（趋势已确认，但追涨风险高）'
            else:
                f86_stage = '阶段二/三过渡（趋势形成中）'

            # F92评估
            if f90 == '抄底区' and rsi < 40:
                f92 = '左侧布局（缩量横盘+主力温和流入），+1.5分'
            elif f90 == '观望区':
                f92 = '信号混杂，需Level-2数据确认'
            else:
                f92 = '追涨风险，不建议追高'

            # 执行决策
            if f90 == '抄底区':
                position_rec = '15-20%仓位（抄底区正常配置）'
                priority = '高（抄底区+催化共振）'
            elif f90 == '观望区':
                position_rec = '10-15%仓位（观望区仓位减半）'
                priority = '中（观望区，等趋势确认）'
            else:
                position_rec = '0-5%仓位（追涨区不建议介入）'
                priority = '低（追涨区，F73红线风险）'

            sector_data = {
                'sector_id': s['sector_id'],
                'sector_name': s['sector_name'],
                'representative_etfs': s['representative_etfs'],
                'f90_classification': f90,
                'market_context': s['market_context'],
                'five_dimension_scoring': {
                    'S1_资金面': {'weight': '25%', 'score': s1_score, 'rationale': f'RSI={rsi}，F90={f90}'},
                    'S2_宏观面': {'weight': '20%', 'score': s2_score, 'rationale': f'板块新闻{len(s.get("sector_news", []))}条'},
                    'S3_产业面': {'weight': '20%', 'score': s3_score, 'rationale': f'催化事件{len(s.get("market_context", {}).get("key_catalysts", []))}个'},
                    'S4_技术面': {'weight': '20%', 'score': s4_score, 'rationale': f'RSI={rsi}，乖离率={bias}%，近3日={gain_3d}%'},
                    'S5_风险面': {'weight': '15%', 'score': s5_score, 'rationale': f'回撤={drawback}%，乖离={bias}%'},
                    'total_score': st_total,
                    'af_adjustment': f'{st_af:+.1f}（F90={f90}，RSI={rsi}）',
                    'final_score': st_final,
                },
                'six_dimension_scoring': {
                    'D1_估值安全边际': {'weight': '35%', 'score': d1_score, 'detail': f'乖离率={bias}%，回撤={drawback}%'},
                    'D2_产业趋势': {'weight': '30%', 'score': d2_score, 'detail': f'板块新闻{len(s.get("sector_news", []))}条'},
                    'D3_盈利质量': {'weight': '15%', 'score': d3_score, 'detail': '需结合基本面数据'},
                    'D4_资金持续性': {'weight': '10%', 'score': d4_score, 'detail': f'RSI={rsi}，F90={f90}'},
                    'D5_催化剂密度': {'weight': '5%', 'score': d5_score, 'detail': f'催化事件{len(s.get("market_context", {}).get("key_catalysts", []))}个'},
                    'D6_价格位置': {'weight': '5%', 'score': d6_score, 'detail': f'RSI={rsi}，乖离={bias}%'},
                    'total_score': lt_total,
                    'rating': lt_rating,
                    'position_limit': lt_position,
                },
                'strategy_filters': {
                    'F90_classification': f'{f90}（RSI={rsi}，乖离={bias}%，近3日={gain_3d}%，近5日={gain_5d}%）',
                    'F73_check': f73_check,
                    'F86_V2_stage': f86_stage,
                    'F92_assessment': f92,
                    'F91_check': '未触发（非极端行情）',
                },
                'execution_decision': {
                    'position_recommendation': position_rec,
                    'entry_timing': '14:50-14:55买入窗口，等待信号确认后分批建仓',
                    'priority': priority,
                    'next_day_action': '次日按贝叶斯后验概率决策，后验概率>0.25可持有3-5天',
                    'risk_control': f'止损线{"-5%" if f90 == "抄底区" else "-3%"}，若跌破则止损',
                },
                'lt_execution': {
                    'holding_period': '3-6个月' if lt_rating in ['A-', 'A', 'A+'] else '6-12个月',
                    'target_return': f'+15%~+30%（评级{lt_rating}）',
                    'stop_loss': '-12%（估值安全边际内）',
                    'batch_building': '四批建仓：当前25%底仓→回调加25%→催化验证加25%→趋势确认加25%',
                    'monitoring': '季度评估：关注板块基本面变化、政策催化、资金流向',
                    'sell_signal': 'D2产业趋势下修或D1估值分位升至80%以上',
                },
                'risk_alerts': self._generate_risk_alerts(f90, rsi, bias, gain_3d, f73_violations),
            }
            sector_analysis.append(sector_data)

        # 对比矩阵
        matrix = []
        if sector_analysis:
            names = [s['sector_name'] for s in sector_analysis]
            matrix.append({'dimension': 'ST综合评分', **{n: str(s['five_dimension_scoring']['final_score']) for n, s in zip(names, sector_analysis)}, 'leader': max(names, key=lambda n: sector_analysis[names.index(n)]['five_dimension_scoring']['final_score'])})
            matrix.append({'dimension': 'LT综合评分', **{n: str(s['six_dimension_scoring']['total_score']) for n, s in zip(names, sector_analysis)}, 'leader': max(names, key=lambda n: sector_analysis[names.index(n)]['six_dimension_scoring']['total_score'])})
            matrix.append({'dimension': 'F90分类', **{n: s['f90_classification'] for n, s in zip(names, sector_analysis)}, 'leader': '—'})
            matrix.append({'dimension': 'LT评级', **{n: s['six_dimension_scoring']['rating'] for n, s in zip(names, sector_analysis)}, 'leader': '—'})

        report_data = {
            'metadata': {
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'target_period': target_period,
                'strategy_used': 'V9.3-ST 超短线 + V9.3-LT 中长期 双模型联合分析',
                'strategy_version': 'V9.3',
                'analysis_type': '全盘扫描板块分析（自动筛选+双模型评分）',
                'sectors_analyzed': [s['sector_name'] for s in sector_analysis],
                'data_source': f'akshare实时数据（截至{datetime.now().strftime("%Y-%m-%d")}）+ V9.3双模型自动评分',
                'scoring_formula': 'ST: (S1×25%+S2×20%+S3×20%+S4×20%+S5×15%)+AF; LT: (D1×35%+D2×30%+D3×15%+D4×10%+D5×5%+D6×5%)',
                'disclaimer': '本分析基于实时市场数据与V9.3策略规则自动推演，非投资建议',
            },
            'sector_analysis': sector_analysis,
            'comparison_matrix': matrix,
            'summary': {
                'total_sectors_scanned': len(sector_analysis),
                'bottom_fishing_sectors': [s['sector_name'] for s in sector_analysis if s['f90_classification'] == '抄底区'],
                'watch_sectors': [s['sector_name'] for s in sector_analysis if s['f90_classification'] == '观望区'],
                'chase_sectors': [s['sector_name'] for s in sector_analysis if s['f90_classification'] == '追涨区'],
            },
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

        print(f'\n报告JSON已生成: {output_path}')
        return output_path

    # ========================================
    # 评分计算辅助函数
    # ========================================
    def _calc_st_s1(self, rsi, f90):
        if f90 == '抄底区' and rsi < 35:
            return 8.5
        elif f90 == '抄底区':
            return 7.5
        elif f90 == '观望区':
            return 6.5
        return 5.0

    def _calc_st_s2(self, news):
        cnt = len(news)
        if cnt >= 5:
            return 8.0
        elif cnt >= 3:
            return 7.0
        elif cnt >= 1:
            return 6.0
        return 5.0

    def _calc_st_s3(self, news):
        cnt = len(news)
        if cnt >= 5:
            return 8.0
        elif cnt >= 3:
            return 7.0
        return 5.5

    def _calc_st_s4(self, rsi, bias, gain_3d, gain_5d, f90):
        if f90 == '抄底区':
            return 8.5
        elif f90 == '追涨区':
            return 4.0
        score = 6.0
        if rsi < 45:
            score += 1.0
        elif rsi > 65:
            score -= 1.0
        return max(3.0, min(9.0, score))

    def _calc_st_s5(self, bias, drawback):
        score = 6.5
        if bias < -3:
            score += 1.5
        if drawback > 10:
            score += 1.0
        if bias > 5:
            score -= 2.0
        return max(3.0, min(9.0, score))

    def _calc_st_af(self, f90, rsi):
        if f90 == '抄底区' and rsi < 35:
            return 0.5
        elif f90 == '抄底区':
            return 0.3
        elif f90 == '追涨区':
            return -0.5
        return 0.0

    def _calc_lt_d1(self, bias, drawback):
        score = 6.5
        if bias < -3:
            score += 1.5
        if drawback > 15:
            score += 1.0
        if bias > 5:
            score -= 2.0
        return max(3.0, min(9.5, score))

    def _calc_lt_d2(self, news):
        cnt = len(news)
        if cnt >= 5:
            return 8.0
        elif cnt >= 3:
            return 7.0
        return 5.5

    def _calc_lt_d4(self, rsi, f90):
        if f90 == '抄底区':
            return 7.5
        elif f90 == '观望区':
            return 6.0
        return 4.5

    def _calc_lt_d5(self, news):
        cnt = len(news)
        if cnt >= 5:
            return 8.5
        elif cnt >= 3:
            return 7.0
        return 5.0

    def _calc_lt_d6(self, rsi, bias, f90):
        if f90 == '抄底区':
            return 8.0
        elif f90 == '追涨区':
            return 4.0
        return 6.0

    def _lt_rating(self, score):
        if score >= 8.5:
            return 'A+'
        elif score >= 8.0:
            return 'A'
        elif score >= 7.0:
            return 'A-'
        elif score >= 6.0:
            return 'B+'
        elif score >= 5.0:
            return 'B'
        elif score >= 4.0:
            return 'C+'
        return 'C'

    def _lt_position(self, rating):
        limits = {'A+': '35%', 'A': '30%', 'A-': '30%', 'B+': '25%', 'B': '20%', 'C+': '15%', 'C': '10%'}
        return limits.get(rating, '15%')

    def _generate_risk_alerts(self, f90, rsi, bias, gain_3d, f73_violations):
        alerts = []
        if f90 == '追涨区':
            alerts.append(f'F90分类为追涨区（RSI={rsi}），追涨风险高')
        if f73_violations:
            alerts.extend(f73_violations)
        if rsi > 70:
            alerts.append(f'RSI={rsi}超买，短期回调压力大')
        if rsi < 30:
            alerts.append(f'RSI={rsi}超卖，可能继续探底')
        if bias > 5:
            alerts.append(f'乖离率={bias}%过高，F73红线三触发')
        if gain_3d > 5:
            alerts.append(f'近3日涨幅{gain_3d}%>5%，F73红线二触发')
        if not alerts:
            alerts.append('暂无重大风险信号')
        return alerts


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='板块全盘扫描器')
    parser.add_argument('mode', choices=['scan', 'analyze', 'list'], help='运行模式: scan=全盘扫描, analyze=指定板块, list=列出所有板块')
    parser.add_argument('sectors', nargs='*', help='analyze模式下的板块名称列表')
    parser.add_argument('--all', action='store_true', help='scan模式: 显示所有板块（不按规则筛选）')
    parser.add_argument('--max', type=int, default=10, help='scan模式: 最大返回板块数')
    parser.add_argument('--report', action='store_true', help='自动生成PDF报告')
    parser.add_argument('--output', type=str, default=None, help='输出JSON文件路径')

    args = parser.parse_args()

    scanner = SectorScanner(cache_ttl=600)

    if args.mode == 'list':
        # 列出所有板块
        sector_etfs = scanner.classify_etfs_by_sector()
        print(f'共发现 {len(sector_etfs)} 个板块:')
        for name, etfs in sorted(sector_etfs.items()):
            print(f'  {name}: {len(etfs)}只ETF')
        return

    if args.mode == 'scan':
        sectors = scanner.scan_all_sectors(filter_rule=not args.all, max_sectors=args.max)
    elif args.mode == 'analyze':
        if not args.sectors:
            print('错误: analyze模式需要指定板块名称')
            return
        sectors = scanner.analyze_specific_sectors(args.sectors)
    else:
        return

    if not sectors:
        print('未找到符合条件的板块')
        return

    # 打印扫描结果
    print('\n=== 扫描结果 ===')
    for s in sectors:
        tech = s.get('technical', {})
        print(f"  [{s['f90_classification']}] {s['sector_name']}: "
              f"RSI={tech.get('rsi14', '—')} 乖离={tech.get('bias_ma20', '—')}% "
              f"近5日={tech.get('gain_5d', '—')}% 新闻={len(s.get('sector_news', []))}条")

    # 生成JSON
    output_path = args.output or f'reports/板块扫描报告_{datetime.now().strftime("%Y%m%d")}.json'
    scanner.generate_report_json(sectors, output_path)

    # 生成PDF报告
    if args.report:
        pdf_path = output_path.replace('.json', '.pdf')
        cmd = f'python "{os.path.join(SKILL_DIR, "generate_sector_report.py")}" "{output_path}" "{pdf_path}"'
        print(f'\n生成PDF报告: {cmd}')
        os.system(cmd)


if __name__ == '__main__':
    import pandas as pd  # noqa: F811 - 确保pandas在main中可用
    main()
