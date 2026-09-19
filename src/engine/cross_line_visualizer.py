"""
Visual Renderer for Cross Line Matka Patterns
==============================================
Renders side-by-side or stacked HTML panel chart snippets with SVG connecting arrows:
1. Current Trailing Line (Vertical / Diagonal)
2. Earlier Historical Cross Line (Diagonal / Step / Horizontal)
"""

from typing import Dict, Any, List, Optional
from src.config import get_jodi_family, CUT_NUMBERS

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_COLS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
DAY_MARATHI = {"Mon": "सोम", "Tue": "मंगळ", "Wed": "बुध", "Thu": "गुरु", "Fri": "शुक्र", "Sat": "शनि", "Sun": "रवि"}

RED_JODIS = {
    "00", "11", "22", "33", "44", "55", "66", "77", "88", "99",
    "05", "50", "16", "61", "27", "72", "38", "83", "49", "94"
}

def render_cross_line_panel_html(
    grid_snippet: List[Dict[str, Any]],
    highlighted_nodes: List[Dict[str, Any]],
    title: str,
    line_color: str = "#00d2ff",
    proj_node: Optional[Dict[str, Any]] = None,
    show_only_days: Optional[List[str]] = None
) -> str:
    """
    Renders an HTML panel chart table for a small window of weeks (4-8 weeks)
    with SVG arrows connecting the highlighted nodes.
    """
    if not grid_snippet:
        return ""

    DATE_W = 90
    CELL_W = 65
    ROW_H = 48
    HEADER_H = 28

    # Determine which days to display
    days_to_show = show_only_days if show_only_days is not None else DAY_ORDER
    day_col_map = {d: i for i, d in enumerate(days_to_show)}
    total_w = DATE_W + len(days_to_show) * CELL_W
    svg_h = HEADER_H + len(grid_snippet) * ROW_H

    # Map (date_range, day) -> (row_idx, col_idx)
    date_to_row = {w.get("date_range", ""): r for r, w in enumerate(grid_snippet)}

    # Collect coordinates for SVG line
    coords = []
    for node in highlighted_nodes:
        dr = node.get("date_range", "")
        day = node.get("day", "")
        if dr in date_to_row and day in day_col_map:
            r = date_to_row[dr]
            c = day_col_map[day]
            cx = DATE_W + c * CELL_W + CELL_W / 2
            cy = HEADER_H + r * ROW_H + ROW_H / 2
            coords.append((cx, cy, node.get("jodi", ""), node.get("step", 1), node.get("match_type", "EXACT")))

    # Check projection node
    proj_coord = None
    if proj_node:
        p_dr = proj_node.get("date_range", "")
        p_day = proj_node.get("day", "")
        if p_dr in date_to_row and p_day in day_col_map:
            pr = date_to_row[p_dr]
            pc = day_col_map[p_day]
            px = DATE_W + pc * CELL_W + CELL_W / 2
            py = HEADER_H + pr * ROW_H + ROW_H / 2
            proj_coord = (px, py, proj_node.get("jodi", ""))

    import math

    # SVG lines & arrows
    svg_elements = []
    # Marker definition
    marker_id = f"arr_{line_color.lstrip('#')}"
    defs = f"""<defs>
        <marker id="{marker_id}" markerWidth="10" markerHeight="10" refX="7" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="{line_color}" />
        </marker>
        <marker id="arr_proj" markerWidth="10" markerHeight="10" refX="7" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#ff007f" />
        </marker>
    </defs>"""

    # Draw lines between consecutive points
    for i in range(len(coords) - 1):
        x1, y1, _, _, _ = coords[i]
        x2, y2, _, _, _ = coords[i+1]
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist > 32:
            sx = x1 + (dx / dist) * 16
            sy = y1 + (dy / dist) * 16
            ex = x2 - (dx / dist) * 16
            ey = y2 - (dy / dist) * 16
        else:
            sx, sy, ex, ey = x1, y1, x2, y2

        svg_elements.append(
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="{line_color}" stroke-width="2.5" stroke-dasharray="6,3" '
            f'marker-end="url(#{marker_id})" opacity="0.95" />'
        )

    # Draw line to projected point if available
    if coords and proj_coord:
        x1, y1, _, _, _ = coords[-1]
        x2, y2, _ = proj_coord
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist > 32:
            sx = x1 + (dx / dist) * 16
            sy = y1 + (dy / dist) * 16
            ex = x2 - (dx / dist) * 16
            ey = y2 - (dy / dist) * 16
        else:
            sx, sy, ex, ey = x1, y1, x2, y2

        svg_elements.append(
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="#ff007f" stroke-width="3" stroke-dasharray="5,2" '
            f'marker-end="url(#arr_proj)" opacity="0.98" />'
        )

    svg_overlay = f"""<svg style="position:absolute;top:0;left:0;pointer-events:none;z-index:10;" 
        width="{total_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
        {defs}{''.join(svg_elements)}
    </svg>"""

    # Table Header
    thead = f"""<thead>
        <tr style="background:#201030;color:#ddd;font-size:11px;height:{HEADER_H}px;">
            <th style="border:1px solid #444;width:{DATE_W}px;text-align:center;">Date Range</th>
            {''.join([f'<th style="border:1px solid #444;width:{CELL_W}px;text-align:center;color:#00d2ff;">{DAY_MARATHI.get(d, d)}<br><span style="color:#888;font-size:9px;">{d}</span></th>' for d in days_to_show])}
        </tr>
    </thead>"""

    # Highlighted lookup: (date_range, day) -> info
    high_map = {(n["date_range"], n["day"]): n for n in highlighted_nodes}
    if proj_node:
        high_map[(proj_node["date_range"], proj_node["day"])] = {**proj_node, "is_proj": True}

    tbody_rows = ""
    for r_idx, w in enumerate(grid_snippet):
        dr = w.get("date_range", "")
        disp_dr = dr.replace(" to ", "<br>to<br>")
        date_td = f'<td style="font-size:9px;padding:2px;border:1px solid #333;background:#131322;color:#aaa;text-align:center;width:{DATE_W}px;line-height:1.2;">{disp_dr}</td>'
        
        day_tds = ""
        for d in days_to_show:
            cell = w.get("days", {}).get(d, {})
            jodi = cell.get("jodi", "")
            is_red = jodi in RED_JODIS

            node_info = high_map.get((dr, d))
            if node_info:
                if node_info.get("is_proj"):
                    # Target / Projected Jodi (Hot Pink Glow)
                    disp_j = node_info.get("jodi") or jodi
                    jodi_html = f'<div style="font-size:15px;font-weight:900;color:#fff;background:#ff007f;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;margin:auto;box-shadow:0 0 12px #ff007f;" title="Projected Target">{disp_j}</div>'
                else:
                    # Highlighted Touch Jodi (Glow Circle)
                    m_type = node_info.get("match_type", "EXACT")
                    border_c = line_color if m_type == "EXACT" else "#ffcc00"
                    jodi_html = f'<div style="font-size:15px;font-weight:bold;color:#fff;border:2.5px solid {border_c};border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;margin:auto;box-shadow:0 0 8px {border_c};">{jodi}</div>'
            else:
                if not jodi or jodi == "**":
                    jodi_html = '<div style="font-size:13px;color:#444;">--</div>'
                else:
                    color = "#ff3344" if is_red else "#888"
                    jodi_html = f'<div style="font-size:14px;color:{color};font-weight:600;">{jodi}</div>'

            bg = "#1a1a2e" if r_idx % 2 == 0 else "#141424"
            day_tds += f'<td style="border:1px solid #222;text-align:center;padding:1px;background:{bg};width:{CELL_W}px;height:{ROW_H}px;">{jodi_html}</td>'

        tbody_rows += f'<tr style="height:{ROW_H}px;">{date_td}{day_tds}</tr>'

    return f"""
<div style="background:#0a0a16;border:1px solid #333366;border-radius:10px;padding:10px;margin-bottom:12px;overflow-x:auto;">
    <div style="font-size:13px;font-weight:bold;color:{line_color};margin-bottom:8px;">{title}</div>
    <div style="position:relative;display:inline-block;min-width:100%;">
        {svg_overlay}
        <table style="width:{total_w}px;border-collapse:collapse;table-layout:fixed;position:relative;z-index:2;">
            {thead}
            <tbody>{tbody_rows}</tbody>
        </table>
    </div>
</div>
"""
