import streamlit as st

from model_state import init_session_state

st.set_page_config(page_title="***Variables del modelo***", layout="wide")
init_session_state()

st.title("Variables del modelo")
st.info("📌 Se pueden editar los valores de las variables por defecto. Los cambios se aplicarán al ejecutar el modelo en Inicio.")

# Mostrar indicador de qué variables se están usando
usando_subidas = st.session_state.get("usar_variables_subidas", False)
#fuente = "del archivo subido" if usando_subidas else "predeterminadas (Modelo.xlsx)"
#st.info(f"📌 Usando ** variables {fuente}**")
vm = st.session_state["variables_modelo_editable"]

# Orden y etiquetas deseadas
ORDEN_VARIABLES = [
    "duracion_anios_negocio",
    "tasa_descuento",
    "crec_factor_inicial",
    "periodo_anios_crec_inicial",
    "crec_factor_final",
    "canon_comercial",
    "costo_pct",
]
ETIQUETAS_VARIABLES = {
    "duracion_anios_negocio": "Años de Operación",
    "tasa_descuento": "Tasa de Descuento",
    "crec_factor_inicial": "Factor 1 de Crecimiento",
    "periodo_anios_crec_inicial": "Años de Crecimiento (si este es >= que Años de Operación, no se usa Factor 2 )",
    "crec_factor_final": "Factor 2 de Crecimiento",
    "canon_comercial": "Canon comercial",
    "costo_pct": "Costo PCT (SI/NO)",
}

# Variables que se muestran como porcentaje
VARIABLES_PORCENTAJE = {
    "canon_comercial",
    "crec_factor_inicial",
    "crec_factor_final",
    "tasa_descuento",
}

# Variable especial con opciones Si/No
VARIABLE_COSTO_PCT = "costo_pct"

claves_ordenadas = []
for clave in ORDEN_VARIABLES:
    if clave in vm:
        claves_ordenadas.append(clave)
for clave in sorted(vm.keys()):
    if clave not in claves_ordenadas:
        claves_ordenadas.append(clave)

for clave in claves_ordenadas:
    valor = vm[clave]
    col1, col2 = st.columns([3, 2])
    with col1:
        etiqueta = ETIQUETAS_VARIABLES.get(clave, clave)
        if clave in VARIABLES_PORCENTAJE:
            etiqueta = f"{etiqueta} (%)"
        st.markdown(etiqueta)
    with col2:
        # Caso especial: costo_pct con opciones Si/No
        if clave == VARIABLE_COSTO_PCT:
            opciones = ["SI", "NO"]
            valor_actual = "SI" if str(valor).upper() in ["SI", "TRUE", "1"] else "NO"
            vm[clave] = st.selectbox(
                f"val_{clave}",
                options=opciones,
                index=opciones.index(valor_actual),
                label_visibility="collapsed",
                key=f"select_{clave}",
            )

        # Caso especial: Variables de porcentaje
        elif clave in VARIABLES_PORCENTAJE:
            if isinstance(valor, (int, float)):
                valor_pct = float(valor) * 100
                nuevo_valor_pct = st.number_input(
                    f"val_{clave}",
                    value=valor_pct,
                    format="%.1f",
                    step=0.1,
                    min_value=0.0,
                    max_value=100.0,
                    label_visibility="collapsed",
                    key=f"pct_{clave}",
                )
                vm[clave] = nuevo_valor_pct / 100
            else:
                vm[clave] = st.text_input(
                    f"val_{clave}",
                    value=str(valor),
                    label_visibility="collapsed",
                    key=f"str_{clave}",
                )

        # Casos normales
        elif isinstance(valor, bool):
            vm[clave] = st.checkbox(
                f"val_{clave}",
                value=bool(valor),
                label_visibility="collapsed",
                key=f"bool_{clave}",
            )
        elif isinstance(valor, int) and not isinstance(valor, bool):
            vm[clave] = int(
                st.number_input(
                    f"val_{clave}",
                    value=int(valor),
                    step=1,
                    min_value=0,
                    label_visibility="collapsed",
                    key=f"int_{clave}",
                )
            )
        elif isinstance(valor, float):
            vm[clave] = float(
                st.number_input(
                    f"val_{clave}",
                    value=float(valor),
                    format="%.6f",
                    step=0.000001,
                    min_value=0.0,
                    label_visibility="collapsed",
                    key=f"float_{clave}",
                )
            )
        else:
            vm[clave] = st.text_input(
                f"val_{clave}",
                value=str(valor),
                label_visibility="collapsed",
                key=f"str_{clave}",
            )

#st.success(f"📌 Usando ** variables {fuente}** por defecto")
#st.success("✓ Variables en memoria.")
