import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.database import MatkaDatabase
from src.engine.tricks_engine import TrickAnalyzer, TRICKS
from src.engine.cross_line_engine import CrossLineEngine, RED_JODIS, are_family
from src.engine.cross_line_visualizer import render_cross_line_panel_html
from src.engine.date_figure_engine import DateFigureEngine, USER_DATE_MAP
from src.engine.family_triangle_engine import FamilyTriangleEngine, render_family_triangle_panel_html, TRIANGLE_PALETTES
from src.engine.family_sequence_triangle_engine import FamilySequenceTriangleEngine, render_family_sequence_triangle_panel_html, find_family_pair_sequence
from src.scraper.ingest import run_ingestion
from src.config import POPULAR_MARKETS, get_jodi_family, CUT_NUMBERS
import textwrap

st.set_page_config(
    page_title="मटका ट्रिक्स व क्रॉस लाईन विश्लेषक",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-title {
    font-size: 1.85rem; font-weight: 900;
    background: linear-gradient(90deg, #ff007f, #ffcc00, #00d2ff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 2px;
}
.sub-title {
    text-align: center; color: #aaa; font-size: 13px; margin-bottom: 12px;
}
.cross-box {
    background: linear-gradient(135deg, #16162d 0%, #0d0d1f 100%);
    border: 2px solid #00d2ff;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 15px;
}
.pred-card {
    background: linear-gradient(135deg, #1e102f 0%, #12091d 100%);
    border: 2px solid #ff007f;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 15px;
}
.red-warning-box {
    background: linear-gradient(135deg, #2a0b12 0%, #170508 100%);
    border: 1.5px solid #ff3344;
    border-radius: 10px;
    padding: 12px 16px;
    margin-top: 10px;
}
.match-step-badge {
    display: inline-block;
    background: #1f2338;
    border: 1px solid #4a5578;
    border-radius: 8px;
    padding: 6px 12px;
    margin: 4px;
    font-size: 14px;
}
.jodi-pill {
    display: inline-block;
    background: #000;
    color: #ffcc00;
    font-weight: bold;
    font-size: 18px;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #ffcc00;
    margin: 3px;
}
.family-pill {
    display: inline-block;
    background: #111;
    color: #00ffcc;
    font-weight: 600;
    font-size: 15px;
    padding: 3px 8px;
    border-radius: 5px;
    border: 1px solid #00ffcc80;
    margin: 2px;
}
.trick-pass {
    background: linear-gradient(135deg,#0d2818,#0a1a10);
    border:2px solid #00ff88;border-radius:10px;
    padding:10px 14px;margin-bottom:8px;
}
.trick-fail {
    background:linear-gradient(135deg,#1a0808,#120606);
    border:1px solid #551111;border-radius:10px;
    padding:10px 14px;margin-bottom:8px;
}
@media (max-width: 768px) {
    .main-title { font-size: 1.35rem !important; }
    .sub-title { font-size: 11px !important; }
    .cross-box, .pred-card, .red-warning-box { padding: 10px !important; border-radius: 8px !important; }
    .jodi-pill { font-size: 15px !important; padding: 3px 7px !important; }
    .family-pill { font-size: 13px !important; padding: 2px 6px !important; }
    .match-step-badge { font-size: 12px !important; padding: 4px 8px !important; margin: 2px !important; }
    .stRadio > div { flex-wrap: wrap !important; }
    .stButton button { width: 100% !important; margin-bottom: 6px !important; }
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    div[data-testid="column"] { min-width: 100% !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Marathi trick translations ──────────────────────────────
MARATHI_TRICKS = {
    "Mon-Tue Same Jodi":
        ("सोम-मंगळ एकसारखी जोडी",
         "नियम: एकाच आठवड्यात सोमवार आणि मंगळवारची जोडी एकसारखी असावी. "
         "किती आठवड्यात असे होते ते मोजतो."),
    "Supplementary Red (Week Has Red Jodi)":
        ("सप्लीमेंटरी रेड (आठवड्यात लाल जोडी)",
         "नियम: ज्या आठवड्यात किमान एक लाल जोडी (00,11..99 किंवा कट-जोडी 05,50,16,61,27,72,38,83,49,94) येते ती आठवडा पास."),
    "Close Line Dekho (Close Digit Repeats in Week)":
        ("क्लोज लाईन पहा (आठवड्यात क्लोज अंक पुनरावृत्ती)",
         "नियम: एकाच आठवड्यात 3+ दिवस एकाच क्लोज (युनिट) अंकावर जोडी येते."),
    "Fix Day Figure (Same Open/Close Digit Same Day Consecutive Weeks)":
        ("फिक्स डे फिगर (एकाच दिवशी लागोपाठ आठवड्यात एकच ओपन अंक)",
         "नियम: एखादा अंक 2+ लागोपाठ आठवड्यात त्याच दिवशी ओपन म्हणून येतो."),
    "Weekly Calculation (Sum Rule)":
        ("साप्ताहिक गणना (बेरीज नियम)",
         "नियम: आठवड्यातील सर्व जोड्यांची बेरीज करा. बेरजेचा युनिट अंक पुढच्या सोमवारच्या ओपन अंकाशी जुळतो."),
    "Single Bracket Scheme (Jodi digit sum bracket)":
        ("सिंगल ब्रॅकेट स्कीम (जोडी अंक बेरीज ब्रॅकेट)",
         "नियम: जोडीच्या दोन अंकांची बेरीज करा. त्याच ब्रॅकेट नंबरची जोडी पुढच्या सोमवारी येते."),
    "Band Week Gine (Consecutive Digit Sequence)":
        ("बँड वीक गिने (लागोपाठ अंकांची रांग)",
         "नियम: एकाच आठवड्यात 3+ दिवसांचे ओपन अंक लागोपाठ क्रमात असतात (उदा. 1,2,3 किंवा 7,8,9)."),
    "Line Ka Order (Jodi Ascending/Descending in Week)":
        ("लाईन का ऑर्डर (जोड्या चढत्या/उतरत्या क्रमात)",
         "नियम: आठवड्यातील जोड्या सोमवार→शनिवार चढत्या किंवा उतरत्या क्रमात असतात."),
    "Jodi Ka Jodbhav (Digit Sum of Two Jodis → Next Jodi)":
        ("जोडी का जोडभाव (दोन जोड्यांची बेरीज → पुढची जोडी)",
         "नियम: (दिवस1 ओपन + दिवस2 ओपन) mod 10 = दिवस3 ओपन. लागोपाठ 3 दिवसांमध्ये हे बेरीज-गणित तपासतो."),
    "Cross Line Dekho (Open of Day = Close 2 Days Later)":
        ("क्रॉस लाईन पहा (दिवसाचा ओपन = 2 दिवसांनंतरचा क्लोज)",
         "नियम: सोमवारचा ओपन अंक = बुधवारचा क्लोज अंक. (तसेच मंगळ→गुरु, बुध→शुक्र)."),
    "Achuk Sangam Scheme (Mon Open = Sat Close)":
        ("अचूक संगम स्कीम (सोम ओपन = शनि क्लोज)",
         "नियम: सोमवारचा ओपन अंक त्याच आठवड्यातील शनिवारच्या क्लोज अंकाशी जुळतो."),
    "Fix Figure Kalyan (Most Frequent Open Digit = Week's Dominant Figure)":
        ("फिक्स फिगर कल्याण (सर्वाधिक ओपन अंक = आठवड्याचा ठरलेला आकडा)",
         "नियम: एकाच आठवड्यात एकच अंक 3+ दिवस ओपन म्हणून येतो."),
    "Milan Day Jodi se Milan Night me Achuk Ank":
        ("मिलन डे जोडीवरून मिलन नाईट अचूक अंक",
         "नियम: जेव्हा मिलन डे मध्ये 22 जोडी येते, तेव्हा त्याच दिवशी मिलन नाईट मध्ये 9 किंवा 7 अंक (किंवा 97 जोडी) येतो. "
         "तसेच जर मिलन डे मध्ये 27, 72 किंवा 77 जोडी आली, तर मिलन नाईट मध्ये 2, 7, 4 किंवा 9 यापैकी अचूक अंक येतो."),
    "Sardarji Ke Figure (Cut of Mon Open = Thu Close)":
        ("सरदारजी के फिगर (सोम ओपनचा कट = गुरु क्लोज)",
         "नियम: सोमवारच्या ओपन अंकाचा कट नंबर गुरुवारच्या क्लोज अंकाशी जुळतो."),
    "Daily Figure Trick I (Yesterday Close = Today Open)":
        ("डेली फिगर ट्रिक १ (काल क्लोज = आज ओपन)",
         "नियम: मागच्या दिवसाचा क्लोज अंक पुढच्या दिवसाचा ओपन अंक असतो."),
    "Daily Figure Trick II (Cut of Yesterday Close = Today Open)":
        ("डेली फिगर ट्रिक २ (काल क्लोजचा कट = आज ओपन)",
         "नियम: मागच्या दिवसाच्या क्लोज अंकाचा कट नंबर पुढच्या दिवसाचा ओपन असतो."),
    "Daily Figure Trick III (Yesterday Open = Today Close)":
        ("डेली फिगर ट्रिक ३ (काल ओपन = आज क्लोज)",
         "नियम: मागच्या दिवसाचा ओपन अंक पुढच्या दिवसाचा क्लोज अंक असतो."),
    "Raise Karke Khele I (Jodi +1 each day)":
        ("रेज करके खेले १ (जोडी दर दिवशी +1)",
         "नियम: प्रत्येक दिवसाची जोडी = मागच्या दिवसाची जोडी +1 (उदा. 23→24→25)."),
    "Raise Karke Khele II (Jodi +11 each day)":
        ("रेज करके खेले २ (जोडी दर दिवशी +11)",
         "नियम: प्रत्येक दिवसाची जोडी = मागच्या दिवसाची जोडी +11 (उदा. 12→23→34)."),
    "Daily Figure Trick IV (Reverse Jodi Next Day)":
        ("डेली फिगर ट्रिक ४ (उलटी जोडी पुढच्या दिवशी)",
         "नियम: आजच्या जोडीची उलटी जोडी उद्या येते (उदा. 23→32)."),
    "Daily Figure Trick V (Open+Close Sum Digit = Next Open)":
        ("डेली फिगर ट्रिक ५ (ओपन+क्लोज बेरीज = पुढचा ओपन)",
         "नियम: (ओपन + क्लोज) mod 10 = पुढच्या दिवसाचा ओपन अंक."),
    "4-Markets (MD-KA-MN-MAIN) Mon-Tue Jodi Repeat":
        ("४ मार्केट्स (MD, KA, MN, MAIN) सोम-मंगळ जोडी / ब्रॅकेट ग्रुप रिपीट",
         "नियम: मिलन डे (MD), कल्याण (KA), मिलन नाईट (MN) आणि मेन बाजार (MAIN) या ४ प्रमुख खेळांमध्ये सोमवारची जोडी किंवा तिचा ८-फॅमिली ब्रॅकेट ग्रुप मंगळवारी याच ४ खेळांमध्ये रिपीट होतो."),
}

ALL_MARKETS = [m["name"] for m in POPULAR_MARKETS]

# ── Sidebar ─────────────────────────────────────────────────
st.sidebar.markdown("## ⚙️ कंट्रोल पॅनेल")

if st.sidebar.button("🔄 नवीन डेटा सिंक करा (Sync Live DpBoss)", use_container_width=True):
    with st.spinner("⚡ DpBoss वरून सर्व चार्ट्स व आजचे नवीन निकाल अपडेट करत आहे..."):
        try:
            run_ingestion()
            st.cache_data.clear()
            st.sidebar.success("✅ सर्व चार्ट्स व निकाल यशस्वीरित्या अपडेट झाले!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"अपडेट करताना त्रुटी: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Market निवडा (Scroll Bar)")

selected_market = st.sidebar.radio(
    label="निवडा Market:",
    options=ALL_MARKETS,
    index=0,
    key="market_select",
)

st.sidebar.markdown("---")
target_day = st.sidebar.selectbox(
    "🎯 टार्गेट दिवस (Target Day):",
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    index=0,
    format_func=lambda d: {
        "Mon": "सोमवार (Mon)",
        "Tue": "मंगळवार (Tue)",
        "Wed": "बुधवार (Wed)",
        "Thu": "गुरुवार (Thu)",
        "Fri": "शुक्रवार (Fri)",
        "Sat": "शनिवार (Sat)",
        "Sun": "रविवार (Sun)"
    }[d]
)

min_touch = st.sidebar.slider("किमान टच लाईन (Min Touch Length):", 2, 5, 3)

# ── Header ──────────────────────────────────────────────────
st.markdown('<div class="main-title">🎯 मटका क्रॉस लाईन फॅमिली ट्रिक व ट्रिक्स विश्लेषक</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">निवडलेला मार्केट: <b style="color:#ffcc00;font-size:15px;">{selected_market}</b> &nbsp;|&nbsp; टार्गेट: <b style="color:#00ffcc;font-size:15px;">{target_day}</b></div>', unsafe_allow_html=True)

# ── Main Tabs ───────────────────────────────────────────────
tab_cross, tab_all_tricks, tab_date, tab_triangle, tab_seq_triangle = st.tabs([
    "📐 क्रॉस लाईन फॅमिली मॅचिंग ट्रिक (Cross Line / Line Dekho)",
    "📊 इतर सर्व 22 ट्रिक्स झोन (Tricks Zone Pass/Fail)",
    "📅 तारीखेनुसार १००% फिक्स अंक ट्रिक (Date-Wise Fix Figures)",
    "🔺 चालू चार्ट फॅमिली त्रिकोण स्कीम (Family Triangle Scheme)",
    "⚡ चालू चार्ट फॅमिली सीक्वेन्स त्रिकोण (Sequence Triangle Scheme)",
])

# ============================================================
# TAB 1: CROSS LINE / LINE DEKHO TRICK
# ============================================================
with tab_cross:
    st.markdown(f"### 📐 क्रॉस लाईन फॅमिली मॅचिंग — `{selected_market}` ({target_day})")
    
    st.info("""
    **💡 क्रॉस लाईन ट्रिकचा खरा नियम (Cross Line Family Rule):**
    1. चालू आठवड्यातील मागील लागोपाठच्या आठवड्यांची लाईन (उभी किंवा तिरपी) घेतली जाते.
    2. संपूर्ण इतिहासामध्ये (Past Charts) अशीच क्रॉस लाईन (Cross / Diagonal Line) कधी आली होती का ते तपासले जाते.
    3. जर मागील सर्व जोड्या **Same Jodi किंवा Family Jodi** मध्ये जुळल्या, तर त्या क्रॉस लाईनची पुढची उरलेली जोडी (आणि तिची 8-Family) येण्याची **99.9% शक्यता** असते!
    4. **⚠️ सेफ्टी रुल (Red Jodi Fallback):** जर ही लाईन कधी फेल झाली, तर त्या दिवशी **RED JODI (डबल किंवा कट जोडी)** येण्याची दाट शक्यता असते!
    """)

    cross_engine = CrossLineEngine()

    @st.cache_data(ttl=300, show_spinner=False)
    def load_cross_matches(market, day, min_l):
        return CrossLineEngine().find_cross_line_matches(market, target_day=day, min_length=min_l)

    with st.spinner(f"इतिहासामध्ये {selected_market} साठी सर्व क्रॉस लाईन्स शोधत आहे..."):
        matches = load_cross_matches(selected_market, target_day, min_touch)

    if matches:
        top_match = matches[0]
        cur_seq = top_match["current_sequence"]
        hist_line = top_match["historical_line"]
        pred_jodi = top_match["predicted_jodi"]
        pred_family = top_match["predicted_family"]
        confidence = top_match["confidence"]
        hist_dr = top_match["hist_anchor_date"]
        hist_day = top_match["hist_anchor_day"]
        actual_jodi = top_match["actual_target_jodi"]

        # ── Visual Graphical Panels with SVG Arrows ──
        st.markdown("#### 📐 व्हिज्युअल क्रॉस लाईन चार्ट्स (Visual Panel Charts with Arrows):")
        
        full_grid = cross_engine.get_grid(selected_market, max_weeks=350, target_day=target_day)

        # ── Active Current Line Overview Banner ──
        st.markdown(f"#### 🔵 चालू लाईन (Active Current Line — {target_day}):")
        cur_touch_pills = []
        for s in cur_seq:
            cur_touch_pills.append(f"""<div class="match-step-badge">
<span style="color:#00d2ff;font-weight:bold;">टच {s['step']} ({s['day']}):</span> <span class="jodi-pill" style="font-size:16px;padding:2px 8px;">{s['jodi']}</span> 
<span style="font-size:11px;color:#888;">({s['date_range']})</span><br>
<span style="font-size:10px;color:#00ffcc;">Family: {', '.join(s['family'][:4])}...</span>
</div>""")
        cur_touch_pills.append(f"""<div class="match-step-badge" style="border:2px dashed #ff007f;background:#ff007f15;">
<span style="color:#ff007f;font-weight:bold;">🎯 टार्गेट टच {len(cur_seq)+1} ({target_day}):</span> <span class="jodi-pill" style="font-size:16px;padding:2px 8px;border-color:#ff007f;color:#ff007f;">???</span><br>
<span style="font-size:10px;color:#ff99aa;">(भविष्यवाणी येणे बाकी)</span>
</div>""")
        st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;'>{''.join(cur_touch_pills)}</div>", unsafe_allow_html=True)

        # ── View Mode Selector ──
        c_ctrl1, c_ctrl2 = st.columns([1, 1.5])
        with c_ctrl1:
            cur_rows_count = st.radio("चालू लाईन आठवडे (Current Line Rows):", [3, 4], index=1, horizontal=True)
        with c_ctrl2:
            comb_view_mode = st.radio(
                "पाहण्याची पद्धत (View Mode):",
                ["🖼️ सर्व कॉम्बिनेशन्स चालू लाईनसह (All Combinations Side-by-Side)", "🎯 एका वेळी एक निवडून पाहा (Single Selector)"],
                index=0,
                horizontal=True
            )

        # ── 1. ALL COMBINATIONS SIDE-BY-SIDE WITH CURRENT LINE ──
        if comb_view_mode.startswith("🖼️"):
            st.markdown(f"#### 📐 सर्व {len(matches)} ऐतिहासिक कॉम्बिनेशन्स चालू लाईनसह व्हिज्युअल तुलना:")

            cur_snippet = full_grid[-cur_rows_count:] if len(full_grid) >= cur_rows_count else full_grid

            for idx, m in enumerate(matches):
                st.markdown(f"""
                <div style="background:#121224;border:2px solid #333366;border-radius:12px;padding:14px;margin-bottom:20px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                        <span style="font-size:18px;font-weight:900;color:#00d2ff;">🔹 कॉम्बिनेशन #{idx+1} ({m['match_length']}-टच मॅच)</span>
                        <span style="background:#bb86fc22;color:#bb86fc;border:1px solid #bb86fc;padding:3px 10px;border-radius:15px;font-weight:bold;font-size:13px;">
                            {m['hist_line_type']} · विश्वासार्हता: {m['confidence']}%
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                # Generate Current snippet for this combination
                cur_proj_info = {
                    "date_range": cur_snippet[-1]["date_range"],
                    "day": target_day,
                    "jodi": "??",
                    "is_proj": True
                }

                cur_chart_html = render_cross_line_panel_html(
                    grid_snippet=cur_snippet,
                    highlighted_nodes=m["current_sequence"],
                    title=f"🔵 चालू लाईन (Current Line — शेवटचे {cur_rows_count} आठवडे)",
                    line_color="#00d2ff",
                    proj_node=cur_proj_info
                )

                # Generate Historical snippet for this combination
                m_h_rows = [h["row"] for h in m["historical_line"]]
                # Get exact historical snippet for this combination
                m_hist_snip = m.get("hist_snippet", [])

                m_proj_info = {
                    "date_range": m["hist_anchor_date"],
                    "day": m["hist_anchor_day"],
                    "jodi": m["predicted_jodi"],
                    "is_proj": True
                }

                hist_chart_html = render_cross_line_panel_html(
                    grid_snippet=m_hist_snip,
                    highlighted_nodes=m["historical_line"],
                    title=f"🟣 इतिहास क्रॉस लाईन #{idx+1} ({m['hist_anchor_day']} · {m['hist_anchor_date']})",
                    line_color="#bb86fc",
                    proj_node=m_proj_info
                )

                # Render Side-by-Side Charts
                cg1, cg2 = st.columns(2)
                with cg1:
                    st.markdown(cur_chart_html, unsafe_allow_html=True)
                with cg2:
                    st.markdown(hist_chart_html, unsafe_allow_html=True)

                # Step by step touch match verification for this combination
                step_badges = []
                for s, h in zip(m["current_sequence"], m["historical_line"]):
                    mb = '<span style="background:#00ff8822;color:#00ff88;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:11px;">EXACT</span>' if h['match_type'] == "EXACT" else '<span style="background:#00d2ff22;color:#00d2ff;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:11px;">FAMILY</span>'
                    step_badges.append(f"""<div style="display:inline-block;background:#181830;border:1px solid #333355;padding:4px 8px;border-radius:6px;margin:3px;font-size:12px;">
<b>टच {s['step']}:</b> चालू <span style="color:#00d2ff;font-weight:bold;">{s['jodi']}</span> ⟷ इतिहास <span style="color:#bb86fc;font-weight:bold;">{h['jodi']}</span> {mb}
</div>""")

                fam_pills = "".join([f'<span class="family-pill">{j}</span>' for j in m['predicted_family']])
                st.markdown(f"""
                <div style="margin-top:8px;">
                    <div style="margin-bottom:6px;">{''.join(step_badges)}</div>
                    <div style="background:#1a102a;border:1px solid #ff007f80;border-radius:8px;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                        <div>
                            <span style="color:#ff007f;font-weight:bold;font-size:13px;">🎯 कॉम्बिनेशन #{idx+1} भविष्यवाणी ਜੋडी:</span>
                            <span class="jodi-pill" style="font-size:16px;padding:2px 8px;">{m['predicted_jodi']}</span>
                        </div>
                        <div>
                            <b style="color:#ffcc00;font-size:12px;">8-फॅमिली जोड्या:</b> {fam_pills}
                        </div>
                    </div>
                </div>
                </div>
                """, unsafe_allow_html=True)

        # ── 2. SINGLE COMBINATION DETAILED FOCUS SELECTOR ──
        else:
            match_options = [
                f"कॉम्बिनेशन #{i+1}: {m['match_length']}-टच ({m['confidence']}%) | {m['hist_line_type']} ({m['hist_anchor_date']}) ➔ जोडी: {m['predicted_jodi']}"
                for i, m in enumerate(matches)
            ]
            sel_match_idx = st.selectbox("📌 पाहायचे असलेले ऐतिहासिक कॉम्बिनेशन निवडा (Select Historical Combination):", range(len(matches)), format_func=lambda i: match_options[i], index=0)

            chosen_match = matches[sel_match_idx]
            cur_seq = chosen_match["current_sequence"]
            hist_line = chosen_match["historical_line"]
            pred_jodi = chosen_match["predicted_jodi"]
            pred_family = chosen_match["predicted_family"]
            confidence = chosen_match["confidence"]
            hist_dr = chosen_match["hist_anchor_date"]
            hist_day = chosen_match["hist_anchor_day"]
            actual_jodi = chosen_match["actual_target_jodi"]

            st.markdown(f"#### 📐 निवडलेले कॉम्बिनेशन #{sel_match_idx+1} — व्हिज्युअल चार्ट्स:")
            
            cur_snippet = full_grid[-cur_rows_count:] if len(full_grid) >= cur_rows_count else full_grid
            cur_proj_info = {
                "date_range": cur_snippet[-1]["date_range"],
                "day": target_day,
                "jodi": "??",
                "is_proj": True
            }

            cur_chart_html = render_cross_line_panel_html(
                grid_snippet=cur_snippet,
                highlighted_nodes=cur_seq,
                title=f"🔵 चालू लाईन (Current Line — शेवटचे {cur_rows_count} आठवडे)",
                line_color="#00d2ff",
                proj_node=cur_proj_info
            )
            
            # Get exact historical snippet for chosen combination
            hist_snippet = chosen_match.get("hist_snippet", [])

            proj_node_info = {
                "date_range": hist_dr,
                "day": hist_day,
                "jodi": pred_jodi,
                "is_proj": True
            }

            hist_chart_html = render_cross_line_panel_html(
                grid_snippet=hist_snippet,
                highlighted_nodes=hist_line,
                title=f"🟣 इतिहासातील क्रॉस लाईन #{sel_match_idx+1} ({hist_day} · {hist_dr})",
                line_color="#bb86fc",
                proj_node=proj_node_info
            )

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown(cur_chart_html, unsafe_allow_html=True)
            with col_g2:
                st.markdown(hist_chart_html, unsafe_allow_html=True)

            fam_badges = "".join([f'<span class="family-pill">{j}</span>' for j in pred_family])
            pred_html = f"""<div class="pred-card">
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div>
        <span style="color:#00d2ff;font-size:14px;font-weight:bold;">🎯 क्रॉस लाईन #{sel_match_idx+1} भविष्यवाणी (Prediction for {target_day}):</span><br>
        <span style="font-size:24px;font-weight:900;color:#fff;">मुख्य जोडी: <span class="jodi-pill">{pred_jodi}</span></span>
    </div>
    <div style="text-align:right;">
        <span style="background:#00d2ff22;border:1px solid #00d2ff;color:#00d2ff;padding:4px 12px;border-radius:20px;font-weight:bold;font-size:14px;">
            विश्वासार्हता: {confidence}% ({chosen_match['match_length']}-टच मॅच)
        </span>
    </div>
</div>
<div style="margin-top:12px;">
    <b style="color:#ffcc00;font-size:14px;">👥 8-फॅमिली जोडी ग्रुप (Strong Family Group):</b><br>
    <div style="margin-top:4px;">
        {fam_badges}
    </div>
</div>
<div style="margin-top:10px;font-size:12px;color:#aaa;">
    📌 ही जोडी इतिहासातील <b>{hist_dr} ({hist_day})</b> च्या क्रॉस लाईनवरून प्रोजेक्ट झाली आहे.
</div>
<div class="red-warning-box">
    <b style="color:#ff5566;font-size:13px;">⚠️ लाईन फेल झाल्यास सेफ्टी बॅकअप (Red Jodi Fallback):</b><br>
    <span style="font-size:12px;color:#ccc;">
        जर ही क्रॉस लाईन फेल झाली तर बाजारात <b>RED JODI</b> (डबल किंवा कट जोडी) येते:<br>
        <code style="color:#ff99aa;">00, 11, 22, 33, 44, 55, 66, 77, 88, 99 | 05, 50, 16, 61, 27, 72, 38, 83, 49, 94</code>
    </span>
</div>
</div>"""
            st.markdown(pred_html, unsafe_allow_html=True)

        # ── All Historical Matches Table ──
        st.markdown("---")
        st.markdown(f"### 📋 इतिहासात सापडलेल्या सर्व क्रॉस लाईन्सचा सारांश ({len(matches)} एकूण कॉम्बिनेशन्स):")
        
        table_rows = []
        for i, m in enumerate(matches):
            cur_j = " ➔ ".join([s["jodi"] for s in m["current_sequence"]])
            hist_j = " ➔ ".join([h["jodi"] for h in m["historical_line"]])
            types = ", ".join([h["match_type"][:3] for h in m["historical_line"]])
            table_rows.append({
                "क्र.": i + 1,
                "टच": f"{m['match_length']}-टच",
                "विश्वासार्हता": f"{m['confidence']}%",
                "चालू लाईन": cur_j,
                "इतिहास क्रॉस लाईन": hist_j,
                "मॅच प्रकार": types,
                "इतिहास तारीख": f"{m['hist_anchor_day']} ({m['hist_anchor_date']})",
                "भविष्यवाणी जोडी": m["predicted_jodi"],
                "8-फॅमिली जोड्या": ", ".join(m["predicted_family"]),
            })

        df_m = pd.DataFrame(table_rows)
        st.dataframe(df_m, use_container_width=True, height=350)

    else:
        st.warning(f"⚠️ `{selected_market}` साठी {target_day} दिवशी {min_touch}-टच क्रॉस लाईन सापडली नाही. किमान टच कमी करा (उदा. 2 किंवा 3).")

# ============================================================
# TAB 2: ALL 21 TRICKS PASS/FAIL DASHBOARD
# ============================================================
with tab_all_tricks:
    st.markdown(f"### 📊 सर्व 21 ट्रिक्स झोन पास/फेल विश्लेषण — `{selected_market}`")
    st.caption("dpbossking.in वरील सर्व 21 ट्रिक्सचा ऐतिहासिक पास दर आणि चालू आठवड्यातील अचूक स्थिती.")

    @st.cache_data(ttl=300, show_spinner=False)
    def load_tricks(market):
        return TrickAnalyzer().analyze_all(market)

    with st.spinner(f"{selected_market} साठी सर्व ट्रिक्स तपासत आहे..."):
        trick_results = load_tricks(selected_market)

    # Summary metrics row
    c1, c2, c3, c4 = st.columns(4)
    passing_now = [r for r in trick_results if r.get("streak_type","").startswith("✅") and r["current_streak"] >= 2]
    best = trick_results[0] if trick_results else {}
    long_s = max(trick_results, key=lambda x: x.get("current_streak",0)) if trick_results else {}

    c1.metric("एकूण ट्रिक्स (Total Tricks)", len(trick_results))
    c2.metric("सध्या चालू पास (2+ आठवडे)", len(passing_now))
    c3.metric("सर्वोत्तम पास दर",
              f"{best.get('pass_rate',0):.1f}%" if best else "—",
              MARATHI_TRICKS.get(best.get("trick_name",""), (best.get("trick_name",""),))[0][:18] if best else "")
    c4.metric("सर्वात लांब Streak",
              f"{long_s.get('current_streak',0)}w {long_s.get('streak_type','')[:2]}" if long_s else "—",
              MARATHI_TRICKS.get(long_s.get("trick_name",""), (long_s.get("trick_name",""),))[0][:18] if long_s else "")

    st.markdown("---")

    # Pass rate bar chart
    labels_marathi = []
    colors_bar = []
    rates_bar = []
    for r in trick_results:
        mn = MARATHI_TRICKS.get(r["trick_name"], (r["trick_name"],))[0]
        labels_marathi.append(mn[:35])
        rates_bar.append(r["pass_rate"])
        is_p = r.get("streak_type","").startswith("✅")
        colors_bar.append("#00ff88" if is_p else "#ff4444")

    fig_bar = go.Figure(go.Bar(
        x=rates_bar, y=labels_marathi, orientation="h",
        marker_color=colors_bar,
        text=[f"{v:.0f}%" for v in rates_bar], textposition="outside",
    ))
    fig_bar.update_layout(
        paper_bgcolor="#0a0a15", plot_bgcolor="#0a0a15", font_color="#ccc",
        height=max(400, len(trick_results) * 30 + 80),
        xaxis=dict(range=[0, 110], gridcolor="#1a1a2a", title="पास दर %"),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=280, r=60, t=20, b=30),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Detailed Cards for Each Trick
    for r in trick_results:
        is_pass = r.get("streak_type","").startswith("✅")
        streak = r["current_streak"]
        st_type = r["streak_type"]
        last8 = r.get("last8", [])
        sparks = "".join(["🟩" if x else "🟥" for x in last8])
        pr = r["pass_rate"]
        pr_color = "#00ff88" if pr >= 50 else ("#ffcc00" if pr >= 30 else "#ff5555")
        card_cls = "trick-pass" if is_pass else "trick-fail"
        mn_name, mn_desc = MARATHI_TRICKS.get(r["trick_name"], (r["trick_name"], r["description"]))
        status_icon = "🟢" if is_pass else "🔴"

        st.markdown(f"""
        <div class="{card_cls}">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
            <div>
              <span style="font-size:16px;font-weight:bold;color:#fff;">{status_icon} {mn_name}</span>
              <span style="font-size:11px;color:#777;margin-left:8px;background:#1a1a2a;
                padding:1px 6px;border-radius:4px;">{r['category']}</span>
            </div>
            <div style="display:flex;gap:12px;align-items:center;">
              <span style="color:{pr_color};font-size:24px;font-weight:900;">{pr:.1f}%</span>
              <span style="color:#aaa;font-size:13px;">{streak} आठवडे {st_type}</span>
              <span style="font-size:16px;">{sparks}</span>
            </div>
          </div>
          <div style="font-size:12px;color:#99aacc;margin-top:6px;">{mn_desc}</div>
          <div style="font-size:11px;color:#555;margin-top:4px;">
            तपासले: {r['total_weeks']} आठवडे &nbsp;|&nbsp;
            ✅ {r['passes']} पास &nbsp;|&nbsp;
            ❌ {r['fails']} फेल &nbsp;|&nbsp;
            शेवटचा: <b style="color:#888;">{r['latest_date']}</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # 4-Markets Mon-Tue Live Drilldown Table
    st.markdown("---")
    with st.expander("🔍 ४ मार्केट्स (MD | KA | MN | MAIN) सोम-मंगळ रेकॉर्ड तपासा (4-Markets Mon-Tue Live Record)", expanded=False):
        st.markdown("""
        **नियम सारांश:** सोमवारच्या ४ बाजारांमधील (मिलन डे, कल्याण, मिलन नाईट, मेन बाजार) जोड्या मंगळवारी याच ४ बाजारांमध्ये 
        एकसारखी (Exact) किंवा ८-फॅमिली ग्रुप (Family Bracket) मध्ये रिपीट होतात.
        """)
        @st.cache_data(ttl=300, show_spinner=False)
        def load_4m_records():
            return TrickAnalyzer().get_4markets_recent_analysis(limit=16)

        four_m_recs = load_4m_records()
        if four_m_recs:
            rows_4m = []
            for fr in four_m_recs:
                m_str = f"MD: <b>{fr['mon']['MD']}</b> | KA: <b>{fr['mon']['KA']}</b> | MN: <b>{fr['mon']['MN']}</b> | MU: <b>{fr['mon']['MU']}</b>"
                t_str = f"MD: <b>{fr['tue']['MD']}</b> | KA: <b>{fr['tue']['KA']}</b> | MN: <b>{fr['tue']['MN']}</b> | MU: <b>{fr['tue']['MU']}</b>"
                all_m = fr['exact_pairs'] + fr['family_pairs']
                matches_str = "<br>".join(all_m) if all_m else "—"
                status_str = "✅ <span style='color:#00ff88;font-weight:bold;'>PASS</span>" if fr['is_pass'] else "❌ <span style='color:#ff4444;font-weight:bold;'>FAIL</span>"
                rows_4m.append({
                    "आठवडा (Week)": fr['date_range'],
                    "सोमवार जोड्या (Mon Jodis)": m_str,
                    "मंगळवार जोड्या (Tue Jodis)": t_str,
                    "मॅच झालेल्या जोड्या/फॅमिली (Repeat Match)": matches_str,
                    "निकाल (Result)": status_str
                })
            df_4m = pd.DataFrame(rows_4m)
            st.write(df_4m.to_html(escape=False, index=False), unsafe_allow_html=True)



# ============================================================
# TAB 3: DATE-WISE FIX FIGURES TRICK
# ============================================================
with tab_date:
    st.markdown(f"### 📅 तारीखेनुसार १००% फिक्स अंक ट्रिक (Date-Wise Fix Figure Analysis) — `{selected_market}`")
    
    st.info("""
    **💡 तारीखेनुसार फिक्स अंक काढण्याचा नियम (Date-Wise Fix Rule):**
    - कोणत्याही दिवसाचा खेळ हा त्या दिवसाच्या **कॅलेंडर तारखेवर (Date)** अवलंबून असतो.
    - **नियम:** ज्या तारखेचा गेम खेळायचा आहे, त्या तारखेचा **शेवटचा अंक (Unit Digit)** घ्या. त्यामधून:
      1. मागची तारीख (Date - 1)
      2. आजची तारीख (Date)
      3. पुढची तारीख (Date + 1)
    - या ३ तारखांचे **३ मूळ अंक + ३ कट अंक = एकूण ६ फिक्स अंक (३ कट जोड्या)** मिळतात.
    - हे ६ अंक भारतातील कोणत्याही मटका बाजारात **Open किंवा Close मध्ये ८५%+ वेळा येतातच येतात!**
    """)

    date_engine = DateFigureEngine()

    # ── 1. Interactive Live Date Calculator ──
    st.markdown("#### 🎯 कोणत्याही तारखेचे फिक्स ६ अंक काढा (Live Date Calculator):")
    
    col_d1, col_d2 = st.columns([1.5, 2])
    with col_d1:
        import datetime
        sel_date = st.date_input("📅 तारीख निवडा (Select Date):", value=datetime.date.today())
        sel_day_num = sel_date.day
        fig_data = date_engine.get_figures_for_date(sel_day_num)
        
    with col_d2:
        base_str = ", ".join(str(x) for x in fig_data["base_digits"])
        cut_str = ", ".join(str(x) for x in fig_data["cut_digits"])
        fix_pills = " ".join([f'<span class="jodi-pill" style="font-size:18px;padding:3px 10px;margin:2px;">{x}</span>' for x in fig_data["fix_figures"]])
        
        st.markdown(f"""
        <div style="background:#14122b;border:2px solid #00d2ff;border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                <span style="font-size:16px;font-weight:bold;color:#00ffcc;">
                    🗓️ तारीख: {sel_date.strftime('%d/%m/%Y')} (तारीख युनिट: <b style="color:#ffcc00;font-size:18px;">{fig_data['unit_digit']}</b>)
                </span>
                <span style="background:#00d2ff22;color:#00d2ff;border:1px solid #00d2ff;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:bold;">
                    ३ कट जोड्या: {fig_data['pairs_str']}
                </span>
            </div>
            <div style="font-size:13px;color:#ccc;margin-bottom:6px;">
                • मागची तारीख: <b>{fig_data['prev_digit']}</b> &nbsp;|&nbsp; आजची: <b>{fig_data['unit_digit']}</b> &nbsp;|&nbsp; पुढची: <b>{fig_data['next_digit']}</b><br>
                • मूळ ३ अंक: <b style="color:#ffcc00;">{base_str}</b> &nbsp;|&nbsp; कट ३ अंक: <b style="color:#bb86fc;">{cut_str}</b>
            </div>
            <div style="margin-top:8px;">
                <span style="color:#fff;font-weight:bold;font-size:14px;">🎯 आजचे ६ अचूक फिक्स अंक:</span><br>
                <div style="margin-top:6px;">{fix_pills}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 2. Weekly Accurate Pass/Fail History ──
    st.markdown(f"#### 📊 `{selected_market}` मधील आठवडा-दर-आठवडा अचूक पास रेकॉर्ड (Weekly Pass History):")
    st.caption("खालील प्रत्येक आठवड्यात कोणत्या दिवशी कोणती तारीख होती, त्या दिवशी कोणते ६ अंक बनले आणि बाजारात जोडी काय आली याचा संपूर्ण अचूक हिशोब.")

    @st.cache_data(ttl=300, show_spinner=False)
    def load_date_weeks(mkt):
        return DateFigureEngine().analyze_market_weeks(mkt, limit_weeks=12)

    with st.spinner(f"`{selected_market}` साठी आठवडा-निहाय पास रेकॉर्ड लोड करत आहे..."):
        week_data = load_date_weeks(selected_market)

    if week_data:
        # Summary metrics
        tot_w = len(week_data)
        perfect_w = sum(1 for w in week_data if w["is_perfect_week"])
        tot_d = sum(w["total_days"] for w in week_data)
        pass_d = sum(w["passed_days"] for w in week_data)
        overall_rate = round((pass_d / tot_d) * 100, 1) if tot_d else 0

        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("तपासलेले आठवडे", f"{tot_w} आठवडे", f"{tot_d} एकूण दिवस")
        sm2.metric("दिवसनिहाय पास दर", f"{overall_rate}%", f"{pass_d}/{tot_d} दिवस पास")
        sm3.metric("१००% परफेक्ट आठवडे", f"{perfect_w} आठवडे", f"सर्व ६ दिवस पास")
        sm4.metric("सरासरी आठवडा स्कोअर", f"{round(pass_d/tot_w, 1)} दिवस/आठवडा", "६ दिवसांपैकी")

        st.markdown("<br>", unsafe_allow_html=True)

        for w in week_data:
            badge_color = "#00ff88" if w["pass_rate"] >= 80 else ("#ffcc00" if w["pass_rate"] >= 60 else "#ff4444")
            st.markdown(f"""
            <div style="background:#0f0f20;border:1.5px solid #2a2a4a;border-radius:10px;padding:12px;margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                    <span style="font-size:16px;font-weight:bold;color:#00d2ff;">
                        📅 आठवडा: {w['date_range']}
                    </span>
                    <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color};padding:3px 12px;border-radius:15px;font-weight:900;font-size:13px;">
                        {w['passed_days']}/{w['total_days']} दिवस पास ({w['pass_rate']}%)
                    </span>
                </div>
            """, unsafe_allow_html=True)

            day_rows = []
            for d in w["days"]:
                status_badge = f"<span style='color:#00ff88;font-weight:bold;'>✅ {d['hit_desc']}</span>" if d['is_hit'] else "<span style='color:#ff4444;font-weight:bold;'>❌ फेल (Miss)</span>"
                figs_formatted = " ".join([f"<span style='background:#222238;padding:1px 5px;border-radius:4px;color:#ffcc00;font-weight:bold;'>{x}</span>" for x in d['fix_figures']])
                
                day_rows.append({
                    "वार (Day)": f"<b>{d['day_marathi']}</b>",
                    "तारीख (Date)": d["date_formatted"],
                    "तारीखेचे ६ फिक्स अंक": figs_formatted,
                    "बाजारातील निकाल (Jodi)": f"ओपन: <b>{d['o_d']}</b> | क्लोज: <b>{d['c_d']}</b> ➔ <span class='jodi-pill'>{d['jodi']}</span>",
                    "निकाल (Status)": status_badge
                })

            df_days = pd.DataFrame(day_rows)
            st.write(df_days.to_html(escape=False, index=False), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ या मार्केटसाठी डेटा उपलब्ध नाही.")

    # ── 3. Master Date Chart Reference ──
    st.markdown("---")
    with st.expander("📖 संपूर्ण १ ते ० तारखांचा मास्टर फिक्स अंक चार्ट (Master Date 1-0 Reference Chart)", expanded=False):
        st.markdown("""
        **तारीख युनिट चार्ट (Date Last Digit 1 to 0 Reference):**
        """)
        chart_rows = [
            {"तारीख शेवटचा अंक": "<b>1</b> (उदा. 1, 11, 21, 31)", "३ तारखा": "0, 1, 2", "६ फिक्स अंक": "<b>1, 6, 0, 5, 4, 9</b>", "कट जोड्या": "1-6 | 0-5 | 4-9"},
            {"तारीख शेवटचा अंक": "<b>2</b> (उदा. 2, 12, 22)", "३ तारखा": "1, 2, 3", "६ फिक्स अंक": "<b>2, 7, 3, 8, 1, 6</b>", "कट जोड्या": "2-7 | 3-8 | 1-6"},
            {"तारीख शेवटचा अंक": "<b>3</b> (उदा. 3, 13, 23)", "३ तारखा": "2, 3, 4", "६ फिक्स अंक": "<b>3, 8, 4, 9, 2, 7</b>", "कट जोड्या": "3-8 | 4-9 | 2-7"},
            {"तारीख शेवटचा अंक": "<b>4</b> (उदा. 4, 14, 24)", "३ तारखा": "3, 4, 5", "६ फिक्स अंक": "<b>4, 9, 0, 5, 3, 8</b>", "कट जोड्या": "4-9 | 0-5 | 3-8"},
            {"तारीख शेवटचा अंक": "<b>5</b> (उदा. 5, 15, 25)", "३ तारखा": "4, 5, 6", "६ फिक्स अंक": "<b>0, 5, 1, 6, 4, 9</b>", "कट जोड्या": "0-5 | 1-6 | 4-9"},
            {"तारीख शेवटचा अंक": "<b>6</b> (उदा. 6, 16, 26)", "३ तारखा": "5, 6, 7", "६ फिक्स अंक": "<b>1, 6, 2, 7, 0, 5</b>", "कट जोड्या": "1-6 | 2-7 | 0-5"},
            {"तारीख शेवटचा अंक": "<b>7</b> (उदा. 7, 17, 27)", "३ तारखा": "6, 7, 8", "६ फिक्स अंक": "<b>2, 7, 3, 8, 1, 6</b>", "कट जोड्या": "2-7 | 3-8 | 1-6"},
            {"तारीख शेवटचा अंक": "<b>8</b> (उदा. 8, 18, 28)", "३ तारखा": "7, 8, 9", "६ फिक्स अंक": "<b>3, 8, 2, 7, 4, 9</b>", "कट जोड्या": "3-8 | 2-7 | 4-9"},
            {"तारीख शेवटचा अंक": "<b>9</b> (उदा. 9, 19, 29)", "३ तारखा": "8, 9, 0", "६ फिक्स अंक": "<b>4, 9, 0, 5, 3, 8</b>", "कट जोड्या": "4-9 | 0-5 | 3-8"},
            {"तारीख शेवटचा अंक": "<b>0</b> (उदा. 10, 20, 30)", "३ तारखा": "9, 0, 1", "६ फिक्स अंक": "<b>0, 5, 1, 6, 4, 9</b>", "कट जोड्या": "0-5 | 1-6 | 4-9"},
        ]
        st.write(pd.DataFrame(chart_rows).to_html(escape=False, index=False), unsafe_allow_html=True)


# ============================================================
# TAB 5: FAMILY TRIANGLE SCHEME (फॅमिली त्रिकोण स्कीम)
# ============================================================
with tab_triangle:
    st.markdown(f"### 🔺 चालू चार्ट फॅमिली त्रिकोण स्कीम (Family Triangle Scheme) — `{selected_market}`")
    
    st.info("""
    **💡 फॅमिली त्रिकोण स्कीमचा नियम (Family Triangle Geometric Scheme):**
    - **नियम:** चालू चार्टमधील **२, ३, ४, ५ किंवा ६ आठवड्यांमध्ये** ३ नोड्स (Cells) मिळून **फॅमिली त्रिकोण** तयार होतो ज्यांची ३ टोके **एकाच ८-फॅमिली ग्रुपमधील (Same Family Jodis)** असतात.
    - **🔹 २ ओळी (2-Row Micro-Triangle):** मागील व चालू आठवड्यातील जलद २-आठवडे सायकल.
    - **🔹 ३ ओळी (3-Row Classic Triangle):** ३ आठवड्यांचा क्लासिक त्रिकोण लूप (Base + Apex फॉर्मेशन).
    - **🔹 ४-६ ओळी (Multi-Week Patterns):** डेल्टा V-त्रिकोण, समद्विभुज व काटकोन त्रिकोण.
    - **🎯 टार्गेट त्रिकोण:** आधीच्या २ जोड्या एकाच फॅमिलीतील असून त्रिकोणाचे ३ रे टोक चालू टार्गेट दिवसावर (`??`) येते, तेव्हा चालू दिवशी त्याच फॅमिलीची जोडी येण्याची दाट शक्यता असते!
    """)

    tri_engine = FamilyTriangleEngine()

    c_tr1, c_tr2 = st.columns([1.2, 1.8])
    with c_tr1:
        tri_rows_cnt = st.radio("चालू चार्ट ओळींची संख्या (Chart Rows):", [2, 3, 4, 5, 6], index=1, horizontal=True, key="tri_rows_rad")
    with c_tr2:
        tri_mode = st.radio(
            "त्रिकोण पाहण्याची पद्धत (Triangle View Mode):",
            [
                "🎯 टार्गेट फॅमिली त्रिकोण — एक-एक पाहा (Single Target View)",
                "✨ सर्व टार्गेट त्रिकोण एकत्र पाहा (Overlay All Target Triangles)",
                "🔺 चार्टमधील पूर्ण झालेले जुने त्रिकोण (Completed Triangles)"
            ],
            index=0,
            horizontal=True,
            key="tri_mode_rad"
        )

    @st.cache_data(ttl=300, show_spinner=False)
    def load_triangle_data(mkt, rows, t_day):
        eng = FamilyTriangleEngine()
        try:
            snip = eng.get_snippet(mkt, rows_count=rows, target_day=t_day)
        except TypeError:
            snip = eng.get_snippet(mkt, rows_count=rows)
        data = eng.find_all_triangles(snip, target_day=t_day)
        return snip, data

    with st.spinner(f"`{selected_market}` च्या शेवटच्या {tri_rows_cnt} ओळींमध्ये फॅमिली त्रिकोण शोधत आहे..."):
        tri_snip, tri_data = load_triangle_data(selected_market, tri_rows_cnt, target_day)

    comp_triangles = tri_data.get("completed", [])
    proj_triangles = tri_data.get("projected", [])

    if tri_mode.startswith("🎯"):
        # Projected Target Triangles - Single View
        st.markdown(f"#### 🎯 टार्गेट `{target_day}` कडे पॉईंट करणारे फॅमिली त्रिकोण ({len(proj_triangles)} सापडले):")
        
        if proj_triangles:
            opt_labels = [
                f"त्रिकोण #{i+1}: {t['summary']} ➔ 8-Family: {', '.join(t['predicted_family'][:4])}..."
                for i, t in enumerate(proj_triangles)
            ]
            sel_proj_idx = st.selectbox("📌 पाहायचा असलेला टार्गेट त्रिकोण निवडा (Select Target Triangle):", range(len(proj_triangles)), format_func=lambda i: opt_labels[i], index=0)
            
            chosen_proj = proj_triangles[sel_proj_idx]
            
            # Render Visual Chart
            chart_html = render_family_triangle_panel_html(
                grid_snippet=tri_snip,
                triangles=proj_triangles,
                active_idx=sel_proj_idx,
                title=f"🔺 टार्गेट फॅमिली त्रिकोण #{sel_proj_idx+1} (शेवटच्या {tri_rows_cnt} ओळी — टार्गेट: {target_day})"
            )
            st.markdown(chart_html, unsafe_allow_html=True)

            # Details card
            node_A, node_B, node_T = chosen_proj["nodes"]
            fam_pills_proj = "".join([f'<span class="family-pill">{j}</span>' for j in chosen_proj["predicted_family"]])
            
            st.markdown(f"""
            <div style="background:#1a102a;border:2px solid #ff007f;border-radius:12px;padding:16px;margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                    <span style="font-size:18px;font-weight:900;color:#ff007f;">🎯 टार्गेट त्रिकोण #{sel_proj_idx+1} भविष्यवाणी — {target_day}</span>
                    <span style="background:#ff007f22;border:1px solid #ff007f;color:#ff007f;padding:3px 10px;border-radius:15px;font-weight:bold;font-size:12px;">
                        {chosen_proj['type_title']}
                    </span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">टोक १ (Vertex A):</span> <span class="jodi-pill">{node_A['jodi']}</span> ({node_A['day']} · {node_A['date_range']})
                    </div>
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">टोक २ (Vertex B):</span> <span class="jodi-pill">{node_B['jodi']}</span> ({node_B['day']} · {node_B['date_range']})
                    </div>
                    <div class="match-step-badge" style="border-color:#ff007f;background:#ff007f15;">
                        <span style="color:#ff007f;font-weight:bold;">🎯 टार्गेट टोक ३:</span> <span class="jodi-pill" style="border-color:#ff007f;color:#ff007f;">??</span> ({target_day} चालू आठवडा)
                    </div>
                </div>
                <div>
                    <b style="color:#ffcc00;font-size:14px;">👥 त्रिकोण पूर्ण करणारा ८-फॅमिली जोडी ग्रुप:</b><br>
                    <div style="margin-top:6px;">{fam_pills_proj}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"ℹ️ चालू चार्टच्या शेवटच्या {tri_rows_cnt} ओळींमध्ये {target_day} साठी टार्गेट त्रिकोण सापडला नाही. ओळींची संख्या बदलून पाहा.")

    elif tri_mode.startswith("✨"):
        # Overlay All Target Triangles pointing only to target_day (e.g. Tuesday)
        st.markdown(f"#### ✨ `{target_day}` कडे पॉईंट करणारे सर्व टार्गेट फॅमिली त्रिकोण एकत्र ({len(proj_triangles)} सापडले):")
        if proj_triangles:
            overlay_html = render_family_triangle_panel_html(
                grid_snippet=tri_snip,
                triangles=proj_triangles,
                active_idx=None,
                title=f"✨ {target_day} '??' ला पॉईंट करणारे सर्व {len(proj_triangles)} फॅमिली त्रिकोण (एकत्रित ओव्हरले — शेवटचे {tri_rows_cnt} आठवडे)"
            )
            st.markdown(overlay_html, unsafe_allow_html=True)

            st.markdown(f"##### 📋 सर्व {len(proj_triangles)} टार्गेट त्रिकोणांची भविष्यवाणी:")
            grid_cols = st.columns(min(len(proj_triangles), 3) if len(proj_triangles) > 0 else 1)
            for i, t in enumerate(proj_triangles):
                with grid_cols[i % len(grid_cols)]:
                    pal = TRIANGLE_PALETTES[i % len(TRIANGLE_PALETTES)]
                    fam_pills = "".join([f'<span class="family-pill" style="font-size:11px;padding:2px 6px;">{j}</span>' for j in t["predicted_family"][:4]])
                    st.markdown(f"""
                    <div style="background:#141126;border:1.5px solid {pal['stroke']};border-radius:10px;padding:10px;margin-bottom:10px;">
                        <b style="color:{pal['stroke']};font-size:13px;">त्रिकोण #{i+1}: {t['type_title']}</b><br>
                        <span style="font-size:12px;color:#ccc;">🔗 {t['summary']}</span><br>
                        <div style="margin-top:5px;"><b style="color:#ffcc00;font-size:11px;">8-Family:</b> {fam_pills}...</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"ℹ️ चालू चार्टच्या शेवटच्या {tri_rows_cnt} ओळींमध्ये {target_day} '??' कडे पॉईंट करणारे फॅमिली त्रिकोण सापडले नाहीत.")

    elif tri_mode.startswith("🔺"):
        # Completed Triangles
        st.markdown(f"#### 🔺 चार्टमधील पूर्ण झालेले फॅमिली त्रिकोण ({len(comp_triangles)} सापडले):")
        
        if comp_triangles:
            opt_comp_labels = [
                f"त्रिकोण #{i+1}: {t['summary']} ({t['type_title'][:20]}) ➔ Family: {', '.join(t['family'][:4])}..."
                for i, t in enumerate(comp_triangles)
            ]
            sel_comp_idx = st.selectbox("📌 पाहायचा असलेला पूर्ण त्रिकोण निवडा (Select Completed Triangle):", range(len(comp_triangles)), format_func=lambda i: opt_comp_labels[i], index=0)
            
            chosen_comp = comp_triangles[sel_comp_idx]
            
            # Render Visual Chart
            comp_chart_html = render_family_triangle_panel_html(
                grid_snippet=tri_snip,
                triangles=comp_triangles,
                active_idx=sel_comp_idx,
                title=f"🔺 पूर्ण झालेला फॅमिली त्रिकोण #{sel_comp_idx+1} ({chosen_comp['type_title']})"
            )
            st.markdown(comp_chart_html, unsafe_allow_html=True)

            # Details card
            nA, nB, nC = chosen_comp["nodes"]
            fam_pills_comp = "".join([f'<span class="family-pill">{j}</span>' for j in chosen_comp["family"]])
            
            st.markdown(f"""
            <div style="background:#121226;border:2px solid #00d2ff;border-radius:12px;padding:16px;margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                    <span style="font-size:18px;font-weight:900;color:#00d2ff;">🔺 फॅमिली त्रिकोण #{sel_comp_idx+1} तपशील</span>
                    <span style="background:#00d2ff22;border:1px solid #00d2ff;color:#00d2ff;padding:3px 10px;border-radius:15px;font-weight:bold;font-size:12px;">
                        {chosen_comp['type_title']} · विस्तार: {chosen_comp['row_span']} आठवडे
                    </span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">टोक १ (Vertex A):</span> <span class="jodi-pill">{nA['jodi']}</span> ({nA['day']} · {nA['date_range']})
                    </div>
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">टोक २ (Vertex B):</span> <span class="jodi-pill">{nB['jodi']}</span> ({nB['day']} · {nB['date_range']})
                    </div>
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">टोक ३ (Vertex C):</span> <span class="jodi-pill">{nC['jodi']}</span> ({nC['day']} · {nC['date_range']})
                    </div>
                </div>
                <div>
                    <b style="color:#ffcc00;font-size:14px;">👥 या त्रिकोणातील समान ८-फॅमिली जोडी ग्रुप:</b><br>
                    <div style="margin-top:6px;">{fam_pills_comp}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"ℹ️ चालू चार्टच्या शेवटच्या {tri_rows_cnt} ओळींमध्ये पूर्ण झालेले त्रिकोण सापडले नाहीत.")

    # ── Summary Table of All Discovered Triangles ──
    st.markdown("---")
    with st.expander(f"📋 चालू चार्टमधील सर्व फॅमिली त्रिकोणांची यादी ({len(comp_triangles)} पूर्ण / {len(proj_triangles)} टार्गेट)", expanded=False):
        all_rows_tri = []
        for i, t in enumerate(comp_triangles):
            all_rows_tri.append({
                "प्रकार": "🔺 पूर्ण त्रिकोण",
                "आकार": t["type_title"],
                "टोके (Vertices)": t["summary"],
                "जोड्या": ", ".join(t["jodis"]),
                "८-फॅमिली": ", ".join(t["family"][:4]) + "..."
            })
        for i, t in enumerate(proj_triangles):
            all_rows_tri.append({
                "प्रकार": "🎯 टार्गेट त्रिकोण",
                "आकार": t["type_title"],
                "टोके (Vertices)": t["summary"],
                "जोड्या": ", ".join(t["known_jodis"]) + " ➔ ??",
                "८-फॅमिली": ", ".join(t["predicted_family"][:4]) + "..."
            })
        if all_rows_tri:
            st.write(pd.DataFrame(all_rows_tri).to_html(escape=False, index=False), unsafe_allow_html=True)


# ============================================================
# TAB 6: FAMILY SEQUENCE TRIANGLE SCHEME (फॅमिली सीक्वेन्स त्रिकोण)
# ============================================================
with tab_seq_triangle:
    st.markdown(f"### ⚡ चालू चार्ट फॅमिली सीक्वेन्स त्रिकोण (Family Sequence Triangle) — `{selected_market}`")
    
    st.info("""
    **💡 फॅमिली सीक्वेन्स त्रिकोण स्कीमचा नियम (Family Sequence Rule):**
    - **नियम:** अंक वेगळे न बघता **पूर्ण २-अंकी जोडी लेव्हलवर सलग फॅमिली क्रम (Sequence)** तपासला जातो.
    - **उदा.** त्रिकोणात टोक १ = **`81`** (यात ३१ आहे) आणि टोक २ = **`23`** (यात ३२ आहे) $\implies$ **`31 ➔ 32`** चा सलग +१ क्रम तयार झाला!
    - **🎯 टार्गेट टोक (`??`):** हा क्रम पूर्ण करण्यासाठी चालू दिवशी २ संभाव्य फॅमिलीज मिळतात:
      1. ⏩ **पुढील क्रम (+१):** $31 \to 32 \to \mathbf{33}$ $\implies$ **३३ ची फॅमिली** (`33, 38, 83, 88`)
      2. ⏪ **मागील क्रम (-१):** $\mathbf{30} \to 31 \to 32$ $\implies$ **३० ची फॅमिली** (`30, 35, 80, 85, 03, 08, 53, 58`)
    """)

    seq_tri_engine = FamilySequenceTriangleEngine()

    c_sq1, c_sq2 = st.columns([1.2, 1.8])
    with c_sq1:
        seq_rows_cnt = st.radio("चालू चार्ट ओळींची संख्या (Chart Rows):", [2, 3, 4, 5, 6], index=1, horizontal=True, key="seq_rows_rad")
    with c_sq2:
        seq_mode = st.radio(
            "सीक्वेन्स पाहण्याची पद्धत (Sequence View Mode):",
            [
                "🎯 टार्गेट फॅमिली सीक्वेन्स — एक-एक पाहा (Single Target View)",
                "✨ सर्व टार्गेट सीक्वेन्स एकत्र पाहा (Overlay All Target Sequences)",
                "⚡ चार्टमधील पूर्ण झालेले जुने सीक्वेन्स (Completed Sequences)"
            ],
            index=0,
            horizontal=True,
            key="seq_mode_rad"
        )

    @st.cache_data(ttl=300, show_spinner=False)
    def load_seq_triangle_data(mkt, rows, t_day):
        eng = FamilySequenceTriangleEngine()
        try:
            snip = eng.get_snippet(mkt, rows_count=rows, target_day=t_day)
        except TypeError:
            snip = eng.get_snippet(mkt, rows_count=rows)
        data = eng.find_all_sequence_triangles(snip, target_day=t_day)
        return snip, data

    with st.spinner(f"`{selected_market}` च्या शेवटच्या {seq_rows_cnt} ओळींमध्ये फॅमिली सीक्वेन्स शोधत आहे..."):
        seq_snip, seq_data = load_seq_triangle_data(selected_market, seq_rows_cnt, target_day)

    comp_seq_tri = seq_data.get("completed", [])
    proj_seq_tri = seq_data.get("projected", [])

    if seq_mode.startswith("🎯"):
        st.markdown(f"#### 🎯 टार्गेट `{target_day}` कडे जाणारे फॅमिली सीक्वेन्स त्रिकोण ({len(proj_seq_tri)} सापडले):")
        
        if proj_seq_tri:
            opt_seq_labels = [
                f"सीक्वेन्स #{i+1}: {t['summary']} ➔ {t['sequence_formula']}"
                for i, t in enumerate(proj_seq_tri)
            ]
            sel_seq_idx = st.selectbox("📌 पाहायचा असलेला टार्गेट सीक्वेन्स निवडा:", range(len(proj_seq_tri)), format_func=lambda i: opt_seq_labels[i], index=0)
            chosen_seq = proj_seq_tri[sel_seq_idx]
            
            # Render SVG Chart
            seq_chart_html = render_family_sequence_triangle_panel_html(
                grid_snippet=seq_snip,
                triangles=proj_seq_tri,
                active_idx=sel_seq_idx,
                title=f"⚡ टार्गेट फॅमिली सीक्वेन्स #{sel_seq_idx+1} (शेवटच्या {seq_rows_cnt} ओळी — टार्गेट: {target_day})"
            )
            st.markdown(seq_chart_html, unsafe_allow_html=True)

            # Details card
            node_A, node_B, node_T = chosen_seq["nodes"]
            fwd_pills = "".join([f'<span class="family-pill">{j}</span>' for j in chosen_seq["fwd_family"]])
            bwd_pills = "".join([f'<span class="family-pill" style="border-color:#ff007f80;color:#ff77aa;">{j}</span>' for j in chosen_seq["bwd_family"]])
            
            st.markdown(f"""
            <div style="background:#13112b;border:2px solid #00d2ff;border-radius:12px;padding:16px;margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                    <span style="font-size:18px;font-weight:900;color:#00d2ff;">⚡ सीक्वेन्स #{sel_seq_idx+1} भाकीत — {target_day}</span>
                    <span style="background:#00d2ff22;border:1px solid #00d2ff;color:#00d2ff;padding:3px 10px;border-radius:15px;font-weight:bold;font-size:12px;">
                        {chosen_seq['type_title']}
                    </span>
                </div>
                <div style="font-size:15px;color:#fff;margin-bottom:12px;background:#1b1938;padding:8px 12px;border-radius:8px;">
                    <b style="color:#ffcc00;">🔗 सीक्वेन्स फॉर्म्युला:</b> <span style="color:#00ffcc;font-weight:bold;">{chosen_seq['sequence_formula']}</span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">① टोक १:</span> <span class="jodi-pill">{node_A['jodi']}</span> ({node_A['day']} · {node_A['date_range']})
                    </div>
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">② टोक २:</span> <span class="jodi-pill">{node_B['jodi']}</span> ({node_B['day']} · {node_B['date_range']})
                    </div>
                    <div class="match-step-badge" style="border-color:#ff007f;background:#ff007f15;">
                        <span style="color:#ff007f;font-weight:bold;">🎯 टार्गेट ३:</span> <span class="jodi-pill" style="border-color:#ff007f;color:#ff007f;">??</span> ({target_day} चालू आठवडा)
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:12px;">
                    <div style="background:#0c1d24;border:1.5px solid #00ffcc;border-radius:10px;padding:12px;">
                        <b style="color:#00ffcc;font-size:14px;">⏩ पुढील क्रम (+१) ➔ {chosen_seq['fwd_target_jodi']} ची फॅमिली:</b>
                        <div style="margin-top:6px;">{fwd_pills}</div>
                    </div>
                    <div style="background:#240c1d;border:1.5px solid #ff007f;border-radius:10px;padding:12px;">
                        <b style="color:#ff007f;font-size:14px;">⏪ मागील क्रम (-१) ➔ {chosen_seq['bwd_target_jodi']} ची फॅमिली:</b>
                        <div style="margin-top:6px;">{bwd_pills}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"ℹ️ चालू चार्टच्या शेवटच्या {seq_rows_cnt} ओळींमध्ये {target_day} साठी फॅमिली सीक्वेन्स सापडला नाही. ओळींची संख्या बदलून पाहा.")

    elif seq_mode.startswith("✨"):
        # Overlay All Target Sequences pointing only to target_day
        st.markdown(f"#### ✨ `{target_day}` कडे जाणारे सर्व टार्गेट फॅमिली सीक्वेन्स एकत्र ({len(proj_seq_tri)} सापडले):")
        if proj_seq_tri:
            overlay_seq_html = render_family_sequence_triangle_panel_html(
                grid_snippet=seq_snip,
                triangles=proj_seq_tri,
                active_idx=None,
                title=f"✨ {target_day} '??' कडे जाणारे सर्व {len(proj_seq_tri)} सीक्वेन्स त्रिकोण (एकत्रित ओव्हरले — शेवटचे {seq_rows_cnt} आठवडे)"
            )
            st.markdown(overlay_seq_html, unsafe_allow_html=True)

            st.markdown(f"##### 📋 सर्व {len(proj_seq_tri)} टार्गेट सीक्वेन्सची भविष्यवाणी:")
            grid_s_cols = st.columns(min(len(proj_seq_tri), 3) if len(proj_seq_tri) > 0 else 1)
            for i, t in enumerate(proj_seq_tri):
                with grid_s_cols[i % len(grid_s_cols)]:
                    pal = TRIANGLE_PALETTES[i % len(TRIANGLE_PALETTES)]
                    st.markdown(f"""
                    <div style="background:#141126;border:1.5px solid {pal['stroke']};border-radius:10px;padding:10px;margin-bottom:10px;">
                        <b style="color:{pal['stroke']};font-size:13px;">सीक्वेन्स #{i+1}: {t['type_title']}</b><br>
                        <span style="font-size:12px;color:#00ffcc;">🔗 {t['sequence_formula']}</span><br>
                        <span style="font-size:11px;color:#aaa;">⏩ +१: {', '.join(t['fwd_family'][:4])}...</span><br>
                        <span style="font-size:11px;color:#aaa;">⏪ -१: {', '.join(t['bwd_family'][:4])}...</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"ℹ️ चालू चार्टच्या शेवटच्या {seq_rows_cnt} ओळींमध्ये {target_day} '??' कडे जाणारे फॅमिली सीक्वेन्स सापडले नाहीत.")

    elif seq_mode.startswith("⚡"):
        st.markdown(f"#### ⚡ चार्टमधील पूर्ण झालेले फॅमिली सीक्वेन्स त्रिकोण ({len(comp_seq_tri)} सापडले):")
        
        if comp_seq_tri:
            opt_c_labels = [
                f"सीक्वेन्स #{i+1}: {t['summary']} ➔ {t['sequence_desc']}"
                for i, t in enumerate(comp_seq_tri)
            ]
            sel_c_idx = st.selectbox("📌 पाहायचा असलेला पूर्ण सीक्वेन्स निवडा:", range(len(comp_seq_tri)), format_func=lambda i: opt_c_labels[i], index=0)
            chosen_c = comp_seq_tri[sel_c_idx]
            
            c_chart_html = render_family_sequence_triangle_panel_html(
                grid_snippet=seq_snip,
                triangles=comp_seq_tri,
                active_idx=sel_c_idx,
                title=f"⚡ पूर्ण झालेला फॅमिली सीक्वेन्स #{sel_c_idx+1} ({chosen_c['type_title']})"
            )
            st.markdown(c_chart_html, unsafe_allow_html=True)

            nA, nB, nC = chosen_c["nodes"]
            st.markdown(f"""
            <div style="background:#121226;border:2px solid #00ff88;border-radius:12px;padding:16px;margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                    <span style="font-size:18px;font-weight:900;color:#00ff88;">⚡ पूर्ण झालेला सीक्वेन्स #{sel_c_idx+1}</span>
                    <span style="background:#00ff8822;border:1px solid #00ff88;color:#00ff88;padding:3px 10px;border-radius:15px;font-weight:bold;font-size:12px;">
                        {chosen_c['type_title']}
                    </span>
                </div>
                <div style="font-size:15px;color:#fff;margin-bottom:12px;background:#18261e;padding:8px 12px;border-radius:8px;">
                    <b style="color:#ffcc00;">🔗 पूर्ण झालेला क्रम:</b> <span style="color:#00ff88;font-weight:bold;">{chosen_c['sequence_desc']}</span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:10px;">
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">① टोक १:</span> <span class="jodi-pill">{nA['jodi']}</span> ({nA['day']} · {nA['date_range']})
                    </div>
                    <div class="match-step-badge">
                        <span style="color:#00d2ff;font-weight:bold;">② टोक २:</span> <span class="jodi-pill">{nB['jodi']}</span> ({nB['day']} · {nB['date_range']})
                    </div>
                    <div class="match-step-badge" style="border-color:#00ff88;background:#00ff8815;">
                        <span style="color:#00ff88;font-weight:bold;">③ टोक ३:</span> <span class="jodi-pill" style="border-color:#00ff88;color:#00ff88;">{nC['jodi']}</span> ({nC['day']} · {nC['date_range']})
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"ℹ️ चालू चार्टच्या शेवटच्या {seq_rows_cnt} ओळींमध्ये पूर्ण झालेले सीक्वेन्स सापडले नाहीत.")

    # Summary table
    st.markdown("---")
    with st.expander(f"📋 चालू चार्टमधील सर्व फॅमिली सीक्वेन्स यादी ({len(comp_seq_tri)} पूर्ण / {len(proj_seq_tri)} टार्गेट)", expanded=False):
        all_rows_s = []
        for i, t in enumerate(comp_seq_tri):
            all_rows_s.append({
                "प्रकार": "⚡ पूर्ण सीक्वेन्स",
                "क्रम": t["sequence_desc"],
                "टोके (Vertices)": t["summary"],
                "जोड्या": ", ".join(t["jodis"]),
            })
        for i, t in enumerate(proj_seq_tri):
            all_rows_s.append({
                "प्रकार": "🎯 टार्गेट सीक्वेन्स",
                "क्रम": t["sequence_formula"],
                "टोके (Vertices)": t["summary"],
                "पुढील फॅमिली (+१)": ", ".join(t["fwd_family"][:4]) + "...",
                "मागील फॅमिली (-१)": ", ".join(t["bwd_family"][:4]) + "...",
            })
        if all_rows_s:
            st.write(pd.DataFrame(all_rows_s).to_html(escape=False, index=False), unsafe_allow_html=True)





