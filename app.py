import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd
from dateutil.relativedelta import relativedelta

def generar_gastos_recurrentes_automaticos(client, spreadsheet):
    """Genera automáticamente los gastos recurrentes para el mes actual basados en las plantillas"""
    try:
        # Leer plantillas
        plantillas_sheet = spreadsheet.worksheet("Plantillas_Recurrentes")
        plantillas_records = plantillas_sheet.get_all_records()
        
        if not plantillas_records:
            return
            
        # Leer gastos recurrentes existentes
        try:
            recurrentes_sheet = spreadsheet.worksheet("Recurrentes")
            recurrentes_records = recurrentes_sheet.get_all_records()
        except gspread.WorksheetNotFound:
            recurrentes_sheet = spreadsheet.add_worksheet(title="Recurrentes", rows="100", cols="20")
            recurrentes_sheet.append_row(["Fecha", "Monto", "Categoría", "Nota"])
            recurrentes_records = []
        
        # Mes y año actual
        ahora = datetime.now()
        mes_actual = ahora.month
        año_actual = ahora.year
        
        nuevos_gastos = []
        
        for plantilla in plantillas_records:
            nombre = plantilla.get("Nombre", "")
            monto = float(plantilla.get("Monto", 0))
            categoria = plantilla.get("Categoría", "")
            frecuencia = plantilla.get("Frecuencia", "Mensual")
            fecha_inicio_str = plantilla.get("Fecha_Inicio", "")
            nota = plantilla.get("Nota", "")
            
            if not nombre or monto <= 0:
                continue
                
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
            except:
                continue
            
            # Determinar si debe generar gasto para este mes
            debe_generar = False
            fecha_gasto = None
            
            if frecuencia == "Mensual":
                # Generar el día del mes de la fecha de inicio
                dia_inicio = fecha_inicio.day
                fecha_gasto = datetime(año_actual, mes_actual, min(dia_inicio, 28))  # Evitar problemas con febrero
                
                # Verificar si la fecha de inicio es anterior o igual al mes actual
                if fecha_inicio.replace(day=1) <= datetime(año_actual, mes_actual, 1):
                    debe_generar = True
                    
            elif frecuencia == "Anual":
                # Solo generar si es el mes de la fecha de inicio
                if fecha_inicio.month == mes_actual:
                    fecha_gasto = datetime(año_actual, mes_actual, fecha_inicio.day)
                    debe_generar = True
                    
            elif frecuencia == "Semanal":
                # Para semanal, generar si hay alguna semana del mes que corresponda
                # Esto es más complejo, por ahora generamos el mismo día de la semana del inicio
                # si estamos en el mes correcto
                if fecha_inicio.replace(day=1) <= datetime(año_actual, mes_actual, 1):
                    # Generar el gasto en la primera ocurrencia del día de la semana en el mes
                    dia_semana_inicio = fecha_inicio.weekday()
                    # Encontrar el primer día del mes que coincida con el día de la semana
                    primer_dia_mes = datetime(año_actual, mes_actual, 1)
                    dias_diferencia = (dia_semana_inicio - primer_dia_mes.weekday()) % 7
                    fecha_gasto = primer_dia_mes + timedelta(days=dias_diferencia)
                    debe_generar = True
            
            if debe_generar and fecha_gasto:
                # Verificar si ya existe este gasto en el mes actual
                gasto_ya_existe = False
                for rec in recurrentes_records:
                    try:
                        fecha_rec = datetime.strptime(rec.get("Fecha", ""), "%Y-%m-%d")
                        if (fecha_rec.year == año_actual and 
                            fecha_rec.month == mes_actual and
                            rec.get("Categoría") == categoria and
                            float(rec.get("Monto", 0)) == monto and
                            nombre.lower() in rec.get("Nota", "").lower()):
                            gasto_ya_existe = True
                            break
                    except:
                        continue
                
                if not gasto_ya_existe:
                    nuevos_gastos.append({
                        "fecha": fecha_gasto,
                        "monto": monto,
                        "categoria": categoria,
                        "nota": f"{nombre} - {nota}".strip()
                    })
        
        # Añadir los nuevos gastos a la hoja Recurrentes
        if nuevos_gastos:
            for gasto in nuevos_gastos:
                recurrentes_sheet.append_row([
                    gasto["fecha"].strftime("%Y-%m-%d"),
                    gasto["monto"],
                    gasto["categoria"],
                    gasto["nota"]
                ])
            
            st.info(f"Se generaron automáticamente {len(nuevos_gastos)} gastos recurrentes para este mes")
            
    except gspread.WorksheetNotFound:
        # No hay plantillas, continuar normalmente
        pass
    except Exception as e:
        st.warning(f"Error al generar gastos recurrentes automáticos: {str(e)}")

st.title("💸 Gastos personales")

tab1, tab2, tab3, tab4 = st.tabs(["Registrar Gasto", "Ver Gastos", "Resúmenes", "Presupuestos"])

with tab1:
    st.header("Registrar nuevo gasto")
    
    # Inicializar contador para resetear campos
    if 'gasto_counter' not in st.session_state:
        st.session_state.gasto_counter = 0
    
    fecha = st.date_input("Fecha", value=datetime.today())
    # Usar el counter como parte del key para forzar reset
    monto = st.number_input("Monto", min_value=0.0, value=None, key=f"monto_{st.session_state.gasto_counter}")
    categorias = ["Comida", "Transporte", "Entretenimiento", "Salud", "Educación", "Otros"]
    categoria = st.selectbox("Categoría", categorias, key=f"categoria_{st.session_state.gasto_counter}")
    tipo = st.selectbox("Tipo de gasto", ["Variable", "Recurrente"], key=f"tipo_{st.session_state.gasto_counter}")
    nota = st.text_input("Nota", key=f"nota_{st.session_state.gasto_counter}")
    
    # Campos adicionales para gastos recurrentes
    if tipo == "Recurrente":
        st.subheader("Configuración de recurrencia")
        nombre_recurrente = st.text_input("Nombre del gasto recurrente", 
                                        placeholder="Ej: Suscripción Netflix, Alquiler, etc.",
                                        key=f"nombre_recurrente_{st.session_state.gasto_counter}")
        frecuencia = st.selectbox("Frecuencia", ["Mensual", "Semanal", "Anual"], 
                                key=f"frecuencia_{st.session_state.gasto_counter}")
        es_primera_vez = st.checkbox("¿Es la primera vez que registras este gasto recurrente?", 
                                   value=True, key=f"es_primera_vez_{st.session_state.gasto_counter}")
        
        if es_primera_vez:
            st.info("✅ Se creará una plantilla automática para futuros meses")
        else:
            st.info("ℹ️ Solo se registrará este gasto sin crear plantilla")

    if st.button("Guardar gasto"):
        if not monto or monto <= 0:
            st.error("Por favor ingresa un monto válido")
            st.stop()
            
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )

        client = gspread.authorize(creds)
        spreadsheet = client.open("Personal")
        
        # Crear plantilla si es gasto recurrente por primera vez
        if tipo == "Recurrente" and 'es_primera_vez' in locals() and es_primera_vez:
            if not nombre_recurrente:
                st.error("Por favor ingresa un nombre para el gasto recurrente")
                st.stop()
                
            try:
                plantillas_sheet = spreadsheet.worksheet("Plantillas_Recurrentes")
            except gspread.WorksheetNotFound:
                plantillas_sheet = spreadsheet.add_worksheet(title="Plantillas_Recurrentes", rows="100", cols="20")
                plantillas_sheet.append_row(["Nombre", "Monto", "Categoría", "Frecuencia", "Fecha_Inicio", "Nota"])
            
            plantillas_sheet.append_row([
                nombre_recurrente,
                monto,
                categoria,
                frecuencia,
                fecha.strftime("%Y-%m-%d"),
                nota
            ])
            st.info(f"✅ Plantilla creada para '{nombre_recurrente}' - se generarán automáticamente en futuros meses")
        
        # Solo guardar el gasto si NO es recurrente, o si es recurrente pero NO es la primera vez
        if tipo != "Recurrente" or (tipo == "Recurrente" and not es_primera_vez):
            if tipo == "Recurrente":
                try:
                    sheet = spreadsheet.worksheet("Recurrentes")
                except gspread.WorksheetNotFound:
                    sheet = spreadsheet.add_worksheet(title="Recurrentes", rows="100", cols="20")
                    sheet.append_row(["Fecha", "Monto", "Categoría", "Nota"])  # Header
            else:
                try:
                    sheet = spreadsheet.worksheet("Variables")
                except gspread.WorksheetNotFound:
                    sheet = spreadsheet.add_worksheet(title="Variables", rows="100", cols="20")
                    sheet.append_row(["Fecha", "Monto", "Categoría", "Nota"])  # Header

            sheet.append_row([
                fecha.strftime("%Y-%m-%d"),
                monto,
                categoria,
                nota
            ])

        st.success("Gasto guardado en Google Sheets ✅")
        # Incrementar contador para resetear todos los campos
        st.session_state.gasto_counter += 1
        st.rerun()

with tab2:
    st.header("Ver gastos")
    tipo_ver = st.selectbox("Tipo de gasto a ver", ["Variable", "Recurrente"], key="ver_tipo")
    
    if st.button("Cargar gastos"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )

        client = gspread.authorize(creds)
        spreadsheet = client.open("Personal")
        
        if tipo_ver == "Recurrente":
            sheet_name = "Recurrentes"
        else:
            sheet_name = "Variables"
        
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            records = sheet.get_all_records()
            if records:
                df = pd.DataFrame(records)
                st.dataframe(df)
                
                st.subheader("Editar gastos")
                edited_df = st.data_editor(df, num_rows="dynamic")
                
                if st.button("Guardar cambios"):
                    sheet.clear()
                    sheet.append_row(["Fecha", "Monto", "Categoría", "Nota"])
                    for _, row in edited_df.iterrows():
                        sheet.append_row([row["Fecha"], row["Monto"], row["Categoría"], row["Nota"]])
                    st.success("Cambios guardados ✅")
                    st.rerun()
            else:
                st.info("No hay gastos registrados en esta categoría.")
        except gspread.WorksheetNotFound:
            st.error(f"La hoja '{sheet_name}' no existe aún. Registra un gasto primero.")

with tab3:
    st.header("Resúmenes de gastos")
    
    if st.button("Generar resumen"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )

        client = gspread.authorize(creds)
        spreadsheet = client.open("Personal")
        
        # Generar gastos recurrentes automáticos para el mes actual
        generar_gastos_recurrentes_automaticos(client, spreadsheet)
        
        all_records = []
        for sheet_name in ["Variables", "Recurrentes"]:
            try:
                sheet = spreadsheet.worksheet(sheet_name)
                records = sheet.get_all_records()
                for rec in records:
                    rec["Tipo"] = sheet_name[:-1]  # Variable or Recurrente
                    all_records.append(rec)
            except gspread.WorksheetNotFound:
                pass
        
        if all_records:
            df = pd.DataFrame(all_records)
            
            # Strip spaces from column names
            df.columns = df.columns.str.strip()
            
            # Rename columns to match expected names
            column_mapping = {
                "Categoria": "Categoría"
            }
            df = df.rename(columns=column_mapping)
            
            # Check if required columns exist
            required_columns = ["Fecha", "Monto", "Categoría"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Las siguientes columnas no se encontraron en los datos: {', '.join(missing_columns)}. Verifica que las hojas de cálculo tengan los encabezados correctos.")
                st.stop()
            
            df["Fecha"] = pd.to_datetime(df["Fecha"])
            df["Monto"] = pd.to_numeric(df["Monto"])
            
            # Total general
            total = df["Monto"].sum()
            st.metric("Total de gastos", f"${total:.2f}")
            
            # Total por tipo
            tipo_totals = df.groupby("Tipo")["Monto"].sum()
            st.subheader("Total por tipo")
            st.bar_chart(tipo_totals)
            
            # Total por categoría
            cat_totals = df.groupby("Categoría")["Monto"].sum()
            st.subheader("Total por categoría")
            st.bar_chart(cat_totals)
            
            # Gastos por mes
            df["Mes"] = df["Fecha"].dt.to_period("M")
            monthly = df.groupby("Mes")["Monto"].sum()
            st.subheader("Gastos mensuales")
            st.line_chart(monthly)
            
            # Comparación con presupuestos
            try:
                pres_sheet = spreadsheet.worksheet("Presupuestos")
                pres_records = pres_sheet.get_all_records()
                if pres_records:
                    df_pres = pd.DataFrame(pres_records)
                    df_pres["Presupuesto"] = pd.to_numeric(df_pres["Presupuesto"])
                    
                    # Extraer presupuesto general
                    presupuesto_general_row = df_pres[df_pres["Categoría"] == "General"]
                    if not presupuesto_general_row.empty:
                        presupuesto_general_valor = presupuesto_general_row["Presupuesto"].iloc[0]
                        diferencia_general = presupuesto_general_valor - total
                        st.metric("Presupuesto General vs Gastos", f"${diferencia_general:.2f}", 
                                delta=f"${presupuesto_general_valor:.2f} presupuesto")
                    
                    # Comparación por categorías (excluyendo General)
                    df_pres_cat = df_pres[df_pres["Categoría"] != "General"]
                    comparison = pd.merge(cat_totals.reset_index(), df_pres_cat, on="Categoría", how="left")
                    comparison["Diferencia"] = comparison["Presupuesto"] - comparison["Monto"]
                    st.subheader("Comparación con presupuestos por categoría")
                    st.dataframe(comparison)
                    over_budget = comparison[comparison["Diferencia"] < 0]
                    if not over_budget.empty:
                        st.warning("Categorías sobre presupuesto:")
                        for _, row in over_budget.iterrows():
                            st.write(f"- {row['Categoría']}: ${-row['Diferencia']:.2f} sobre presupuesto")
            except gspread.WorksheetNotFound:
                st.info("No hay presupuestos configurados.")
        else:
            st.info("No hay datos para generar resumen.")

with tab4:
    st.header("Configurar presupuestos")
    categorias = ["Comida", "Transporte", "Entretenimiento", "Salud", "Educación", "Otros"]
    
    # Presupuesto general
    presupuesto_general = st.number_input("Presupuesto General Mensual", min_value=0.0, value=0.0)
    
    presupuestos = {}
    for cat in categorias:
        presupuestos[cat] = st.number_input(f"Presupuesto para {cat}", min_value=0.0, value=0.0)
    
    if st.button("Guardar presupuestos"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )

        client = gspread.authorize(creds)
        spreadsheet = client.open("Personal")
        
        try:
            sheet = spreadsheet.worksheet("Presupuestos")
            sheet.clear()  # Clear existing
        except gspread.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title="Presupuestos", rows="10", cols="2")
        
        sheet.append_row(["Categoría", "Presupuesto"])
        # Añadir presupuesto general
        sheet.append_row(["General", presupuesto_general])
        for cat, pres in presupuestos.items():
            sheet.append_row([cat, pres])
        
        st.success("Presupuestos guardados ✅")
