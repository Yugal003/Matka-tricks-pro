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
            pts.append(f"{cx},{cy}")

        if len(pts) == 3:
            pts_str = " ".join(pts)
            svg_elements.append(
                f'<polygon points="{pts_str}" fill="{pal["fill"]}" stroke="{pal["stroke"]}" stroke-width="2.5" stroke-dasharray="6,3" filter="url(#seq-glow-{t_idx})" />'
            )
            step_labels = ["①", "②", "🎯"] if t["nodes"][2].get("is_target") else ["①", "②", "③"]
            for s_idx, n in enumerate(t["nodes"]):
                cx = DATE_W + n["c"] * CELL_W + CELL_W / 2
                cy = HEADER_H + n["r"] * ROW_H + ROW_H / 2
                marker_col = "#ff007f" if n.get("is_target") else "#00d2ff"
                lbl = step_labels[s_idx]
                svg_elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="14" fill="#0b0b14" stroke="{marker_col}" stroke-width="2" /><text x="{cx}" y="{cy+4}" font-size="12" font-weight="bold" fill="{marker_col}" text-anchor="middle">{lbl}</text>'
                )

    table_rows = []
    header_th = "<th style='width:95px;padding:6px;color:#888;font-size:12px;background:#151525;'>आठवडा</th>" + "".join([
        f"<th style='width:70px;padding:6px;color:#00d2ff;font-size:13px;text-align:center;background:#151525;'>{DAY_MARATHI[d]}<br><span style='color:#666;font-size:10px;'>{d}</span></th>"
        for d in DAY_ORDER
    ])
    table_rows.append(f"<tr style='border-bottom:1px solid #333;'>{header_th}</tr>")

    for r_idx, w in enumerate(grid_snippet):
        dr = w.get("date_range", "")
        short_dr = dr.split(" to ")[0] if " to " in dr else dr
        tds = [f"<td style='padding:6px 8px;color:#aaa;font-size:11px;font-weight:bold;background:#111120;border-right:1px solid #222;'>{short_dr}</td>"]
        
        for c_idx, d in enumerate(DAY_ORDER):
            cell = w.get("days", {}).get(d, {})
            j = cell.get("jodi", "")
            if not j:
                tds.append("<td style='padding:6px;text-align:center;color:#444;background:#0d0d18;'>--</td>")
                continue
            cell_style = "padding:6px;text-align:center;border:1px solid #1a1a2e;background:#0d0d18;"
            jodi_html = f"<b style='color:#ffcc00;font-size:15px;'>{j}</b>"
            tds.append(f"<td style='{cell_style}'>{jodi_html}</td>")
            
        table_rows.append(f"<tr>{''.join(tds)}</tr>")

    svg_filters = "".join([
        f'<filter id="seq-glow-{i}" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4" result="blur" /><feComposite in="SourceGraphic" in2="blur" operator="over" /></filter>'
        for i in range(10)
    ])

    svg_els_str = "".join(svg_elements)
    tbl_str = "".join(table_rows)

    html = f"""
    <div style="background:#0b0b16;border:2px solid #00d2ff;border-radius:12px;padding:12px;margin-bottom:15px;overflow-x:auto;">
        <div style="font-size:16px;font-weight:900;color:#00d2ff;margin-bottom:10px;">
            {title}
        </div>
        <div style="position:relative;width:{total_w}px;margin:0 auto;">
            <svg style="position:absolute;top:0;left:0;width:{total_w}px;height:{svg_h}px;pointer-events:none;z-index:10;">
                <defs>{svg_filters}</defs>
                {svg_els_str}
            </svg>
            <table style="border-collapse:collapse;width:{total_w}px;background:#0d0d1a;">
                {tbl_str}
            </table>
        </div>
    </div>
    """
    return html
