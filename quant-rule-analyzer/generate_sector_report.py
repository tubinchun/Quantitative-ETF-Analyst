#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
板块分析报告 PDF 生成器
基于V9.3-ST五维评分框架，对多板块进行对比分析，生成标准化PDF报告。

用法:
    python generate_sector_report.py <input_json> <output_pdf>
"""

import sys
import os
import json
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# 导入共享样式模块
from report_styles import (
    register_fonts, get_styles, safe_get, make_para, make_table,
    make_risk_table, make_info_box, make_section_divider, make_section_banner,
    make_badge, make_score_bar, make_kpi_card, make_kpi_row,
    build_cover_page, build_pdf, setup_matplotlib_style, get_sector_color,
    HeaderFooterCanvas, create_doc,
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_PRIMARY_DARK,
    COLOR_ACCENT, COLOR_ACCENT_LIGHT,
    COLOR_DANGER, COLOR_WARNING, COLOR_SUCCESS, COLOR_INFO,
    COLOR_BG_LIGHT, COLOR_BG_TABLE_ALT, COLOR_ACCENT_PALE,
    COLOR_DANGER_LIGHT, COLOR_WARNING_LIGHT, COLOR_SUCCESS_LIGHT,
    COLOR_TEXT, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_WHITE,
    COLOR_BORDER, COLOR_BORDER_DARK, COLOR_DIVIDER,
    COLOR_SECTOR_PALETTE,
    FONT_NORMAL, FONT_BOLD, FONT_LIGHT,
    PAGE_SIZE, PAGE_WIDTH, PAGE_HEIGHT,
    MARGIN_TOP, MARGIN_BOTTOM, MARGIN_LEFT, MARGIN_RIGHT, CONTENT_WIDTH,
)

# 兼容旧代码中的别名
COLOR_SECONDARY = COLOR_PRIMARY_LIGHT
COLOR_GOLD = COLOR_ACCENT
COLOR_GOLD_LIGHT = COLOR_ACCENT_LIGHT
COLOR_HIGH = COLOR_DANGER
COLOR_MED = COLOR_WARNING
COLOR_LOW = COLOR_SUCCESS
COLOR_HIGH_RISK = COLOR_DANGER
COLOR_MED_RISK = COLOR_WARNING
COLOR_LOW_RISK = COLOR_SUCCESS
COLOR_BG_HIGHLIGHT = COLOR_ACCENT_PALE
COLOR_BG_RISK_HIGH = COLOR_DANGER_LIGHT
COLOR_BG_RISK_MED = COLOR_WARNING_LIGHT
COLOR_BG_RISK_LOW = COLOR_SUCCESS_LIGHT
COLOR_TEXT_LIGHT = COLOR_TEXT_SECONDARY
COLOR_BG_TABLE = COLOR_BG_TABLE_ALT
COLOR_ACCENT_OLD = COLOR_DANGER  # 旧项目符号中的 COLOR_ACCENT
COLOR_SECTOR = {
    '机器人': COLOR_SECTOR_PALETTE[0],
    '创新药': COLOR_SECTOR_PALETTE[1],
    '白酒': COLOR_SECTOR_PALETTE[2],
    '半导体': COLOR_SECTOR_PALETTE[3],
    '人工智能': COLOR_SECTOR_PALETTE[4],
    '科技': COLOR_SECTOR_PALETTE[5],
    '通信': COLOR_SECTOR_PALETTE[6],
}


# ============================================================
# 以下样式/辅助函数由共享模块 report_styles.py 提供：
#   register_fonts, get_styles, safe_get, make_para, make_table,
#   make_risk_table, make_info_box, make_section_divider,
#   build_cover_page, build_pdf, HeaderFooterCanvas 等
# 本文件仅保留板块报告专用的辅助函数
# ============================================================


def _is_numeric(val):
    """判断值是否为数值型（含字符串数字）"""
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        try:
            float(val)
            return True
        except ValueError:
            return False
    return False


# ============================================================
# 雷达图生成
# ============================================================
def generate_radar_chart(sectors, output_path):
    """生成五维评分雷达对比图（v2.0 配色）"""
    if not sectors:
        return None

    setup_matplotlib_style()
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
    plt.rcParams['axes.unicode_minus'] = False

    # 自动检测ST五维或LT六维
    is_lt = sectors[0].get('six_dimension_scoring') is not None
    if is_lt:
        dim_keys = ['D1_估值安全边际', 'D2_产业趋势', 'D3_盈利质量', 'D4_资金持续性', 'D5_催化剂密度', 'D6_价格位置']
        dimensions = ['估值安全边际', '产业趋势', '盈利质量', '资金持续性', '催化剂密度', '价格位置']
        scoring_key = 'six_dimension_scoring'
    else:
        dim_keys = ['S1_资金面', 'S2_宏观面', 'S3_产业面', 'S4_技术面', 'S5_风险面']
        dimensions = ['S1资金面', 'S2宏观面', 'S3产业面', 'S4技术面', 'S5风险面']
        scoring_key = 'five_dimension_scoring'

    n_dims = len(dimensions)
    angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')

    for idx, s in enumerate(sectors):
        sname = safe_get(s, 'sector_name', '板块')
        scoring = s.get(scoring_key, {})
        values = []
        for dk in dim_keys:
            dim_data = scoring.get(dk, {})
            score = dim_data.get('score', 0) if isinstance(dim_data, dict) else 0
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0
            values.append(score)
        values += values[:1]
        color = COLOR_SECTOR.get(sname, COLOR_SECTOR_PALETTE[idx % len(COLOR_SECTOR_PALETTE)])
        ax.plot(angles, values, 'o-', linewidth=2, label=sname, color=color, markersize=5)
        ax.fill(angles, values, alpha=0.12, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, fontsize=10, fontweight='bold', color=COLOR_TEXT)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=8, color=COLOR_TEXT_SECONDARY)
    ax.set_rlabel_position(30)
    framework = 'LT六维' if is_lt else 'ST五维'
    ax.set_title(f'{len(sectors)}大板块{framework}评分对比', fontsize=14, fontweight='bold',
                 color=COLOR_PRIMARY, pad=25)
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), fontsize=9,
              frameon=True, facecolor='white', edgecolor=COLOR_BORDER)
    ax.grid(True, alpha=0.25, color=COLOR_DIVIDER)
    ax.spines['polar'].set_color(COLOR_BORDER)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    return output_path


# ============================================================
# 综合评分柱状图
# ============================================================
def generate_score_bar_chart(sectors, output_path):
    """生成综合评分柱状图（v2.0 配色）"""
    if not sectors:
        return None

    setup_matplotlib_style()
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
    plt.rcParams['axes.unicode_minus'] = False

    is_lt = sectors[0].get('six_dimension_scoring') is not None if sectors else False

    names = []
    scores = []
    sector_colors = []
    for idx, s in enumerate(sectors):
        sname = safe_get(s, 'sector_name', '板块')
        if is_lt:
            scoring = s.get('six_dimension_scoring', {})
            score = safe_get(scoring, 'total_score', 0)
        else:
            scoring = s.get('five_dimension_scoring', {})
            score = safe_get(scoring, 'final_score', 0)
        try:
            score = float(score)
        except (ValueError, TypeError):
            score = 0
        names.append(sname)
        scores.append(score)
        sector_colors.append(COLOR_SECTOR.get(sname, COLOR_SECTOR_PALETTE[idx % len(COLOR_SECTOR_PALETTE)]))

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    bars = ax.bar(names, scores, color=sector_colors, alpha=0.88, edgecolor=COLOR_PRIMARY,
                  linewidth=1.0, width=0.5)

    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                f'{score:.2f}', ha='center', va='bottom', fontsize=13,
                fontweight='bold', color=COLOR_PRIMARY)

    ax.set_ylabel('综合评分', fontsize=11, fontweight='bold', color=COLOR_TEXT)
    title = 'LT六维综合评分对比' if is_lt else 'ST五维综合评分对比'
    ax.set_title(f'{len(sectors)}大板块{title}', fontsize=14, fontweight='bold',
                 color=COLOR_PRIMARY, pad=15)
    ax.set_ylim(0, 10)
    if is_lt:
        ax.axhline(y=8.5, color=COLOR_SUCCESS, linestyle='--', alpha=0.5, linewidth=1.2, label='强烈推荐(8.5)')
        ax.axhline(y=7.5, color=COLOR_INFO, linestyle='--', alpha=0.5, linewidth=1.2, label='可配置(7.5)')
        ax.axhline(y=6.5, color=COLOR_DANGER, linestyle='--', alpha=0.5, linewidth=1.2, label='谨慎参与(6.5)')
    else:
        ax.axhline(y=7.5, color=COLOR_SUCCESS, linestyle='--', alpha=0.5, linewidth=1.2, label='推荐线(7.5)')
        ax.axhline(y=5.0, color=COLOR_DANGER, linestyle='--', alpha=0.5, linewidth=1.2, label='观望线(5.0)')
    ax.legend(fontsize=9, loc='upper right', frameon=True, facecolor='white', edgecolor=COLOR_BORDER)
    ax.grid(axis='y', alpha=0.3, color=COLOR_DIVIDER)
    ax.set_axisbelow(True)
    ax.tick_params(colors=COLOR_TEXT_SECONDARY)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLOR_BORDER)
    ax.spines['bottom'].set_color(COLOR_BORDER)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    return output_path


# ============================================================
# 各章节构建函数
# ============================================================
def build_cover(story, data, styles):
    """封面页（使用共享样式模块的封面构建器）"""
    meta = data.get('metadata', {})
    sectors = safe_get(meta, 'sectors_analyzed', '—')
    if isinstance(sectors, list):
        sectors_str = '、'.join(sectors)
    else:
        sectors_str = str(sectors)

    build_cover_page(story, styles,
                     title='板块分析报告',
                     subtitle=safe_get(meta, 'strategy_used', 'V9.3 双模型板块分析'),
                     info_items=[
                         {'label': '分析周期', 'value': safe_get(meta, 'target_period')},
                         {'label': '分析板块', 'value': sectors_str},
                         {'label': '分析类型', 'value': safe_get(meta, 'analysis_type')},
                         {'label': '分析日期', 'value': safe_get(meta, 'analysis_date')},
                         {'label': '数据来源', 'value': safe_get(meta, 'data_source')},
                         {'label': '评分公式', 'value': safe_get(meta, 'scoring_formula')},
                     ])


def build_overview(story, data, styles):
    meta = data.get('metadata', {})
    story.append(Paragraph('一、分析概述', styles['h1']))

    # KPI统计卡片行
    sectors = data.get('sector_analysis', [])
    total = len(sectors)
    bottom_fishing = sum(1 for s in sectors if s.get('f90_classification', '') == '抄底区')
    watch = sum(1 for s in sectors if s.get('f90_classification', '') == '观望区')
    chase = total - bottom_fishing - watch

    kpi_color = COLOR_PRIMARY if bottom_fishing > 0 else COLOR_PRIMARY_LIGHT
    cards = [
        make_kpi_card('板块总数', str(total), f'分析日期: {safe_get(meta, "analysis_date")}',
                      color=COLOR_PRIMARY, width=50*mm),
        make_kpi_card('抄底区', str(bottom_fishing), 'RSI<40 负乖离 超卖',
                      color=COLOR_SUCCESS if bottom_fishing > 0 else COLOR_TEXT_MUTED, width=50*mm),
        make_kpi_card('观望区', str(watch), '趋势待确认',
                      color=COLOR_WARNING if watch > 0 else COLOR_TEXT_MUTED, width=50*mm),
    ]
    story.append(Table([cards], colWidths=[50*mm, 50*mm, 50*mm]))
    story.append(Spacer(1, 8 * mm))

    # 分析背景
    story.append(make_section_banner('1.1 分析背景', styles))
    sectors_str = '、'.join(safe_get(meta, 'sectors_analyzed', []))
    strategy_name = safe_get(meta, 'strategy_used', 'V9.3双模型')
    story.append(Paragraph(
        f"本报告针对 <b>{safe_get(meta, 'target_period')}</b> 进行板块分析，"
        f"基于 <b>{strategy_name}</b> 的五维评分体系"
        f"（S1资金面25%+S2宏观面20%+S3产业面20%+S4技术面20%+S5风险面15%），"
        f"对 <b>{sectors_str}</b> 等板块进行对比评估，"
        f"结合F90追涨/抄底分类、F73红线安检、F86-V2三阶段确认等策略因子，"
        f"输出各板块的执行决策与配置建议。",
        styles['body']
    ))

    story.append(make_section_banner('1.2 数据说明', styles))
    story.append(Paragraph(safe_get(meta, 'data_source'), styles['body']))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        f"<b>重要提示：</b>{safe_get(meta, 'disclaimer', '本报告基于量化模型自动生成，仅供参考，不构成投资建议。')}",
        styles['highlight']))
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_sector_analysis(story, data, styles, temp_dir):
    sectors = data.get('sector_analysis', [])
    story.append(Paragraph('二、板块详细分析', styles['h1']))

    if not sectors:
        story.append(Paragraph('未配置板块分析数据。', styles['body']))
        return

    # 综合评分柱状图
    chart_path = os.path.join(temp_dir, 'score_bar.png')
    try:
        generate_score_bar_chart(sectors, chart_path)
        if os.path.exists(chart_path):
            img = Image(chart_path, width=140 * mm, height=88 * mm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 8 * mm))
    except Exception as e:
        story.append(Paragraph(f'[评分图生成失败: {e}]', styles['body']))

    # 各板块详细分析（同时展示ST超短线和LT中长期分析）
    for idx, s in enumerate(sectors, 1):
        sname = safe_get(s, 'sector_name', '板块')
        st_scoring = s.get('five_dimension_scoring', {})
        lt_scoring = s.get('six_dimension_scoring', {})
        has_st = bool(st_scoring)
        has_lt = bool(lt_scoring)
        f90 = s.get('f90_classification', '观望区')

        st_final_score = safe_get(st_scoring, 'final_score', '—')
        st_af = safe_get(st_scoring, 'af_adjustment', '—')
        lt_final_score = safe_get(lt_scoring, 'total_score', '—')
        lt_rating = safe_get(lt_scoring, 'rating', '—')
        lt_position_limit = safe_get(lt_scoring, 'position_limit', '—')

        # 板块标题（使用章节横幅 + 状态徽章）
        badge_type = 'success' if f90 == '抄底区' else ('warning' if f90 == '观望区' else 'danger')
        badge_text = f'● {f90}' if f90 else '—'
        sector_color = COLOR_SECTOR.get(sname,
            COLOR_SECTOR_PALETTE[(idx - 1) % len(COLOR_SECTOR_PALETTE)])
        story.append(make_section_banner(f'2.{idx} {sname}', styles, color=sector_color))
        # 状态徽章
        badge = make_badge(badge_text, badge_type=badge_type, styles=styles)
        badge_row = Table([[badge, Spacer(1, 1)]], colWidths=[25*mm, CONTENT_WIDTH - 25*mm])
        badge_row.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
        ]))
        story.append(badge_row)
        story.append(Spacer(1, 2 * mm))

        # 板块概览表 + 评分进度条（同时展示ST和LT评分）
        story.append(Paragraph(f'<b>2.{idx}.1 板块概览</b>', styles['h3']))
        overview_data = [['指标', '数值']]
        overview_data.append([make_para('代表ETF', 'cell', styles),
                              make_para(", ".join(safe_get(s, "representative_etfs", [])), 'cell', styles)])
        if has_st:
            try:
                st_score_val = float(st_final_score)
            except (ValueError, TypeError):
                st_score_val = 0
            overview_data.append([make_para('ST综合评分', 'cell_center', styles),
                                  make_para(str(st_final_score), 'cell_center', styles)])
            overview_data.append([make_para('ST AF调整', 'cell_center', styles),
                                  make_para(str(st_af), 'cell_center', styles)])
        if has_lt:
            try:
                lt_score_val = float(lt_final_score)
            except (ValueError, TypeError):
                lt_score_val = 0
            overview_data.append([make_para('LT综合评分', 'cell_center', styles),
                                  make_para(str(lt_final_score), 'cell_center', styles)])
            overview_data.append([make_para('LT评级', 'cell_center', styles),
                                  make_para(str(lt_rating), 'cell_center', styles)])
            overview_data.append([make_para('LT仓位上限', 'cell_center', styles),
                                  make_para(str(lt_position_limit), 'cell_center', styles)])
        story.append(make_table(overview_data, [35 * mm, 110 * mm], styles))
        story.append(Spacer(1, 2 * mm))

        # 评分可视化进度条
        if has_st and st_score_val > 0:
            story.append(make_score_bar(st_score_val, max_score=10, width=CONTENT_WIDTH,
                         color=COLOR_SUCCESS if st_score_val >= 7 else (COLOR_WARNING if st_score_val >= 5 else COLOR_DANGER)))
        story.append(Spacer(1, 3 * mm))

        # 市场背景详析（合并ST和LT关注的维度）
        ctx = s.get('market_context', {})
        story.append(Paragraph(f'<b>2.{idx}.2 市场背景详析</b>', styles['h3']))
        bg_data = [['分析维度', '详情']]
        # ST关注维度
        bg_data.append([make_para('近期走势', 'cell', styles),
                        make_para(safe_get(ctx, 'july_trend'), 'cell', styles)])
        bg_data.append([make_para('资金流向', 'cell', styles),
                        make_para(safe_get(ctx, 'etf_flows'), 'cell', styles)])
        bg_data.append([make_para('估值水平', 'cell', styles),
                        make_para(safe_get(ctx, 'valuation'), 'cell', styles)])
        # LT关注维度
        bg_data.append([make_para('产业趋势', 'cell', styles),
                        make_para(safe_get(ctx, 'industry_trend'), 'cell', styles)])
        bg_data.append([make_para('盈利质量', 'cell', styles),
                        make_para(safe_get(ctx, 'profitability'), 'cell', styles)])
        bg_data.append([make_para('政策支持', 'cell', styles),
                        make_para(safe_get(ctx, 'policy'), 'cell', styles)])
        story.append(make_table(bg_data, [30 * mm, 115 * mm], styles))
        story.append(Spacer(1, 3 * mm))

        # 关键催化事件详析
        catalysts = safe_get(ctx, 'key_catalysts', [])
        if catalysts:
            story.append(Paragraph(f'<b>2.{idx}.3 关键催化事件</b>', styles['h3']))
            cat_data = [['序号', '催化事件']]
            for ci, c in enumerate(catalysts, 1):
                cat_data.append([
                    make_para(str(ci), 'cell_center', styles),
                    make_para(c, 'cell', styles),
                ])
            story.append(make_table(cat_data, [15 * mm, 130 * mm], styles))
            story.append(Spacer(1, 3 * mm))

        # 机构观点
        inst_views = safe_get(ctx, 'institution_views')
        if inst_views and inst_views != '—':
            story.append(Paragraph(f'<b>2.{idx}.4 机构观点</b>', styles['h3']))
            story.append(Paragraph(inst_views, styles['body']))
            story.append(Spacer(1, 3 * mm))

        # ST超短线策略分析
        if has_st:
            story.append(Paragraph(f'<b>2.{idx}.5 ST超短线策略分析（V9.3-ST）</b>', styles['h3']))

            # ST策略因子判定
            filters = s.get('strategy_filters', {})
            if filters:
                story.append(Paragraph(f'<b>策略因子判定：</b>', styles['body']))
                filter_data = [['因子', '判定结果']]
                filter_map = [
                    ('F90_classification', 'F90追涨/抄底分类'),
                    ('F73_check', 'F73红线安检'),
                    ('F86_V2_stage', 'F86-V2三阶段确认'),
                    ('F92_assessment', 'F92主力承接评估'),
                    ('F91_check', 'F91暴雨航行检测'),
                ]
                for k, label in filter_map:
                    filter_data.append([
                        make_para(label, 'cell', styles),
                        make_para(safe_get(filters, k), 'cell', styles),
                    ])
                story.append(make_table(filter_data, [45 * mm, 100 * mm], styles))
                story.append(Spacer(1, 2 * mm))

            # ST执行决策
            decision = s.get('execution_decision', {})
            if decision:
                story.append(Paragraph(f'<b>执行决策：</b>', styles['body']))
                dec_data = [['决策项', '建议']]
                dec_map = [
                    ('position_recommendation', '仓位建议'),
                    ('entry_timing', '介入时机'),
                    ('priority', '优先级'),
                    ('next_day_action', '次日操作'),
                    ('risk_control', '风控措施'),
                ]
                for k, label in dec_map:
                    dec_data.append([
                        make_para(label, 'cell', styles),
                        make_para(safe_get(decision, k), 'cell', styles),
                    ])
                story.append(make_table(dec_data, [35 * mm, 110 * mm], styles))
            story.append(Spacer(1, 3 * mm))

        # LT中长期策略分析
        if has_lt:
            story.append(Paragraph(f'<b>2.{idx}.6 LT中长期策略分析（V9.3-LT）</b>', styles['h3']))
            lt_exec = s.get('lt_execution', {})
            if lt_exec:
                lt_data = [['决策项', '建议']]
                lt_map = [
                    ('holding_period', '持有周期'),
                    ('target_return', '目标收益'),
                    ('stop_loss', '止损线'),
                    ('batch_building', '分批建仓'),
                    ('monitoring', '季度监测'),
                    ('sell_signal', '卖出信号'),
                ]
                for k, label in lt_map:
                    lt_data.append([
                        make_para(label, 'cell', styles),
                        make_para(safe_get(lt_exec, k), 'cell', styles),
                    ])
                story.append(make_table(lt_data, [30 * mm, 115 * mm], styles))
            story.append(Spacer(1, 3 * mm))

        # 板块风险提示
        risks = s.get('risk_alerts', [])
        if risks:
            story.append(Paragraph(f'<b>2.{idx}.7 板块风险提示</b>', styles['h3']))
            risk_data = [['序号', '风险点']]
            for ri, r in enumerate(risks, 1):
                risk_data.append([
                    make_para(str(ri), 'cell_center', styles),
                    make_para(r, 'cell', styles),
                ])
            story.append(make_table(risk_data, [15 * mm, 130 * mm], styles))

        story.append(Spacer(1, 8 * mm))

    story.append(make_section_divider())


def build_comparison(story, data, styles, temp_dir):
    matrix = data.get('comparison_matrix', [])
    story.append(Paragraph('三、板块对比矩阵', styles['h1']))

    if not matrix:
        story.append(Paragraph('未配置对比矩阵。', styles['body']))
        return

    # 雷达图
    sectors = data.get('sector_analysis', [])
    radar_path = os.path.join(temp_dir, 'radar.png')
    try:
        generate_radar_chart(sectors, radar_path)
        if os.path.exists(radar_path):
            img = Image(radar_path, width=135 * mm, height=135 * mm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 8 * mm))
    except Exception as e:
        story.append(Paragraph(f'[雷达图生成失败: {e}]', styles['body']))

    # 对比表（动态列名，从第一条数据的key推断）
    story.append(Paragraph('3.1 多维度对比表', styles['h2']))
    # 固定字段：dimension 和 leader；中间列动态读取
    fixed_keys = ['dimension', 'leader']
    if matrix:
        first = matrix[0]
        sector_keys = [k for k in first.keys() if k not in fixed_keys]
    else:
        sector_keys = []

    n_sectors = len(sector_keys)

    if n_sectors <= 4:
        # 板块少时用常规布局：维度为行，板块为列
        header = ['对比维度'] + sector_keys + ['领先']
        comp_data = [header]
        for m in matrix:
            row = [make_para(safe_get(m, 'dimension'), 'cell', styles)]
            for sk in sector_keys:
                row.append(make_para(safe_get(m, sk), 'cell_center', styles))
            row.append(make_para(safe_get(m, 'leader'), 'cell_center', styles))
            comp_data.append(row)
        dim_w = 35 * mm
        leader_w = 20 * mm
        remain = 170 * mm - dim_w - leader_w
        sector_w = remain / max(n_sectors, 1)
        col_widths = [dim_w] + [sector_w] * n_sectors + [leader_w]
        story.append(make_table(comp_data, col_widths, styles))
    else:
        # 板板多时(>4)用转置布局：板块为行，维度为列
        # 只取数值型维度（评分类），文本型维度单独列表
        numeric_dims = [m for m in matrix if any(isinstance(m.get(sk), (int, float)) or _is_numeric(m.get(sk)) for sk in sector_keys)]
        text_dims = [m for m in matrix if m not in numeric_dims]

        if numeric_dims:
            header = ['板块'] + [safe_get(m, 'dimension', '') for m in numeric_dims] + ['领先']
            comp_data = [header]
            for sk in sector_keys:
                row = [make_para(sk, 'cell', styles)]
                for m in numeric_dims:
                    row.append(make_para(safe_get(m, sk), 'cell_center', styles))
                # 领先取第一个数值维度的leader
                row.append(make_para(safe_get(numeric_dims[0], 'leader', '—'), 'cell_center', styles))
                comp_data.append(row)
            n_cols = len(header)
            sector_w = 28 * mm
            remain = 170 * mm - sector_w - 18 * mm
            dim_w = remain / max(len(numeric_dims), 1)
            col_widths = [sector_w] + [dim_w] * len(numeric_dims) + [18 * mm]
            story.append(make_table(comp_data, col_widths, styles))

        # 文本型维度单独列表
        if text_dims:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph('3.2 分类与配置对比', styles['h2']))
            header2 = ['板块'] + [safe_get(m, 'dimension', '') for m in text_dims]
            comp_data2 = [header2]
            for sk in sector_keys:
                row = [make_para(sk, 'cell', styles)]
                for m in text_dims:
                    row.append(make_para(safe_get(m, sk), 'cell_center', styles))
                comp_data2.append(row)
            sector_w = 28 * mm
            remain = 170 * mm - sector_w
            dim_w = remain / max(len(text_dims), 1)
            col_widths2 = [sector_w] + [dim_w] * len(text_dims)
            story.append(make_table(comp_data2, col_widths2, styles))

    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_next_week_strategy(story, data, styles):
    strategy = data.get('next_week_strategy', {})
    is_lt = data.get('metadata', {}).get('strategy_version', '') == 'V9.3-LT'
    section_title = '中长期配置策略' if is_lt else '下周配置策略'
    story.append(Paragraph(f'四、{section_title}', styles['h1']))

    # 板块配置
    allocation = strategy.get('sector_allocation', [])
    story.append(Paragraph('4.1 板块仓位配置', styles['h2']))
    if allocation:
        alloc_data = [['板块', '建议仓位', '介入时机', '配置依据', '关注要点']]
        for a in allocation:
            alloc_data.append([
                make_para(safe_get(a, 'sector'), 'cell', styles),
                make_para(safe_get(a, 'allocation'), 'cell_center', styles),
                make_para(safe_get(a, 'timing'), 'cell', styles),
                make_para(safe_get(a, 'rationale'), 'cell', styles),
                make_para(safe_get(a, 'key_watch'), 'cell', styles),
            ])
        story.append(make_table(alloc_data, [20 * mm, 20 * mm, 35 * mm, 45 * mm, 45 * mm], styles))

    story.append(Spacer(1, 4 * mm))
    total_pos = safe_get(strategy, 'total_position')
    story.append(Paragraph(f'<b>总仓位建议：</b>{total_pos}', styles['body']))

    if is_lt:
        # LT分批建仓时间线
        batch_timeline = strategy.get('batch_building_timeline', [])
        if batch_timeline:
            story.append(Paragraph('4.2 分批建仓时间线（四批建仓法）', styles['h2']))
            bt_data = [['批次', '时间', '执行动作']]
            for bt in batch_timeline:
                bt_data.append([
                    make_para(safe_get(bt, 'batch'), 'cell', styles),
                    make_para(safe_get(bt, 'timing'), 'cell_center', styles),
                    make_para(safe_get(bt, 'action'), 'cell', styles),
                ])
            story.append(make_table(bt_data, [35 * mm, 35 * mm, 95 * mm], styles))

        # LT季度评估
        quarterly = strategy.get('quarterly_review', [])
        if quarterly:
            story.append(Paragraph('4.3 季度评估计划', styles['h2']))
            q_data = [['评估季度', '重点关注']]
            for q in quarterly:
                q_data.append([
                    make_para(safe_get(q, 'quarter'), 'cell_center', styles),
                    make_para(safe_get(q, 'focus'), 'cell', styles),
                ])
            story.append(make_table(q_data, [40 * mm, 125 * mm], styles))
    else:
        # ST执行时间线
        timeline = strategy.get('execution_timeline', [])
        if timeline:
            story.append(Paragraph('4.2 下周执行时间线', styles['h2']))
            tl_data = [['时间', '执行动作']]
            for t in timeline:
                tl_data.append([
                    make_para(safe_get(t, 'time'), 'cell_center', styles),
                    make_para(safe_get(t, 'action'), 'cell', styles),
                ])
            story.append(make_table(tl_data, [35 * mm, 130 * mm], styles))

        # ST场景应对
        scenarios = strategy.get('scenario_response', [])
        if scenarios:
            story.append(Paragraph('4.3 场景应对策略', styles['h2']))
            sc_data = [['市场场景', '操作建议', '决策依据']]
            for sc in scenarios:
                sc_data.append([
                    make_para(safe_get(sc, 'scenario'), 'cell', styles),
                    make_para(safe_get(sc, 'action'), 'cell', styles),
                    make_para(safe_get(sc, 'rationale'), 'cell', styles),
                ])
            story.append(make_table(sc_data, [45 * mm, 65 * mm, 55 * mm], styles))

    # ST vs LT对比（如果存在）
    st_lt = data.get('st_lt_comparison', [])
    if st_lt:
        story.append(Paragraph('4.4 ST与LT策略对比', styles['h2']))
        sl_data = [['对比维度', 'ST策略', 'LT策略', '核心差异']]
        for sl in st_lt:
            sl_data.append([
                make_para(safe_get(sl, 'dimension'), 'cell', styles),
                make_para(safe_get(sl, 'ST策略'), 'cell', styles),
                make_para(safe_get(sl, 'LT策略'), 'cell', styles),
                make_para(safe_get(sl, '差异'), 'cell', styles),
            ])
        story.append(make_table(sl_data, [30 * mm, 45 * mm, 45 * mm, 45 * mm], styles))

    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_risk_alerts(story, data, styles):
    risks = data.get('risk_alerts', [])
    story.append(Paragraph('五、风险预警', styles['h1']))

    if not risks:
        story.append(Paragraph('未识别到风险点。', styles['body']))
        return

    risk_data = [['风险点', '等级', '触发场景', '应对措施']]
    for r in risks:
        risk_data.append([
            make_para(safe_get(r, 'risk'), 'cell', styles),
            make_para(safe_get(r, 'level'), 'cell_center', styles),
            make_para(safe_get(r, 'trigger'), 'cell', styles),
            make_para(safe_get(r, 'mitigation'), 'cell', styles),
        ])

    table = make_table(risk_data, [40 * mm, 15 * mm, 50 * mm, 60 * mm], styles)
    style_cmds = []
    for i, r in enumerate(risks, 1):
        level = safe_get(r, 'level')
        if level == '高':
            color = COLOR_HIGH
        elif level == '中':
            color = COLOR_MED
        else:
            color = COLOR_LOW
        style_cmds.append(('TEXTCOLOR', (1, i), (1, i), color))
        style_cmds.append(('FONTNAME', (1, i), (1, i), FONT_BOLD))
    if style_cmds:
        table.setStyle(TableStyle(style_cmds))
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_summary(story, data, styles):
    summary = data.get('summary', {})
    story.append(Paragraph('六、分析总结', styles['h1']))

    story.append(Paragraph('6.1 核心观点', styles['h2']))
    story.append(Paragraph(safe_get(summary, 'core_view'), styles['body']))

    story.append(Paragraph('6.2 评分排名', styles['h2']))
    story.append(Paragraph(safe_get(summary, 'ranking'), styles['body']))

    # ST与LT差异（如果存在）
    st_lt_diff = safe_get(summary, 'st_lt_difference')
    if st_lt_diff and st_lt_diff != '—':
        story.append(Paragraph('6.3 ST与LT策略差异', styles['h2']))
        story.append(Paragraph(st_lt_diff, styles['body']))
        story.append(Paragraph('6.4 关键关注点', styles['h2']))
        story.append(Paragraph(safe_get(summary, 'key_focus'), styles['body']))
        story.append(Paragraph('6.5 仓位指引', styles['h2']))
        story.append(Paragraph(safe_get(summary, 'position_guidance'), styles['body']))
        story.append(Paragraph('6.6 风险优先级', styles['h2']))
        story.append(Paragraph(safe_get(summary, 'risk_priority'), styles['body']))
    else:
        story.append(Paragraph('6.3 关键关注点', styles['h2']))
        story.append(Paragraph(safe_get(summary, 'key_focus'), styles['body']))
        story.append(Paragraph('6.4 仓位指引', styles['h2']))
        story.append(Paragraph(safe_get(summary, 'position_guidance'), styles['body']))
        story.append(Paragraph('6.5 风险优先级', styles['h2']))
        story.append(Paragraph(safe_get(summary, 'risk_priority'), styles['body']))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(safe_get(summary, 'action_principle'), styles['highlight']))
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_disclaimer(story, styles):
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph('免责声明', styles['h2']))
    disclaimer_text = (
        '本报告由 AI 基于 V9.3-ST 超短线量化交易模型五维评分框架自动生成，'
        '结合公开市场信息进行推演分析，<b>不构成任何投资建议</b>。'
        '报告中的板块评分、策略执行决策与配置建议基于策略规则与市场信息的逻辑推断，'
        '实际市场走势需以实时数据为准。'
        '量化交易存在模型失效、参数过拟合、市场极端波动等风险，'
        '投资者应结合自身风险承受能力独立决策。市场有风险，投资需谨慎。'
    )
    story.append(Paragraph(disclaimer_text, styles['disclaimer']))


def generate_report(input_json, output_pdf):
    register_fonts()
    styles = get_styles()

    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    temp_dir = tempfile.mkdtemp(prefix='sector_report_')

    meta = data.get('metadata', {})
    sectors = safe_get(meta, 'sectors_analyzed', [])
    if isinstance(sectors, list):
        sectors_str = '、'.join(sectors)
    else:
        sectors_str = str(sectors)
    report_title = f'板块分析报告 - {sectors_str}'
    report_date = safe_get(meta, 'analysis_date', datetime.now().strftime('%Y-%m-%d'))

    doc = SimpleDocTemplate(
        output_pdf, pagesize=PAGE_SIZE,
        leftMargin=MARGIN_LEFT, rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP + 5 * mm, bottomMargin=MARGIN_BOTTOM + 5 * mm,
        title=report_title,
        author='量化策略分析系统',
    )

    story = []
    build_cover(story, data, styles)
    build_overview(story, data, styles)
    build_sector_analysis(story, data, styles, temp_dir)
    build_comparison(story, data, styles, temp_dir)
    build_next_week_strategy(story, data, styles)
    build_risk_alerts(story, data, styles)
    build_summary(story, data, styles)
    build_disclaimer(story, styles)

    # 使用共享样式模块的页眉页脚
    hf = HeaderFooterCanvas(report_title=report_title, report_date=report_date)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)

    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    file_size = os.path.getsize(output_pdf)
    print(f'PDF 报告已生成: {output_pdf}')
    print(f'文件大小: {file_size / 1024:.1f} KB')
    return output_pdf


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python generate_sector_report.py <input_json> <output_pdf>')
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    if not os.path.exists(input_file):
        print(f'错误: 输入文件不存在: {input_file}')
        sys.exit(1)
    generate_report(input_file, output_file)
