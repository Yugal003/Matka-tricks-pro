"""
Family Triangle (त्रिकोण स्कीम) Engine & Visualizer
===================================================
Discovers geometric Family Triangles in the latest 4-6 rows of Matka charts:
1. Completed Triangles: 3 nodes in the snippet that belong to the same 8-Jodi Family.
2. Projected Triangles: 2 existing nodes in the snippet pointing to the current target cell,
   predicting the winning Family Jodi group.
3. Interactive SVG Visualizer rendering geometric triangle overlays, polygons, and highlighted nodes.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
import datetime
import re
from src.config import get_jodi_family, CUT_NUMBERS
from src.storage.database import MatkaDatabase

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_COLS = {d: i for i, d in enumerate(DAY_ORDER)}
DAY_MARATHI = {"Mon": "सोमवार", "Tue": "मंगळवार", "Wed": "बुधवार", "Thu": "गुरुवार", "Fri": "शुक्रवार", "Sat": "शनिवार", "Sun": "रविवार"}

def compute_next_week_date_range(dr: str) -> str:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4}) to (\d{2})/(\d{2})/(\d{4})", dr)
    if m:
        s_d, s_m, s_y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        e_d, e_m, e_y = int(m.group(4)), int(m.group(5)), int(m.group(6))
        start_dt = datetime.date(s_y, s_m, s_d) + datetime.timedelta(days=7)
        span = (datetime.date(e_y, e_m, e_d) - datetime.date(s_y, s_m, s_d)).days
        end_dt = start_dt + datetime.timedelta(days=span)
        return f"{start_dt.strftime('%d/%m/%Y')} to {end_dt.strftime('%d/%m/%Y')}"
    m1 = re.search(r"(\d{2})/(\d{2})/(\d{4})", dr)
    if m1:
        d, mth, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        start_dt = datetime.date(y, mth, d) + datetime.timedelta(days=7)
        end_dt = start_dt + datetime.timedelta(days=6)
        return f"{start_dt.strftime('%d/%m/%Y')} to {end_dt.strftime('%d/%m/%Y')}"
    m2 = re.search(r"(\d{4})-(\d{2})-(\d{2}) [Tt]o (\d{4})-(\d{2})-(\d{2})", dr)
    if m2:
        s_y, s_m, s_d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        e_y, e_m, e_d = int(m2.group(4)), int(m2.group(5)), int(m2.group(6))
        start_dt = datetime.date(s_y, s_m, s_d) + datetime.timedelta(days=7)
        span = (datetime.date(e_y, e_m, e_d) - datetime.date(s_y, s_m, s_d)).days
        end_dt = start_dt + datetime.timedelta(days=span)
        return f"{start_dt.strftime('%Y-%m-%d')} To {end_dt.strftime('%Y-%m-%d')}"
    return "Next Week"

def should_advance_to_next_week(last_row: Dict[str, Any], target_day: Optional[str] = None) -> bool:
    if not last_row:
        return False
    # 1. Target day was already declared in the last row
    if target_day and target_day in last_row.get("days", {}):
        return True
    # 2. Date range has ended in real time (e.g. from 21-09-2026 onwards)
    dr = last_row.get("date_range", "")
    m = re.search(r"(\d{2})/(\d{2})/(\d{4}) to (\d{2})/(\d{2})/(\d{4})", dr)
    if m:
        e_d, e_m, e_y = int(m.group(4)), int(m.group(5)), int(m.group(6))
        if datetime.date.today() > datetime.date(e_y, e_m, e_d):
            return True
    m2 = re.search(r"(\d{4})-(\d{2})-(\d{2}) [Tt]o (\d{4})-(\d{2})-(\d{2})", dr)
    if m2:
        e_y, e_m, e_d = int(m2.group(4)), int(m2.group(5)), int(m2.group(6))
        if datetime.date.today() > datetime.date(e_y, e_m, e_d):
            return True
    return False

RED_JODIS = {
    "00", "11", "22", "33", "44", "55", "66", "77", "88", "99",
    "05", "50", "16", "61", "27", "72", "38", "83", "49", "94"
}

TRIANGLE_PALETTES = [
    {"stroke": "#ff007f", "fill": "rgba(255, 0, 127, 0.18)", "glow": "rgba(255, 0, 127, 0.6)"},
    {"stroke": "#00d2ff", "fill": "rgba(0, 210, 255, 0.18)", "glow": "rgba(0, 210, 255, 0.6)"},
    {"stroke": "#ffcc00", "fill": "rgba(255, 204, 0, 0.18)", "glow": "rgba(255, 204, 0, 0.6)"},
    {"stroke": "#00ff88", "fill": "rgba(0, 255, 136, 0.18)", "glow": "rgba(0, 255, 136, 0.6)"},
    {"stroke": "#bb86fc", "fill": "rgba(187, 134, 252, 0.18)", "glow": "rgba(187, 134, 252, 0.6)"},
    {"stroke": "#ff7700", "fill": "rgba(255, 119, 0, 0.18)", "glow": "rgba(255, 119, 0, 0.6)"},
    {"stroke": "#ff3366", "fill": "rgba(255, 51, 102, 0.18)", "glow": "rgba(255, 51, 102, 0.6)"},
    {"stroke": "#00e5ff", "fill": "rgba(0, 229, 255, 0.18)", "glow": "rgba(0, 229, 255, 0.6)"},
    {"stroke": "#76ff03", "fill": "rgba(118, 255, 3, 0.18)", "glow": "rgba(118, 255, 3, 0.6)"},
    {"stroke": "#e040fb", "fill": "rgba(224, 64, 251, 0.18)", "glow": "rgba(224, 64, 251, 0.6)"},
]

class FamilyTriangleEngine:
    def __init__(self, db: Optional[MatkaDatabase] = None):
        self.db = db or MatkaDatabase()

    def get_snippet(self, market: str, rows_count: int = 5, target_day: Optional[str] = None, *args, **kwargs) -> List[Dict[str, Any]]:
        """Returns the latest rows_count weeks of a market."""
        df = self.db.get_market_results(market, limit=rows_count * 7 * 2)
        if df.empty:
            return []
        df_sorted = df.sort_values("id", ascending=True)
        grid = []
        for dr, group in df_sorted.groupby("date_range", sort=False):
            row = {"date_range": dr, "days": {}}
            for _, r in group.iterrows():
                row["days"][r["day_of_week"]] = {
                    "jodi": str(r["jodi"]),
                    "open_panna": str(r["open_panna"]),
                    "close_panna": str(r["close_panna"]),
                    "is_red": int(r["is_red_jodi"]),
                }
            grid.append(row)

        # If target_day is already declared or current week has ended, advance to upcoming week
        if grid and should_advance_to_next_week(grid[-1], target_day):
            next_dr = compute_next_week_date_range(grid[-1]["date_range"])
            grid.append({"date_range": next_dr, "days": {}})

        return grid[-rows_count:] if len(grid) >= rows_count else grid

    def find_all_triangles(
        self,
        grid_snippet: List[Dict[str, Any]],
        target_day: str = "Mon"
    ) -> Dict[str, Any]:
        """
        Finds both Completed Family Triangles and Projected Family Triangles in the snippet.
        """
        if not grid_snippet:
            return {"completed": [], "projected": []}

        nodes = []
        for r_idx, w in enumerate(grid_snippet):
            dr = w.get("date_range", "")
            for c_idx, d in enumerate(DAY_ORDER):
                j = w.get("days", {}).get(d, {}).get("jodi", "")
                if j and j.isdigit() and len(j) == 2:
                    nodes.append({
                        "r": r_idx,
                        "c": c_idx,
                        "day": d,
                        "date_range": dr,
                        "jodi": j,
                        "family": get_jodi_family(j)
                    })

        target_r = len(grid_snippet) - 1
        target_c = DAY_COLS.get(target_day, 0)
        target_dr = grid_snippet[-1].get("date_range", "")

        # 1. Completed Triangles (All 3 vertices present in past completed rows)
        completed = []
        comp_nodes = [n for n in nodes if n["r"] < target_r]
        n_nodes = len(comp_nodes)
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                for k in range(j + 1, n_nodes):
                    A, B, C = comp_nodes[i], comp_nodes[j], comp_nodes[k]
                    # Check non-collinear: area of triangle != 0
                    area2 = (B["c"] - A["c"]) * (C["r"] - A["r"]) - (B["r"] - A["r"]) * (C["c"] - A["c"])
                    if area2 == 0:
                        continue
                    
                    # Check same family
                    fam_A = set(A["family"])
                    if B["jodi"] in fam_A and C["jodi"] in fam_A:
                        # Classify triangle shape
                        dist_AB = math.hypot(B["c"] - A["c"], B["r"] - A["r"])
                        dist_BC = math.hypot(C["c"] - B["c"], C["r"] - B["r"])
                        dist_CA = math.hypot(A["c"] - C["c"], A["r"] - C["r"])
                        
                        # Span height
                        min_r = min(A["r"], B["r"], C["r"])
                        max_r = max(A["r"], B["r"], C["r"])
                        row_span = max_r - min_r + 1
                        
                        t_type = "सममित त्रिकोण (Symmetric Triangle)"
                        if abs(dist_AB - dist_BC) < 0.2 or abs(dist_BC - dist_CA) < 0.2 or abs(dist_CA - dist_AB) < 0.2:
                            t_type = "समद्विभुज त्रिकोण (Isosceles Family Triangle)"
                        elif (A["r"] == B["r"] and C["r"] > A["r"]) or (A["r"] == C["r"] and B["r"] > A["r"]):
                            t_type = "डेल्टा / V-त्रिकोण (Delta V-Triangle)"
                        elif A["c"] == B["c"] or B["c"] == C["c"] or A["c"] == C["c"]:
                            t_type = "काटकोन त्रिकोण (Right-Angle Triangle)"
                        
                        completed.append({
                            "type_title": t_type,
                            "nodes": [A, B, C],
                            "jodis": [A["jodi"], B["jodi"], C["jodi"]],
                            "family": sorted(list(fam_A)),
                            "row_span": row_span,
                            "area": abs(area2) / 2.0,
                            "summary": f"{A['day']}({A['jodi']}) ➔ {B['day']}({B['jodi']}) ➔ {C['day']}({C['jodi']})"
                        })

        # 2. Projected Triangles (2 past nodes pointing to Target Cell on the latest week)
        # Base vertices A and B come ONLY from past completed rows (r < target_r).
        # The current active row (target_r) is NEVER used as a base vertex!
        projected = []

        target_node = {
            "r": target_r,
            "c": target_c,
            "day": target_day,
            "date_range": target_dr,
            "jodi": "??",
            "is_target": True
        }

        # Filter past nodes: only previous rows before target_r
        past_nodes = [n for n in nodes if n["r"] < target_r]
        
        for i in range(len(past_nodes)):
            for j in range(i + 1, len(past_nodes)):
                A, B = past_nodes[i], past_nodes[j]
                if B["jodi"] in set(A["family"]):
                    # Check non-collinear with target: area of triangle != 0
                    area2 = (B["c"] - A["c"]) * (target_node["r"] - A["r"]) - (B["r"] - A["r"]) * (target_node["c"] - A["c"])
                    if area2 == 0:
                        continue
                    
                    # Distance to target
                    dist_A_T = math.hypot(target_c - A["c"], target_r - A["r"])
                    dist_B_T = math.hypot(target_c - B["c"], target_r - B["r"])
                    
                    # Determine pattern geometry
                    min_r = min(A["r"], B["r"], target_r)
                    max_r = max(A["r"], B["r"], target_r)
                    r_span = max_r - min_r + 1
                    
                    p_type = f"🎯 टार्गेट फॅमिली त्रिकोण ({r_span}-आठवडे विस्तार)"
                    if A["r"] == B["r"] and target_r > A["r"]:
                        p_type = "🔻 इनव्हर्टेड डेल्टा (Base on Top ➔ Target Apex)"
                    elif A["c"] == target_c or B["c"] == target_c:
                        p_type = "📐 काटकोन टार्गेट (Right-Angle to Target)"
                    elif abs(dist_A_T - dist_B_T) < 0.2:
                        p_type = "🔺 समद्विभुज टार्गेट (Symmetric to Target)"

                    projected.append({
                        "type_title": p_type,
                        "nodes": [A, B, target_node],
                        "known_jodis": [A["jodi"], B["jodi"]],
                        "predicted_family": sorted(list(set(A["family"]))),
                        "target_node": target_node,
                        "row_span": r_span,
                        "area": abs(area2) / 2.0,
                        "summary": f"{A['day']}({A['jodi']}) + {B['day']}({B['jodi']}) ➔ {target_day}(??)"
                    })

        return {
            "completed": completed,
            "projected": projected
        }


def render_family_triangle_panel_html(
    grid_snippet: List[Dict[str, Any]],
    triangles: List[Dict[str, Any]],
    active_idx: Optional[int] = None,
    title: str = "📐 फॅमिली त्रिकोण चार्ट (Family Triangle Chart)"
) -> str:
    """
    Renders HTML table of the grid snippet with SVG polygon triangles and glowing node highlights.
    """
    if not grid_snippet:
        return ""

    DATE_W = 95
    CELL_W = 70
    ROW_H = 56
    HEADER_H = 42

    total_w = DATE_W + len(DAY_ORDER) * CELL_W
    svg_h = HEADER_H + len(grid_snippet) * ROW_H

    # SVG Triangles Layer
    svg_elements = []

    # Map triangles to render
    render_triangles = [triangles[active_idx]] if (active_idx is not None and 0 <= active_idx < len(triangles)) else triangles

    for t_idx, t in enumerate(render_triangles):
        pal = TRIANGLE_PALETTES[(active_idx if active_idx is not None else t_idx) % len(TRIANGLE_PALETTES)]
        pts = []
        for n in t["nodes"]:
            r = n["r"]
            c = n["c"]
            cx = DATE_W + c * CELL_W + CELL_W / 2
            cy = HEADER_H + r * ROW_H + ROW_H / 2
            pts.append((cx, cy))

        if len(pts) == 3:
            pts_str = f"{pts[0][0]:.1f},{pts[0][1]:.1f} {pts[1][0]:.1f},{pts[1][1]:.1f} {pts[2][0]:.1f},{pts[2][1]:.1f}"
            
            # Semi-transparent filled polygon
            svg_elements.append(
                f'<polygon points="{pts_str}" fill="{pal["fill"]}" stroke="{pal["stroke"]}" '
                f'stroke-width="2.5" stroke-dasharray="6,3" style="filter:drop-shadow(0 0 6px {pal["glow"]});" />'
            )
            
            # Draw triangle edges
            for i in range(3):
                p1, p2 = pts[i], pts[(i+1)%3]
                svg_elements.append(
                    f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" '
                    f'stroke="{pal["stroke"]}" stroke-width="2.5" />'
                )

    svg_overlay = f"""<svg style="position:absolute;top:0;left:0;pointer-events:none;z-index:10;" 
        width="{total_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
        {''.join(svg_elements)}
    </svg>"""

    # Table Header
    thead = f"""<thead>
        <tr style="background:#201030;color:#ddd;font-size:12px;height:{HEADER_H}px;">
            <th style="border:1px solid #444;width:{DATE_W}px;text-align:center;box-sizing:border-box;padding:2px 0;height:{HEADER_H}px;line-height:1.1;">Date Range</th>
            {''.join([f'<th style="border:1px solid #444;width:{CELL_W}px;text-align:center;color:#ffcc00;box-sizing:border-box;padding:2px 0;height:{HEADER_H}px;line-height:1.1;">{DAY_MARATHI[d]}<br><span style="color:#888;font-size:10px;">{d}</span></th>' for d in DAY_ORDER])}
        </tr>
    </thead>"""

    # Highlight map: (r, c) -> node info
    high_map = {}
    for t_idx, t in enumerate(render_triangles):
        pal = TRIANGLE_PALETTES[(active_idx if active_idx is not None else t_idx) % len(TRIANGLE_PALETTES)]
        for n in t["nodes"]:
            high_map[(n["r"], n["c"])] = {**n, "palette": pal}

    tbody_rows = ""
    for r_idx, w in enumerate(grid_snippet):
        dr = w.get("date_range", "")
        disp_dr = dr.replace(" to ", "<br>to<br>")
        date_td = f'<td style="font-size:9px;padding:2px;border:1px solid #333;background:#131322;color:#aaa;text-align:center;width:{DATE_W}px;height:{ROW_H}px;box-sizing:border-box;line-height:1.2;">{disp_dr}</td>'

        day_tds = ""
        for c_idx, d in enumerate(DAY_ORDER):
            cell = w.get("days", {}).get(d, {})
            jodi = cell.get("jodi", "")
            is_red = jodi in RED_JODIS

            node_info = high_map.get((r_idx, c_idx))
            if node_info:
                pal = node_info.get("palette", TRIANGLE_PALETTES[0])
                if node_info.get("is_target"):
                    # Target node
                    jodi_html = f'<div style="font-size:16px;font-weight:900;color:#fff;background:#ff007f;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;margin:auto;box-shadow:0 0 14px #ff007f;" title="टार्गेट त्रिकोण टोक">??</div>'
                else:
                    # Highlighted Vertex
                    jodi_html = f'<div style="font-size:15px;font-weight:900;color:#fff;background:#181830;border:3px solid {pal["stroke"]};border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;margin:auto;box-shadow:0 0 10px {pal["glow"]};">{jodi or "??"}</div>'
            else:
                if not jodi:
                    jodi_html = '<div style="font-size:13px;color:#444;">--</div>'
                else:
                    color = "#ff3344" if is_red else "#888"
                    jodi_html = f'<div style="font-size:14px;color:{color};font-weight:600;">{jodi}</div>'

            bg = "#1a1a2e" if r_idx % 2 == 0 else "#141424"
            day_tds += f'<td style="border:1px solid #222;text-align:center;padding:0;background:{bg};width:{CELL_W}px;height:{ROW_H}px;box-sizing:border-box;">{jodi_html}</td>'

        tbody_rows += f'<tr style="height:{ROW_H}px;box-sizing:border-box;">{date_td}{day_tds}</tr>'

    return f"""
<div style="background:#0a0a16;border:2px solid #333366;border-radius:12px;padding:12px;margin-bottom:15px;overflow-x:auto;">
    <div style="font-size:15px;font-weight:bold;color:#ffcc00;margin-bottom:10px;">{title}</div>
    <div style="position:relative;display:inline-block;min-width:100%;">
        {svg_overlay}
        <table style="width:{total_w}px;border-collapse:collapse;table-layout:fixed;position:relative;z-index:2;box-sizing:border-box;margin:0;">
            {thead}
            <tbody>{tbody_rows}</tbody>
        </table>
    </div>
</div>
"""
