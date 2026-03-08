import streamlit as st
import requests
import re
import json

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
.header-block h1 { font-family: 'Playfair Display', serif; font-size: 2.2rem; font-weight: 900; margin: 0; color: #f5f0e8; }
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

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
}

def limpiar_html(html):
    html = re.sub(r'<(script|style)[^>]*>.*?</(script|style)>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<(br|p|div|h[1-6])[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    html = html.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    lineas = [l.strip() for l in html.splitlines() if len(l.strip()) > 40]
    return '\n'.join(lineas)

def extraer_texto(url):
    try:
        r = requests.get(url, headers=FETCH_HEADERS, timeout=15)
        r.raise_for_status()
        html = r.text
        match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        texto = limpiar_html(match.group(1) if match else html)
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        titulo = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ""
        if not texto:
            return titulo, "", "No se pudo extraer texto."
        return titulo, texto[:6000], None
    except Exception as e:
        return "", "", str(e)[:120]

def llamar_claude(api_key, prompt):
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=30
    )
    data = response.json()
    if "content" in data:
        return data["content"][0]["text"]
    return f"Error: {data.get('error', {}).get('message', 'Respuesta inesperada')}"

REGLAS = """
REGLAS ESTRICTAS:
- Usá ÚNICAMENTE información que esté en el texto fuente.
- Si un dato no aparece en el texto, no lo incluyas.
- Reescribí con palabras propias pero sin agregar nada que no esté en la fuente.
- Si el texto no alcanza para la tarea, avisalo en vez de inventar.
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

    st.markdown('<div class="section-label">Resumen ejecutivo</div>', unsafe_allow_html=True)
    with st.spinner("Generando resumen..."):
        resumen = llamar_claude(api_key, f"""Sos un editor periodístico de deportes argentino. Castellano rioplatense, directo, sin relleno.
{REGLAS}
Texto fuente:
\"\"\"{cuerpo}\"\"\"
Escribí un resumen de 3 a 5 oraciones con los hechos más importantes. Sin introducción ni cierre.""")
    st.markdown(f'<div class="output-box">{resumen}</div>', unsafe_allow_html=True)
    st.code(resumen, language=None)
    st.markdown('<hr class="ruled">', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Opciones de titular</div>', unsafe_allow_html=True)
    with st.spinner("Generando titulares..."):
        titulares = llamar_claude(api_key, f"""Sos un editor periodístico de deportes argentino. Castellano rioplatense, directo, sin relleno.
{REGLAS}
Texto fuente:
\"\"\"{cuerpo}\"\"\"
Generá 5 titulares alternativos. Enfoques: impactante, informativo, gancho emocional, dato concreto, pregunta. Máximo 12 palabras. Numeralos del 1 al 5, uno por línea, sin explicaciones.""")
    st.markdown(f'<div class="output-box">{titulares}</div>', unsafe_allow_html=True)
    st.code(titulares, language=None)
    st.markdown('<hr class="ruled">', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Copete / bajada</div>', unsafe_allow_html=True)
    with st.spinner("Generando copete..."):
        copete = llamar_claude(api_key, f"""Sos un editor periodístico de deportes argentino. Castellano rioplatense, directo, sin relleno.
{REGLAS}
Texto fuente:
\"\"\"{cuerpo}\"\"\"
Escribí 2 copetes: Versión A descriptiva (qué pasó, quiénes, dónde). Versión B con gancho (dato llamativo del texto, no inventado). Máximo 30 palabras cada uno.""")
    st.markdown(f'<div class="output-box">{copete}</div>', unsafe_allow_html=True)
    st.code(copete, language=None)
    st.markdown('<hr class="ruled">', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Ángulo para nota propia</div>', unsafe_allow_html=True)
    with st.spinner("Buscando ángulos..."):
        angulo = llamar_claude(api_key, f"""Sos un editor periodístico de deportes argentino. Castellano rioplatense, directo, sin relleno.
{REGLAS}
Texto fuente:
\"\"\"{cuerpo}\"\"\"
Sugerí 3 ángulos para nota propia. Cada uno parte de algo concreto del texto. Podés sugerir preguntas o fuentes a consultar, aclarando que son sugerencias de trabajo. Numeralos, 2 oraciones máximo cada uno.""")
    st.markdown(f'<div class="output-box">{angulo}</div>', unsafe_allow_html=True)
    st.code(angulo, language=None)

    st.markdown("---")
    st.caption("💡 Los bloques de código gris permiten copiar el texto con un clic.")
