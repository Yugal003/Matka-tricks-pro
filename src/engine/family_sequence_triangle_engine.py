"""
Family Sequence Triangle Scheme Engine & Visualizer
===================================================
Finds geometric triangles where vertices form a progressive Family Sequence (सलग फॅमिली क्रम):
- Node 1 (J1 from Family F1) and Node 2 (J2 from Family F2) have aligned sibling jodis forming step +1 (e.g. 31 -> 32)
- Node 3 / Target completes the sequence: Forward (31 -> 32 -> 33 -> 33/38 Family) or Backward (30 -> 31 -> 32 -> 30 Family)
- Works across 2, 3, 4, 5, 6 row chart snippets.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from src.config import get_jodi_family, CUT_NUMBERS
from src.storage.database import MatkaDatabase

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
DAY_COLS = {d: i for i, d in enumerate(DAY_ORDER)}
DAY_MARATHI = {"Mon": "सोमवार", "Tue": "मंगळवार", "Wed": "बुधवार", "Thu": "गुरुवार", "Fri": "शुक्रवार", "Sat": "शनिवार"}

TRIANGLE_PALETTES = [
    {"stroke": "#00d2ff", "fill": "rgba(0, 210, 255, 0.18)", "glow": "rgba(0, 210, 255, 0.6)"},
    {"stroke": "#ff007f", "fill": "rgba(255, 0, 127, 0.18)", "glow": "rgba(255, 0, 127, 0.6)"},
    {"stroke": "#00ff88", "fill": "rgba(0, 255, 136, 0.18)", "glow": "rgba(0, 255, 136, 0.6)"},
    {"stroke": "#ffcc00", "fill": "rgba(255, 204, 0, 0.18)", "glow": "rgba(255, 204, 0, 0.6)"},
    {"stroke": "#bb86fc", "fill": "rgba(187, 134, 252, 0.18)", "glow": "rgba(187, 134, 252, 0.6)"},
    {"stroke": "#ff7700", "fill": "rgba(255, 119, 0, 0.18)", "glow": "rgba(255, 119, 0, 0.6)"},
    {"stroke": "#ff3366", "fill": "rgba(255, 51, 102, 0.18)", "glow": "rgba(255, 51, 102, 0.6)"},
    {"stroke": "#00e5ff", "fill": "rgba(0, 229, 255, 0.18)", "glow": "rgba(0, 229, 255, 0.6)"},
    {"stroke": "#76ff03", "fill": "rgba(118, 255, 3, 0.18)", "glow": "rgba(118, 255, 3, 0.6)"},
    {"stroke": "#e040fb", "fill": "rgba(224, 64, 251, 0.18)", "glow": "rgba(224, 64, 251, 0.6)"},
]


def find_family_pair_sequence(j1: str, j2: str) -> List[Dict[str, Any]]:
    """
    Finds sequence relationships between two Jodi families.
    e.g. 81 (has 31) and 23 (has 32) -> Sequence step +1 (31 -> 32)
    """
    fam1 = get_jodi_family(j1)
    fam2 = get_jodi_family(j2)
    seqs = []
    seen = set()

    for a in fam1:
        for b in fam2:
            val_a = int(a)
            val_b = int(b)
            # Step +1 (Forward consecutive)
            if val_b == (val_a + 1):
                fwd_val = (val_b + 1) % 100
                bwd_val = (val_a - 1) % 100
                fwd_str = f"{fwd_val:02d}"
                bwd_str = f"{bwd_val:02d}"
                key = (fwd_str, bwd_str)
                if key not in seen:
                    seen.add(key)
                    seqs.append({
                        "aligned_A": a,
                        "aligned_B": b,
                        "step": 1,
                        "type_desc": f"सलग +१ क्रम ({a} ➔ {b})",
                        "fwd_target_jodi": fwd_str,
                        "fwd_family": sorted(list(set(get_jodi_family(fwd_str)))),
                        "bwd_target_jodi": bwd_str,
                        "bwd_family": sorted(list(set(get_jodi_family(bwd_str)))),
                    })
            # Step -1 (Backward consecutive)
            elif val_b == (val_a - 1):
                fwd_val = (val_b - 1) % 100
                bwd_val = (val_a + 1) % 100
                fwd_str = f"{fwd_val:02d}"
                bwd_str = f"{bwd_val:02d}"
                key = (fwd_str, bwd_str)
                if key not in seen:
                    seen.add(key)
                    seqs.append({
                        "aligned_A": a,
                        "aligned_B": b,
                        "step": -1,
                        "type_desc": f"सलग -१ उलट क्रम ({a} ➔ {b})",
                        "fwd_target_jodi": fwd_str,
                        "fwd_family": sorted(list(set(get_jodi_family(fwd_str)))),
                        "bwd_target_jodi": bwd_str,
                        "bwd_family": sorted(list(set(get_jodi_family(bwd_str)))),
                    })
    return seqs


class FamilySequenceTriangleEngine:
    def __init__(self, db: Optional[MatkaDatabase] = None):
        self.db = db or MatkaDatabase()

    def get_snippet(self, market: str, rows_count: int = 5) -> List[Dict[str, Any]]:
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
        return grid[-rows_count:] if len(grid) >= rows_count else grid

    def find_all_sequence_triangles(
        self,
        grid_snippet: List[Dict[str, Any]],
        target_day: str = "Mon"
    ) -> Dict[str, Any]:
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

        # 1. Completed Triangles (Node A -> Node B -> Node C form a sequence)
        completed = []
        n_nodes = len(nodes)
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                for k in range(j + 1, n_nodes):
                    A, B, C = nodes[i], nodes[j], nodes[k]
                    # Check non-collinear
                    area2 = (B["c"] - A["c"]) * (C["r"] - A["r"]) - (B["r"] - A["r"]) * (C["c"] - A["c"])
                    if area2 == 0:
                        continue

                    # Check if J1 -> J2 sequence leads to J3's family
                    seq_AB = find_family_pair_sequence(A["jodi"], B["jodi"])
                    if not seq_AB:
                        continue

                    fam_C = set(C["family"])
                    matched_seq = None
                    for s in seq_AB:
                        if C["jodi"] in s["fwd_family"] or C["jodi"] in s["bwd_family"]:
                            matched_seq = s
                            break

                    if matched_seq:
                        min_r = min(A["r"], B["r"], C["r"])
                        max_r = max(A["r"], B["r"], C["r"])
                        row_span = max_r - min_r + 1

                        completed.append({
                            "type_title": f"⚡ फॅमिली सीक्वेन्स त्रिकोण ({matched_seq['type_desc']})",
                            "sequence_desc": f"{matched_seq['aligned_A']} ➔ {matched_seq['aligned_B']} ➔ {C['jodi']}",
                            "nodes": [A, B, C],
                            "jodis": [A["jodi"], B["jodi"], C["jodi"]],
                            "family_A": sorted(list(set(A["family"]))),
                            "family_B": sorted(list(set(B["family"]))),
                            "family_C": sorted(list(set(C["family"]))),
                            "row_span": row_span,
                            "area": abs(area2) / 2.0,
                            "summary": f"{A['day']}({A['jodi']}) ➔ {B['day']}({B['jodi']}) ➔ {C['day']}({C['jodi']})"
                        })

        # 2. Projected Triangles (Node A and Node B point to target ??)
        projected = []
        target_r = len(grid_snippet) - 1
        target_c = DAY_COLS.get(target_day, 0)
        target_dr = grid_snippet[-1].get("date_range", "")

        target_node = {
            "r": target_r,
            "c": target_c,
            "day": target_day,
            "date_range": target_dr,
            "jodi": "??",
            "is_target": True
        }

        past_nodes = [n for n in nodes if not (n["r"] == target_r and n["c"] == target_c)]

        for i in range(len(past_nodes)):
            for j in range(i + 1, len(past_nodes)):
                A, B = past_nodes[i], past_nodes[j]
                area2 = (B["c"] - A["c"]) * (target_node["r"] - A["r"]) - (B["r"] - A["r"]) * (target_node["c"] - A["c"])
                if area2 == 0:
                    continue

                seq_list = find_family_pair_sequence(A["jodi"], B["jodi"])
                if not seq_list:
                    continue

                best_seq = seq_list[0]
                min_r = min(A["r"], B["r"], target_r)
                max_r = max(A["r"], B["r"], target_r)
                row_span = max_r - min_r + 1

                projected.append({
                    "type_title": f"🎯 टार्गेट फॅमिली सीक्वेन्स ({best_seq['type_desc']})",
                    "sequence_formula": f"{best_seq['aligned_A']} (Family {A['jodi']}) ➔ {best_seq['aligned_B']} (Family {B['jodi']}) ➔ {best_seq['fwd_target_jodi']} / {best_seq['bwd_target_jodi']}",
                    "nodes": [A, B, target_node],
                    "known_jodis": [A["jodi"], B["jodi"]],
                    "aligned_A": best_seq["aligned_A"],
                    "aligned_B": best_seq["aligned_B"],
                    "fwd_target_jodi": best_seq["fwd_target_jodi"],
                    "fwd_family": best_seq["fwd_family"],
                    "bwd_target_jodi": best_seq["bwd_target_jodi"],
                    "bwd_family": best_seq["bwd_family"],
                    "target_node": target_node,
                    "row_span": row_span,
                    "area": abs(area2) / 2.0,
                    "summary": f"{A['day']}({A['jodi']}) + {B['day']}({B['jodi']}) ➔ {target_day}(??)"
                })

        return {
            "completed": completed,
            "projected": projected
        }


def render_family_sequence_triangle_panel_html(
    grid_snippet: List[Dict[str, Any]],
    triangles: List[Dict[str, Any]],
    active_idx: Optional[int] = None,
    title: str = "⚡ फॅमिली सीक्वेन्स त्रिकोण चार्ट"
) -> str:
    if not grid_snippet:
        return ""

    DATE_W = 95
    CELL_W = 70
    ROW_H = 50
    HEADER_H = 30

    total_w = DATE_W + len(DAY_ORDER) * CELL_W
    svg_h = HEADER_H + len(grid_snippet) * ROW_H

    render_triangles = [triangles[active_idx]] if (active_idx is not None and 0 <= active_idx < len(triangles)) else triangles
    svg_elements = []

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
            svg_elements.append(
                f'<polygon points="{pts_str}" fill="{pal["fill"]}" stroke="{pal["stroke"]}" '
                f'stroke-width="2.5" stroke-dasharray="6,3" style="filter:drop-shadow(0 0 6px {pal["glow"]});" />'
            )
            for i in range(3):
                p1, p2 = pts[i], pts[(i+1)%3]
                svg_elements.append(
                    f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" '
                    f'stroke="{pal["stroke"]}" stroke-width="2.5" />'
                )

            # Draw step labels ①, ②, 🎯 if in single triangle view
            if active_idx is not None:
                step_labels = ["①", "②", "🎯"] if t["nodes"][2].get("is_target") else ["①", "②", "③"]
                for s_idx, n in enumerate(t["nodes"]):
                    cx = DATE_W + n["c"] * CELL_W + CELL_W / 2
                    cy = HEADER_H + n["r"] * ROW_H + ROW_H / 2
                    marker_col = "#ff007f" if n.get("is_target") else pal["stroke"]
                    lbl = step_labels[s_idx]
                    svg_elements.append(
                        f'<circle cx="{cx}" cy="{cy}" r="13" fill="#0b0b14" stroke="{marker_col}" stroke-width="2" />'
                        f'<text x="{cx}" y="{cy+4}" font-size="11" font-weight="bold" fill="{marker_col}" text-anchor="middle">{lbl}</text>'
                    )

    svg_overlay = f"""<svg style="position:absolute;top:0;left:0;pointer-events:none;z-index:10;" 
        width="{total_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
        {''.join(svg_elements)}
    </svg>"""

    # Table Header
    thead = f"""<thead>
        <tr style="background:#15152b;color:#ddd;font-size:12px;height:{HEADER_H}px;">
            <th style="border:1px solid #444;width:{DATE_W}px;text-align:center;">Date Range</th>
            {''.join([f'<th style="border:1px solid #444;width:{CELL_W}px;text-align:center;color:#00d2ff;">{DAY_MARATHI[d]}<br><span style="color:#888;font-size:10px;">{d}</span></th>' for d in DAY_ORDER])}
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
        date_td = f'<td style="font-size:9.5px;padding:2px;border:1px solid #333;background:#131322;color:#aaa;text-align:center;width:{DATE_W}px;line-height:1.2;">{disp_dr}</td>'

        day_tds = ""
        for c_idx, d in enumerate(DAY_ORDER):
            cell = w.get("days", {}).get(d, {})
            jodi = cell.get("jodi", "")

            node_info = high_map.get((r_idx, c_idx))
            if node_info:
                pal = node_info.get("palette", TRIANGLE_PALETTES[0])
                if node_info.get("is_target"):
                    # Target node
                    jodi_html = f'<div style="font-size:16px;font-weight:900;color:#fff;background:#ff007f;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;margin:auto;box-shadow:0 0 14px #ff007f;" title="टार्गेट सीक्वेन्स टोक">??</div>'
                else:
                    # Highlighted Vertex
                    jodi_html = f'<div style="font-size:15px;font-weight:900;color:#fff;background:#181830;border:3px solid {pal["stroke"]};border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;margin:auto;box-shadow:0 0 10px {pal["glow"]};">{jodi or "??"}</div>'
            else:
                if not jodi:
                    jodi_html = '<div style="font-size:13px;color:#444;">--</div>'
                else:
                    jodi_html = f'<div style="font-size:14px;color:#888;font-weight:600;">{jodi}</div>'

            bg = "#1a1a2e" if r_idx % 2 == 0 else "#141424"
            day_tds += f'<td style="border:1px solid #222;text-align:center;padding:1px;background:{bg};width:{CELL_W}px;height:{ROW_H}px;">{jodi_html}</td>'

        tbody_rows += f'<tr style="height:{ROW_H}px;">{date_td}{day_tds}</tr>'

    return f"""
<div style="background:#0a0a16;border:2px solid #00d2ff;border-radius:12px;padding:12px;margin-bottom:15px;overflow-x:auto;">
    <div style="font-size:16px;font-weight:900;color:#00d2ff;margin-bottom:10px;">{title}</div>
    <div style="position:relative;display:inline-block;min-width:100%;">
        {svg_overlay}
        <table style="width:{total_w}px;border-collapse:collapse;table-layout:fixed;position:relative;z-index:2;">
            {thead}
            <tbody>{tbody_rows}</tbody>
        </table>
    </div>
</div>
"""
