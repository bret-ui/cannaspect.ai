import streamlit as st
import google.genai as genai
from google.genai import types
import os
import json
import time
import base64
from PIL import Image
import io

# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CannaSpect.ai",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Gemini client setup ──────────────────────────────────────────────────────────
# Streamlit reads this from your "Secrets" tab
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# This is the standard, high-speed connection for 2026
client = genai.Client(api_key=GEMINI_API_KEY)

# Use the latest model for the best Sommelier IQ
MODEL_NAME = "gemini-3-flash"
# ── Global CSS ───────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  .stApp {
    background: linear-gradient(135deg, #0a0f0a 0%, #0d1a0d 50%, #091209 100%);
    min-height: 100vh;
  }
  [data-testid="stAppViewContainer"] { background: transparent; }
  [data-testid="stHeader"] {
    background: rgba(0,0,0,0.4);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(74,222,128,0.15);
  }
  #MainMenu, footer { visibility: hidden; }
  html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    color: #e2f0e2;
  }

  .glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(74,222,128,0.18);
    border-radius: 16px;
    padding: 28px 32px;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
    margin-bottom: 20px;
  }

  .hero-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #4ade80, #86efac, #22c55e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    line-height: 1.1;
  }
  .hero-sub {
    font-size: 1.1rem;
    color: rgba(134,239,172,0.7);
    margin-top: 6px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 500;
  }
  .hero-badge {
    display: inline-block;
    background: rgba(74,222,128,0.12);
    border: 1px solid rgba(74,222,128,0.3);
    color: #4ade80;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 12px;
    text-transform: uppercase;
  }

  @keyframes laserSweep {
    0%   { top: 5%;  opacity: 1; }
    48%  { top: 92%; opacity: 1; }
    50%  { top: 92%; opacity: 0.3; }
    52%  { top: 92%; opacity: 1; }
    100% { top: 5%;  opacity: 1; }
  }
  @keyframes scanGlow {
    0%, 100% { box-shadow: 0 0 8px 2px rgba(74,222,128,0.8), 0 0 20px 6px rgba(74,222,128,0.3); }
    50%       { box-shadow: 0 0 16px 4px rgba(74,222,128,1), 0 0 40px 12px rgba(74,222,128,0.5); }
  }
  @keyframes scanPulse {
    0%, 100% { opacity: 0.7; }
    50%       { opacity: 1; }
  }
  @keyframes borderFlicker {
    0%, 90%, 100% { border-color: rgba(74,222,128,0.5); }
    92%, 96%       { border-color: rgba(74,222,128,0.95); }
  }
  .laser-container {
    position: relative;
    width: 100%;
    height: 320px;
    border: 2px solid rgba(74,222,128,0.5);
    border-radius: 12px;
    background: rgba(0,20,0,0.6);
    overflow: hidden;
    animation: borderFlicker 0.4s infinite;
  }
  .laser-beam {
    position: absolute;
    left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, transparent, #4ade80, #86efac, #4ade80, transparent);
    animation: laserSweep 1.2s ease-in-out infinite, scanGlow 0.6s ease-in-out infinite;
  }
  .scan-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(74,222,128,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(74,222,128,0.04) 1px, transparent 1px);
    background-size: 32px 32px;
  }
  .scan-corner-tl {
    position: absolute; top: 8px; left: 8px;
    width: 24px; height: 24px;
    border-top: 3px solid #4ade80;
    border-left: 3px solid #4ade80;
  }
  .scan-corner-br {
    position: absolute; bottom: 8px; right: 8px;
    width: 24px; height: 24px;
    border-bottom: 3px solid #4ade80;
    border-right: 3px solid #4ade80;
  }
  .scan-status {
    position: absolute;
    bottom: 14px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    color: #4ade80;
    text-transform: uppercase;
    animation: scanPulse 0.8s ease-in-out infinite;
    white-space: nowrap;
  }
  .scan-label {
    position: absolute;
    top: 14px; left: 16px;
    font-size: 0.72rem;
    color: rgba(74,222,128,0.5);
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }
  .preview-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.2;
  }
  .preview-overlay img {
    max-height: 100%;
    max-width: 100%;
    object-fit: contain;
    filter: saturate(0.3) brightness(0.6);
  }

  .score-circle {
    width: 120px; height: 120px;
    border-radius: 50%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    border: 3px solid;
    box-shadow: 0 0 24px rgba(74,222,128,0.3);
    font-weight: 800;
  }
  .score-number { font-size: 2.2rem; line-height: 1; }
  .score-label-sm {
    font-size: 0.65rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    opacity: 0.7;
  }

  .pgr-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    border-radius: 40px;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.05em;
    border: 2px solid;
  }
  .pgr-clean    { background: rgba(74,222,128,0.12);  border-color: #4ade80;  color: #4ade80;  }
  .pgr-warning  { background: rgba(251,191,36,0.12);  border-color: #fbbf24;  color: #fbbf24;  }
  .pgr-detected { background: rgba(239,68,68,0.12);   border-color: #ef4444;  color: #ef4444;  }

  .section-header {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #4ade80;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(74,222,128,0.15);
  }

  .blurred-section { position: relative; border-radius: 12px; overflow: hidden; }
  .blur-content { filter: blur(8px); user-select: none; pointer-events: none; }
  .blur-overlay {
    position: absolute; inset: 0;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    background: rgba(0,0,0,0.45);
    backdrop-filter: blur(2px);
    border-radius: 12px;
    gap: 8px;
  }
  .blur-lock-icon { font-size: 2rem; }
  .blur-lock-text {
    font-size: 0.8rem; font-weight: 600;
    letter-spacing: 0.1em;
    color: rgba(134,239,172,0.8);
    text-transform: uppercase;
  }

  .detail-pill {
    background: rgba(74,222,128,0.08);
    border: 1px solid rgba(74,222,128,0.2);
    border-radius: 8px;
    padding: 8px 14px;
    margin: 4px 0;
    font-size: 0.88rem;
    color: rgba(226,240,226,0.9);
    line-height: 1.5;
  }
  .pill-label {
    color: #4ade80;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .alert-item {
    background: rgba(251,191,36,0.08);
    border-left: 3px solid #fbbf24;
    border-radius: 0 8px 8px 0;
    padding: 8px 14px;
    margin: 6px 0;
    font-size: 0.87rem;
    color: rgba(253,230,138,0.9);
  }

  [data-testid="stFileUploader"] {
    border: 2px dashed rgba(74,222,128,0.3) !important;
    border-radius: 12px !important;
    background: rgba(74,222,128,0.03) !important;
  }

  .stButton > button {
    background: linear-gradient(135deg, #16a34a, #15803d) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    padding: 14px 0 !important;
    font-size: 1rem !important;
    width: 100% !important;
    box-shadow: 0 4px 16px rgba(22,163,74,0.35) !important;
    transition: all 0.2s ease !important;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #22c55e, #16a34a) !important;
    box-shadow: 0 6px 24px rgba(34,197,94,0.5) !important;
    transform: translateY(-1px) !important;
  }
  .stButton > button:disabled {
    background: rgba(74,222,128,0.1) !important;
    color: rgba(74,222,128,0.4) !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
  }

  .dev-key-wrap {
    background: rgba(74,222,128,0.05);
    border: 1px solid rgba(74,222,128,0.15);
    border-radius: 10px;
    padding: 12px 16px;
    margin-top: 8px;
  }
  .stTextInput > div > div > input {
    background: rgba(0,0,0,0.3) !important;
    border: 1px solid rgba(74,222,128,0.25) !important;
    border-radius: 8px !important;
    color: #e2f0e2 !important;
  }
  .info-muted {
    font-size: 0.8rem;
    color: rgba(134,239,172,0.45);
    font-style: italic;
    text-align: center;
    margin-top: 10px;
  }
</style>
""",
    unsafe_allow_html=True,
)


# ── Helpers ──────────────────────────────────────────────────────────────────────
def score_color(score: float) -> str:
    if score >= 8.5:
        return "#4ade80"
    elif score >= 7.0:
        return "#86efac"
    elif score >= 5.5:
        return "#fbbf24"
    elif score >= 4.0:
        return "#f97316"
    return "#ef4444"


def score_grade(score: float) -> str:
    if score >= 9.0:
        return "Exceptional"
    elif score >= 8.0:
        return "Premium"
    elif score >= 7.0:
        return "Very Good"
    elif score >= 6.0:
        return "Good"
    elif score >= 5.0:
        return "Average"
    elif score >= 4.0:
        return "Below Average"
    return "Poor"


def image_to_b64(pil_image: Image.Image) -> str:
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def analyze_cannabis(pil_image: Image.Image) -> dict:
    img_b64 = image_to_b64(pil_image)

    prompt = """You are a master Cannabis Sommelier and independent laboratory analyst with over 20 years of experience evaluating cannabis specimens. Your assessments are authoritative, precise, and professionally worded — equal parts science and connoisseurship.

Analyze the cannabis specimen in this image and return a comprehensive quality inspection report as a JSON object. Be thorough, specific, and honest. Do not exaggerate quality — credibility is paramount.

Return ONLY a valid JSON object with this exact structure (no markdown, no code fences):
{
  "qualityScore": <float 0.0-10.0>,
  "executiveSummary": "<2-3 sentence sommelier-style overview of this specimen>",
  "pgrCheck": {
    "verdict": "<CLEAN|SUSPICIOUS|DETECTED>",
    "confidence": "<High|Medium|Low>",
    "indicators": ["<visual indicator 1>", "<visual indicator 2>"],
    "explanation": "<1-2 sentence professional assessment of PGR markers>"
  },
  "safetyAlerts": ["<alert if any — omit array entries if none>"],
  "visualQualityMarkers": {
    "trichomeDensity": "<assessment>",
    "colorProfile": "<assessment>",
    "structureAndForm": "<assessment>",
    "trimQuality": "<assessment>",
    "moistureLevel": "<assessment>"
  },
  "potencyEstimate": {
    "thcRange": "<e.g. 18-24%>",
    "maturityNotes": "<trichome maturity assessment>",
    "recommendation": "<sommelier recommendation>"
  },
  "terpeneProfile": {
    "estimatedDominant": "<e.g. Myrcene, Limonene, Caryophyllene>",
    "aromaProfile": "<predicted aroma characteristics>",
    "effectsProfile": "<predicted effects based on visual cues>",
    "pairingNotes": "<sommelier-style pairing or occasion recommendation>"
  },
  "labNotes": [
    "<detailed technical observation 1>",
    "<detailed technical observation 2>",
    "<detailed technical observation 3>"
  ],
  "overallVerdict": "<one powerful concluding sentence in sommelier tone>"
}

If this is not a cannabis image, set qualityScore to 0 and explain in executiveSummary."""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=base64.b64decode(img_b64), mime_type="image/jpeg"),
        ],
        config=types.GenerateContentConfig(max_output_tokens=8192),
    )
    raw = response.text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


# ── Session state ─────────────────────────────────────────────────────────────────
if "report" not in st.session_state:
    st.session_state.report = None
if "dev_unlocked" not in st.session_state:
    st.session_state.dev_unlocked = False


# ── Hero header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="glass-card" style="text-align:center;padding:40px 32px 32px;">
  <div class="hero-badge">🌿 AI Cannabis Analysis</div>
  <div class="hero-title">CannaSpect.ai</div>
  <div class="hero-sub">Professional Sommelier Inspection Report</div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Two-column layout ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.45], gap="large")

with col_left:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📷 Upload Specimen</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop your cannabis photo here",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        pil_image = Image.open(uploaded_file)
        st.image(pil_image, use_container_width=True, caption="Specimen loaded")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">🔑 Expert Access</div>', unsafe_allow_html=True)
    st.markdown('<div class="dev-key-wrap">', unsafe_allow_html=True)

    dev_key = st.text_input(
        "dev_key",
        type="password",
        placeholder="Enter key to unlock all sections…",
        label_visibility="collapsed",
    )
    if dev_key == "DEV123":
        st.session_state.dev_unlocked = True
        st.markdown(
            '<p style="color:#4ade80;font-size:0.82rem;font-weight:600;margin:4px 0 0;">'
            "✓ Expert access granted — all sections unlocked</p>",
            unsafe_allow_html=True,
        )
    elif dev_key:
        st.session_state.dev_unlocked = False
        st.markdown(
            '<p style="color:#ef4444;font-size:0.82rem;margin:4px 0 0;">✗ Invalid key</p>',
            unsafe_allow_html=True,
        )
    else:
        st.session_state.dev_unlocked = False

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    analyze_clicked = st.button(
        "🔬 Run Laser Scan Analysis",
        disabled=(uploaded_file is None),
        use_container_width=True,
    )
    st.markdown(
        '<p class="info-muted">Powered by Gemini 2.5 Flash · Cannabis Sommelier AI</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


with col_right:
    if analyze_clicked and uploaded_file:
        pil_image = Image.open(uploaded_file)
        img_b64_preview = image_to_b64(pil_image)

        # ── Laser scan animation placeholder ─────────────────────────────────
        scan_slot = st.empty()
        scan_slot.markdown(
            f"""
<div class="glass-card" style="padding:16px;">
  <div class="section-header">⚡ Scanning Specimen…</div>
  <div class="laser-container">
    <div class="scan-grid"></div>
    <div class="preview-overlay">
      <img src="data:image/jpeg;base64,{img_b64_preview}" />
    </div>
    <div class="laser-beam"></div>
    <div class="scan-corner-tl"></div>
    <div class="scan-corner-br"></div>
    <div class="scan-label">CannaSpect.ai</div>
    <div class="scan-status">🔬 Deep Spectral Analysis In Progress</div>
  </div>
  <p style="text-align:center;color:rgba(74,222,128,0.55);font-size:0.78rem;
            margin-top:12px;letter-spacing:0.12em;">
    TRICHOME MAPPING · PGR DETECTION · POTENCY ESTIMATION
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

        # Call API, guarantee at least 3 s of animation
        t0 = time.time()
        try:
            report = analyze_cannabis(pil_image)
            st.session_state.report = report
        except Exception as exc:
            elapsed = time.time() - t0
            if elapsed < 3.0:
                time.sleep(3.0 - elapsed)
            scan_slot.empty()
            st.error(f"Analysis failed: {exc}")
            st.stop()

        elapsed = time.time() - t0
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)

        scan_slot.empty()

    # ── Report ────────────────────────────────────────────────────────────────
    report = st.session_state.report
    unlocked = st.session_state.dev_unlocked

    if report is None:
        st.markdown(
            """
<div class="glass-card" style="text-align:center;padding:60px 32px;">
  <div style="font-size:3rem;margin-bottom:16px;">🌿</div>
  <div style="font-size:1.05rem;color:rgba(134,239,172,0.7);font-weight:500;line-height:1.7;">
    Upload a specimen photo and click<br>
    <strong style="color:#4ade80;">Run Laser Scan Analysis</strong><br>
    to generate your report.
  </div>
  <div style="margin-top:20px;font-size:0.75rem;color:rgba(74,222,128,0.35);letter-spacing:0.12em;">
    TRICHOME · PGR · POTENCY · TERPENES · LAB NOTES
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        score = float(report.get("qualityScore", 0))
        color = score_color(score)
        grade = score_grade(score)
        pgr = report.get("pgrCheck", {})
        verdict = pgr.get("verdict", "CLEAN").upper()
        pgr_cls = {"CLEAN": "pgr-clean", "SUSPICIOUS": "pgr-warning", "DETECTED": "pgr-detected"}.get(verdict, "pgr-clean")
        pgr_icon = {"CLEAN": "✅", "SUSPICIOUS": "⚠️", "DETECTED": "🚫"}.get(verdict, "✅")

        # Overall score
        st.markdown(
            f"""
<div class="glass-card">
  <div class="section-header">🏆 Overall Quality Assessment</div>
  <div style="display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
      <div class="score-circle" style="border-color:{color};color:{color};">
        <span class="score-number">{score:.1f}</span>
        <span class="score-label-sm">/ 10</span>
      </div>
      <span style="font-size:0.85rem;font-weight:700;color:{color};letter-spacing:0.04em;">{grade}</span>
    </div>
    <div style="flex:1;min-width:180px;">
      <p style="font-size:0.95rem;line-height:1.7;color:rgba(226,240,226,0.9);margin:0;">
        {report.get("executiveSummary", "")}
      </p>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # PGR check
        indicators_html = "".join(
            f'<div class="detail-pill">• {i}</div>'
            for i in pgr.get("indicators", [])
        )
        st.markdown(
            f"""
<div class="glass-card">
  <div class="section-header">🧪 PGR Detection Check</div>
  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px;">
    <span class="pgr-badge {pgr_cls}">{pgr_icon} PGR {verdict}</span>
    <span style="font-size:0.82rem;color:rgba(134,239,172,0.55);">Confidence: {pgr.get("confidence","—")}</span>
  </div>
  <p style="font-size:0.9rem;color:rgba(226,240,226,0.85);margin-bottom:10px;">{pgr.get("explanation","")}</p>
  {indicators_html}
</div>
""",
            unsafe_allow_html=True,
        )

        # Safety alerts
        alerts = [a for a in report.get("safetyAlerts", []) if a]
        if alerts:
            alerts_html = "".join(f'<div class="alert-item">⚠️ {a}</div>' for a in alerts)
            st.markdown(
                f"""
<div class="glass-card" style="border-color:rgba(251,191,36,0.28);">
  <div class="section-header" style="color:#fbbf24;">⚠️ Safety Alerts</div>
  {alerts_html}
</div>
""",
                unsafe_allow_html=True,
            )

        # Visual quality markers
        vqm = report.get("visualQualityMarkers", {})
        if vqm:
            vqm_labels = {
                "trichomeDensity": "Trichome Density",
                "colorProfile": "Color Profile",
                "structureAndForm": "Structure & Form",
                "trimQuality": "Trim Quality",
                "moistureLevel": "Moisture Level",
            }
            markers_html = "".join(
                f'<div class="detail-pill"><span class="pill-label">{vqm_labels.get(k, k)}</span><br>{v}</div>'
                for k, v in vqm.items()
            )
            st.markdown(
                f"""
<div class="glass-card">
  <div class="section-header">🔍 Visual Quality Markers</div>
  {markers_html}
</div>
""",
                unsafe_allow_html=True,
            )

        # Potency (blurred if locked)
        potency = report.get("potencyEstimate", {})
        potency_inner = f"""
<div class="detail-pill"><span class="pill-label">Estimated THC Range</span><br>{potency.get("thcRange","—")}</div>
<div class="detail-pill"><span class="pill-label">Maturity Assessment</span><br>{potency.get("maturityNotes","—")}</div>
<div class="detail-pill"><span class="pill-label">Sommelier Recommendation</span><br>{potency.get("recommendation","—")}</div>
"""
        if unlocked:
            st.markdown(
                f"""
<div class="glass-card" style="border-color:rgba(74,222,128,0.38);">
  <div class="section-header">⚗️ Potency Estimate
    <span style="font-size:0.62rem;background:rgba(74,222,128,0.15);padding:2px 8px;
                 border-radius:10px;margin-left:8px;">EXPERT ACCESS</span>
  </div>
  {potency_inner}
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
<div class="glass-card">
  <div class="section-header">⚗️ Potency Estimate</div>
  <div class="blurred-section">
    <div class="blur-content">{potency_inner}</div>
    <div class="blur-overlay">
      <div class="blur-lock-icon">🔒</div>
      <div class="blur-lock-text">Expert Access Required</div>
      <div style="font-size:0.72rem;color:rgba(134,239,172,0.45);margin-top:2px;">Enter DEV key to unlock</div>
    </div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        # Terpene profile (blurred if locked)
        terp = report.get("terpeneProfile", {})
        terp_inner = f"""
<div class="detail-pill"><span class="pill-label">Dominant Terpenes</span><br>{terp.get("estimatedDominant","—")}</div>
<div class="detail-pill"><span class="pill-label">Aroma Profile</span><br>{terp.get("aromaProfile","—")}</div>
<div class="detail-pill"><span class="pill-label">Effects Profile</span><br>{terp.get("effectsProfile","—")}</div>
<div class="detail-pill"><span class="pill-label">Pairing Notes</span><br>{terp.get("pairingNotes","—")}</div>
"""
        if unlocked:
            st.markdown(
                f"""
<div class="glass-card" style="border-color:rgba(74,222,128,0.38);">
  <div class="section-header">🌸 Terpene Profile
    <span style="font-size:0.62rem;background:rgba(74,222,128,0.15);padding:2px 8px;
                 border-radius:10px;margin-left:8px;">EXPERT ACCESS</span>
  </div>
  {terp_inner}
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
<div class="glass-card">
  <div class="section-header">🌸 Terpene Profile</div>
  <div class="blurred-section">
    <div class="blur-content">{terp_inner}</div>
    <div class="blur-overlay">
      <div class="blur-lock-icon">🔒</div>
      <div class="blur-lock-text">Expert Access Required</div>
      <div style="font-size:0.72rem;color:rgba(134,239,172,0.45);margin-top:2px;">Enter DEV key to unlock</div>
    </div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        # Lab notes
        lab_notes = report.get("labNotes", [])
        if lab_notes:
            notes_html = "".join(f'<div class="detail-pill">📋 {n}</div>' for n in lab_notes)
            st.markdown(
                f"""
<div class="glass-card">
  <div class="section-header">📋 Laboratory Notes</div>
  {notes_html}
</div>
""",
                unsafe_allow_html=True,
            )

        # Verdict
        overall = report.get("overallVerdict", "")
        if overall:
            st.markdown(
                f"""
<div class="glass-card" style="border-color:rgba(74,222,128,0.42);
     background:rgba(74,222,128,0.04);text-align:center;padding:24px 32px;">
  <div style="font-size:1.2rem;color:#86efac;font-style:italic;line-height:1.6;">
    "{overall}"
  </div>
  <div style="margin-top:10px;font-size:0.7rem;color:rgba(74,222,128,0.45);letter-spacing:0.15em;">
    — CannaSpect.ai Sommelier AI
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
