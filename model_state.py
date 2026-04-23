from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from leer_excel import (
    cargar_excel,
    leer_variables_modelo,
    leer_parametros_tecnicos,
)


def _load_default_variables_and_params() -> tuple[dict, dict]:
    """
    Carga las variables del modelo y parámetros técnicos desde Modelo.xlsx.
    Retorna (variables, parametros) o ({}, {}) si no encuentra el archivo.
    """
    modelo_path = Path(__file__).parent / "var&param.xlsx"
    if not modelo_path.exists():
        print(modelo_path)
        return {}, {}
    
    try:
        variables = leer_variables_modelo(str(modelo_path))
        params = leer_parametros_tecnicos(str(modelo_path))
        return variables, params
    except Exception:
        return {}, {}


def init_session_state() -> None:
    # Cargar variables y parámetros predeterminados desde Modelo.xlsx
    default_variables, default_params = _load_default_variables_and_params()
    
    st.session_state.setdefault("archivo_cargado", False)
    st.session_state.setdefault("uploaded_name", None)
    st.session_state.setdefault("uploaded_suffix", ".xlsx")
    st.session_state.setdefault("uploaded_bytes", None)
    st.session_state.setdefault("upload_signature", None)
    st.session_state.setdefault("usar_variables_subidas", False)
    
    # Variables y parámetros: predeterminados y subidas (inmutables)
    st.session_state.setdefault("variables_modelo_default", default_variables)
    st.session_state.setdefault("tablas_default", default_params)
    st.session_state.setdefault("variables_modelo_subidas", {})
    st.session_state.setdefault("tablas_subidas", {})
    
    # Variables y parámetros EDITABLES: Es lo que el usuario edita y lo que se usa para calcular
    st.session_state.setdefault("variables_modelo_editable", default_variables.copy())
    st.session_state.setdefault("tablas_editable", default_params.copy())
    
    st.session_state.setdefault("df_tramos", pd.DataFrame())
    st.session_state.setdefault("gf_result", None)


def load_excel_to_session(uploaded_name: str, uploaded_bytes: bytes) -> None:
    """
    Carga tramos y guarda variables/parámetros como "subidas" (sin usarlas por defecto).
    Las variables activas siguen siendo las predeterminadas a menos que el usuario
    marque el checkbox 'usar_variables_subidas'.
    """
    suffix = Path(uploaded_name).suffix or ".xlsx"
    signature = (uploaded_name, len(uploaded_bytes))
    if st.session_state.get("upload_signature") == signature:
        return

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_bytes)
            tmp_path = tmp.name
        df_tramos = cargar_excel(tmp_path)
        #params, tablas,
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

    st.session_state["archivo_cargado"] = True
    st.session_state["uploaded_name"] = uploaded_name
    st.session_state["uploaded_suffix"] = suffix
    st.session_state["uploaded_bytes"] = uploaded_bytes
    st.session_state["upload_signature"] = signature
    #st.session_state["variables_modelo_subidas"] = params
    #st.session_state["tablas_subidas"] = tablas
    st.session_state["df_tramos"] = df_tramos
    st.session_state["gf_result"] = None
    
    # Por defecto, seguir usando las predeterminadas (a menos que cambien el checkbox luego)
    st.session_state["usar_variables_subidas"] = False


def update_active_variables() -> None:
    """
    Actualiza las variables EDITABLES según si el usuario marcó 'usar_variables_subidas'.
    Copia la versión correspondiente (default o subidas) a editable.
    Llamar después de que el usuario cambie el checkbox.
    """
    # st.session_state["variables_modelo_editable"] = (
    #     st.session_state.get("variables_modelo_default", {}).copy()
    # )
    # st.session_state["tablas_editable"] = (
    #     st.session_state.get("tablas_default", {}).copy()
    # )

    if st.session_state.get("usar_variables_subidas"):
        # Copiar subidas a editable
        st.session_state["variables_modelo_editable"] = (
            st.session_state.get("variables_modelo_subidas", {}).copy()
        )
        st.session_state["tablas_editable"] = (
            st.session_state.get("tablas_subidas", {}).copy()
        )
    else:
        # Copiar default a editable
        st.session_state["variables_modelo_editable"] = (
            st.session_state.get("variables_modelo_default", {}).copy()
        )
        st.session_state["tablas_editable"] = (
            st.session_state.get("tablas_default", {}).copy()
        )
