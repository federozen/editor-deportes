import streamlit as st
import requests
from bs4 import BeautifulSoup
import anthropic

st.set_page_config(page_title="Sala de Redacción", page_icon="📋", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Source+Sans+3:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; }
.header-block {
    background: #0d0d0d; color: #f5f0e8;
    padding: 28px 36px 22px; margin: -1rem -1rem 2rem -1rem;
    border-bottom: 4px solid #c8a84b;
    display: flex; align-items: baseline; gap: 18px;
}
.header-block h1 {
    font-family: 'Playfair Display', serif; font-size: 2.2rem;
    font-weight: 900; margin: 0; color: #f5f0e8;
}
.header-block .tagline { font-size: 0.85rem; color: #c8a84b; letter-spacing: 2px; text-transform: uppercase; font-weight: 600; }
.section-label { font-size: 0.7rem; letter-spacing: 3px; text-transform: uppercase; color: #c8a84b; font-weight: 700; margin-bottom: 6px; }
.source-card { background: #faf9f6; border: 1px solid #e0ddd5; border-left: 4px solid #0d0d0d; padding: 14px 18px; border-radius: 2px; margin-bottom: 16px; font-size: 0.9rem; color: #333; }
.output-box { background: #fff; border: 1px solid #e0ddd5; border-top: 3px solid #c8a84b; padding: 20px 22px; border-radius: 2px; font-size: 0.95rem; line-height: 1.7; color: #1a1a1a; white-space: pre-wrap; margin-bottom: 12px; }
.ruled { border: none; border-top: 1px solid #d0ccc2; margin: 24px 0; }
.block-container { padding-top: 0 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-block">
    <h1>Sala de Redacción</h1>
    <span class="tagline">Asistente editorial · Deportes</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    api_key = st.text_input("API Key de Anthropic", type="password", help="Conseguila en console.anthropic.com")
    st.markdown("---")
    st.markdown("**¿Cómo usar?**")
    st.markdown("1. Pegá la API Key arriba")
    st.markdown("2. Ingresá la URL de la nota")
    st.markdown("3. Hacé clic en Analizar")
    st.markdown("4. Copiá lo que necesités")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
}

def extraer_texto(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else (soup.title.string or "")
        article = soup.find("article")
        parrafos = article.find_all("p") if article else soup.find_all("p")
        body = " ".join(p.get_text(strip=True) for p in parrafos if len(p.get_text(strip=True)) > 40)
        if not body:
            return title, "", "No se pudo extraer texto del artículo."
        return title, body[:6000], None
    except Exception as e:
        return "", "", str(e)[:120]

def llamar_claude(api_key, prompt):
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text

# Reglas estrictas anti-alucinación que se inyectan en todos los prompts
REGLAS = """
REGLAS ESTRICTAS (no las rompas bajo ninguna circunstancia):
- Usá ÚNICAMENTE información que esté explícitamente en el texto fuente.
- Si un dato, nombre, cifra o hecho no aparece en el texto, no lo incluyas.
- No parafraseés: reescribí con tus propias palabras y estructura, pero sin cambiar el sentido ni agregar nada.
- No completes con contexto general, conocimiento propio ni suposiciones, aunque parezcan obvias.
- Si el texto no tiene suficiente información para cumplir la tarea, avisalo en vez de inventar.
"""

st.markdown('<div class="section-label">Fuente</div>', unsafe_allow_html=True)
url_input = st.text_input("URL de la nota original", placeholder="https://www.ole.com.ar/...", label_visibility="collapsed")

col_btn, _ = st.columns([1, 3])
with col_btn:
    analizar = st.button("Analizar nota →", type="primary", use_container_width=True)

if analizar:
    if not api_key:
        st.error("⚠️ Ingresá tu API Key de Anthropic en el panel izquierdo.")
        st.stop()
    if not url_input.strip():
        st.warning("Ingresá una URL primero.")
        st.stop()

    with st.spinner("Extrayendo contenido..."):
        titulo_orig, cuerpo, err = extraer_texto(url_input.strip())

    if err and not cuerpo:
        st.error(f"No se pudo leer la nota: {err}")
        st.stop()

    st.markdown(f"""
    <div class="source-card">
        <strong>Fuente:</strong> {url_input}<br>
        <strong>Título detectado:</strong> {titulo_orig or '(no detectado)'}
        <br><small style="color:#888">{len(cuerpo)} caracteres extraídos</small>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="ruled">', unsafe_allow_html=True)

    # ── RESUMEN ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Resumen ejecutivo</div>', unsafe_allow_html=True)
    with st.spinner("Generando resumen..."):
        prompt = f"""Sos un editor periodístico de deportes argentino. Escribís en castellano rioplatense, directo y sin relleno.
{REGLAS}
Texto fuente:
\"\"\"
{cuerpo}
\"\"\"
Tarea: escribí un resumen de 3 a 5 oraciones con los hechos más importantes.
Reescribí con estructura y palabras propias, pero sin agregar ningún dato que no esté en el texto. Sin introducción ni cierre."""
        resumen = llamar_claude(api_key, prompt)
    st.markdown(f'<div class="output-box">{resumen}</div>', unsafe_allow_html=True)
    st.code(resumen, language=None)

    st.markdown('<hr class="ruled">', unsafe_allow_html=True)

    # ── TITULARES ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Opciones de titular</div>', unsafe_allow_html=True)
    with st.spinner("Generando titulares..."):
        prompt = f"""Sos un editor periodístico de deportes argentino. Escribís en castellano rioplatense, directo y sin relleno.
{REGLAS}
Texto fuente:
\"\"\"
{cuerpo}
\"\"\"
Tarea: generá 5 titulares alternativos.
- Variá los enfoques: impactante, informativo, gancho emocional, dato concreto, pregunta.
- Máximo 12 palabras por titular.
- Cada titular debe poder respaldarse con algo que esté literalmente en el texto fuente.
- Numeralos del 1 al 5, uno por línea, sin explicaciones adicionales."""
        titulares = llamar_claude(api_key, prompt)
    st.markdown(f'<div class="output-box">{titulares}</div>', unsafe_allow_html=True)
    st.code(titulares, language=None)

    st.markdown('<hr class="ruled">', unsafe_allow_html=True)

    # ── COPETE ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Copete / bajada</div>', unsafe_allow_html=True)
    with st.spinner("Generando copete..."):
        prompt = f"""Sos un editor periodístico de deportes argentino. Escribís en castellano rioplatense, directo y sin relleno.
{REGLAS}
Texto fuente:
\"\"\"
{cuerpo}
\"\"\"
Tarea: escribí 2 versiones de copete/bajada.
- Versión A: descriptiva (qué pasó, quiénes, dónde) — solo con datos del texto.
- Versión B: con gancho (arranca con un dato llamativo o tensión) — el dato debe estar en el texto, no lo inventes.
Cada copete: máximo 30 palabras. Si el texto no tiene suficiente info para la versión B, decilo en vez de completar con suposiciones."""
        copete = llamar_claude(api_key, prompt)
    st.markdown(f'<div class="output-box">{copete}</div>', unsafe_allow_html=True)
    st.code(copete, language=None)

    st.markdown('<hr class="ruled">', unsafe_allow_html=True)

    # ── ÁNGULO PROPIO ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Ángulo para nota propia</div>', unsafe_allow_html=True)
    with st.spinner("Buscando ángulos..."):
        prompt = f"""Sos un editor periodístico de deportes argentino. Escribís en castellano rioplatense, directo y sin relleno.
{REGLAS}
Texto fuente:
\"\"\"
{cuerpo}
\"\"\"
Tarea: sugerí 3 ángulos para escribir una nota propia.
- Cada ángulo debe partir de algo concreto que SÍ esté en el texto (una cita, un dato, un hecho).
- Podés sugerir qué preguntas hacer o qué fuentes consultar para ampliar, pero dejá claro que son sugerencias de trabajo, no información ya existente.
- No afirmes nada que no esté en el texto.
Numeralos y describí cada uno en 2 oraciones máximo."""
        angulo = llamar_claude(api_key, prompt)
    st.markdown(f'<div class="output-box">{angulo}</div>', unsafe_allow_html=True)
    st.code(angulo, language=None)

    st.markdown("---")
    st.caption("💡 Los bloques de código gris permiten copiar el texto con un clic.")
