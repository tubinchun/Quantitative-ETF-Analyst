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

# 导入共享样式模块
from report_styles import (
    register_fonts, get_styles, safe_get, make_para, make_table,
    make_risk_table, make_info_box, make_section_divider, make_section_banner,
    make_badge, make_score_bar, make_kpi_card,
    build_cover_page, build_pdf, setup_matplotlib_style,
    HeaderFooterCanvas, create_doc,
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_PRIMARY_DARK,
    COLOR_ACCENT, COLOR_ACCENT_LIGHT,
    COLOR_DANGER, COLOR_WARNING, COLOR_SUCCESS, COLOR_INFO,
    COLOR_BG_LIGHT, COLOR_BG_TABLE_ALT, COLOR_ACCENT_PALE,
    COLOR_DANGER_LIGHT, COLOR_WARNING_LIGHT, COLOR_SUCCESS_LIGHT,
    COLOR_TEXT, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_WHITE,
    COLOR_BORDER, COLOR_BORDER_DARK, COLOR_DIVIDER,
    FONT_NORMAL, FONT_BOLD, FONT_LIGHT,
    PAGE_SIZE, PAGE_WIDTH, PAGE_HEIGHT,
    MARGIN_TOP, MARGIN_BOTTOM, MARGIN_LEFT, MARGIN_RIGHT, CONTENT_WIDTH,
)

# 兼容旧代码中的别名
COLOR_SECONDARY = COLOR_PRIMARY_LIGHT
COLOR_GOLD = COLOR_ACCENT
COLOR_GOLD_LIGHT = COLOR_ACCENT_LIGHT
COLOR_HIGH_RISK = COLOR_DANGER
COLOR_MED_RISK = COLOR_WARNING
COLOR_LOW_RISK = COLOR_SUCCESS
COLOR_BG_TABLE = COLOR_BG_TABLE_ALT
COLOR_BG_HIGHLIGHT = COLOR_ACCENT_PALE
COLOR_BG_RISK_HIGH = COLOR_DANGER_LIGHT
COLOR_BG_RISK_MED = COLOR_WARNING_LIGHT
COLOR_BG_RISK_LOW = COLOR_SUCCESS_LIGHT
COLOR_TEXT_LIGHT = COLOR_TEXT_SECONDARY
COLOR_ACCENT_RED = COLOR_DANGER  # 旧项目符号中的 COLOR_ACCENT


# ============================================================
# 流程图生成
# ============================================================
def generate_flowchart(logic_flow, model_name, output_path):
    """使用 matplotlib 生成决策流程图（v2.0 配色：优化版、增大字体、动态尺寸、中文支持）"""
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
    ax.set_facecolor('#F8FAFC')
    fig.patch.set_facecolor('white')

    # 增大盒子尺寸和字体
    box_w = 11.0  # 增加盒子宽度
    box_h = 0.95  # 增加盒子高度
    x_center = fig_width / 2
    y_start = n_steps + 1.0

    colors = ['#2C4A7C', '#1B2D4E', '#2980B9', '#2D8B7A', '#2C4A7C',
              '#1B2D4E', '#2980B9', '#2D8B7A', '#C0392B', '#E67E22']

    for i, step in enumerate(logic_flow):
        y = y_start - i - 0.6
        color = colors[i % len(colors)]
        is_alert = '暴雨' in str(step.get('action', '')) or '极端' in str(step.get('output', ''))
        if is_alert:
            color = '#C0392B'

        # 绘制圆角矩形
        box = FancyBboxPatch(
            (x_center - box_w / 2, y - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.12",
            facecolor=color, edgecolor=COLOR_PRIMARY_DARK, linewidth=1.5,
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
                color=COLOR_TEXT_SECONDARY, linewidth=2.0,
                mutation_scale=1.5
            )
            ax.add_patch(arrow)

    # 标题 - 增大字号
    ax.text(x_center, y_start + 0.6, f'{model_name} 决策流程',
            ha='center', va='center', fontsize=16, fontweight='bold',
            color=COLOR_PRIMARY)

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
    story.append(make_table(table_data, [40 * mm, 130 * mm], styles))
    story.append(Spacer(1, 6 * mm))
    story.append(make_section_divider())


def build_strategy_overview(story, data, styles):
    """维度2：核心交易策略概述"""
    overview = data.get('strategy_overview', {})
    story.append(Paragraph('二、核心交易策略概述', styles['h1']))

    # 模型定位
    story.append(make_section_banner('2.1 模型定位', styles))
    story.append(Paragraph(safe_get(overview, 'positioning'), styles['body']))

    # 核心因子体系
    story.append(make_section_banner('2.2 核心因子体系', styles))
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
    story.append(make_section_banner('2.3 评分公式', styles, color=COLOR_ACCENT))
    formula = safe_get(overview, 'scoring_formula')
    if formula and formula != '—':
        story.append(make_info_box(formula, styles, box_color=COLOR_ACCENT))
    else:
        story.append(Paragraph('文档未提及评分公式。', styles['body']))

    # 决策阈值
    story.append(make_section_banner('2.4 决策阈值', styles))
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
    story.append(make_section_banner('2.5 核心交易纪律', styles))
    rules = overview.get('key_rules', [])
    if rules:
        for rule in rules:
            story.append(Paragraph(f'• {rule}', styles['bullet']))
    else:
        story.append(Paragraph('文档未提及核心交易纪律。', styles['body']))

    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


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
    story.append(make_section_banner('3.1 流程步骤说明', styles))
    flow_data = [['步骤', '时间', '执行动作', '触发条件', '输出/结果']]
    for step in logic_flow:
        flow_data.append([
            make_para(safe_get(step, 'step'), 'cell_center', styles),
            make_para(safe_get(step, 'time'), 'cell_center', styles),
            make_para(safe_get(step, 'action'), 'cell', styles),
            make_para(safe_get(step, 'condition'), 'cell', styles),
            make_para(safe_get(step, 'output'), 'cell', styles),
        ])
    story.append(make_table(flow_data, [12 * mm, 18 * mm, 45 * mm, 50 * mm, 45 * mm], styles))

    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


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
        story.append(make_section_banner(title, styles))
        if items:
            param_data = [['参数名', '取值/规则', '触发条件', '数据来源']]
            for p in items:
                param_data.append([
                    make_para(safe_get(p, 'name'), 'cell', styles),
                    make_para(safe_get(p, 'value'), 'cell', styles),
                    make_para(safe_get(p, 'condition'), 'cell', styles),
                    make_para(safe_get(p, 'source'), 'cell', styles),
                ])
            story.append(make_table(param_data, [35 * mm, 55 * mm, 45 * mm, 35 * mm], styles))
        else:
            story.append(Paragraph('文档未提及此类参数。', styles['body']))
        story.append(Spacer(1, 4 * mm))

    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_risk_analysis(story, data, styles):
    """维度5：潜在风险点分析"""
    risks = data.get('risk_analysis', [])
    story.append(Paragraph('五、潜在风险点分析', styles['h1']))

    if not risks:
        story.append(Paragraph('未识别到明确的风险点。', styles['body']))
        return

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
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_effectiveness(story, data, styles):
    """维度6：规则有效性评估"""
    eff = data.get('effectiveness_evaluation', {})
    story.append(Paragraph('六、规则有效性评估', styles['h1']))

    # 优势与不足并排
    story.append(make_section_banner('6.1 优势与不足', styles))
    strengths = eff.get('strengths', [])
    weaknesses = eff.get('weaknesses', [])

    strengths_text = '<br/>'.join([f'• {s}' for s in strengths]) if strengths else '未识别到明确优势'
    weaknesses_text = '<br/>'.join([f'• {w}' for w in weaknesses]) if weaknesses else '未识别到明确不足'

    sw_data = [
        [make_para('优势', 'header', styles), make_para('不足', 'header', styles)],
        [make_para(strengths_text, 'cell', styles), make_para(weaknesses_text, 'cell', styles)],
    ]
    sw_table = Table(sw_data, colWidths=[85 * mm, 85 * mm])
    sw_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), COLOR_SUCCESS),
        ('BACKGROUND', (1, 0), (1, 0), COLOR_DANGER),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 1), (-1, 1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sw_table)
    story.append(Spacer(1, 6 * mm))

    # 评估详情
    story.append(make_section_banner('6.2 评估详情', styles))
    eval_data = [
        ['回测验证状态', safe_get(eff, 'backtesting_status')],
        ['市场环境适应性', safe_get(eff, 'adaptability')],
        ['完整性评分', f'{safe_get(eff, "completeness")} / 10'],
        ['评分理由', safe_get(eff, 'completeness_reason')],
    ]
    eval_table_data = [['评估项', '结果']] + [
        [make_para(k, 'cell', styles), make_para(v, 'cell', styles)] for k, v in eval_data
    ]
    story.append(make_table(eval_table_data, [40 * mm, 130 * mm], styles))
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_optimization(story, data, styles):
    """维度7：优化建议"""
    suggestions = data.get('optimization_suggestions', [])
    story.append(Paragraph('七、优化建议', styles['h1']))

    if not suggestions:
        story.append(Paragraph('暂无优化建议。', styles['body']))
        return

    sug_data = [['建议内容', '优先级', '预期效果', '实施难度']]
    for s in suggestions:
        sug_data.append([
            make_para(safe_get(s, 'suggestion'), 'cell', styles),
            make_para(safe_get(s, 'priority'), 'cell_center', styles),
            make_para(safe_get(s, 'expected_effect'), 'cell', styles),
            make_para(safe_get(s, 'difficulty'), 'cell_center', styles),
        ])

    table = make_table(sug_data, [65 * mm, 18 * mm, 60 * mm, 27 * mm], styles)

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

    metadata = data.get('metadata', {})
    model_name = safe_get(metadata, 'model_name', '量化交易规则')
    report_title = f'量化交易规则分析报告 - {model_name}'
    report_date = datetime.now().strftime('%Y-%m-%d')

    # 创建文档（使用共享样式模块的页眉页脚）
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP + 5 * mm,
        bottomMargin=MARGIN_BOTTOM + 5 * mm,
        title=report_title,
        author='量化策略分析系统',
    )

    story = []

    # 构建封面页（使用共享样式模块的封面构建器）
    build_cover_page(story, styles,
                     title=f'{model_name} 分析报告',
                     subtitle='量化交易规则结构化分析',
                     info_items=[
                         {'label': '模型名称', 'value': model_name},
                         {'label': '模型版本', 'value': safe_get(metadata, 'model_version')},
                         {'label': '模型类型', 'value': safe_get(metadata, 'model_type')},
                         {'label': '分析日期', 'value': report_date},
                         {'label': '分析框架', 'value': '七维结构化分析'},
                     ])

    # 构建各章节
    build_metadata(story, data, styles)
    build_strategy_overview(story, data, styles)
    build_logic_flow(story, data, styles, temp_dir)
    build_key_parameters(story, data, styles)
    build_risk_analysis(story, data, styles)
    build_effectiveness(story, data, styles)
    build_optimization(story, data, styles)
    build_disclaimer(story, styles)

    # 构建 PDF（使用共享样式模块的页眉页脚）
    hf = HeaderFooterCanvas(report_title=report_title, report_date=report_date)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)

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