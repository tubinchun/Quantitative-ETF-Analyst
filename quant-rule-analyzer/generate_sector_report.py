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

# ============================================================
# 字体注册
# ============================================================
FONT_REGISTERED = False
FONT_NORMAL = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

def register_fonts():
    global FONT_REGISTERED, FONT_NORMAL, FONT_BOLD
    if FONT_REGISTERED:
        return
    font_candidates = [
        (r'C:\Windows\Fonts\msyh.ttc', 'MSYH', 'MSYH-Bold'),
        (r'C:\Windows\Fonts\msyhbd.ttc', None, 'MSYH-Bold'),
        (r'C:\Windows\Fonts\simsun.ttc', 'SimSun', 'SimSun-Bold'),
        (r'C:\Windows\Fonts\simhei.ttf', 'SimHei', 'SimHei'),
    ]
    normal_registered = False
    bold_registered = False
    for path, normal_name, bold_name in font_candidates:
        if not os.path.exists(path):
            continue
        try:
            if normal_name and not normal_registered:
                pdfmetrics.registerFont(TTFont(normal_name, path))
                FONT_NORMAL = normal_name
                normal_registered = True
            if bold_name and not bold_registered:
                if normal_name and path == r'C:\Windows\Fonts\msyh.ttc':
                    try:
                        pdfmetrics.registerFont(TTFont(bold_name, r'C:\Windows\Fonts\msyhbd.ttc'))
                        FONT_BOLD = bold_name
                        bold_registered = True
                    except Exception:
                        FONT_BOLD = normal_name or FONT_NORMAL
                elif path == r'C:\Windows\Fonts\simhei.ttf':
                    pdfmetrics.registerFont(TTFont(bold_name, path))
                    FONT_BOLD = bold_name
                    bold_registered = True
                else:
                    FONT_BOLD = normal_name or FONT_NORMAL
                    bold_registered = True
        except Exception:
            continue
    if not normal_registered:
        FONT_NORMAL = 'Helvetica'
        FONT_BOLD = 'Helvetica-Bold'
    if not bold_registered:
        FONT_BOLD = FONT_NORMAL
    FONT_REGISTERED = True


# ============================================================
# 颜色定义
# ============================================================
COLOR_PRIMARY = HexColor('#1a5276')
COLOR_SECONDARY = HexColor('#2e86c1')
COLOR_ACCENT = HexColor('#e74c3c')
COLOR_BG_LIGHT = HexColor('#ebf5fb')
COLOR_BG_TABLE = HexColor('#f8f9fa')
COLOR_TEXT = HexColor('#2c3e50')
COLOR_TEXT_LIGHT = HexColor('#7f8c8d')
COLOR_BORDER = HexColor('#bdc3c7')
COLOR_HIGH = HexColor('#e74c3c')
COLOR_MED = HexColor('#f39c12')
COLOR_LOW = HexColor('#27ae60')
COLOR_SECTOR = {
    '机器人': '#2e86c1',
    '创新药': '#27ae60',
    '白酒': '#f39c12',
}


# ============================================================
# 样式定义
# ============================================================
def get_styles():
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('ReportTitle', parent=styles['Title'],
        fontName=FONT_BOLD, fontSize=24, leading=34, textColor=COLOR_PRIMARY,
        alignment=TA_CENTER, spaceAfter=10)
    style_subtitle = ParagraphStyle('ReportSubtitle', parent=styles['Normal'],
        fontName=FONT_NORMAL, fontSize=13, leading=18, textColor=COLOR_TEXT_LIGHT,
        alignment=TA_CENTER, spaceAfter=6)
    style_h1 = ParagraphStyle('SectionH1', parent=styles['Heading1'],
        fontName=FONT_BOLD, fontSize=16, leading=24, textColor=white,
        alignment=TA_LEFT, backColor=COLOR_PRIMARY, borderPadding=(8, 10, 8, 10),
        spaceBefore=20, spaceAfter=12, leftIndent=0)
    style_h2 = ParagraphStyle('SectionH2', parent=styles['Heading2'],
        fontName=FONT_BOLD, fontSize=12, leading=17, textColor=COLOR_PRIMARY,
        alignment=TA_LEFT, spaceBefore=12, spaceAfter=6, leftIndent=0)
    style_h3 = ParagraphStyle('SectionH3', parent=styles['Heading3'],
        fontName=FONT_BOLD, fontSize=10.5, leading=15, textColor=COLOR_SECONDARY,
        alignment=TA_LEFT, spaceBefore=8, spaceAfter=4, leftIndent=0)
    style_body = ParagraphStyle('BodyText', parent=styles['Normal'],
        fontName=FONT_NORMAL, fontSize=10, leading=16, textColor=COLOR_TEXT,
        alignment=TA_JUSTIFY, spaceAfter=6)
    style_bullet = ParagraphStyle('BulletText', parent=style_body,
        leftIndent=18, bulletIndent=6, spaceAfter=4)
    style_cell = ParagraphStyle('TableCell', parent=styles['Normal'],
        fontName=FONT_NORMAL, fontSize=8.5, leading=12, textColor=COLOR_TEXT,
        alignment=TA_LEFT)
    style_cell_center = ParagraphStyle('TableCellCenter', parent=style_cell,
        alignment=TA_CENTER)
    style_header = ParagraphStyle('TableHeader', parent=styles['Normal'],
        fontName=FONT_BOLD, fontSize=9, leading=12, textColor=white,
        alignment=TA_CENTER)
    style_disclaimer = ParagraphStyle('Disclaimer', parent=style_body,
        fontSize=8.5, leading=13, textColor=COLOR_TEXT_LIGHT,
        leftIndent=10, rightIndent=10)
    style_highlight = ParagraphStyle('Highlight', parent=style_body,
        fontName=FONT_BOLD, fontSize=10.5, leading=16, textColor=COLOR_ACCENT,
        alignment=TA_CENTER, backColor=HexColor('#fdf2e9'),
        borderPadding=(8, 10, 8, 10), spaceBefore=6, spaceAfter=10)
    return {
        'title': style_title, 'subtitle': style_subtitle, 'h1': style_h1,
        'h2': style_h2, 'h3': style_h3, 'body': style_body, 'bullet': style_bullet,
        'cell': style_cell, 'cell_center': style_cell_center, 'header': style_header,
        'disclaimer': style_disclaimer, 'highlight': style_highlight,
    }


def safe_get(data, key, default='—'):
    val = data.get(key, default) if isinstance(data, dict) else default
    if val is None or val == '':
        return default
    return val


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


def make_para(text, style_key='cell', styles=None):
    if styles is None:
        return Paragraph(str(text), get_styles()['cell'])
    text = str(text) if text is not None else '—'
    return Paragraph(text, styles[style_key])


def make_table(data, col_widths, styles, header_color=COLOR_PRIMARY):
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NORMAL),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXT),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), COLOR_BG_TABLE))
    table.setStyle(TableStyle(style_cmds))
    return table


# ============================================================
# 雷达图生成
# ============================================================
def generate_radar_chart(sectors, output_path):
    """生成五维评分雷达对比图"""
    if not sectors:
        return None

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

    for s in sectors:
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
        color = COLOR_SECTOR.get(sname, '#2e86c1')
        ax.plot(angles, values, 'o-', linewidth=2, label=sname, color=color)
        ax.fill(angles, values, alpha=0.15, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, fontsize=10, fontweight='bold')
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=8)
    framework = 'LT六维' if is_lt else 'ST五维'
    ax.set_title(f'{len(sectors)}大板块{framework}评分对比', fontsize=14, fontweight='bold',
                 color='#1a5276', pad=25)
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    return output_path


# ============================================================
# 综合评分柱状图
# ============================================================
def generate_score_bar_chart(sectors, output_path):
    """生成综合评分柱状图"""
    if not sectors:
        return None

    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
    plt.rcParams['axes.unicode_minus'] = False

    is_lt = sectors[0].get('six_dimension_scoring') is not None if sectors else False

    names = []
    scores = []
    colors = []
    for s in sectors:
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
        colors.append(COLOR_SECTOR.get(sname, '#2e86c1'))

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, scores, color=colors, alpha=0.85, edgecolor='#1a5276',
                  linewidth=1.2, width=0.5)

    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                f'{score:.2f}', ha='center', va='bottom', fontsize=13,
                fontweight='bold', color='#1a5276')

    ax.set_ylabel('综合评分', fontsize=11, fontweight='bold')
    title = 'LT六维综合评分对比' if is_lt else 'ST五维综合评分对比'
    ax.set_title(f'{len(sectors)}大板块{title}', fontsize=14, fontweight='bold',
                 color='#1a5276', pad=15)
    ax.set_ylim(0, 10)
    if is_lt:
        ax.axhline(y=8.5, color='#27ae60', linestyle='--', alpha=0.6, label='强烈推荐(8.5)')
        ax.axhline(y=7.5, color='#2980b9', linestyle='--', alpha=0.6, label='可配置(7.5)')
        ax.axhline(y=6.5, color='#e74c3c', linestyle='--', alpha=0.6, label='谨慎参与(6.5)')
    else:
        ax.axhline(y=7.5, color='#27ae60', linestyle='--', alpha=0.6, label='推荐线(7.5)')
        ax.axhline(y=5.0, color='#e74c3c', linestyle='--', alpha=0.6, label='观望线(5.0)')
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    return output_path


# ============================================================
# 各章节构建函数
# ============================================================
def build_cover(story, data, styles):
    meta = data.get('metadata', {})
    story.append(Spacer(1, 45 * mm))
    story.append(Paragraph('板块分析报告', styles['title']))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph('基于V9.3-ST五维评分框架', styles['subtitle']))
    story.append(Spacer(1, 20 * mm))

    line_table = Table([['']], colWidths=[120 * mm])
    line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 2, COLOR_PRIMARY)]))
    story.append(line_table)
    story.append(Spacer(1, 25 * mm))

    sectors = safe_get(meta, 'sectors_analyzed', '—')
    if isinstance(sectors, list):
        sectors_str = '、'.join(sectors)
    else:
        sectors_str = str(sectors)

    cover_info = [
        ['分析周期', safe_get(meta, 'target_period')],
        ['使用策略', safe_get(meta, 'strategy_used')],
        ['分析板块', sectors_str],
        ['分析类型', safe_get(meta, 'analysis_type')],
        ['分析日期', safe_get(meta, 'analysis_date')],
        ['数据来源', safe_get(meta, 'data_source')],
        ['评分公式', safe_get(meta, 'scoring_formula')],
    ]
    cover_data = [[make_para(k, 'cell', styles), make_para(v, 'cell', styles)] for k, v in cover_info]
    story.append(make_table([['字段', '内容']] + cover_data, [40 * mm, 100 * mm], styles))
    story.append(Spacer(1, 25 * mm))

    story.append(Paragraph(
        '本报告基于V9.3-ST超短线量化交易模型的五维评分框架，'
        '对机器人、创新药、白酒三大板块进行结构化对比分析，'
        '输出各板块评分、策略执行决策与下周配置建议。',
        styles['subtitle']
    ))
    story.append(PageBreak())


def build_overview(story, data, styles):
    meta = data.get('metadata', {})
    story.append(Paragraph('一、分析概述', styles['h1']))

    story.append(Paragraph('1.1 分析背景', styles['h2']))
    story.append(Paragraph(
        f"本报告针对 {safe_get(meta, 'target_period')} 进行板块分析，"
        f"基于 {safe_get(meta, 'strategy_used')} 的五维评分体系"
        f"（S1资金面25%+S2宏观面20%+S3产业面20%+S4技术面20%+S5风险面15%），"
        f"对{'、'.join(safe_get(meta, 'sectors_analyzed', []))}三大板块进行对比评估，"
        "结合F90追涨/抄底分类、F73红线安检、F86-V2三阶段确认等策略因子，"
        "输出各板块的执行决策与配置建议。",
        styles['body']
    ))

    story.append(Paragraph('1.2 数据说明', styles['h2']))
    story.append(Paragraph(safe_get(meta, 'data_source'), styles['body']))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"<b>重要提示：</b>{safe_get(meta, 'disclaimer')}", styles['highlight']))


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
        # 同时读取ST和LT评分数据
        st_scoring = s.get('five_dimension_scoring', {})
        lt_scoring = s.get('six_dimension_scoring', {})
        has_st = bool(st_scoring)
        has_lt = bool(lt_scoring)

        # ST评分
        st_final_score = safe_get(st_scoring, 'final_score', '—')
        st_af = safe_get(st_scoring, 'af_adjustment', '—')
        # LT评分
        lt_final_score = safe_get(lt_scoring, 'total_score', '—')
        lt_rating = safe_get(lt_scoring, 'rating', '—')
        lt_position_limit = safe_get(lt_scoring, 'position_limit', '—')

        story.append(Paragraph(f'2.{idx} {sname}', styles['h2']))

        # 板块概览表（同时展示ST和LT评分）
        story.append(Paragraph(f'<b>2.{idx}.1 板块概览</b>', styles['h3']))
        overview_data = [['指标', '数值']]
        overview_data.append([make_para('代表ETF', 'cell', styles),
                              make_para(", ".join(safe_get(s, "representative_etfs", [])), 'cell', styles)])
        if has_st:
            overview_data.append([make_para('ST综合评分', 'cell_center', styles),
                                  make_para(str(st_final_score), 'cell_center', styles)])
            overview_data.append([make_para('ST AF调整', 'cell_center', styles),
                                  make_para(str(st_af), 'cell_center', styles)])
        if has_lt:
            overview_data.append([make_para('LT综合评分', 'cell_center', styles),
                                  make_para(str(lt_final_score), 'cell_center', styles)])
            overview_data.append([make_para('LT评级', 'cell_center', styles),
                                  make_para(str(lt_rating), 'cell_center', styles)])
            overview_data.append([make_para('LT仓位上限', 'cell_center', styles),
                                  make_para(str(lt_position_limit), 'cell_center', styles)])
        story.append(make_table(overview_data, [35 * mm, 110 * mm], styles))
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


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFont(FONT_NORMAL, 8)
    canvas.setFillColor(COLOR_TEXT_LIGHT)
    canvas.drawString(20 * mm, height - 12 * mm, '板块分析报告（V9.3-ST五维评分）')
    canvas.drawRightString(width - 20 * mm, height - 12 * mm,
                           datetime.now().strftime('%Y-%m-%d'))
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.line(20 * mm, height - 14 * mm, width - 20 * mm, height - 14 * mm)
    canvas.setFont(FONT_NORMAL, 8)
    canvas.setFillColor(COLOR_TEXT_LIGHT)
    canvas.drawCentredString(width / 2, 12 * mm, f'第 {doc.page} 页')
    canvas.line(20 * mm, 15 * mm, width - 20 * mm, 15 * mm)
    canvas.restoreState()


def generate_report(input_json, output_pdf):
    register_fonts()
    styles = get_styles()

    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    temp_dir = tempfile.mkdtemp(prefix='sector_report_')

    doc = SimpleDocTemplate(
        output_pdf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title='板块分析报告 - 三大板块五维评分',
        author='quant-rule-analyzer (AI Skill)',
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

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

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
