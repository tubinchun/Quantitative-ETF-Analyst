#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易规则分析报告 PDF 生成器
读取七维分析结果 JSON，生成标准化 PDF 分析报告。

用法:
    python generate_report.py <input_json> <output_pdf>
"""

import sys
import os
import json
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ============================================================
# 字体注册（中文支持）
# ============================================================
FONT_REGISTERED = False
FONT_NORMAL = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

def register_fonts():
    """注册中文字体，优先使用微软雅黑，其次宋体"""
    global FONT_REGISTERED, FONT_NORMAL, FONT_BOLD
    if FONT_REGISTERED:
        return

    font_candidates = [
        (r'C:\Windows\Fonts\msyh.ttc', 'MSYH', 'MSYH-Bold'),       # 微软雅黑
        (r'C:\Windows\Fonts\msyhbd.ttc', None, 'MSYH-Bold'),
        (r'C:\Windows\Fonts\simsun.ttc', 'SimSun', 'SimSun-Bold'),  # 宋体
        (r'C:\Windows\Fonts\simhei.ttf', 'SimHei', 'SimHei'),       # 黑体
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
                    # msyh.ttc 包含多个字重，尝试注册粗体
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
        # 回退：使用 reportlab 内置字体（不支持中文，但不会崩溃）
        FONT_NORMAL = 'Helvetica'
        FONT_BOLD = 'Helvetica-Bold'

    if not bold_registered:
        FONT_BOLD = FONT_NORMAL

    FONT_REGISTERED = True


# ============================================================
# 颜色定义
# ============================================================
COLOR_PRIMARY = HexColor('#12324a')      # 深蓝主色
COLOR_SECONDARY = HexColor('#245e8a')    # 中蓝副色
COLOR_ACCENT = HexColor('#b63f2f')       # 红色强调
COLOR_BG_LIGHT = HexColor('#f4f7fb')     # 浅底色
COLOR_BG_PANEL = HexColor('#ffffff')     # 面板底色
COLOR_BG_TABLE = HexColor('#f7f9fc')     # 表格交替背景
COLOR_TEXT = HexColor('#22303c')         # 正文文字
COLOR_TEXT_LIGHT = HexColor('#637080')   # 辅助文字
COLOR_BORDER = HexColor('#d8e0ea')       # 边框
COLOR_HIGH_RISK = HexColor('#c0392b')    # 高风险红
COLOR_MED_RISK = HexColor('#e67e22')     # 中风险橙
COLOR_LOW_RISK = HexColor('#1e8449')     # 低风险绿
COLOR_INFO = HexColor('#2563eb')
COLOR_SUCCESS = HexColor('#1e8449')
COLOR_WARN = HexColor('#d97706')
COLOR_MUTED = HexColor('#8a97a6')


# ============================================================
# 样式定义
# ============================================================
def get_styles():
    """获取段落样式集"""
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        'ReportTitle', parent=styles['Title'],
        fontName=FONT_BOLD, fontSize=24, leading=31,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER,
        spaceAfter=8
    )
    style_subtitle = ParagraphStyle(
        'ReportSubtitle', parent=styles['Normal'],
        fontName=FONT_NORMAL, fontSize=12.5, leading=18,
        textColor=COLOR_TEXT_LIGHT, alignment=TA_CENTER,
        spaceAfter=6
    )
    style_h1 = ParagraphStyle(
        'SectionH1', parent=styles['Heading1'],
        fontName=FONT_BOLD, fontSize=15, leading=20,
        textColor=white, alignment=TA_LEFT,
        backColor=COLOR_PRIMARY,
        borderPadding=(8, 10, 8, 10),
        spaceBefore=16, spaceAfter=10,
        leftIndent=0
    )
    style_h2 = ParagraphStyle(
        'SectionH2', parent=styles['Heading2'],
        fontName=FONT_BOLD, fontSize=12, leading=16,
        textColor=COLOR_PRIMARY, alignment=TA_LEFT,
        spaceBefore=10, spaceAfter=6,
        leftIndent=0
    )
    style_h3 = ParagraphStyle(
        'SectionH3', parent=styles['Heading3'],
        fontName=FONT_BOLD, fontSize=10.5, leading=14,
        textColor=COLOR_SECONDARY, alignment=TA_LEFT,
        spaceBefore=6, spaceAfter=4
    )
    style_body = ParagraphStyle(
        'BodyText', parent=styles['Normal'],
        fontName=FONT_NORMAL, fontSize=9.6, leading=15,
        textColor=COLOR_TEXT, alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    style_bullet = ParagraphStyle(
        'BulletText', parent=style_body,
        leftIndent=18, bulletIndent=6, spaceAfter=4
    )
    style_table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName=FONT_NORMAL, fontSize=8.2, leading=11.5,
        textColor=COLOR_TEXT, alignment=TA_LEFT
    )
    style_table_header = ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontName=FONT_BOLD, fontSize=8.8, leading=11.5,
        textColor=white, alignment=TA_CENTER
    )
    style_table_cell_center = ParagraphStyle(
        'TableCellCenter', parent=style_table_cell,
        alignment=TA_CENTER
    )
    style_disclaimer = ParagraphStyle(
        'Disclaimer', parent=style_body,
        fontSize=8.2, leading=12.5, textColor=COLOR_TEXT_LIGHT,
        leftIndent=10, rightIndent=10
    )
    style_formula = ParagraphStyle(
        'Formula', parent=style_body,
        fontName='Courier', fontSize=9, leading=13,
        textColor=COLOR_PRIMARY, alignment=TA_LEFT,
        backColor=COLOR_BG_LIGHT, borderPadding=(7, 8, 7, 8),
        spaceBefore=6, spaceAfter=8
    )
    style_kpi_label = ParagraphStyle(
        'KpiLabel', parent=styles['Normal'],
        fontName=FONT_BOLD, fontSize=8.4, leading=10.5,
        textColor=COLOR_MUTED, alignment=TA_CENTER
    )
    style_kpi_value = ParagraphStyle(
        'KpiValue', parent=styles['Normal'],
        fontName=FONT_BOLD, fontSize=13, leading=16,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER
    )
    style_kpi_note = ParagraphStyle(
        'KpiNote', parent=styles['Normal'],
        fontName=FONT_NORMAL, fontSize=7.8, leading=10,
        textColor=COLOR_TEXT_LIGHT, alignment=TA_CENTER
    )

    return {
        'title': style_title,
        'subtitle': style_subtitle,
        'h1': style_h1,
        'h2': style_h2,
        'h3': style_h3,
        'body': style_body,
        'bullet': style_bullet,
        'cell': style_table_cell,
        'cell_center': style_table_cell_center,
        'header': style_table_header,
        'disclaimer': style_disclaimer,
        'formula': style_formula,
        'kpi_label': style_kpi_label,
        'kpi_value': style_kpi_value,
        'kpi_note': style_kpi_note,
    }


# ============================================================
# 辅助函数
# ============================================================
def safe_get(data, key, default='—'):
    """安全获取字典值"""
    val = data.get(key, default) if isinstance(data, dict) else default
    if val is None or val == '':
        return default
    return val


def make_para(text, style_key='cell', styles=None):
    """创建段落，自动处理None和空值"""
    if styles is None:
        return Paragraph(str(text), get_styles()['cell'])
    text = str(text) if text is not None else '—'
    return Paragraph(text, styles[style_key])


def make_table(data, col_widths, styles, header_color=COLOR_PRIMARY):
    """创建带样式的表格"""
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        # 表头
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # 正文
        ('FONTNAME', (0, 1), (-1, -1), FONT_NORMAL),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXT),
        # 边框
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, COLOR_PRIMARY),
        # 内边距
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    # 交替行背景
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), COLOR_BG_TABLE))
    table.setStyle(TableStyle(style_cmds))
    return table


def make_section_rule(width=170 * mm, color=COLOR_BORDER):
    line_table = Table([['']], colWidths=[width])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 1.1, color),
    ]))
    return line_table


def make_panel(title, value, note='', color=COLOR_PRIMARY, title_style=None, value_style=None, note_style=None):
    title_style = title_style or get_styles()['kpi_label']
    value_style = value_style or get_styles()['kpi_value']
    note_style = note_style or get_styles()['kpi_note']
    cell = Table(
        [[Paragraph(title, title_style)],
         [Paragraph(str(value), value_style)],
         [Paragraph(note or ' ', note_style)]],
        colWidths=[48 * mm]
    )
    cell.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_PANEL),
        ('BOX', (0, 0), (-1, -1), 0.9, color),
        ('INNERGRID', (0, 0), (-1, -1), 0.0, COLOR_BG_PANEL),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return cell


def severity_color(level, default=COLOR_SECONDARY):
    if str(level) == '高':
        return COLOR_HIGH_RISK
    if str(level) == '中':
        return COLOR_MED_RISK
    if str(level) == '低':
        return COLOR_LOW_RISK
    return default


# ============================================================
# 流程图生成
# ============================================================
def generate_flowchart(logic_flow, model_name, output_path):
    """使用 matplotlib 生成决策流程图（优化版：增大字体、动态尺寸、中文支持）"""
    if not logic_flow:
        return None

    # 设置中文字体 - 优先使用系统中文字体
    import matplotlib.font_manager as fm
    
    # 查找可用的中文字体
    chinese_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'FangSong', 'KaiTi']
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    # 选择第一个可用的中文字体
    selected_font = None
    for font in chinese_fonts:
        if font in available_fonts:
            selected_font = font
            break
    
    if selected_font:
        plt.rcParams['font.sans-serif'] = [selected_font] + chinese_fonts
    else:
        # 回退：尝试直接使用字体文件路径
        font_paths = [
            r'C:\Windows\Fonts\msyh.ttc',
            r'C:\Windows\Fonts\simhei.ttf',
            r'C:\Windows\Fonts\simsun.ttc',
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font_prop = fm.FontProperties(fname=fp)
                    fm.fontManager.addfont(fp)
                    selected_font = font_prop.get_name()
                    plt.rcParams['font.sans-serif'] = [selected_font] + chinese_fonts
                    break
                except Exception:
                    continue
    
    plt.rcParams['axes.unicode_minus'] = False

    n_steps = len(logic_flow)
    
    # 根据步骤数动态调整图片尺寸
    # 每个步骤分配足够的空间
    fig_height = max(8, n_steps * 1.3)
    fig_width = 14  # 增加宽度以容纳更多文字
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(0, fig_width)
    ax.set_ylim(0, n_steps + 2)
    ax.axis('off')
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # 增大盒子尺寸和字体
    box_w = 11.0  # 增加盒子宽度
    box_h = 0.95  # 增加盒子高度
    x_center = fig_width / 2
    y_start = n_steps + 1.0

    colors = ['#2e86c1', '#1a5276', '#2874a6', '#2471a3', '#2e86c1',
              '#1a5276', '#2874a6', '#2471a3', '#c0392b', '#e74c3c']

    for i, step in enumerate(logic_flow):
        y = y_start - i - 0.6
        color = colors[i % len(colors)]
        is_alert = '暴雨' in str(step.get('action', '')) or '极端' in str(step.get('output', ''))
        if is_alert:
            color = '#c0392b'

        # 绘制圆角矩形
        box = FancyBboxPatch(
            (x_center - box_w / 2, y - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.12",
            facecolor=color, edgecolor='#1a5276', linewidth=1.5,
            alpha=0.92
        )
        ax.add_patch(box)

        # 步骤编号圆圈 - 增大尺寸
        circle_r = 0.22
        circle_x = x_center - box_w / 2 + 0.4
        circle = plt.Circle((circle_x, y), circle_r,
                            color='white', alpha=0.95, zorder=5)
        ax.add_patch(circle)
        ax.text(circle_x, y, str(step.get('step', i + 1)),
                ha='center', va='center', fontsize=11, fontweight='bold',
                color=color, zorder=6)

        # 步骤文本 - 使用智能换行代替硬截断
        import textwrap
        time_str = f"[{step.get('time', '')}] " if step.get('time') else ""
        action = str(step.get('action', ''))
        output = str(step.get('output', ''))
        
        # 对 action 文本进行智能换行（每行最多12个字符）
        if len(action) > 12:
            action_lines = textwrap.wrap(action, width=12)
            action = '\n'.join(action_lines[:2])  # 最多2行
            if len(action_lines) > 2:
                action += '..'  # 如果还有更多行，添加省略号
        
        # 对 output 文本进行智能换行
        if output and output != '—':
            if len(output) > 15:
                output_lines = textwrap.wrap(output, width=15)
                output = '\n'.join(output_lines[:2])
                if len(output_lines) > 2:
                    output += '..'
        
        label = f"{time_str}{action}"
        if output and output != '—':
            label += f"\n→ {output}"

        # 增大字体
        ax.text(x_center + 0.2, y, label,
                ha='center', va='center', fontsize=10, color='white',
                fontweight='bold', zorder=6,
                linespacing=1.3)

        # 绘制连接箭头 - 优化样式
        if i < n_steps - 1:
            arrow = FancyArrowPatch(
                (x_center, y - box_h / 2 - 0.02),
                (x_center, y - 0.98 + box_h / 2 + 0.02),
                arrowstyle='->,head_width=0.35,head_length=0.25',
                color='#566573', linewidth=2.0,
                mutation_scale=1.5
            )
            ax.add_patch(arrow)

    # 标题 - 增大字号
    ax.text(x_center, y_start + 0.6, f'{model_name} 决策流程',
            ha='center', va='center', fontsize=16, fontweight='bold',
            color='#1a5276')

    plt.tight_layout(pad=2.0)
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    
    # 使用 PIL 读取实际保存的 PNG 尺寸
    from PIL import Image as PILImage
    try:
        pil_img = PILImage.open(output_path)
        width_px, height_px = pil_img.size
        # 将像素转换为mm (dpi=150, 1inch=25.4mm)
        img_width_mm = width_px / 150 * 25.4
        img_height_mm = height_px / 150 * 25.4
        pil_img.close()
    except ImportError:
        # 如果没有PIL，使用近似计算
        img_width_mm = fig_width * 25.4  # inches to mm
        img_height_mm = fig_height * 25.4
    except Exception:
        img_width_mm = fig_width * 25.4
        img_height_mm = fig_height * 25.4
    
    return {'path': output_path, 'width': img_width_mm, 'height': img_height_mm}


# ============================================================
# 各章节构建函数
# ============================================================
def build_cover(story, data, styles):
    """封面页"""
    meta = data.get('metadata', {})
    story.append(Spacer(1, 34 * mm))
    story.append(Paragraph('量化交易规则', styles['subtitle']))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph('结构化分析报告', styles['title']))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        safe_get(meta, 'model_name', '模型') + ' 规则解构与评估',
        styles['subtitle']
    ))
    story.append(Spacer(1, 10 * mm))
    story.append(make_section_rule(width=135 * mm, color=COLOR_PRIMARY))
    story.append(Spacer(1, 12 * mm))

    meta_panels = [
        make_panel('模型版本', safe_get(meta, 'model_version'), '版本标识', COLOR_INFO, styles['kpi_label'], styles['kpi_value'], styles['kpi_note']),
        make_panel('模型类型', safe_get(meta, 'model_type'), '策略定位', COLOR_SECONDARY, styles['kpi_label'], styles['kpi_value'], styles['kpi_note']),
        make_panel('持有周期', safe_get(meta, 'holding_period'), '执行周期', COLOR_SUCCESS, styles['kpi_label'], styles['kpi_value'], styles['kpi_note']),
        make_panel('目标收益', safe_get(meta, 'target_return'), '收益目标', COLOR_WARN, styles['kpi_label'], styles['kpi_value'], styles['kpi_note']),
    ]
    panel_table = Table([meta_panels[:2], meta_panels[2:]], colWidths=[48 * mm, 48 * mm], rowHeights=[32 * mm, 32 * mm])
    panel_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(panel_table)
    story.append(Spacer(1, 6 * mm))

    summary_info = [
        ['文件名', safe_get(meta, 'file_name')],
        ['分析日期', datetime.now().strftime('%Y-%m-%d')],
        ['分析工具', 'quant-rule-analyzer (AI Skill)'],
    ]
    story.append(make_table(
        [['字段', '内容']] + [[make_para(k, 'cell', styles), make_para(v, 'cell', styles)] for k, v in summary_info],
        [34 * mm, 136 * mm], styles
    ))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        '本报告将交易规则拆解为七个维度，并优先突出策略定位、评分阈值、风险暴露与优化方向，'
        '方便快速判断模型是否具备可执行性、完整性和可扩展性。',
        styles['subtitle']
    ))
    story.append(PageBreak())


def build_metadata(story, data, styles):
    """维度1：文件基本信息"""
    meta = data.get('metadata', {})
    story.append(Paragraph('一、文件基本信息', styles['h1']))

    info_rows = [
        ['文件名', safe_get(meta, 'file_name')],
        ['模型名称', safe_get(meta, 'model_name')],
        ['模型版本', safe_get(meta, 'model_version')],
        ['模型类型', safe_get(meta, 'model_type')],
        ['持有周期', safe_get(meta, 'holding_period')],
        ['目标收益', safe_get(meta, 'target_return')],
        ['核心原则', safe_get(meta, 'core_principle')],
        ['文档范围', safe_get(meta, 'document_scope', '—')],
    ]
    table_data = [['字段', '内容']] + [
        [make_para(k, 'cell', styles), make_para(v, 'cell', styles)] for k, v in info_rows
    ]
    story.append(make_table(table_data, [42 * mm, 128 * mm], styles))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        '这一部分先给出规则文件的身份信息，后续章节会围绕这些元数据展开交易逻辑、参数、风险与优化判断。',
        styles['body']
    ))


def build_strategy_overview(story, data, styles):
    """维度2：核心交易策略概述"""
    overview = data.get('strategy_overview', {})
    story.append(Paragraph('二、核心交易策略概述', styles['h1']))

    # 模型定位
    story.append(Paragraph('2.1 模型定位', styles['h2']))
    story.append(Paragraph(safe_get(overview, 'positioning'), styles['body']))

    # 核心因子体系
    story.append(Paragraph('2.2 核心因子体系', styles['h2']))
    factors = overview.get('core_factors', [])
    if factors:
        factor_data = [['维度/因子', '权重', '说明']]
        for f in factors:
            factor_data.append([
                make_para(safe_get(f, 'name'), 'cell', styles),
                make_para(safe_get(f, 'weight'), 'cell_center', styles),
                make_para(safe_get(f, 'description'), 'cell', styles),
            ])
        story.append(make_table(factor_data, [45 * mm, 25 * mm, 100 * mm], styles))
    else:
        story.append(Paragraph('文档未提及核心因子体系。', styles['body']))

    # 评分公式
    story.append(Paragraph('2.3 评分公式', styles['h2']))
    formula = safe_get(overview, 'scoring_formula')
    if formula and formula != '—':
        story.append(Paragraph(formula, styles['formula']))
    else:
        story.append(Paragraph('文档未提及评分公式。', styles['body']))

    # 决策阈值
    story.append(Paragraph('2.4 决策阈值', styles['h2']))
    thresholds = overview.get('decision_thresholds', [])
    if thresholds:
        th_data = [['阈值条件', '对应操作']]
        for t in thresholds:
            th_data.append([
                make_para(safe_get(t, 'condition'), 'cell', styles),
                make_para(safe_get(t, 'action'), 'cell', styles),
            ])
        story.append(make_table(th_data, [70 * mm, 100 * mm], styles))
    else:
        story.append(Paragraph('文档未提及决策阈值。', styles['body']))

    # 核心交易纪律
    story.append(Paragraph('2.5 核心交易纪律', styles['h2']))
    rules = overview.get('key_rules', [])
    if rules:
        rule_rows = [[make_para(f'纪律 {i+1}', 'header', styles), make_para(rule, 'cell', styles)] for i, rule in enumerate(rules)]
        story.append(make_table([['序号', '规则']] + rule_rows, [24 * mm, 146 * mm], styles))
    else:
        story.append(Paragraph('文档未提及核心交易纪律。', styles['body']))


def build_logic_flow(story, data, styles, temp_dir):
    """维度3：规则逻辑流程图"""
    logic_flow = data.get('logic_flow', [])
    meta = data.get('metadata', {})
    model_name = safe_get(meta, 'model_name', '模型')
    story.append(Paragraph('三、规则逻辑流程图', styles['h1']))

    if not logic_flow:
        story.append(Paragraph('文档未包含明确的决策流程描述。', styles['body']))
        return

    # 生成流程图图片
    chart_path = os.path.join(temp_dir, 'flowchart.png')
    try:
        result = generate_flowchart(logic_flow, model_name, chart_path)
        if os.path.exists(chart_path) and result:
            # 使用动态尺寸替代固定尺寸
            img_width = result.get('width', 140)
            img_height = result.get('height', 100)
            
            # 限制最大宽度为170mm（A4页面可用宽度）
            max_width = 170
            if img_width > max_width:
                scale = max_width / img_width
                img_width = max_width
                img_height = img_height * scale
            
            # 限制最大高度为220mm（A4页面可用高度）
            max_height = 220
            if img_height > max_height:
                scale = max_height / img_height
                img_height = max_height
                img_width = img_width * scale
            
            img = Image(chart_path, width=img_width * mm, height=img_height * mm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 8 * mm))
    except Exception as e:
        story.append(Paragraph(f'[流程图生成失败: {e}]', styles['body']))

    # 步骤说明表
    story.append(Paragraph('3.1 流程步骤说明', styles['h2']))
    flow_data = [['步骤', '时间', '执行动作', '触发条件', '输出/结果']]
    for step in logic_flow:
        flow_data.append([
            make_para(safe_get(step, 'step'), 'cell_center', styles),
            make_para(safe_get(step, 'time'), 'cell_center', styles),
            make_para(safe_get(step, 'action'), 'cell', styles),
            make_para(safe_get(step, 'condition'), 'cell', styles),
            make_para(safe_get(step, 'output'), 'cell', styles),
        ])
    story.append(make_table(flow_data, [12 * mm, 18 * mm, 44 * mm, 48 * mm, 48 * mm], styles))


def build_key_parameters(story, data, styles):
    """维度4：关键参数说明"""
    params = data.get('key_parameters', {})
    story.append(Paragraph('四、关键参数说明', styles['h1']))

    sections = [
        ('position_management', '4.1 仓位管理参数'),
        ('risk_control', '4.2 风险控制参数'),
        ('scoring', '4.3 评分参数'),
        ('timing', '4.4 时间参数'),
        ('filtering', '4.5 筛选/剔除参数'),
    ]

    for key, title in sections:
        items = params.get(key, [])
        story.append(Paragraph(title, styles['h2']))
        if items:
            param_data = [['参数名', '取值/规则', '触发条件', '数据来源']]
            for p in items:
                param_data.append([
                    make_para(safe_get(p, 'name'), 'cell', styles),
                    make_para(safe_get(p, 'value'), 'cell', styles),
                    make_para(safe_get(p, 'condition'), 'cell', styles),
                    make_para(safe_get(p, 'source'), 'cell', styles),
                ])
            story.append(make_table(param_data, [34 * mm, 55 * mm, 48 * mm, 34 * mm], styles))
        else:
            story.append(Paragraph('文档未提及此类参数。', styles['body']))
        story.append(Spacer(1, 4 * mm))


def build_risk_analysis(story, data, styles):
    """维度5：潜在风险点分析"""
    risks = data.get('risk_analysis', [])
    story.append(Paragraph('五、潜在风险点分析', styles['h1']))

    if not risks:
        story.append(Paragraph('未识别到明确的风险点。', styles['body']))
        return

    story.append(Paragraph('5.1 风险总览', styles['h2']))
    risk_panels = []
    for level in ['高', '中', '低']:
        count = sum(1 for r in risks if str(safe_get(r, 'level')) == level)
        color = severity_color(level)
        risk_panels.append(make_panel(f'{level}风险', str(count), '条目数', color, styles['kpi_label'], styles['kpi_value'], styles['kpi_note']))
    risk_summary = Table([risk_panels], colWidths=[53 * mm, 53 * mm, 53 * mm])
    risk_summary.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(risk_summary)
    story.append(Spacer(1, 5 * mm))

    risk_data = [['风险描述', '等级', '触发场景', '影响范围']]
    for r in risks:
        level = safe_get(r, 'level')
        risk_data.append([
            make_para(safe_get(r, 'description'), 'cell', styles),
            make_para(level, 'cell_center', styles),
            make_para(safe_get(r, 'scenario'), 'cell', styles),
            make_para(safe_get(r, 'impact'), 'cell', styles),
        ])

    table = make_table(risk_data, [55 * mm, 15 * mm, 55 * mm, 45 * mm], styles)

    # 为风险等级添加颜色标记
    style_cmds = []
    for i, r in enumerate(risks, 1):
        level = safe_get(r, 'level')
        if level == '高':
            color = COLOR_HIGH_RISK
        elif level == '中':
            color = COLOR_MED_RISK
        else:
            color = COLOR_LOW_RISK
        style_cmds.append(('TEXTCOLOR', (1, i), (1, i), color))
        style_cmds.append(('FONTNAME', (1, i), (1, i), FONT_BOLD))
    if style_cmds:
        existing_style = table._cellStyles
        table.setStyle(TableStyle(style_cmds))

    story.append(table)
    story.append(Spacer(1, 4 * mm))

    # 风险等级图例
    legend_data = [[
        make_para('● 高风险', 'cell', styles),
        make_para('● 中风险', 'cell', styles),
        make_para('● 低风险', 'cell', styles),
    ]]
    legend = Table(legend_data, colWidths=[50 * mm, 50 * mm, 50 * mm])
    legend.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (0, 0), COLOR_HIGH_RISK),
        ('TEXTCOLOR', (1, 0), (1, 0), COLOR_MED_RISK),
        ('TEXTCOLOR', (2, 0), (2, 0), COLOR_LOW_RISK),
        ('FONTNAME', (0, 0), (-1, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(legend)


def build_effectiveness(story, data, styles):
    """维度6：规则有效性评估"""
    eff = data.get('effectiveness_evaluation', {})
    story.append(Paragraph('六、规则有效性评估', styles['h1']))

    # 优势与不足并排
    story.append(Paragraph('6.1 优势与不足', styles['h2']))
    strengths = eff.get('strengths', [])
    weaknesses = eff.get('weaknesses', [])

    strengths_text = '<br/>'.join([f'• {s}' for s in strengths]) if strengths else '未识别到明确优势'
    weaknesses_text = '<br/>'.join([f'• {w}' for w in weaknesses]) if weaknesses else '未识别到明确不足'
    sw_data = [
        [Paragraph('优势', styles['header']), Paragraph('不足', styles['header'])],
        [Paragraph(strengths_text, styles['cell']), Paragraph(weaknesses_text, styles['cell'])],
    ]
    sw_table = Table(sw_data, colWidths=[85 * mm, 85 * mm])
    sw_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), COLOR_SUCCESS),
        ('BACKGROUND', (1, 0), (1, 0), COLOR_ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ('TOPPADDING', (0, 1), (-1, 1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sw_table)
    story.append(Spacer(1, 6 * mm))

    # 评估详情
    story.append(Paragraph('6.2 评估详情', styles['h2']))
    eval_data = [
        ['回测验证状态', safe_get(eff, 'backtesting_status')],
        ['市场环境适应性', safe_get(eff, 'adaptability')],
        ['完整性评分', f'{safe_get(eff, "completeness")} / 10'],
        ['评分理由', safe_get(eff, 'completeness_reason')],
    ]
    eval_table_data = [['评估项', '结果']] + [
        [make_para(k, 'cell', styles), make_para(v, 'cell', styles)] for k, v in eval_data
    ]
    story.append(make_table(eval_table_data, [42 * mm, 128 * mm], styles))


def build_optimization(story, data, styles):
    """维度7：优化建议"""
    suggestions = data.get('optimization_suggestions', [])
    story.append(Paragraph('七、优化建议', styles['h1']))

    if not suggestions:
        story.append(Paragraph('暂无优化建议。', styles['body']))
        return

    priority_panels = []
    for level in ['高', '中', '低']:
        count = sum(1 for s in suggestions if str(safe_get(s, 'priority')) == level)
        priority_panels.append(make_panel(f'{level}优先', str(count), '建议条数', severity_color(level), styles['kpi_label'], styles['kpi_value'], styles['kpi_note']))
    priority_table = Table([priority_panels], colWidths=[53 * mm, 53 * mm, 53 * mm])
    priority_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(priority_table)
    story.append(Spacer(1, 5 * mm))

    sug_data = [['建议内容', '优先级', '预期效果', '实施难度']]
    for s in suggestions:
        sug_data.append([
            make_para(safe_get(s, 'suggestion'), 'cell', styles),
            make_para(safe_get(s, 'priority'), 'cell_center', styles),
            make_para(safe_get(s, 'expected_effect'), 'cell', styles),
            make_para(safe_get(s, 'difficulty'), 'cell_center', styles),
        ])

    table = make_table(sug_data, [63 * mm, 18 * mm, 58 * mm, 29 * mm], styles)

    # 优先级颜色标记
    style_cmds = []
    for i, s in enumerate(suggestions, 1):
        priority = safe_get(s, 'priority')
        if priority == '高':
            style_cmds.append(('TEXTCOLOR', (1, i), (1, i), COLOR_HIGH_RISK))
            style_cmds.append(('FONTNAME', (1, i), (1, i), FONT_BOLD))
        elif priority == '中':
            style_cmds.append(('TEXTCOLOR', (1, i), (1, i), COLOR_MED_RISK))
            style_cmds.append(('FONTNAME', (1, i), (1, i), FONT_BOLD))
    if style_cmds:
        table.setStyle(TableStyle(style_cmds))

    story.append(table)


def build_disclaimer(story, styles):
    """免责声明"""
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph('免责声明', styles['h2']))
    disclaimer_text = (
        '本报告由 AI 结构化分析技能集（quant-rule-analyzer）自动生成，'
        '仅基于对量化交易规则文件的内容分析，不构成任何投资建议。'
        '报告中的风险评估与优化建议基于规则文本的逻辑推断，'
        '实际交易效果需经过严格的历史回测与实盘验证。'
        '量化交易存在模型失效、参数过拟合、市场极端波动等风险，'
        '投资者应结合自身风险承受能力独立决策。市场有风险，投资需谨慎。'
    )
    story.append(Paragraph(disclaimer_text, styles['disclaimer']))


# ============================================================
# 页眉页脚
# ============================================================
def header_footer(canvas, doc):
    """页眉页脚"""
    canvas.saveState()
    width, height = A4

    # 页眉
    canvas.setFont(FONT_NORMAL, 7.8)
    canvas.setFillColor(COLOR_TEXT_LIGHT)
    canvas.drawString(20 * mm, height - 12 * mm, '量化交易规则分析报告')
    canvas.drawRightString(width - 20 * mm, height - 12 * mm,
                           datetime.now().strftime('%Y-%m-%d'))
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.line(20 * mm, height - 14 * mm, width - 20 * mm, height - 14 * mm)

    # 页脚
    canvas.setFont(FONT_NORMAL, 7.8)
    canvas.setFillColor(COLOR_TEXT_LIGHT)
    canvas.drawCentredString(width / 2, 12 * mm, f'第 {doc.page} 页')
    canvas.line(20 * mm, 15 * mm, width - 20 * mm, 15 * mm)

    canvas.restoreState()


# ============================================================
# 主函数
# ============================================================
def generate_report(input_json, output_pdf):
    """生成 PDF 报告"""
    register_fonts()
    styles = get_styles()

    # 读取分析数据
    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 创建临时目录存放流程图
    temp_dir = tempfile.mkdtemp(prefix='quant_report_')

    # 创建文档
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f'量化交易规则分析报告 - {safe_get(data.get("metadata", {}), "model_name")}',
        author='quant-rule-analyzer (AI Skill)',
    )

    story = []

    # 构建各章节
    build_cover(story, data, styles)
    build_metadata(story, data, styles)
    build_strategy_overview(story, data, styles)
    build_logic_flow(story, data, styles, temp_dir)
    build_key_parameters(story, data, styles)
    build_risk_analysis(story, data, styles)
    build_effectiveness(story, data, styles)
    build_optimization(story, data, styles)
    build_disclaimer(story, styles)

    # 构建 PDF
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

    # 清理临时文件
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
        print('用法: python generate_report.py <input_json> <output_pdf>')
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f'错误: 输入文件不存在: {input_file}')
        sys.exit(1)

    generate_report(input_file, output_file)
