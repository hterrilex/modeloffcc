"""
App Streamlit — Modelo GF
=========================
Sube el Excel con las hojas de entrada, ejecuta el modelo y descarga el mismo libro
con todas las hojas de salida escritas (nombre de archivo con [fecha hora]).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from escribir_excel import escribir_resultados_bytes
from model_state import init_session_state, load_excel_to_session, update_active_variables
from modelo_gf import (
    calc_min_carga_por_anio,
    calc_suma_producto,
    calc_suma_simple_por_anio,
    calcular,
)


def _build_consolidado_dataframe(df_salida: pd.DataFrame, params: dict = None) -> pd.DataFrame:
    """Vista previa alineada con la hoja consolidado2 (misma lógica que el Excel)."""
    if params is None:
        params = {}
    
    # Obtener la cantidad de años de la variable del modelo, default 40 si no existe
    num_years = params.get("duracion_anios_negocio", 40)
    
    s_carga_prom = calc_suma_producto(
        df_salida,
        "Carga proyectada por año (q) (tn) - LIMITADA",
        desde_anio_1=False,
        por_longitud=False,
    )
    s_tnkm = calc_suma_simple_por_anio(df_salida, "Carga anual TN.KM")
    s_vida_util = calc_suma_producto(
        df_salida, "% Vida útil consumida", desde_anio_1=False, por_longitud=False
    )
#### VER AÑOS ####
    años = pd.RangeIndex(0, num_years + 1, name="año")
    out = pd.DataFrame(index=años)
    out.index.name = "año"
    out["Carga anual promedio ponderada TN"] = s_carga_prom.reindex(años, fill_value=0)
    out["Carga anual TN.KM"] = s_tnkm.reindex(años, fill_value=0)
    out["%Vida útil consumida promedio"] = s_vida_util.reindex(años, fill_value=0)

    obras = [
        ("Obra de Renovación", True),
        ("Obra de Mejoramiento", True),
        ("Desvíos a construir", True),
        ("Conservación costo fijo anual", True),
        ("Primer Tramo de Mantenimiento", True),
        ("Segundo Tramo de Mantenimiento", True),
        ("Costo operación infraestructura del tramo", True),
        ("Velocidad", False),
        ("Carga x Eje", False),
    ]
    for col, por_longitud in obras:
        serie = calc_suma_producto(
            df_salida, col, desde_anio_1=True, por_longitud=por_longitud
        )
        aligned = serie.reindex(años, fill_value=None)
        out[col] = aligned

    s_min_eje = calc_min_carga_por_anio(df_salida, "Carga x Eje")
    out["CARGA POR EJE LIMITANTE DE LA RED"] = s_min_eje.reindex(años, fill_value=0)
    out.loc[0, "CARGA POR EJE LIMITANTE DE LA RED"] = None

    return out.reset_index()


def _nombre_descarga(original_name: str) -> str:
    """nombre.xlsx → nombre_YY-MM-DD_HH.xlsx"""
    stem = Path(original_name).stem
    suf = Path(original_name).suffix or ".xlsx"
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{stem}_[{ts}]{suf}"


def main() -> None:
    st.set_page_config(page_title="Modelo GF", layout="wide")
    init_session_state()
    st.title("**Modelo de Mantenimiento y Gestión Ferroviaria**")
    st.caption(
        "**Entradas:** obligatorio excel con **Listado de Tramos** /// **Salidas:** Resultados x Tramos y Años, Resumen x Tramos, Consolidado y **Copia de Consolidado (Excel)**"
    )
    #, opcional Hojas «Variables del Modelo», «Parámetros Técnicos»\n
    st.info(
        "📌 **Las Variables del Modelo y los Parámetros Técnicos están predeterminados**. Se pueden cambiar desde el menú lateral"        
    )
# o desde el Excel que se sube.
    uploaded = st.file_uploader(
        "Subir Archivo Excel (.xlsx)",
        type=["xlsx"],
        help="Debe incluir **Listado de Tramos** (Obligatorio) con los campos xxx",
    )

    if uploaded is not None:
        try:
            load_excel_to_session(uploaded.name, uploaded.getvalue())
        except Exception as e:
            st.error(f"Error al cargar el archivo Excel: {e}")
            st.session_state["archivo_cargado"] = False  # Ensure it's not loaded
            return  # Stop further execution

    # Mostrar opción para usar variables del archivo subido
    #if st.session_state.get("archivo_cargado"):
    #    col1, col2 = st.columns([3, 1])
        # with col2:
        #     usar_subidas = st.checkbox(
        #         "Usar variables del archivo subido",
        #         value=st.session_state.get("usar_variables_subidas", False),
        #         key="checkbox_usar_variables_subidas",
        #         help="Si está marcado, usa las Variables y los Parámetros Técnicos del archivo que acabas de subir. "
        #              "\nSi no, usa los predeterminados del Modelo (ver solapas)",
        #     )
        #     if usar_subidas != st.session_state.get("usar_variables_subidas"):
        #         st.session_state["usar_variables_subidas"] = usar_subidas
        #         update_active_variables()
        #         st.rerun()

    run = st.button(
        "Ejecutar modelo",
        type="primary",
        disabled=not st.session_state.get("archivo_cargado"),
        help="Necesita cargar un Excel con el «Listado de Tramos»",
    )

    if run:
        try:
            with st.spinner("Calculando con variables & parámetros actuales…"):
                params = dict(st.session_state["variables_modelo_editable"])
                tablas = dict(st.session_state["tablas_editable"])
                df_tramos = st.session_state["df_tramos"].copy()
                resultado = calcular(params, tablas, df_tramos)
                df_salida = resultado["df_salida"]
                df_agregado = resultado["df_agregado"]
                df_consolidado = _build_consolidado_dataframe(df_salida, params)
                libro_con_resultados = escribir_resultados_bytes(
                    st.session_state["uploaded_bytes"],
                    df_salida,
                    df_agregado,
                    suffix=st.session_state["uploaded_suffix"],
                    variables=st.session_state["variables_modelo_editable"],
                )
            st.session_state["gf_result"] = {
                "df_salida": df_salida,
                "df_agregado": df_agregado,
                "df_consolidado": df_consolidado,
                "source_name": st.session_state["uploaded_name"],
                "libro_con_resultados": libro_con_resultados,
            }
        except Exception as e:
            st.error(f"Error al ejecutar: {e}")
            raise

    res = st.session_state.get("gf_result")
    if not res:
        st.info("📌 Carga un archivo en la sección superior (con «Listado de Tramos») y pulsa **Ejecutar modelo**")                 
        return

    st.success(f"Modelo ejecutado sobre «{res['source_name']}».")

    tab1, tab2, tab3 = st.tabs(["Tramos (detalle)", "Resumen por tramo", "Consolidado"])
    with tab1:
        st.dataframe(res["df_salida"], width='stretch', height=400)
    with tab2:
        st.dataframe(res["df_agregado"], width='stretch', height=400)
    with tab3:
        st.dataframe(res["df_consolidado"], width='stretch', height=400)

    st.download_button(
        label="Descargar Excel con resultados",
        data=res["libro_con_resultados"],
        file_name=_nombre_descarga(res["source_name"]),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
