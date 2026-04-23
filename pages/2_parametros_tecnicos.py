import pandas as pd
import streamlit as st

from model_state import init_session_state


def _tabla_dict_a_df(name: str, data: dict) -> pd.DataFrame:
    filas = []
    for key, values in data.items():
        row = {}
        if isinstance(key, tuple):
            for i, k in enumerate(key, start=1):
                row[f"key_{i}"] = k
        else:
            row["key"] = key
        row.update(values if isinstance(values, dict) else {"value": values})
        filas.append(row)
    df = pd.DataFrame(filas)
    df.insert(0, "tabla", name)
    return df


st.set_page_config(page_title="**Parámetros Técnicos**", layout="wide")
init_session_state()

st.title("Parámetros Técnicos")
st.caption("Vista de los datos tomados de la hoja «Parámetros Técnicos».")

# Mostrar indicador de qué parámetros se están usando
usando_subidas = st.session_state.get("usar_variables_subidas", False)
fuente = "del archivo subido" if usando_subidas else "predeterminados (Modelo.xlsx)"
#st.info(f"📌 Usando parámetros **{fuente}**")

tablas = st.session_state.get("tablas_editable", {})
if not tablas:
    st.warning("No hay parámetros cargados.")
    st.stop()

for nombre, tabla in tablas.items():
    st.subheader(nombre)
    df = _tabla_dict_a_df(nombre, tabla)
    #st.dataframe(df, use_container_width=True, height=240)
    st.dataframe(df, width='stretch', height=240)
