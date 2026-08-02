#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化分析报告共享样式模块 v2.0
───────────────────────────────────────────────────
全面重构版：现代化金融级报告样式系统
涵盖：色彩体系、字体层级、页眉页脚、封面、表格、图表、KPI卡片、状态徽章、评分进度条

设计理念：
  - 深海蓝 + 珊瑚金 + 青瓷色 三色体系
  - 卡片式信息布局，层次分明
  - 金融级专业排版，留白舒适
  - 数据可视化元素统一风格
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# 一、色彩体系 ── 深海蓝 × 珊瑚金 × 青瓷色
# ============================================================

# ◆ 主色系：深海蓝 (Deep Ocean Blue)
COLOR_PRIMARY        = HexColor('#1B2D4E')   # 深海蓝（主色：页眉、表头、章节标题）
COLOR_PRIMARY_DARK   = HexColor('#0F1A30')   # 极深蓝（封面背景）
COLOR_PRIMARY_LIGHT  = HexColor('#2C4A7C')   # 中蓝（副标题、强调）
COLOR_PRIMARY_PALE   = HexColor('#D6E4F0')   # 浅蓝（边框、分隔）
COLOR_PRIMARY_BG     = HexColor('#F0F4FA')   # 极浅蓝（卡片背景）

# ◆ 强调色：珊瑚金 (Coral Gold)
COLOR_ACCENT         = HexColor('#D4945C')   # 珊瑚金（装饰线、重要标记）
COLOR_ACCENT_LIGHT   = HexColor('#F2D9B8')   # 浅珊瑚金（高亮背景）
COLOR_ACCENT_PALE    = HexColor('#FDF6EE')   # 极浅珊瑚金（温和强调）

# ◆ 辅助色：青瓷色 (Celadon)
COLOR_CELADON        = HexColor('#2D8B7A')   # 青瓷色（评分、正向指标）
COLOR_CELADON_LIGHT  = HexColor('#C8E6DE')   # 浅青瓷（正向背景）
COLOR_CELADON_PALE   = HexColor('#F0F8F5')   # 极浅青瓷（正向行背景）

# ◆ 功能色：风险等级
COLOR_DANGER         = HexColor('#C0392B')   # 高风险红
COLOR_DANGER_LIGHT   = HexColor('#F5D6D4')   # 浅红（风险背景）
COLOR_WARNING        = HexColor('#E67E22')   # 中风险橙
COLOR_WARNING_LIGHT  = HexColor('#FCE4CD')   # 浅橙（警告背景）
COLOR_SUCCESS        = HexColor('#27AE60')   # 低风险绿
COLOR_SUCCESS_LIGHT  = HexColor('#D5F0DF')   # 浅绿（安全背景）
COLOR_INFO           = HexColor('#2980B9')   # 信息蓝

# ◆ 中性色系
COLOR_TEXT           = HexColor('#2C3E50')   # 正文文字（深灰蓝）
COLOR_TEXT_SECONDARY = HexColor('#6B7D8E')   # 次要文字（中灰蓝）
COLOR_TEXT_MUTED     = HexColor('#9BA8B3')   # 弱化文字（浅灰蓝）
COLOR_WHITE          = white
COLOR_BLACK          = black

# ◆ 边框与分割
COLOR_BORDER         = HexColor('#DDE3EB')   # 表格边框（浅灰蓝）
COLOR_BORDER_DARK    = HexColor('#BCC5D1')   # 深边框
COLOR_DIVIDER        = HexColor('#EEF1F5')   # 分割线（极浅）

# ◆ 背景层级
COLOR_BG_PAGE        = HexColor('#FFFFFF')   # 页面背景
COLOR_BG_CARD        = HexColor('#F8FAFC')   # 卡片背景
COLOR_BG_TABLE_ALT   = HexColor('#F7F9FC')   # 表格交替行

# ◆ 板块专属色（12色环，用于图表区分）
COLOR_SECTOR_PALETTE = [
    '#2C4A7C', '#27AE60', '#D4945C', '#8E44AD',
    '#E67E22', '#2D8B7A', '#2980B9', '#C0392B',
    '#1B2D4E', '#D4A017', '#1ABC9C', '#7F8C8D',
    '#E74C3C', '#3498DB', '#2ECC71', '#9B59B6',
]

# 兼容旧别名
COLOR_PRIMARY_OLD = COLOR_PRIMARY
COLOR_GOLD = COLOR_ACCENT
COLOR_GOLD_LIGHT = COLOR_ACCENT_LIGHT
COLOR_HIGH_RISK = COLOR_DANGER
COLOR_MED_RISK = COLOR_WARNING
COLOR_LOW_RISK = COLOR_SUCCESS
COLOR_BG_LIGHT = COLOR_PRIMARY_BG
COLOR_BG_TABLE = COLOR_BG_TABLE_ALT
COLOR_BG_HIGHLIGHT = COLOR_ACCENT_PALE
COLOR_BG_RISK_HIGH = COLOR_DANGER_LIGHT
COLOR_BG_RISK_MED = COLOR_WARNING_LIGHT
COLOR_BG_RISK_LOW = COLOR_SUCCESS_LIGHT
COLOR_TEXT_LIGHT = COLOR_TEXT_SECONDARY
COLOR_TEXT_MUTED_OLD = COLOR_TEXT_MUTED
COLOR_DIVIDER_OLD = COLOR_DIVIDER


# ============================================================
# 二、字体系统
# ============================================================
FONT_REGISTERED = False
FONT_NORMAL = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_LIGHT = 'Helvetica'

def register_fonts():
    """注册中文字体，优先微软雅黑"""
    global FONT_REGISTERED, FONT_NORMAL, FONT_BOLD, FONT_LIGHT
    if FONT_REGISTERED:
        return

    font_candidates = [
        (r'C:\Windows\Fonts\msyh.ttc', 'MSYH', 'MSYH-Bold'),
        (r'C:\Windows\Fonts\msyhbd.ttc', None, 'MSYH-Bold'),
        (r'C:\Windows\Fonts\simhei.ttf', 'SimHei', 'SimHei'),
        (r'C:\Windows\Fonts\simsun.ttc', 'SimSun', 'SimSun-Bold'),
    ]

    normal_ok = False
    bold_ok = False

    for path, normal_name, bold_name in font_candidates:
        if not os.path.exists(path):
            continue
        try:
            if normal_name and not normal_ok:
                pdfmetrics.registerFont(TTFont(normal_name, path))
                FONT_NORMAL = normal_name
                normal_ok = True
            if bold_name and not bold_ok:
                bold_path = r'C:\Windows\Fonts\msyhbd.ttc' if 'MSYH' in bold_name else path
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                    FONT_BOLD = bold_name
                    bold_ok = True
                else:
                    FONT_BOLD = FONT_NORMAL
                    bold_ok = True
        except Exception:
            continue

    if not normal_ok:
        FONT_NORMAL = 'Helvetica'
        FONT_BOLD = 'Helvetica-Bold'
    if not bold_ok:
        FONT_BOLD = FONT_NORMAL
    FONT_LIGHT = FONT_NORMAL

    try:
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily(FONT_NORMAL, normal=FONT_NORMAL, bold=FONT_BOLD,
                           italic=FONT_NORMAL, boldItalic=FONT_BOLD)
    except Exception:
        pass

    FONT_REGISTERED = True


# ============================================================
# 三、页面布局
# ============================================================
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_TOP = 28 * mm
MARGIN_BOTTOM = 28 * mm
MARGIN_LEFT = 22 * mm
MARGIN_RIGHT = 22 * mm
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # ≈166mm


# ============================================================
# 四、段落样式集 ── 完整字体层级
# ============================================================
def get_styles():
    """获取统一段落样式集（v2.0层级化设计）"""
    register_fonts()
    base = getSampleStyleSheet()

    # ── 封面系列 ──
    cov_title = ParagraphStyle('CoverTitle', parent=base['Title'],
        fontName=FONT_BOLD, fontSize=30, leading=44,
        textColor=COLOR_WHITE, alignment=TA_CENTER, spaceAfter=14)
    cov_subtitle = ParagraphStyle('CoverSubtitle', parent=base['Normal'],
        fontName=FONT_NORMAL, fontSize=14, leading=22,
        textColor=COLOR_ACCENT_LIGHT, alignment=TA_CENTER, spaceAfter=8)
    cov_info = ParagraphStyle('CoverInfo', parent=base['Normal'],
        fontName=FONT_NORMAL, fontSize=11, leading=18,
        textColor=COLOR_WHITE, alignment=TA_CENTER, spaceAfter=4)
    cov_tag = ParagraphStyle('CoverTag', parent=base['Normal'],
        fontName=FONT_BOLD, fontSize=9, leading=12,
        textColor=COLOR_ACCENT, alignment=TA_CENTER)

    # ── 内页标题系列 ──
    sty_title = ParagraphStyle('ReportTitle', parent=base['Title'],
        fontName=FONT_BOLD, fontSize=24, leading=36,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER, spaceAfter=12)

    # H1: 章节标题（深蓝底白字 + 左侧金色竖线）
    sty_h1 = ParagraphStyle('SectionH1', parent=base['Heading1'],
        fontName=FONT_BOLD, fontSize=14, leading=20,
        textColor=COLOR_WHITE, alignment=TA_LEFT,
        backColor=COLOR_PRIMARY,
        borderPadding=(7, 14, 7, 14),
        spaceBefore=22, spaceAfter=12,
        leftIndent=0, rightIndent=0)

    # H2: 小节标题（深海蓝 + 左侧装饰条）
    sty_h2 = ParagraphStyle('SectionH2', parent=base['Heading2'],
        fontName=FONT_BOLD, fontSize=12, leading=17,
        textColor=COLOR_PRIMARY, alignment=TA_LEFT,
        spaceBefore=16, spaceAfter=7,
        borderPadding=(3, 0, 3, 8))

    # H3: 子标题（中蓝）
    sty_h3 = ParagraphStyle('SectionH3', parent=base['Heading3'],
        fontName=FONT_BOLD, fontSize=10.5, leading=15,
        textColor=COLOR_PRIMARY_LIGHT, alignment=TA_LEFT,
        spaceBefore=8, spaceAfter=5)

    # ── 正文系列 ──
    sty_body = ParagraphStyle('BodyText', parent=base['Normal'],
        fontName=FONT_NORMAL, fontSize=10, leading=17,
        textColor=COLOR_TEXT, alignment=TA_JUSTIFY,
        spaceAfter=8, firstLineIndent=0)

    sty_bullet = ParagraphStyle('BulletText', parent=sty_body,
        leftIndent=20, bulletIndent=8, spaceAfter=5)

    sty_lead = ParagraphStyle('LeadText', parent=sty_body,
        fontName=FONT_BOLD, fontSize=10.5, leading=18,
        textColor=COLOR_PRIMARY, spaceAfter=10)

    # ── 表格系列 ──
    sty_cell = ParagraphStyle('TableCell', parent=base['Normal'],
        fontName=FONT_NORMAL, fontSize=9, leading=13.5,
        textColor=COLOR_TEXT, alignment=TA_LEFT)

    sty_cell_center = ParagraphStyle('TableCellCenter', parent=sty_cell,
        alignment=TA_CENTER)

    sty_cell_right = ParagraphStyle('TableCellRight', parent=sty_cell,
        alignment=TA_RIGHT)

    sty_cell_bold = ParagraphStyle('TableCellBold', parent=sty_cell,
        fontName=FONT_BOLD)

    sty_header = ParagraphStyle('TableHeader', parent=base['Normal'],
        fontName=FONT_BOLD, fontSize=9, leading=13,
        textColor=COLOR_WHITE, alignment=TA_CENTER)

    sty_header_left = ParagraphStyle('TableHeaderLeft', parent=sty_header,
        alignment=TA_LEFT)

    # ── 特殊组件样式 ──
    sty_kpi_value = ParagraphStyle('KPIValue', parent=base['Normal'],
        fontName=FONT_BOLD, fontSize=24, leading=28,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER)

    sty_kpi_label = ParagraphStyle('KPILabel', parent=base['Normal'],
        fontName=FONT_NORMAL, fontSize=9, leading=12,
        textColor=COLOR_TEXT_MUTED, alignment=TA_CENTER)

    sty_badge = ParagraphStyle('Badge', parent=base['Normal'],
        fontName=FONT_BOLD, fontSize=8.5, leading=11,
        textColor=COLOR_WHITE, alignment=TA_CENTER)

    # ── 页眉页脚 ──
    sty_hf_text = ParagraphStyle('HeaderFooter', parent=base['Normal'],
        fontName=FONT_NORMAL, fontSize=7.5, leading=10,
        textColor=COLOR_TEXT_MUTED, alignment=TA_LEFT)

    # ── 免责声明 ──
    sty_disclaimer = ParagraphStyle('Disclaimer', parent=sty_body,
        fontSize=8, leading=12, textColor=COLOR_TEXT_MUTED,
        leftIndent=12, rightIndent=12, alignment=TA_JUSTIFY)

    # ── 公式 / 代码 ──
    sty_formula = ParagraphStyle('Formula', parent=sty_body,
        fontName='Courier', fontSize=9.5, leading=15,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER,
        backColor=COLOR_PRIMARY_BG,
        borderPadding=(6, 10, 6, 10), spaceBefore=8, spaceAfter=12)

    # ── 高亮框 ──
    sty_highlight = ParagraphStyle('Highlight', parent=sty_body,
        fontName=FONT_BOLD, fontSize=11, leading=17,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER,
        backColor=COLOR_ACCENT_PALE,
        borderColor=COLOR_ACCENT, borderWidth=0.5,
        borderPadding=(8, 12, 8, 12), spaceBefore=8, spaceAfter=12)

    return {
        # 封面
        'cover_title': cov_title, 'cover_subtitle': cov_subtitle,
        'cover_info': cov_info, 'cover_tag': cov_tag,
        # 标题
        'title': sty_title, 'h1': sty_h1, 'h2': sty_h2, 'h3': sty_h3,
        # 正文
        'body': sty_body, 'bullet': sty_bullet, 'lead': sty_lead,
        # 表格
        'cell': sty_cell, 'cell_center': sty_cell_center,
        'cell_right': sty_cell_right, 'cell_bold': sty_cell_bold,
        'header': sty_header, 'header_left': sty_header_left,
        # 组件
        'kpi_value': sty_kpi_value, 'kpi_label': sty_kpi_label,
        'badge': sty_badge, 'hf_text': sty_hf_text,
        # 其他
        'disclaimer': sty_disclaimer, 'formula': sty_formula,
        'highlight': sty_highlight,
        'subtitle': ParagraphStyle('Subtitle', parent=base['Normal'],
            fontName=FONT_NORMAL, fontSize=13, leading=20,
            textColor=COLOR_TEXT_SECONDARY, alignment=TA_CENTER, spaceAfter=8),
        'header_text': sty_hf_text, 'footer_text': sty_hf_text,
    }


# ============================================================
# 五、辅助函数
# ============================================================
def safe_get(data, key, default='—'):
    val = data.get(key, default) if isinstance(data, dict) else default
    if val is None or val == '':
        return default
    return val


def _is_numeric(val):
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
        styles = get_styles()
    text = str(text) if text is not None else '—'
    return Paragraph(text, styles.get(style_key, styles['cell']))


# ============================================================
# 六、表格组件 ── 卡片式专业表格
# ============================================================
def make_table(data, col_widths, styles, header_color=None, alt_rows=True,
               first_col_style=None):
    """创建专业样式表格（v2.0卡片式设计）

    Args:
        data:          表格数据（第一行为表头）
        col_widths:    列宽列表
        styles:        样式集
        header_color:  表头颜色（默认主色）
        alt_rows:      是否交替行背景
        first_col_style: 第一列样式 'bold'|'center'|None
    """
    if header_color is None:
        header_color = COLOR_PRIMARY

    table = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        # ── 表头 ──
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # ── 正文 ──
        ('FONTNAME', (0, 1), (-1, -1), FONT_NORMAL),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXT),
        # ── 边框：只有水平线（更简洁现代） ──
        ('LINEBELOW', (0, 0), (-1, 0), 2, COLOR_ACCENT),   # 表头下珊瑚金线
        ('LINEBELOW', (0, -1), (-1, -1), 1.2, COLOR_PRIMARY),  # 末行下深蓝线
        ('LINEABOVE', (0, 0), (-1, 0), 1.2, COLOR_PRIMARY),    # 表头上深蓝线
        ('INNERGRID', (0, 1), (-1, -1), 0.25, COLOR_DIVIDER),  # 内部极细线
        ('BOX', (0, 0), (-1, -1), 0.4, COLOR_BORDER),   # 外框细线
        # ── 内边距 ──
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    # 交替行背景
    if alt_rows:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), COLOR_BG_TABLE_ALT))
    # 第一列特殊样式
    if first_col_style == 'bold':
        for i in range(1, len(data)):
            style_cmds.append(('FONTNAME', (0, i), (0, i), FONT_BOLD))
    elif first_col_style == 'center':
        style_cmds.append(('ALIGN', (0, 1), (0, -1), 'CENTER'))

    table.setStyle(TableStyle(style_cmds))
    return table


def make_risk_table(data, col_widths, styles, risk_col=2):
    """风险表格：根据风险等级自动着色行背景"""
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NORMAL),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('LINEBELOW', (0, 0), (-1, 0), 2, COLOR_ACCENT),
        ('INNERGRID', (0, 1), (-1, -1), 0.25, COLOR_DIVIDER),
        ('BOX', (0, 0), (-1, -1), 0.4, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    for i in range(1, len(data)):
        risk_text = str(data[i][risk_col]) if risk_col < len(data[i]) else ''
        if '高' in risk_text:
            style_cmds += [
                ('BACKGROUND', (0, i), (-1, i), COLOR_DANGER_LIGHT),
                ('TEXTCOLOR', (risk_col, i), (risk_col, i), COLOR_DANGER),
                ('FONTNAME', (risk_col, i), (risk_col, i), FONT_BOLD)]
        elif '中' in risk_text:
            style_cmds += [
                ('BACKGROUND', (0, i), (-1, i), COLOR_WARNING_LIGHT),
                ('TEXTCOLOR', (risk_col, i), (risk_col, i), COLOR_WARNING),
                ('FONTNAME', (risk_col, i), (risk_col, i), FONT_BOLD)]
        elif '低' in risk_text:
            style_cmds += [
                ('BACKGROUND', (0, i), (-1, i), COLOR_SUCCESS_LIGHT),
                ('TEXTCOLOR', (risk_col, i), (risk_col, i), COLOR_SUCCESS),
                ('FONTNAME', (risk_col, i), (risk_col, i), FONT_BOLD)]
        elif i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), COLOR_BG_TABLE_ALT))
    table.setStyle(TableStyle(style_cmds))
    return table


# ============================================================
# 七、新型组件：KPI卡片 / 状态徽章 / 评分进度条 / 章节横幅
# ============================================================

def make_kpi_card(label, value, sub_text=None, color=None, width=50*mm):
    """KPI指标卡片：大数值 + 标签 + 副文本

    Args:
        label:    指标名称
        value:    指标数值
        sub_text: 副文本（可选）
        color:    数值颜色（默认主色）
        width:    卡片宽度
    """
    if color is None:
        color = COLOR_PRIMARY
    sty = get_styles()
    val_color = color

    # 构建内容
    cells = [[Paragraph(str(value), ParagraphStyle('KPIValue', parent=sty['kpi_value'],
                textColor=val_color))]]
    cells.append([Paragraph(label, sty['kpi_label'])])
    if sub_text:
        cells.append([Paragraph(str(sub_text), ParagraphStyle('KPISub',
            parent=sty['kpi_label'], fontSize=7.5, textColor=COLOR_TEXT_MUTED))])

    t = Table(cells, colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_CARD),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINEABOVE', (0, 0), (-1, 0), 3, color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return t


def make_kpi_row(cards):
    """KPI卡片行：将多个KPI卡片并排"""
    return Table([cards], colWidths=[c.minWidth() for c in cards])


def make_badge(text, badge_type='neutral', styles=None):
    """状态徽章：彩色标签

    Args:
        text:       徽章文字
        badge_type: 'success'|'warning'|'danger'|'info'|'neutral'|'primary'
    """
    if styles is None:
        styles = get_styles()

    color_map = {
        'success': (COLOR_SUCCESS, COLOR_SUCCESS_LIGHT),
        'warning': (COLOR_WARNING, COLOR_WARNING_LIGHT),
        'danger':  (COLOR_DANGER, COLOR_DANGER_LIGHT),
        'info':    (COLOR_INFO, COLOR_PRIMARY_BG),
        'primary': (COLOR_PRIMARY, COLOR_PRIMARY_PALE),
        'neutral': (COLOR_TEXT_SECONDARY, COLOR_BG_CARD),
    }
    fg, bg = color_map.get(badge_type, color_map['neutral'])

    badge_style = ParagraphStyle('BadgeInline', parent=styles['badge'],
        textColor=fg, backColor=bg,
        borderPadding=(2, 8, 2, 8), fontSize=8, leading=10)

    p = Paragraph(text, badge_style)
    t = Table([[p]], colWidths=[None])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def make_score_bar(score, max_score=10, width=80*mm, height=5*mm,
                   color=None, show_label=True, styles=None):
    """评分进度条：可视化分数

    Args:
        score:       当前分数
        max_score:   满分
        width:       总宽度
        height:      高度
        color:       颜色（自动根据分数选择）
        show_label:  是否显示分数标签
    """
    if styles is None:
        styles = get_styles()
    if color is None:
        if score >= 8:
            color = COLOR_SUCCESS
        elif score >= 6:
            color = COLOR_PRIMARY_LIGHT
        elif score >= 4:
            color = COLOR_WARNING
        else:
            color = COLOR_DANGER

    ratio = max(0.02, min(1.0, score / max_score))
    fill_width = width * ratio

    label_text = f'{score}/{max_score}' if show_label else ''

    # 使用两个嵌套表格模拟进度条
    bar_data = [['']]
    bar = Table(bar_data, colWidths=[width], rowHeights=[height])
    bar.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_DIVIDER),
        ('BOX', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ('LINEBEFORE', (0, 0), (0, 0), fill_width, color),
    ]))

    if show_label:
        label = Paragraph(label_text, ParagraphStyle('BarLabel', parent=styles['body'],
            fontSize=7.5, leading=9, textColor=COLOR_TEXT_SECONDARY, alignment=TA_RIGHT))
        return Table([[bar, label]], colWidths=[width, 20*mm])

    return bar


def make_section_banner(title, styles, color=None):
    """章节横幅：带装饰色条的标题

    Args:
        title:  章节标题
        styles: 样式集
        color:  装饰条颜色
    """
    if color is None:
        color = COLOR_PRIMARY

    bar = Table([['']], colWidths=[4*mm], rowHeights=[18])
    bar.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), color)]))

    p = Paragraph(title, styles['h2'])
    banner = Table([[bar, p]], colWidths=[4*mm, CONTENT_WIDTH - 4*mm])
    banner.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))
    return banner


def make_info_box(text, styles, box_color=None, text_color=None):
    """信息提示框：左边框色条 + 浅色背景"""
    if box_color is None:
        box_color = COLOR_PRIMARY_LIGHT
    if text_color is None:
        text_color = COLOR_TEXT

    style = ParagraphStyle('InfoBox', parent=styles['body'],
        fontSize=9.5, leading=15, textColor=text_color,
        leftIndent=8, rightIndent=8,
        backColor=COLOR_BG_CARD,
        borderColor=box_color, borderWidth=0,
        borderPadding=(6, 8, 6, 10))
    p = Paragraph(text, style)
    t = Table([[p]], colWidths=[CONTENT_WIDTH])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_CARD),
        ('LINEBEFORE', (0, 0), (0, -1), 3, box_color),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('BOX', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
    ]))
    return t


def make_section_divider(color=None):
    """章节分割线"""
    if color is None:
        color = COLOR_ACCENT
    t = Table([['']], colWidths=[CONTENT_WIDTH], rowHeights=[2])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, color),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, color),
    ]))
    return t


# ============================================================
# 八、页眉页脚（v2.0 双层设计）
# ============================================================
class HeaderFooterCanvas:
    """页眉页脚绘制器 v2.0 ── 双层设计 + 进度指示"""

    def __init__(self, report_title='量化分析报告', report_date=None):
        self.report_title = report_title
        self.report_date = report_date or datetime.now().strftime('%Y-%m-%d')

    def __call__(self, canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()

        # ═══════════════ 页眉 ═══════════════
        header_y = PAGE_HEIGHT - 16 * mm

        # 页眉背景色条（深蓝）
        canvas.setFillColor(COLOR_PRIMARY)
        canvas.rect(0, header_y - 3 * mm, PAGE_WIDTH, 10 * mm, fill=1, stroke=0)

        # 左侧：报告标题（白色）
        canvas.setFont(FONT_BOLD, 8.5)
        canvas.setFillColor(COLOR_WHITE)
        canvas.drawString(MARGIN_LEFT, header_y, self.report_title)

        # 右侧：日期
        canvas.setFont(FONT_NORMAL, 8)
        canvas.setFillColor(COLOR_ACCENT_LIGHT)
        canvas.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, header_y, self.report_date)

        # 页眉底部珊瑚金细线
        canvas.setStrokeColor(COLOR_ACCENT)
        canvas.setLineWidth(1)
        canvas.line(0, header_y - 4 * mm, PAGE_WIDTH, header_y - 4 * mm)

        # ═══════════════ 页脚 ═══════════════
        footer_y = 14 * mm

        # 页脚分割线（渐变效果用两段线模拟）
        canvas.setStrokeColor(COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_LEFT, footer_y + 3 * mm, PAGE_WIDTH - MARGIN_RIGHT, footer_y + 3 * mm)
        canvas.setStrokeColor(COLOR_ACCENT)
        canvas.setLineWidth(1.5)
        canvas.line(MARGIN_LEFT, footer_y + 3 * mm, MARGIN_LEFT + 40 * mm, footer_y + 3 * mm)

        # 页码（居中）
        canvas.setFont(FONT_BOLD, 9)
        canvas.setFillColor(COLOR_PRIMARY)
        canvas.drawCentredString(PAGE_WIDTH / 2, footer_y - 2 * mm, str(page_num))

        # 左下角：系统标识
        canvas.setFont(FONT_NORMAL, 7)
        canvas.setFillColor(COLOR_TEXT_MUTED)
        canvas.drawString(MARGIN_LEFT, footer_y - 8 * mm, 'Quant Rule Analyzer v2.0')

        # 右下角：机密标识
        canvas.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, footer_y - 8 * mm, 'CONFIDENTIAL')

        canvas.restoreState()


# ============================================================
# 九、封面页构建器（v2.0 深度重构）
# ============================================================
class CoverBackground(Flowable):
    """封面背景：深蓝渐变 + 装饰几何图形
    不占用布局空间，仅在 canvas 上绘制背景"""

    def __init__(self, width=PAGE_WIDTH, height=PAGE_HEIGHT):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        # 不占用布局空间，但仍在 draw() 中绘制
        return (0, 0)

    def draw(self):
        c = self.canv
        # 主背景：深蓝
        c.setFillColor(COLOR_PRIMARY_DARK)
        c.rect(-MARGIN_LEFT, -MARGIN_BOTTOM, self.width, self.height, fill=1, stroke=0)

        # 左侧装饰色块（中蓝）
        c.setFillColor(COLOR_PRIMARY_LIGHT)
        c.setFillAlpha(0.3)
        c.rect(-MARGIN_LEFT, self.height * 0.35, self.width * 0.45,
               self.height * 0.3, fill=1, stroke=0)
        c.setFillAlpha(1)

        # 顶部装饰线组
        c.setStrokeColor(COLOR_ACCENT)
        c.setLineWidth(2.5)
        c.line(0, self.height - 38 * mm, CONTENT_WIDTH, self.height - 38 * mm)
        c.setLineWidth(0.8)
        c.line(0, self.height - 42 * mm, CONTENT_WIDTH * 0.6, self.height - 42 * mm)

        # 底部装饰线组
        c.setLineWidth(1.5)
        c.line(0, 32 * mm, CONTENT_WIDTH, 32 * mm)
        c.setLineWidth(0.5)
        c.setStrokeColor(COLOR_ACCENT_LIGHT)
        c.line(0, 28 * mm, CONTENT_WIDTH * 0.4, 28 * mm)

        # 右上角装饰：大三角 + 小方块
        c.setFillColor(COLOR_ACCENT)
        c.setFillAlpha(0.15)
        # 三角
        path = c.beginPath()
        path.moveTo(CONTENT_WIDTH, self.height * 0.65)
        path.lineTo(CONTENT_WIDTH - 60 * mm, self.height * 0.65)
        path.lineTo(CONTENT_WIDTH, self.height * 0.65 + 40 * mm)
        path.close()
        c.drawPath(path, fill=1, stroke=0)
        c.setFillAlpha(1)

        # 几何方块
        c.setFillColor(COLOR_ACCENT)
        c.rect(CONTENT_WIDTH - 18 * mm, self.height - 52 * mm, 10 * mm, 10 * mm, fill=1, stroke=0)
        c.setFillColor(COLOR_PRIMARY_LIGHT)
        c.setFillAlpha(0.5)
        c.rect(CONTENT_WIDTH - 6 * mm, self.height - 48 * mm, 6 * mm, 6 * mm, fill=1, stroke=0)
        c.setFillAlpha(1)


def build_cover_page(story, styles, title, subtitle, info_items=None):
    """构建封面页 v2.0

    Args:
        story:      reportlab story列表
        styles:     样式集
        title:      报告主标题（支持换行符 \n）
        subtitle:   副标题
        info_items: 封面信息项 [{'label':..., 'value':...}, ...]
    """
    if info_items is None:
        info_items = []

    # ★ 关键：先添加深蓝背景（必须在所有文字元素之前）
    story.append(CoverBackground())

    # 顶部留白
    story.append(Spacer(1, 45 * mm))

    # 主标题区域装饰线
    story.append(Spacer(1, 8 * mm))

    # 主标题（支持多行）
    for line in title.split('\n'):
        story.append(Paragraph(line, styles['cover_title']))
    story.append(Spacer(1, 8 * mm))

    # 副标题
    story.append(Paragraph(subtitle, styles['cover_subtitle']))

    story.append(Spacer(1, 25 * mm))

    # 信息卡片区（白色半透明效果）
    if info_items:
        info_rows = []
        for item in info_items:
            label = item.get('label', '')
            value = item.get('value', '')
            info_rows.append([
                Paragraph(f'<font color="#C0C8D4">{label}</font>',
                          ParagraphStyle('CovL', parent=styles['cover_info'],
                              fontSize=10, textColor=HexColor('#C0C8D4'), alignment=TA_RIGHT)),
                Paragraph(str(value), ParagraphStyle('CovV', parent=styles['cover_info'],
                              fontSize=10, textColor=COLOR_WHITE, alignment=TA_LEFT, fontName=FONT_BOLD)),
            ])

        info_table = Table(info_rows, colWidths=[40 * mm, 90 * mm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)

    story.append(Spacer(1, 30 * mm))

    # 底部标识
    story.append(Paragraph('量化策略分析系统', ParagraphStyle('CovBot',
        parent=styles['cover_info'], fontSize=10, textColor=COLOR_ACCENT_LIGHT)))
    story.append(Paragraph('Quant Rule Analyzer v2.0', ParagraphStyle('CovBot2',
        parent=styles['cover_subtitle'], fontSize=9, textColor=COLOR_ACCENT_LIGHT)))

    story.append(PageBreak())


# ============================================================
# 十、文档构建器
# ============================================================
def create_doc(output_path, report_title='量化分析报告', report_date=None):
    register_fonts()
    doc = SimpleDocTemplate(
        output_path, pagesize=PAGE_SIZE,
        topMargin=MARGIN_TOP + 5 * mm,
        bottomMargin=MARGIN_BOTTOM + 5 * mm,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        title=report_title,
        author='量化策略分析系统',
    )
    hf = HeaderFooterCanvas(report_title=report_title, report_date=report_date)
    doc.headerFooterCallback = hf
    return doc, hf


def build_pdf(output_path, story, report_title='量化分析报告', report_date=None):
    register_fonts()
    doc = SimpleDocTemplate(
        output_path, pagesize=PAGE_SIZE,
        topMargin=MARGIN_TOP + 5 * mm,
        bottomMargin=MARGIN_BOTTOM + 5 * mm,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        title=report_title,
        author='量化策略分析系统',
    )
    hf = HeaderFooterCanvas(report_title=report_title, report_date=report_date)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return output_path


# ============================================================
# 十一、Matplotlib图表样式
# ============================================================
def setup_matplotlib_style():
    """配置matplotlib图表样式（v2.0 与报告色彩一致）"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # 配色
    plt.rcParams['axes.facecolor'] = '#F8FAFC'
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.edgecolor'] = '#DDE3EB'
    plt.rcParams['axes.labelcolor'] = '#2C3E50'
    plt.rcParams['xtick.color'] = '#6B7D8E'
    plt.rcParams['ytick.color'] = '#6B7D8E'
    plt.rcParams['axes.titlecolor'] = '#1B2D4E'
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9

    # 网格
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.color'] = '#EEF1F5'
    plt.rcParams['grid.linewidth'] = 0.5
    plt.rcParams['grid.alpha'] = 0.8

    # 线条
    plt.rcParams['axes.linewidth'] = 0.8
    plt.rcParams['lines.linewidth'] = 2.0
    plt.rcParams['lines.markersize'] = 6

    # 图例
    plt.rcParams['legend.fontsize'] = 9
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.facecolor'] = 'white'
    plt.rcParams['legend.edgecolor'] = '#DDE3EB'
    plt.rcParams['legend.framealpha'] = 0.9

    return plt


def get_sector_color(index):
    """获取板块配色"""
    return COLOR_SECTOR_PALETTE[index % len(COLOR_SECTOR_PALETTE)]


# ============================================================
# 十二、快捷样式对比对照表
# ============================================================
"""
┌─────────────────────┬──────────────────────────┬──────────────────────────┐
│ 组件                │ 旧版 (v1.x)              │ 新版 (v2.0)              │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 主色                │ #1a3a5c 深蓝             │ #1B2D4E 深海蓝           │
│ 强调色              │ #c9a96e 金色              │ #D4945C 珊瑚金           │
│ 辅助色              │ 无                       │ #2D8B7A 青瓷色           │
│ 封面                │ 纯色深蓝 + 简单装饰线     │ 渐变深蓝 + 几何图形      │
│ 页眉                │ 浅灰文字 + 单线           │ 深蓝底栏 + 白字 + 珊瑚线  │
│ 页脚                │ 简单页码                  │ 三层设计 + 进度指示      │
│ 表格                │ 网格边框 + 交替行         │ 水平线 + 交替行 + 卡片感  │
│ 字体层级            │ 4级                      │ 7级完整层级              │
│ 新增组件            │ 无                       │ KPI卡片/徽章/进度条/横幅  │
│ 风险表格            │ 行背景着色               │ 行背景 + 粗体文字 + 色标  │
│ 信息框              │ 左侧色条                 │ 左侧色条 + 卡片边框      │
│ 图表配色            │ 基础配置                 │ 完整色彩体系             │
└─────────────────────┴──────────────────────────┴──────────────────────────┘
"""