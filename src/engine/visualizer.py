"""
Matka Chart Visualizer — Multi-Pattern SVG Arrow Renderer
==========================================================
Renders a dark-theme weekly panel chart with:
  - Multi-colored SVG dashed arrows between seed and repeat nodes
    (one color per gap length: 3wk=violet, 4wk=cyan ... 8wk=pink ... 14wk=blue)
  - Blue glow circles on any circled node
  - Red coloring for red jodis (doubles + cut pairs)
  - Open / Close panna digits beside each jodi
  - Prediction extension arrows (dashed) pointing to future rows
"""

from typing import Dict, Any, List, Optional, Tuple
from src.config import get_jodi_family

# Layout constants
DATE_W  = 94    # px — date column width
CELL_W  = 80    # px — per-day column width
ROW_H   = 58    # px — per-row height
HEADER_H = 34   # px — thead height

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

GAP_COLORS = {
    3:  "#bb86fc",
    4:  "#00d2ff",
    5:  "#00ff99",
    6:  "#ffcc00",
    7:  "#ff9933",
    8:  "#ff007f",
    9:  "#ff4444",
    10: "#cc44ff",
    11: "#44aaff",
    12: "#aaffaa",
    13: "#ffaaaa",
    14: "#aaaaff",
}


def _cx(col: int) -> float:
    """Centre-x for a data column (0-indexed)."""
    return DATE_W + col * CELL_W + CELL_W / 2


def _cy(row: int) -> float:
    """Centre-y for a data row (0-indexed after header)."""
    return HEADER_H + row * ROW_H + ROW_H / 2


def render_interactive_scheme_html(
    grid: List[Dict[str, Any]],
    scheme: Optional[Dict[str, Any]] = None,
    patterns: Optional[List[Dict[str, Any]]] = None,
    gap_filter: Optional[List[int]] = None,
) -> str:
    """
    Render the full HTML panel chart with SVG overlay.

    Args:
        grid      : List of weekly dicts (date_range, days {day: {jodi, open_panna, close_panna, is_red}})
        scheme    : Active triangle scheme (legacy, still supported)
        patterns  : List of visible pattern dicts from FamilyRepeatPatternDetector
        gap_filter: Which gap weeks to draw (None = all)
    """
    if not grid:
        return "<p style='color:#bbb;'>No chart data. Please sync first.</p>"

    display_grid = grid[-14:]   # show last 14 weeks
    n_rows = len(display_grid)
    day_to_col = {d: i for i, d in enumerate(DAY_ORDER)}

    # ---- Visible patterns within the display window ------------------
    date_to_row = {w.get("date_range", ""): i for i, w in enumerate(display_grid)}
    vis_patterns = []
    if patterns:
        for p in patterns:
            s_row = date_to_row.get(p.get("seed_date", ""))
            r_row = date_to_row.get(p.get("repeat_date", ""))
            if s_row is None or r_row is None:
                continue
            s_col = day_to_col.get(p.get("seed_day", ""))
            r_col = day_to_col.get(p.get("repeat_day", ""))
            if s_col is None or r_col is None:
                continue
            gap = p.get("gap_weeks", 0)
            if gap_filter and gap not in gap_filter:
                continue
            vis_patterns.append({**p, "seed_row": s_row, "seed_col": s_col,
                                  "repeat_row": r_row, "repeat_col": r_col})

    # ---- Nodes that have a circle glow ---------------------------------
    # Legacy scheme nodes
    circled: Dict[Tuple[int, int], str] = {}  # (row, col) → colour
    if scheme:
        for key, col in [("point_a", "#00d2ff"), ("point_b", "#ffcc00"),
                         ("point_c", "#ff007f")]:
            pt = scheme.get(key, {})
            dr = pt.get("date_range", "")
            day = pt.get("day", "")
            if dr in date_to_row and day in day_to_col:
                circled[(date_to_row[dr], day_to_col[day])] = col

    # Pattern nodes
    for p in vis_patterns:
        circled[(p["seed_row"], p["seed_col"])] = p.get("color", "#ffffff")
        circled[(p["repeat_row"], p["repeat_col"])] = p.get("color", "#ffffff")

    # Target week declared jodis always lit green
    last_week = display_grid[-1]
    last_row = n_rows - 1
    for d in DAY_ORDER:
        cell = last_week.get("days", {}).get(d, {})
        j = cell.get("jodi", "")
        if j and not j.startswith("*"):
            circled[(last_row, day_to_col[d])] = "#00ff99"

    # ---- TABLE HTML ---------------------------------------------------
    total_w = DATE_W + len(DAY_ORDER) * CELL_W
    svg_h = HEADER_H + n_rows * ROW_H

    # Thead
    day_ths = "".join(
        f'<th style="border:1px solid #555;width:{CELL_W}px;text-align:center;">{d}</th>'
        for d in DAY_ORDER
    )
    thead = (
        f'<thead><tr style="background:#c20060;color:#fff;font-size:12px;height:{HEADER_H}px;">'
        f'<th style="border:1px solid #555;width:{DATE_W}px;text-align:center;">Date Range</th>'
        f'{day_ths}</tr></thead>'
    )

    # Tbody
    tbody_rows = ""
    for r_idx, w in enumerate(display_grid):
        dr = w.get("date_range", "")
        date_disp = dr.replace(" to ", "<br>to<br>")
        is_last = (r_idx == n_rows - 1)

        # Date cell
        date_cell = (
            f'<td style="font-size:10px;padding:3px;border:1px solid #444;'
            f'background:{"#1a1a40" if is_last else "#181824"};color:#ccc;'
            f'text-align:center;width:{DATE_W}px;line-height:1.3;">{date_disp}</td>'
        )

        # Day cells
        day_cells = ""
        for d in DAY_ORDER:
            col_idx = day_to_col[d]
            cell = w.get("days", {}).get(d, {})
            jodi = cell.get("jodi", "**")
            open_p = cell.get("open_panna", "")
            close_p = cell.get("close_panna", "")
            is_red = cell.get("is_red", 0)

            cir_col = circled.get((r_idx, col_idx), "")
            if cir_col:
                jodi_style = (
                    f"font-size:20px;font-weight:bold;padding:3px 7px;"
                    f"{'color:#ff3344;' if is_red else 'color:#fff;'}"
                    f"border:2.5px solid {cir_col};"
                    f"border-radius:50%;box-shadow:0 0 12px {cir_col}80;"
                    f"display:inline-block;min-width:32px;text-align:center;"
                )
            else:
                jodi_style = (
                    f"font-size:20px;font-weight:bold;padding:3px 7px;"
                    f"{'color:#ff3344;' if is_red else 'color:#ccc;'}"
                    f"display:inline-block;min-width:32px;text-align:center;"
                )

            op_fmt = "<br>".join(list(open_p)) if open_p and open_p not in ("**", "") else ""
            cp_fmt = "<br>".join(list(close_p)) if close_p and close_p not in ("**", "") else ""

            row_bg = "#1c1c3a" if is_last else ("#242440" if r_idx % 2 == 0 else "#1c1c2e")
            day_cells += (
                f'<td style="border:1px solid #2a2a4a;text-align:center;padding:1px;'
                f'background:{row_bg};width:{CELL_W}px;height:{ROW_H}px;">'
                f'<div style="display:flex;align-items:center;justify-content:center;gap:2px;height:100%;">'
                f'<div style="font-size:8px;color:#555;line-height:10px;min-width:9px;text-align:right;">{op_fmt}</div>'
                f'<div style="{jodi_style}">{jodi}</div>'
                f'<div style="font-size:8px;color:#555;line-height:10px;min-width:9px;text-align:left;">{cp_fmt}</div>'
                f'</div></td>'
            )

        tbody_rows += f'<tr style="height:{ROW_H}px;">{date_cell}{day_cells}</tr>'

    # ---- SVG OVERLAY --------------------------------------------------
    # Collect all unique gap colours for marker defs
    used_colors = set(p.get("color", "#ffffff") for p in vis_patterns)
    if scheme:
        used_colors |= {"#00d2ff", "#ffcc00", "#ff007f"}

    def _safe_id(col: str) -> str:
        return col.lstrip("#")

    arrow_defs = "<defs>"
    for col in used_colors:
        sid = _safe_id(col)
        arrow_defs += (
            f'<marker id="arr{sid}" markerWidth="9" markerHeight="9" '
            f'refX="7" refY="3.5" orient="auto">'
            f'<polygon points="0 0, 9 3.5, 0 7" fill="{col}" opacity="0.9"/>'
            f'</marker>'
        )
    arrow_defs += "</defs>"

    svg_lines = ""

    # Draw pattern arrows (dashed coloured lines)
    drawn_pairs = set()
    for p in vis_patterns:
        key = (p["seed_row"], p["seed_col"], p["repeat_row"], p["repeat_col"])
        if key in drawn_pairs:
            continue
        drawn_pairs.add(key)

        x1 = _cx(p["seed_col"])
        y1 = _cy(p["seed_row"])
        x2 = _cx(p["repeat_col"])
        y2 = _cy(p["repeat_row"])
        col = p.get("color", "#ffffff")
        sid = _safe_id(col)
        gap = p.get("gap_weeks", "?")

        svg_lines += (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{col}" stroke-width="2" stroke-dasharray="7,4" '
            f'marker-end="url(#arr{sid})" opacity="0.75"/>'
        )
        # Label in the middle
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        svg_lines += (
            f'<text x="{mx:.1f}" y="{my - 5:.1f}" fill="{col}" '
            f'font-size="9" text-anchor="middle" opacity="0.9">{gap}w</text>'
        )

    # Legacy scheme connector lines
    if scheme:
        node_coords: Dict[str, Tuple[float, float]] = {}
        for key, pt_col in [("point_a", "#00d2ff"), ("point_b", "#ffcc00"), ("point_c", "#ff007f")]:
            pt = scheme.get(key, {})
            dr = pt.get("date_range", "")
            day = pt.get("day", "")
            if dr in date_to_row and day in day_to_col:
                r = date_to_row[dr]
                c = day_to_col[day]
                node_coords[key] = (_cx(c), _cy(r))

        conn_pairs = [
            ("point_a", "point_b", "#00d2ff"),
            ("point_b", "point_c", "#ffcc00"),
        ]
        for s, e, col in conn_pairs:
            if s in node_coords and e in node_coords:
                x1, y1 = node_coords[s]
                x2, y2 = node_coords[e]
                sid = _safe_id(col)
                svg_lines += (
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="{col}" stroke-width="2.5" stroke-dasharray="8,4" '
                    f'marker-end="url(#arr{sid})" opacity="0.85"/>'
                )

    svg_overlay = (
        f'<svg style="position:absolute;top:0;left:0;pointer-events:none;z-index:10;" '
        f'width="{total_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">'
        f'{arrow_defs}{svg_lines}</svg>'
    )

    # ---- GAP LEGEND --------------------------------------------------
    shown_gaps = sorted(set(p.get("gap_weeks", 0) for p in vis_patterns))
    legend_items = ""
    for g in shown_gaps:
        c = GAP_COLORS.get(g, "#fff")
        legend_items += (
            f'<span style="display:inline-flex;align-items:center;margin:3px 8px 3px 0;">'
            f'<span style="display:inline-block;width:28px;height:3px;background:{c};'
            f'margin-right:5px;border-radius:2px;"></span>'
            f'<span style="color:{c};font-size:11px;font-weight:bold;">{g}-week</span></span>'
        )

    # ---- FINAL HTML --------------------------------------------------
    final_html = f"""
<div style="background:#0d0d1a;border:2px solid #ff007f;border-radius:14px;
            padding:14px;overflow-x:auto;font-family:'Segoe UI',sans-serif;">

  <div style="text-align:center;margin-bottom:10px;">
    <span style="font-size:16px;font-weight:bold;
    background:linear-gradient(90deg,#ff007f,#ffcc00,#00d2ff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
      📐 FAMILY JODI REPEAT PATTERN CHART — ALL ARROWS
    </span>
  </div>

  <!-- Gap colour legend -->
  <div style="text-align:center;margin-bottom:10px;padding:6px;
              background:#13132a;border-radius:8px;border:1px solid #2a2a4a;">
    <span style="font-size:11px;color:#888;margin-right:8px;">Arrow colour by gap:</span>
    {legend_items}
    <span style="color:#00ff99;font-size:11px;font-weight:bold;">● Current Week</span>
  </div>

  <!-- Chart with SVG overlay -->
  <div style="position:relative;display:inline-block;min-width:100%;">
    {svg_overlay}
    <table style="width:{total_w}px;border-collapse:collapse;table-layout:fixed;position:relative;z-index:2;">
      {thead}
      <tbody>{tbody_rows}</tbody>
    </table>
  </div>

  <div style="font-size:10px;color:#555;margin-top:8px;text-align:center;">
    Dashed arrows: seed jodi → family member repeat (same family = cut-pair permutations).
    Family rule: 0↔5, 1↔6, 2↔7, 3↔8, 4↔9 (direct + reverse + half-cut + full-cut = 8 members)
  </div>
</div>
"""
    return final_html
