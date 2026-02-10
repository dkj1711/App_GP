import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.title("💸 Gastos personales")

monto = st.number_input("Monto", min_value=0.0)
categoria = st.text_input("Categoría")
nota = st.text_input("Nota")

if st.button("Guardar gasto"):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sheet = client.open("Personal").sheet1

    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d"),
        monto,
        categoria,
        nota
    ])

    st.success("Gasto guardado en Google Sheets ✅")
