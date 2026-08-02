#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下周一走势分析报告 PDF 生成器
基于V9.3-ST策略规则，对下周多市场场景进行推演分析，生成标准化PDF报告。

用法:
    python generate_trend_report.py <input_json> <output_pdf>
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
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

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
    COLOR_SECTOR_PALETTE,
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
COLOR_HIGH = COLOR_DANGER
COLOR_MED = COLOR_WARNING
COLOR_LOW = COLOR_SUCCESS

# 场景配色（走势报告专用，v2.0 配色）
COLOR_SCENARIO = {
    'S1': COLOR_DANGER,        # 高开-红
    'S2': COLOR_SUCCESS,        # 平开-绿
    'S3': COLOR_WARNING,        # 低开-橙
    'S4': HexColor('#8E44AD'),  # 极端-紫
}

# 以下样式/辅助函数由共享模块 report_styles.py 提供：
#   register_fonts, get_styles, safe_get, make_para, make_table 等


# ============================================================
# 场景概率分布图
# ============================================================
def generate_scenario_chart(scenarios, output_path):
    """生成场景概率分布饼图（v2.0 配色）"""
    if not scenarios:
        return None

    setup_matplotlib_style()
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
    plt.rcParams['axes.unicode_minus'] = False

    labels = []
    sizes = []
    pie_colors = []
    for s in scenarios:
        prob_str = safe_get(s, 'probability', '0%').replace('%', '')
        try:
            prob = float(prob_str)
        except ValueError:
            prob = 25
        labels.append(f"{safe_get(s, 'scenario_name')}\n({safe_get(s, 'probability')})")
        sizes.append(prob)
        sid = safe_get(s, 'scenario_id', 'S1')
        # v2.0 场景配色
        color_map = {
            'S1': COLOR_DANGER,
            'S2': COLOR_SUCCESS,
            'S3': COLOR_WARNING,
            'S4': HexColor('#8E44AD'),
        }
        pie_colors.append(color_map.get(sid, COLOR_PRIMARY_LIGHT))

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('#FFFFFF')
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=pie_colors, autopct='%1.0f%%',
        startangle=90, textprops={'fontsize': 9, 'fontweight': 'bold', 'color': COLOR_TEXT},
        pctdistance=0.75, labeldistance=1.15
    )
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(11)

    ax.set_title('下周一市场场景概率分布', fontsize=13, fontweight='bold',
                 color=COLOR_PRIMARY, pad=20)
    ax.axis('equal')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    return output_path


# ============================================================
# 执行时间线图
# ============================================================
def generate_timeline_chart(timeline, output_path):
    """生成执行时间线图（v2.0 配色）"""
    if not timeline:
        return None

    setup_matplotlib_style()
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
    plt.rcParams['axes.unicode_minus'] = False

    n_steps = len(timeline)
    fig_height = max(7, n_steps * 0.9)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, n_steps + 1)
    ax.axis('off')

    box_w = 8.5
    box_h = 0.65
    x_center = 5.0
    y_start = n_steps + 0.3

    for i, step in enumerate(timeline):
        y = y_start - i - 0.5
        action = str(safe_get(step, 'action', ''))
        is_key = '关键' in action or '暴雨' in action or '买入' in action or '执行' in action
        color = COLOR_DANGER if is_key else COLOR_PRIMARY_LIGHT

        box = FancyBboxPatch(
            (x_center - box_w / 2, y - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.1",
            facecolor=color, edgecolor=COLOR_PRIMARY_DARK, linewidth=1.2, alpha=0.92
        )
        ax.add_patch(box)

        circle = plt.Circle((x_center - box_w / 2 + 0.3, y), 0.18,
                            color='white', alpha=0.9, zorder=5)
        ax.add_patch(circle)
        ax.text(x_center - box_w / 2 + 0.3, y, str(safe_get(step, 'step', i + 1)),
                ha='center', va='center', fontsize=8, fontweight='bold',
                color=color, zorder=6)

        time_str = f"[{safe_get(step, 'time', '')}] " if safe_get(step, 'time', '') != '—' else ""
        label = f"{time_str}{action}"
        ax.text(x_center + 0.1, y, label,
                ha='center', va='center', fontsize=7.5, color='white',
                fontweight='bold', zorder=6, wrap=True)

        if i < n_steps - 1:
            arrow = FancyArrowPatch(
                (x_center, y - box_h / 2 - 0.05),
                (x_center, y - 0.95 + box_h / 2 + 0.05),
                arrowstyle='->,head_width=0.3,head_length=0.2',
                color=COLOR_TEXT_SECONDARY, linewidth=1.5
            )
            ax.add_patch(arrow)

    ax.text(x_center, y_start + 0.4, '下周一执行时间线',
            ha='center', va='center', fontsize=13, fontweight='bold',
            color=COLOR_PRIMARY)

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
    build_cover_page(story, styles,
                     title='下周一走势分析报告',
                     subtitle='基于V9.3-ST策略规则的场景推演',
                     info_items=[
                         {'label': '目标日期', 'value': safe_get(meta, 'target_date')},
                         {'label': '使用策略', 'value': safe_get(meta, 'strategy_used')},
                         {'label': '策略版本', 'value': safe_get(meta, 'strategy_version')},
                         {'label': '分析类型', 'value': safe_get(meta, 'analysis_type')},
                         {'label': '分析日期', 'value': safe_get(meta, 'analysis_date')},
                         {'label': '数据来源', 'value': safe_get(meta, 'data_source')},
                     ])


def build_metadata(story, data, styles):
    """分析概述"""
    meta = data.get('metadata', {})
    story.append(Paragraph('一、分析概述', styles['h1']))

    story.append(make_section_banner('1.1 分析背景', styles))
    story.append(Paragraph(
        f"本报告针对 {safe_get(meta, 'target_date')} 进行走势场景推演，"
        f"基于 {safe_get(meta, 'strategy_used')} 的交易规则体系，"
        "对四种可能的市场场景（高开高走、平开震荡、低开低走、极端暴跌）进行策略执行推演，"
        "输出各场景下的仓位决策、候选标的筛选逻辑与次日操作预案。",
        styles['body']
    ))

    story.append(make_section_banner('1.2 数据说明', styles))
    story.append(Paragraph(safe_get(meta, 'data_source'), styles['body']))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<b>重要提示：</b>{safe_get(meta, 'disclaimer')}",
        styles['highlight']
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_scenarios(story, data, styles, temp_dir):
    """市场场景分析"""
    scenarios = data.get('market_scenarios', [])
    story.append(Paragraph('二、市场场景分析', styles['h1']))

    if not scenarios:
        story.append(Paragraph('未配置市场场景。', styles['body']))
        return

    # 场景概率分布图
    chart_path = os.path.join(temp_dir, 'scenario_chart.png')
    try:
        generate_scenario_chart(scenarios, chart_path)
        if os.path.exists(chart_path):
            img = Image(chart_path, width=140 * mm, height=90 * mm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 8 * mm))
    except Exception as e:
        story.append(Paragraph(f'[场景图生成失败: {e}]', styles['body']))

    # 各场景详细分析
    for s in scenarios:
        sid = safe_get(s, 'scenario_id', 'S1')
        sname = safe_get(s, 'scenario_name', '场景')
        prob = safe_get(s, 'probability', '—')
        story.append(Paragraph(f'2.{sid[-1]} {sname}（概率：{prob}）', styles['h2']))

        # 场景假设
        story.append(Paragraph(f'<b>市场假设：</b>{safe_get(s, "market_assumption")}', styles['body']))

        # 关键指标
        indicators = s.get('key_indicators', {})
        if indicators:
            ind_data = [['指标', '数值']]
            label_map = {
                'index_open': '指数开盘',
                'volume': '成交量',
                'sentiment': '市场情绪',
                'limit_up_count': '涨停数量',
                'limit_down_count': '跌停数量',
            }
            for k, label in label_map.items():
                if k in indicators:
                    ind_data.append([
                        make_para(label, 'cell', styles),
                        make_para(safe_get(indicators, k), 'cell', styles)
                    ])
            story.append(make_table(ind_data, [50 * mm, 90 * mm], styles))
            story.append(Spacer(1, 3 * mm))

        # 策略执行
        execution = s.get('strategy_execution', {})
        if execution:
            story.append(Paragraph('<b>策略执行推演：</b>', styles['body']))
            exec_data = [['执行项', '推演结果']]
            exec_map = [
                ('f91_check', 'F91暴雨航行检测'),
                ('s6_temperature', 'S6市场温度'),
                ('position_limit', '仓位上限'),
                ('f90_classification', 'F90追涨/抄底分类'),
                ('candidate_pool', '候选标的池'),
                ('f92_assessment', 'F92主力承接评估'),
                ('scoring_focus', '评分重点'),
                ('execution_decision', '执行决策'),
                ('buy_window', '买入窗口'),
                ('next_day_action', '次日操作'),
            ]
            for k, label in exec_map:
                if k in execution:
                    exec_data.append([
                        make_para(label, 'cell', styles),
                        make_para(safe_get(execution, k), 'cell', styles)
                    ])
            story.append(make_table(exec_data, [45 * mm, 95 * mm], styles))
            story.append(Spacer(1, 3 * mm))

        # 风险提示与预期结果
        story.append(Paragraph(f'<b>风险提示：</b>{safe_get(s, "risk_alert")}', styles['body']))
        story.append(Paragraph(f'<b>预期结果：</b>{safe_get(s, "expected_outcome")}', styles['body']))
        story.append(Spacer(1, 6 * mm))

    story.append(make_section_divider())


def build_decision_matrix(story, data, styles):
    """场景决策矩阵"""
    matrix = data.get('scenario_decision_matrix', [])
    story.append(Paragraph('三、场景决策矩阵', styles['h1']))

    if not matrix:
        story.append(Paragraph('未配置决策矩阵。', styles['body']))
        return

    story.append(make_section_banner('3.1 各市场状态下策略执行对照表', styles))

    matrix_data = [['市场状态', 'F91状态', '仓位上限', '候选策略', '优先因子', '风险等级']]
    for m in matrix:
        matrix_data.append([
            make_para(safe_get(m, 'market_state'), 'cell', styles),
            make_para(safe_get(m, 'f91_status'), 'cell_center', styles),
            make_para(safe_get(m, 'position_limit'), 'cell_center', styles),
            make_para(safe_get(m, 'candidate_strategy'), 'cell', styles),
            make_para(safe_get(m, 'priority_factor'), 'cell', styles),
            make_para(safe_get(m, 'risk_level'), 'cell_center', styles),
        ])

    table = make_table(matrix_data, [28 * mm, 22 * mm, 25 * mm, 35 * mm, 35 * mm, 20 * mm], styles)

    # 风险等级颜色
    style_cmds = []
    for i, m in enumerate(matrix, 1):
        level = safe_get(m, 'risk_level')
        if level == '高':
            color = COLOR_HIGH
        elif level == '中高':
            color = HexColor('#D35400')
        elif level == '中':
            color = COLOR_MED
        else:
            color = COLOR_LOW
        style_cmds.append(('TEXTCOLOR', (5, i), (5, i), color))
        style_cmds.append(('FONTNAME', (5, i), (5, i), FONT_BOLD))
    if style_cmds:
        table.setStyle(TableStyle(style_cmds))

    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_timeline(story, data, styles, temp_dir):
    """执行时间线"""
    timeline = data.get('execution_timeline', [])
    story.append(Paragraph('四、下周一执行时间线', styles['h1']))

    if not timeline:
        story.append(Paragraph('未配置执行时间线。', styles['body']))
        return

    # 时间线图
    chart_path = os.path.join(temp_dir, 'timeline.png')
    try:
        generate_timeline_chart(timeline, chart_path)
        if os.path.exists(chart_path):
            img = Image(chart_path, width=155 * mm, height=110 * mm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 8 * mm))
    except Exception as e:
        story.append(Paragraph(f'[时间线图生成失败: {e}]', styles['body']))

    # 步骤详表
    story.append(make_section_banner('4.1 执行步骤详表', styles))
    tl_data = [['步骤', '时间', '执行动作', '详细说明']]
    for step in timeline:
        tl_data.append([
            make_para(safe_get(step, 'step'), 'cell_center', styles),
            make_para(safe_get(step, 'time'), 'cell_center', styles),
            make_para(safe_get(step, 'action'), 'cell', styles),
            make_para(safe_get(step, 'detail'), 'cell', styles),
        ])
    story.append(make_table(tl_data, [12 * mm, 22 * mm, 45 * mm, 86 * mm], styles))
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_risk_alerts(story, data, styles):
    """风险预警"""
    risks = data.get('key_risk_alerts', [])
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


def build_recommendations(story, data, styles):
    """操作建议"""
    recs = data.get('operation_recommendations', [])
    story.append(Paragraph('六、操作建议', styles['h1']))

    if not recs:
        story.append(Paragraph('暂无操作建议。', styles['body']))
        return

    rec_data = [['场景', '操作建议', '优先级', '决策依据']]
    for r in recs:
        rec_data.append([
            make_para(safe_get(r, 'scenario'), 'cell', styles),
            make_para(safe_get(r, 'action'), 'cell', styles),
            make_para(safe_get(r, 'priority'), 'cell_center', styles),
            make_para(safe_get(r, 'rationale'), 'cell', styles),
        ])

    table = make_table(rec_data, [35 * mm, 55 * mm, 15 * mm, 60 * mm], styles)

    style_cmds = []
    for i, r in enumerate(recs, 1):
        priority = safe_get(r, 'priority')
        if priority == '高':
            style_cmds.append(('TEXTCOLOR', (2, i), (2, i), COLOR_HIGH))
            style_cmds.append(('FONTNAME', (2, i), (2, i), FONT_BOLD))
        elif priority == '中':
            style_cmds.append(('TEXTCOLOR', (2, i), (2, i), COLOR_MED))
            style_cmds.append(('FONTNAME', (2, i), (2, i), FONT_BOLD))
    if style_cmds:
        table.setStyle(TableStyle(style_cmds))

    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_summary(story, data, styles):
    """总结"""
    summary = data.get('summary', {})
    story.append(Paragraph('七、分析总结', styles['h1']))

    story.append(make_section_banner('7.1 核心观点', styles))
    story.append(Paragraph(safe_get(summary, 'core_view'), styles['body']))

    story.append(make_section_banner('7.2 关键关注点', styles))
    story.append(Paragraph(safe_get(summary, 'key_focus'), styles['body']))

    story.append(make_section_banner('7.3 仓位指引', styles))
    story.append(Paragraph(safe_get(summary, 'position_guidance'), styles['body']))

    story.append(make_section_banner('7.4 风险优先级', styles))
    story.append(Paragraph(safe_get(summary, 'risk_priority'), styles['body']))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(safe_get(summary, 'action_principle'), styles['highlight']))
    story.append(Spacer(1, 4 * mm))
    story.append(make_section_divider())


def build_disclaimer(story, styles):
    """免责声明"""
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph('免责声明', styles['h2']))
    disclaimer_text = (
        '本报告由 AI 基于 V9.3-ST 超短线量化交易模型规则自动生成，'
        '仅基于策略规则对下周一可能的市场场景进行推演分析，'
        '<b>不构成任何投资建议，非真实走势预测</b>。'
        '报告中的场景假设、概率分布与执行推演基于策略文本的逻辑推断，'
        '实际市场走势需以实时数据为准。'
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

    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    temp_dir = tempfile.mkdtemp(prefix='trend_report_')

    meta = data.get('metadata', {})
    target_date = safe_get(meta, 'target_date', '')
    report_title = f'下周一走势分析报告 - {target_date}'
    report_date = safe_get(meta, 'analysis_date', datetime.now().strftime('%Y-%m-%d'))

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

    build_cover(story, data, styles)
    build_metadata(story, data, styles)
    build_scenarios(story, data, styles, temp_dir)
    build_decision_matrix(story, data, styles)
    build_timeline(story, data, styles, temp_dir)
    build_risk_alerts(story, data, styles)
    build_recommendations(story, data, styles)
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
        print('用法: python generate_trend_report.py <input_json> <output_pdf>')
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f'错误: 输入文件不存在: {input_file}')
        sys.exit(1)

    generate_report(input_file, output_file)
