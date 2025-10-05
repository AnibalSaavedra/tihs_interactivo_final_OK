
import streamlit as st
from preguntas import preguntas
from fpdf import FPDF
import matplotlib.pyplot as plt
import smtplib
from email.message import EmailMessage
import os
from io import BytesIO
from dotenv import load_dotenv
from datetime import date

load_dotenv()
EMAIL_RECEPTOR = "estudios.preventivos@gmail.com"
EMAIL_EMISOR = os.getenv("EMAIL_EMISOR")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

st.set_page_config(page_title="Test Heridas del Ser", layout="wide")
st.title("🧠 Test Interactivo de Heridas del Ser (TIHS)")

if "pagina" not in st.session_state:
    st.session_state.pagina = 0
if "respuestas" not in st.session_state:
    st.session_state.respuestas = {}
if "datos_usuario" not in st.session_state:
    st.session_state.datos_usuario = {}

total_paginas = 5
heridas_por_pagina = len(preguntas) // total_paginas
pag_actual = st.session_state.pagina

opciones = {
    "❌ Nunca": 0,
    "🤔 Regular": 1,
    "✅ Muy de acuerdo": 2
}

if pag_actual == 0:
    st.subheader("📝 Información personal")
    nombre = st.text_input("Nombre")
    apellido_paterno = st.text_input("Apellido paterno")
    apellido_materno = st.text_input("Apellido materno")
    identificacion = st.text_input("Identificación / RUT / DNI")
    fecha_nacimiento = st.date_input("Fecha de nacimiento", min_value=date(1910, 1, 1), max_value=date.today())
    hora_nacimiento = st.text_input("Hora de nacimiento (opcional)")
    ciudad_nacimiento = st.text_input("Ciudad de nacimiento (opcional)")
    correo = st.text_input("Correo electrónico (obligatorio para recibir el informe)")
    whatsapp = st.text_input("Número de WhatsApp (opcional)")

    if st.button("Comenzar"):
        if nombre and apellido_paterno and correo:
            st.session_state.datos_usuario = {
                "Nombre": nombre,
                "Apellido paterno": apellido_paterno,
                "Apellido materno": apellido_materno,
                "Identificación": identificacion,
                "Fecha de nacimiento": str(fecha_nacimiento),
                "Hora de nacimiento": hora_nacimiento,
                "Ciudad de nacimiento": ciudad_nacimiento,
                "Correo": correo,
                "WhatsApp": whatsapp
            }
            st.session_state.pagina += 1
        else:
            st.warning("Por favor completa al menos nombre, apellido paterno y correo.")
else:
    inicio = (pag_actual - 1) * heridas_por_pagina
    fin = inicio + heridas_por_pagina
    heridas_pagina = list(preguntas.items())[inicio:fin]

    st.header(f"Página {pag_actual} de {total_paginas}")

    for herida, items in heridas_pagina:
        st.subheader(f"🌀 {herida}")
        for idx, pregunta in enumerate(items):
            key = f"{herida}_{idx}"
            st.session_state.respuestas[key] = st.selectbox(
                pregunta,
                list(opciones.keys()),
                key=key
            )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Anterior") and st.session_state.pagina > 1:
            st.session_state.pagina -= 1
    with col2:
        if st.session_state.pagina < total_paginas:
            if st.button("Siguiente"):
                st.session_state.pagina += 1
        else:
            observaciones = st.text_area("🗒 Observaciones clínicas (opcional)")

            if st.button("Finalizar y enviar resultados"):
                resultados = {}
                for herida in preguntas:
                    suma = sum(
                        opciones.get(st.session_state.respuestas.get(f"{herida}_{i}", "❌ Nunca"), 0)
                        for i in range(5)
                    )
                    resultados[herida] = suma

                st.success("✅ Resultados calculados correctamente")
                st.write(resultados)

                fig, ax = plt.subplots(figsize=(10, 5))
                ax.bar(resultados.keys(), resultados.values(), color='skyblue')
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                img_bytes = BytesIO()
                plt.savefig(img_bytes, format="png")
                img_bytes.seek(0)

                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, f"Informe - {st.session_state.datos_usuario['Nombre']} {st.session_state.datos_usuario['Apellido paterno']}", ln=True)
                pdf.set_font("Arial", "", 12)

                for k, v in st.session_state.datos_usuario.items():
                    pdf.cell(0, 10, f"{k}: {v}", ln=True)

                pdf.ln(5)
                top3 = sorted(resultados.items(), key=lambda x: x[1], reverse=True)[:3]
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "Resumen de heridas más activas:", ln=True)
                pdf.set_font("Arial", "", 12)
                for herida, valor in top3:
                    pdf.cell(0, 10, f"- {herida}: {valor}", ln=True)

                if observaciones:
                    pdf.ln(5)
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, "Observaciones del profesional:", ln=True)
                    pdf.set_font("Arial", "", 12)
                    for linea in observaciones.splitlines():
                        pdf.multi_cell(0, 10, linea)

                pdf.ln(10)
                img_file = "grafico.png"
                with open(img_file, "wb") as f:
                    f.write(img_bytes.read())
                pdf.image(img_file, x=10, y=pdf.get_y(), w=180)
                pdf_file = f"informe_{st.session_state.datos_usuario['Nombre'].replace(' ', '_')}.pdf"
                pdf.output(pdf_file)

                msg = EmailMessage()
                msg["Subject"] = "Resultados TIHS"
                msg["From"] = EMAIL_EMISOR
                msg["To"] = EMAIL_RECEPTOR
                contenido = (
                    "🧾 Nuevo test recibido con los siguientes datos:\n\n" +
                    "\n".join([f"{k}: {v}" for k, v in st.session_state.datos_usuario.items()]) +
                    "\n\nHeridas más activas:\n" +
                    "\n".join([f"{h}: {v}" for h, v in top3])
                )
                msg.set_content(contenido)

                with open(pdf_file, "rb") as f:
                    msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=pdf_file)

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                    smtp.login(EMAIL_EMISOR, EMAIL_PASSWORD)
                    smtp.send_message(msg)

                st.success("📧 Informe enviado exitosamente por correo.")
