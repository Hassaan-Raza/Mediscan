import streamlit as st
from google import genai
from google.genai import types
import base64
import json
import re
from PIL import Image
import io

try:
    import fitz  # PyMuPDF
    PDF_SUPPORTED = True
except ImportError:
    PDF_SUPPORTED = False

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MediScan — Gemini Diagnostic Suite",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# GLOBAL STYLES
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Space+Grotesk:wght@300;400;500;600&family=Instrument+Serif:ital@0;1&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main {
  background: #090E14 !important;
  color: #E8F0F7 !important;
}

[data-testid="stHeader"]     { background: transparent !important; }
[data-testid="stSidebar"]    { background: #0D1520 !important; }
[data-testid="stToolbar"]    { display: none; }
[data-testid="stDecoration"] { display: none; }

[data-testid="stFileUploader"] > div {
  background: #0D1520 !important;
  border: 1.5px dashed #1E3A4A !important;
  border-radius: 14px !important;
  transition: border-color .25s;
}
[data-testid="stFileUploader"] > div:hover { border-color: #00C9A7 !important; }
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] p {
  color: #6B8A9A !important;
  font-family: 'Space Grotesk', sans-serif !important;
}

.stTextInput input, .stTextArea textarea {
  background: #0D1520 !important;
  border: 1.5px solid #1E3A4A !important;
  border-radius: 10px !important;
  font-family: 'Space Grotesk', sans-serif !important;
  color: #E8F0F7 !important;
  font-size: .92rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: #00C9A7 !important;
  box-shadow: 0 0 0 3px rgba(0,201,167,.12) !important;
  outline: none !important;
}
.stTextInput label, .stTextArea label { color: #6B8A9A !important; }

.stButton > button {
  background: linear-gradient(135deg, #00C9A7 0%, #0096B4 100%) !important;
  color: #090E14 !important;
  border: none !important;
  border-radius: 10px !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 700 !important;
  font-size: .88rem !important;
  letter-spacing: .06em !important;
  padding: .75rem 1.8rem !important;
  transition: opacity .2s, transform .15s !important;
  cursor: pointer !important;
  text-transform: uppercase !important;
}
.stButton > button:hover { opacity: .88 !important; transform: translateY(-1px) !important; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #090E14; }
::-webkit-scrollbar-thumb { background: #1E3A4A; border-radius: 3px; }

.block-container { padding: 0 !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.ms-nav {
  background: #0D1520; padding: 1.2rem 3rem;
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid #0F2030;
  position: relative; overflow: hidden;
}
.ms-nav::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #00C9A7, #0096B4, #A855F7, #00C9A7);
  background-size: 200% 100%;
  animation: shimmer 3s linear infinite;
}
@keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
.ms-logo {
  font-family: 'Syne', sans-serif; font-size: 1.35rem; font-weight: 800;
  color: #E8F0F7; letter-spacing: -.02em;
  display: flex; align-items: center; gap: .5rem;
}
.ms-logo-gem {
  width: 28px; height: 28px;
  background: linear-gradient(135deg, #00C9A7, #0096B4);
  border-radius: 6px; display: inline-flex; align-items: center; justify-content: center;
  font-size: .9rem;
}
.ms-logo em { color: #00C9A7; font-style: normal; }
.ms-badge-gem {
  font-family: 'Space Grotesk', sans-serif; font-size: .65rem; font-weight: 600;
  color: #00C9A7; background: rgba(0,201,167,.1); border: 1px solid rgba(0,201,167,.25);
  border-radius: 6px; padding: 4px 10px; letter-spacing: .08em; text-transform: uppercase;
}
</style>
<div class="ms-nav">
  <div class="ms-logo">
    <div class="ms-logo-gem">⬡</div>
    Medi<em>Scan</em>
  </div>
  <div style="display:flex; gap:.8rem; align-items:center;">
    <span class="ms-badge-gem">Gemini Vision · Diagnosis</span>
    <span class="ms-badge-gem">Nano Banana 2 · Body Map</span>
    <span class="ms-badge-gem">Veo 3.1 · Exercise Videos</span>
    <span class="ms-badge-gem">v5.0</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.ms-hero { padding: 4rem 3rem 2rem; }
.ms-eyebrow {
  font-family: 'Space Grotesk', sans-serif; font-size: .68rem; font-weight: 600;
  color: #00C9A7; letter-spacing: .18em; text-transform: uppercase; margin-bottom: 1rem;
}
.ms-h1 {
  font-family: 'Syne', sans-serif; font-size: 3.4rem; font-weight: 800;
  color: #E8F0F7; line-height: 1.0; letter-spacing: -.035em; margin-bottom: 1.1rem;
}
.ms-h1 .accent { color: #00C9A7; }
.ms-h1 .italic { font-family: 'Instrument Serif', serif; font-weight: 400; font-style: italic; }
.ms-body {
  font-family: 'Space Grotesk', sans-serif; font-size: .96rem; color: #6B8A9A;
  line-height: 1.7; max-width: 560px; margin-bottom: 2rem;
}
.ms-pipeline { display: flex; gap: 0; align-items: center; flex-wrap: wrap; }
.ms-pipe-step {
  display: flex; align-items: center; gap: .5rem;
  font-family: 'Space Grotesk', sans-serif; font-size: .78rem; font-weight: 500; color: #4A6878;
}
.ms-pipe-step .num {
  width: 24px; height: 24px; border-radius: 50%;
  background: #0D1520; border: 1px solid #1E3A4A;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Syne', sans-serif; font-size: .7rem; font-weight: 700; color: #00C9A7;
}
.ms-pipe-arrow { color: #1E3A4A; margin: 0 .5rem; font-size: .8rem; }
</style>
<div class="ms-hero">
  <div class="ms-eyebrow">⬡ AI-Powered Clinical Diagnostic Suite</div>
  <h1 class="ms-h1">Diagnose. Visualize.<br><span class="italic accent">Rehabilitate.</span></h1>
  <p class="ms-body">
    Upload any X-ray, MRI, CT scan, or medical report. Gemini Vision diagnoses the condition,
    Nano Banana 2 generates a real anatomical body map highlighting affected regions,
    and Veo 3.1 generates an actual video demonstration of every exercise in your rehab plan.
  </p>
  <div class="ms-pipeline">
    <div class="ms-pipe-step"><div class="num">1</div>Upload Scan</div>
    <div class="ms-pipe-arrow">→</div>
    <div class="ms-pipe-step"><div class="num">2</div>Gemini Diagnoses</div>
    <div class="ms-pipe-arrow">→</div>
    <div class="ms-pipe-step"><div class="num">3</div>AI Body Map Generated</div>
    <div class="ms-pipe-arrow">→</div>
    <div class="ms-pipe-step"><div class="num">4</div>Veo Exercise Videos</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="height:1px;background:linear-gradient(90deg,#1E3A4A,#090E14);margin:0 3rem 2rem;"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# API KEY — loaded from Streamlit secrets (never hardcoded)
# In your Streamlit Cloud dashboard go to:
#   App settings → Secrets → add:
#   GEMINI_API_KEY = "AIza..."
# For local dev create .streamlit/secrets.toml with the same key.
# ─────────────────────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.markdown("""
    <div style="margin:1rem 3rem;background:#1A1508;border:1px solid #FF6B6B55;
         border-radius:10px;padding:1rem 1.4rem;
         font-family:'Space Grotesk',sans-serif;font-size:.88rem;color:#FF6B6B;line-height:1.7;">
      <strong>⚠ API key not found.</strong><br>
      Add <code style="background:#FF6B6B18;padding:1px 5px;border-radius:4px;">GEMINI_API_KEY = "AIza..."</code>
      to your Streamlit secrets.<br>
      <span style="color:#4A6878;font-size:.8rem;">
        Streamlit Cloud: App settings → Secrets &nbsp;|&nbsp;
        Local: <code style="background:#1E3A4A;padding:1px 5px;border-radius:4px;">.streamlit/secrets.toml</code>
      </span>
    </div>""", unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────────────────────
# UPLOAD + CONTEXT
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide Streamlit's default file uploader browse button label overlap */
[data-testid="stFileUploaderDropzone"] button { display: none !important; }
[data-testid="stFileUploaderDropzone"] {
  background: #0D1520 !important;
  border: 1.5px dashed #1E3A4A !important;
  border-radius: 14px !important;
  padding: 2rem 1rem !important;
  text-align: center !important;
  cursor: pointer !important;
  transition: border-color .25s;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: #00C9A7 !important; }
[data-testid="stFileUploaderDropzone"] small { display: none !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding:0 3rem 1.2rem;">
  <p style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:700;
     color:#E8F0F7;letter-spacing:-.02em;">Upload Medical Scan</p>
  <p style="font-family:'Space Grotesk',sans-serif;font-size:.78rem;color:#4A6878;margin-top:.3rem;">
    Accepts PNG, JPG, WEBP images and PDF reports
  </p>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div style="padding:0 0 0 3rem;">', unsafe_allow_html=True)

    # Single uploader that accepts both images and PDFs
    uploaded_file = st.file_uploader(
        "Upload scan (PNG, JPG, WEBP, PDF)",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        label_visibility="collapsed",
        key="uploader"
    )

    if uploaded_file:
        is_pdf = uploaded_file.name.lower().endswith(".pdf")
        if is_pdf:
            st.markdown(f"""
            <div style="background:#0D1520;border:1px solid #1E3A4A;border-radius:12px;
                 padding:1rem 1.2rem;margin-top:.5rem;display:flex;align-items:center;gap:.8rem;">
              <span style="font-size:1.4rem;">📄</span>
              <div>
                <p style="font-family:'Syne',sans-serif;font-size:.88rem;font-weight:700;
                   color:#E8F0F7;margin-bottom:.15rem;">{uploaded_file.name}</p>
                <p style="font-family:'Space Grotesk',sans-serif;font-size:.72rem;color:#00C9A7;">
                  PDF detected — will convert first page to image for analysis
                </p>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#0D1520;border:1px solid #1E3A4A;border-radius:12px;
                 padding:.8rem;margin-top:.5rem;overflow:hidden;">
            """, unsafe_allow_html=True)
            st.image(uploaded_file, caption="", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown('<div style="padding:0 3rem 0 0;">', unsafe_allow_html=True)
    st.markdown("""
    <p style="font-family:'Space Grotesk',sans-serif;font-size:.68rem;font-weight:600;
       color:#4A6878;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.4rem;">
      Patient Context <span style="color:#1E3A4A;">(optional)</span>
    </p>""", unsafe_allow_html=True)
    context_text = st.text_area(
        "context", height=130,
        placeholder="Age, symptoms, duration, medical history…\ne.g. 38-year-old male, chronic lower back pain, desk job",
        label_visibility="collapsed"
    )
    st.markdown("""
    <p style="font-family:'Space Grotesk',sans-serif;font-size:.78rem;color:#4A6878;
       margin-top:.6rem;line-height:1.5;">
      Context helps Gemini tailor the diagnosis and exercise plan.
    </p>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("⬡  Run Gemini Diagnostic", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# PDF → IMAGE CONVERSION
# ─────────────────────────────────────────────────────────────

def pdf_to_image(pdf_bytes: bytes) -> bytes:
    """Convert first page of PDF to a high-res JPEG image."""
    if not PDF_SUPPORTED:
        raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    # 2x zoom for high resolution
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# GEMINI FUNCTIONS
# ─────────────────────────────────────────────────────────────

def get_client(api_key: str):
    return genai.Client(api_key=api_key)


def analyze_with_gemini(img_bytes: bytes, api_key: str, context: str = "") -> dict:
    """Gemini 1.5 Flash — vision analysis → structured JSON diagnosis."""
    client = get_client(api_key)

    prompt = f"""You are a senior radiologist and clinical AI. Analyze this medical image carefully.

Respond ONLY with a raw JSON object — no markdown, no code fences, no extra text.

{{
  "image_type": "X-ray | MRI | CT | Ultrasound | Report | Photo | Other",
  "diagnosis": "Primary diagnosis in clear plain language (1-2 sentences)",
  "confidence": "high | medium | low",
  "severity": "mild | moderate | severe",
  "affected_regions": ["specific body regions affected"],
  "findings": ["finding 1", "finding 2", "finding 3", "finding 4"],
  "recommendations": ["rec 1", "rec 2", "rec 3"],
  "body_map_prompt": "Detailed prompt for Gemini image generation: a front-view full human body medical anatomical illustration on white background, with [SPECIFIC REGION] highlighted in glowing red/orange with arrows and labels. Professional medical illustration style, clean, precise anatomy.",
  "exercise_needed": true,
  "exercises": [
    {{
      "name": "Exercise name",
      "purpose": "Why this helps",
      "difficulty": "easy | moderate | hard",
      "duration": "e.g. 10 minutes",
      "reps": "e.g. 3 sets of 10",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "illustration_prompt": "Instructional fitness illustration of a person performing [exercise] showing correct body position and form. Clean white background, flat design style, like a physical therapy guide. No text in image."
    }}
  ],
  "urgency": "routine | urgent | emergency",
  "disclaimer": "Always consult a qualified physician before acting on any AI-generated medical analysis."
}}

Give 3-4 exercises if exercise_needed is true, else empty array.
Make body_map_prompt and illustration_prompts vivid and specific to the actual condition.
{f'Patient context: {context}' if context else ''}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            prompt
        ]
    )
    raw = response.text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    return json.loads(raw)


def generate_image(prompt: str, api_key: str, style_suffix: str = "") -> Image.Image | None:
    """Nano Banana 2 — generate body map image."""
    try:
        client = get_client(api_key)
        full_prompt = prompt + (style_suffix or "")
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[full_prompt],
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return Image.open(io.BytesIO(part.inline_data.data))
    except Exception as e:
        st.warning(f"Body map generation failed: {e}")
    return None


def generate_exercise_video(prompt: str, api_key: str) -> bytes | None:
    """Veo 3.1 — generate an exercise demonstration video. Returns raw MP4 bytes."""
    import time
    try:
        client = get_client(api_key)
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
        )
        # Poll until done (Veo is async, typically 30-90s)
        for _ in range(30):  # max ~5 min
            if operation.done:
                break
            time.sleep(10)
            operation = client.operations.get(operation)

        if operation.done and operation.response.generated_videos:
            video = operation.response.generated_videos[0]
            client.files.download(file=video.video)
            return video.video.video_bytes
    except Exception as e:
        st.warning(f"Exercise video generation failed: {e}")
    return None


# ─────────────────────────────────────────────────────────────
# RUN ANALYSIS PIPELINE
# ─────────────────────────────────────────────────────────────

if analyze_btn:
    if not uploaded_file:
        st.markdown("""
        <div style="margin:1rem 3rem;background:#1A1508;border:1px solid #F59E0B55;
             border-radius:10px;padding:.9rem 1.2rem;
             font-family:'Space Grotesk',sans-serif;font-size:.88rem;color:#F59E0B;">
          ⚠️  Please upload a medical scan or report before running analysis.
        </div>""", unsafe_allow_html=True)
    else:
        raw_bytes = uploaded_file.read()
        is_pdf    = uploaded_file.name.lower().endswith(".pdf")

        # ── Convert PDF → JPEG if needed
        if is_pdf:
            with st.spinner("Converting PDF to image…"):
                try:
                    img_bytes = pdf_to_image(raw_bytes)
                except Exception as e:
                    st.error(f"PDF conversion failed: {e}. Make sure PyMuPDF is installed.")
                    st.stop()
        else:
            pil_raw = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
            buf     = io.BytesIO()
            pil_raw.save(buf, format="JPEG", quality=92)
            img_bytes = buf.getvalue()

        # ── Step 1: Diagnosis via Gemini Vision
        with st.spinner("Step 1 / 3 — Gemini Vision analyzing your scan…"):
            try:
                result = analyze_with_gemini(img_bytes, GEMINI_API_KEY, context_text)
                st.session_state["result"]         = result
                st.session_state["body_map_img"]   = None
                st.session_state["exercise_videos"]= {}
            except Exception as e:
                st.error(f"Diagnosis failed: {e}")
                st.stop()

        # ── Step 2: Body map via Gemini 3 Pro Image
        with st.spinner("Step 2 / 3 — Gemini 3 Pro Image generating body map…"):
            body_prompt = result.get("body_map_prompt", "")
            if body_prompt:
                img = generate_image(
                    body_prompt,
                    GEMINI_API_KEY,
                    " Medical illustration, white background, anatomical precision, professional."
                )
                st.session_state["body_map_img"] = img

        # ── Step 3: Exercise videos via Veo 3.1
        exercises = result.get("exercises", [])
        ex_videos = {}
        if exercises and result.get("exercise_needed", True):
            n = len(exercises[:4])
            for i, ex in enumerate(exercises[:4]):
                with st.spinner(f"Step 3 / 3 — Veo generating exercise video {i+1} of {n}… (may take ~60s)"):
                    ex_prompt = (
                        ex.get("illustration_prompt",
                               f"A person performing {ex.get('name','an exercise')} correctly.")
                        + " Fitness demonstration video, clear body form, bright studio lighting, "
                          "plain white background, slow and instructional pace, no text overlays."
                    )
                    video_bytes = generate_exercise_video(ex_prompt, GEMINI_API_KEY)
                    if video_bytes:
                        ex_videos[i] = video_bytes
        st.session_state["exercise_videos"] = ex_videos
        st.rerun()


# ─────────────────────────────────────────────────────────────
# RESULTS DISPLAY
# ─────────────────────────────────────────────────────────────

result     = st.session_state.get("result")
body_map   = st.session_state.get("body_map_img")
ex_videos  = st.session_state.get("exercise_videos", {})

if result:
    st.markdown("""
    <div style="height:1px;background:linear-gradient(90deg,#1E3A4A,#090E14);margin:2rem 3rem;"></div>
    """, unsafe_allow_html=True)

    urgency    = result.get("urgency",    "routine")
    severity   = result.get("severity",   "moderate")
    confidence = result.get("confidence", "medium")
    diagnosis  = result.get("diagnosis",  "")
    image_type = result.get("image_type", "")

    urg_map  = {"routine":("#00C9A7","#00C9A718"),"urgent":("#F59E0B","#F59E0B18"),"emergency":("#FF6B6B","#FF6B6B18")}
    sev_map  = {"mild":("#00C9A7","#00C9A718"),"moderate":("#F59E0B","#F59E0B18"),"severe":("#FF6B6B","#FF6B6B18")}
    conf_map = {"high":("#A855F7","#A855F718"),"medium":("#0096B4","#0096B418"),"low":("#6B8A9A","#6B8A9A18")}
    uc, ubg  = urg_map.get(urgency,    urg_map["routine"])
    sc, sbg  = sev_map.get(severity,   sev_map["moderate"])
    cc, cbg  = conf_map.get(confidence,conf_map["medium"])

    # Diagnosis banner
    st.markdown(f"""
    <style>
    .ms-result-header {{
      margin:0 3rem 2rem; padding:2rem 2.4rem;
      background:#0D1520; border:1px solid #1E3A4A; border-radius:20px;
      position:relative; overflow:hidden;
    }}
    .ms-result-header::before {{
      content:''; position:absolute; top:0; left:0; right:0; height:3px;
      background:linear-gradient(90deg,#00C9A7,#0096B4,#A855F7);
    }}
    .ms-result-eyebrow {{
      font-family:'Space Grotesk',sans-serif; font-size:.65rem; font-weight:600;
      color:#4A6878; letter-spacing:.15em; text-transform:uppercase; margin-bottom:.6rem;
    }}
    .ms-result-title {{
      font-family:'Syne',sans-serif; font-size:2rem; font-weight:800;
      color:#E8F0F7; line-height:1.15; letter-spacing:-.03em; margin-bottom:1.1rem;
    }}
    .ms-result-badges {{ display:flex; gap:.5rem; flex-wrap:wrap; }}
    .ms-rbadge {{
      font-family:'Space Grotesk',sans-serif; font-size:.62rem; font-weight:600;
      letter-spacing:.08em; text-transform:uppercase; padding:4px 12px;
      border-radius:7px; border:1px solid;
    }}
    </style>
    <div class="ms-result-header">
      <div class="ms-result-eyebrow">⬡ Gemini AI Diagnosis Result</div>
      <div class="ms-result-title">{diagnosis}</div>
      <div class="ms-result-badges">
        <span class="ms-rbadge" style="color:{uc};background:{ubg};border-color:{uc}44;">{urgency.upper()}</span>
        <span class="ms-rbadge" style="color:{sc};background:{sbg};border-color:{sc}44;">SEVERITY: {severity.upper()}</span>
        <span class="ms-rbadge" style="color:{cc};background:{cbg};border-color:{cc}44;">CONFIDENCE: {confidence.upper()}</span>
        <span class="ms-rbadge" style="color:#6B8A9A;background:#6B8A9A18;border-color:#6B8A9A44;">{image_type}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Full-width row layout
    st.markdown('<div style="padding:0 3rem;">', unsafe_allow_html=True)

    # ── ROW 1: Key Findings + Recommendations side by side
    st.markdown("""
    <p style="font-family:'Space Grotesk',sans-serif;font-size:.62rem;font-weight:600;
       color:#4A6878;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.9rem;">
      ⬡ Key Findings
    </p>""", unsafe_allow_html=True)

    findings_cols = st.columns(2, gap="large")
    findings = result.get("findings", [])
    mid = (len(findings) + 1) // 2
    for col, chunk in zip(findings_cols, [findings[:mid], findings[mid:]]):
        with col:
            for i, f in enumerate(chunk):
                idx = findings.index(f)
                st.markdown(f"""
                <div style="display:flex;gap:.8rem;align-items:flex-start;margin-bottom:.65rem;
                     padding:.85rem 1rem;background:#0D1520;border-radius:10px;border-left:2px solid #00C9A7;">
                  <span style="font-family:'Syne',sans-serif;font-size:.65rem;font-weight:800;
                     color:#00C9A7;padding-top:1px;flex-shrink:0;min-width:16px;">0{idx+1}</span>
                  <span style="font-family:'Space Grotesk',sans-serif;font-size:.88rem;
                     color:#A8C0CC;line-height:1.55;">{f}</span>
                </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="height:1.2rem;"></div>
    <p style="font-family:'Space Grotesk',sans-serif;font-size:.62rem;font-weight:600;
       color:#4A6878;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.9rem;">
      ⬡ Clinical Recommendations
    </p>""", unsafe_allow_html=True)

    rec_cols = st.columns(3, gap="large")
    for i, rec in enumerate(result.get("recommendations", [])):
        with rec_cols[i % 3]:
            st.markdown(f"""
            <div style="display:flex;gap:.8rem;align-items:flex-start;margin-bottom:.65rem;
                 padding:.85rem 1rem;background:#0D1520;border-radius:10px;border-left:2px solid #0096B4;">
              <span style="font-family:'Syne',sans-serif;font-size:.85rem;color:#0096B4;flex-shrink:0;">→</span>
              <span style="font-family:'Space Grotesk',sans-serif;font-size:.88rem;
                 color:#A8C0CC;line-height:1.55;">{rec}</span>
            </div>""", unsafe_allow_html=True)

    # ── DIVIDER
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,#1E3A4A,#090E14);margin:2rem 0;"></div>', unsafe_allow_html=True)

    # ── ROW 2: Body Map full width
    st.markdown("""
    <p style="font-family:'Space Grotesk',sans-serif;font-size:.62rem;font-weight:600;
       color:#4A6878;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.9rem;">
      ⬡ AI Body Map — Affected Regions
    </p>""", unsafe_allow_html=True)

    if body_map:
        bmap_col, btag_col = st.columns([1.4, 1], gap="large")
        with bmap_col:
            st.markdown('<div style="background:#0D1520;border:1px solid #1E3A4A;border-radius:16px;padding:1rem;overflow:hidden;">', unsafe_allow_html=True)
            st.image(body_map, use_container_width=True, caption="")
            st.markdown("</div>", unsafe_allow_html=True)
        with btag_col:
            sev_c   = {"mild":"#00C9A7","moderate":"#F59E0B","severe":"#A855F7"}.get(severity,"#F59E0B")
            regions = result.get("affected_regions", [])
            st.markdown(f"""
            <div style="background:#0D1520;border:1px solid #1E3A4A;border-radius:16px;
                 padding:1.5rem;height:100%;">
              <p style="font-family:'Syne',sans-serif;font-size:.78rem;font-weight:700;
                 color:#E8F0F7;margin-bottom:1rem;letter-spacing:-.01em;">Highlighted Regions</p>
              <div style="display:flex;flex-wrap:wrap;gap:.5rem;">
                {"".join([
                    f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:.72rem;font-weight:600;'
                    f'background:{sev_c}18;color:{sev_c};border:1px solid {sev_c}33;'
                    f'border-radius:8px;padding:5px 12px;letter-spacing:.04em;">{r.upper()}</span>'
                    for r in regions
                ])}
              </div>
              <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #1E3A4A;">
                <p style="font-family:'Space Grotesk',sans-serif;font-size:.7rem;color:#4A6878;
                   line-height:1.6;">
                  The body map above was generated by <strong style="color:#00C9A7;">Nano Banana 2</strong>
                  based on the diagnosed condition. Highlighted regions indicate areas of clinical concern
                  identified in the scan.
                </p>
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#0D1520;border:1px dashed #1E3A4A;border-radius:16px;
             padding:2.5rem;text-align:center;">
          <p style="font-family:'Space Grotesk',sans-serif;font-size:.8rem;color:#2A4A5E;">
            Body map unavailable
          </p>
        </div>""", unsafe_allow_html=True)

    # ── DIVIDER
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,#1E3A4A,#090E14);margin:2rem 0;"></div>', unsafe_allow_html=True)

    # ── ROW 3: Exercise plan full width
    st.markdown("""
    <p style="font-family:'Space Grotesk',sans-serif;font-size:.62rem;font-weight:600;
       color:#4A6878;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.9rem;">
      ⬡ Veo-Generated Recovery Plan
    </p>""", unsafe_allow_html=True)

    exercises = result.get("exercises", [])
    if not exercises or not result.get("exercise_needed", True):
        st.markdown("""
        <div style="padding:1.2rem;background:#0D1520;border-radius:10px;
             font-family:'Space Grotesk',sans-serif;font-size:.85rem;color:#4A6878;
             border:1px solid #1E3A4A;line-height:1.6;">
          No specific exercises recommended. Follow clinical recommendations above.
        </div>""", unsafe_allow_html=True)
    else:
        palette    = ["#00C9A7","#0096B4","#A855F7","#F59E0B","#FF6B6B"]
        diff_color = {"easy":"#00C9A7","moderate":"#F59E0B","hard":"#FF6B6B"}

        for i, ex in enumerate(exercises[:4]):
            color      = palette[i % len(palette)]
            name       = ex.get("name","Exercise")
            purpose    = ex.get("purpose","")
            steps      = ex.get("steps",[])
            duration   = ex.get("duration","")
            reps       = ex.get("reps","")
            difficulty = ex.get("difficulty","moderate")
            dc         = diff_color.get(difficulty.lower(),"#F59E0B")

            meta = ""
            if duration:
                meta += f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:.68rem;color:{color};background:{color}18;border-radius:5px;padding:3px 10px;margin-right:.4rem;">⏱ {duration}</span>'
            if reps:
                meta += f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:.68rem;color:{color};background:{color}18;border-radius:5px;padding:3px 10px;margin-right:.4rem;">↺ {reps}</span>'
            meta += f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:.68rem;color:{dc};background:{dc}18;border-radius:5px;padding:3px 10px;">{difficulty.upper()}</span>'

            steps_html = "".join([
                f'<div style="display:flex;gap:.6rem;margin-bottom:.45rem;align-items:flex-start;">'
                f'<span style="font-family:\'Syne\',sans-serif;font-size:.62rem;font-weight:800;'
                f'color:{color};background:{color}18;border-radius:4px;padding:2px 6px;flex-shrink:0;margin-top:1px;">{j+1}</span>'
                f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:.85rem;color:#6B8A9A;line-height:1.5;">{s}</span>'
                f'</div>'
                for j, s in enumerate(steps[:3])
            ])

            # Exercise card: info left, video right
            st.markdown(f"""
            <div style="background:#0D1520;border:1px solid #1E3A4A;border-radius:20px;
                 padding:1.8rem 2rem;margin-bottom:1.2rem;position:relative;overflow:hidden;">
              <div style="position:absolute;top:0;left:0;width:4px;height:100%;
                   background:linear-gradient(180deg,{color},{color}44);border-radius:4px 0 0 4px;"></div>
              <div style="display:flex;gap:2rem;align-items:flex-start;flex-wrap:wrap;">
                <div style="flex:1;min-width:260px;">
                  <p style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;
                     color:#E8F0F7;margin-bottom:.4rem;padding-left:.3rem;">{name}</p>
                  <p style="font-family:'Space Grotesk',sans-serif;font-size:.88rem;
                     color:#4A6878;line-height:1.6;margin-bottom:.9rem;padding-left:.3rem;">{purpose}</p>
                  <div style="margin-bottom:1rem;padding-left:.3rem;">{meta}</div>
                  <div style="padding-left:.3rem;">{steps_html}</div>
                </div>
            """, unsafe_allow_html=True)

            # Video on the right in a nested column
            vid_col1, vid_col2 = st.columns([1, 1], gap="large")
            with vid_col2:
                if i in ex_videos and ex_videos[i]:
                    st.video(ex_videos[i], format="video/mp4", autoplay=False)
                else:
                    st.markdown(f"""
                    <div style="background:#0A1018;border-radius:12px;height:140px;
                         display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.5rem;">
                      <span style="font-size:1.5rem;opacity:.3;">🎬</span>
                      <span style="font-family:'Space Grotesk',sans-serif;font-size:.72rem;color:#1E3A4A;">
                        Video not yet generated
                      </span>
                    </div>""", unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)
            if i < len(exercises[:4]) - 1:
                st.markdown('<div style="height:.4rem;"></div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Disclaimer
    st.markdown(f"""
    <div style="margin:2.5rem 3rem 1rem;padding:1rem 1.4rem;
         background:#0D1520;border:1px solid #1E3A4A;border-radius:10px;
         font-family:'Space Grotesk',sans-serif;font-size:.78rem;color:#4A6878;line-height:1.6;">
      <strong style="color:#6B8A9A;">⚠ Medical Disclaimer</strong> — 
      {result.get('disclaimer','This AI-generated analysis is for informational purposes only. Always consult a qualified healthcare professional.')}
    </div>""", unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="margin:1.5rem 3rem 3rem;padding:3.5rem 2rem;
         background:#0D1520;border:1.5px dashed #1E3A4A;border-radius:20px;text-align:center;">
      <div style="font-size:2rem;margin-bottom:1rem;opacity:.3;">⬡</div>
      <p style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;
         color:#2A4A5E;margin-bottom:.5rem;">Awaiting your scan</p>
      <p style="font-family:'Space Grotesk',sans-serif;font-size:.83rem;color:#1E3A4A;">
        Upload a medical image above and click <em>Run Gemini Diagnostic</em>
      </p>
    </div>""", unsafe_allow_html=True)


# Footer
st.markdown("""
<div style="margin-top:3rem;padding:1.5rem 3rem;border-top:1px solid #0F2030;
     display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;">
  <span style="font-family:'Syne',sans-serif;font-size:.85rem;font-weight:700;color:#1E3A4A;">
    MediScan ⬡
  </span>
  <span style="font-family:'Space Grotesk',sans-serif;font-size:.62rem;color:#1E3A4A;
     letter-spacing:.1em;text-transform:uppercase;">
    Gemini Vision · Nano Banana 2 · Veo 3.1 · For Educational Use Only
  </span>
</div>
""", unsafe_allow_html=True)
