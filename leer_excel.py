"""
leer_excel.py
=============
Lee todas las entradas del modelo desde el archivo Excel:
  - Hoja "Variables del Modelo"   → params dict
  - Hoja "Parámetros Técnicos"    → tablas dict (via build_dicts_from_dataframes)
  - Hoja "Listado de Tramos"      → df_tramos DataFrame

Uso:
    from leer_excel import cargar_excel
    params, tablas, df_tramos = cargar_excel("parametrostecnicos.xlsx")
"""

import pandas as pd
import numpy as np
from modelo_gf import build_dicts_from_dataframes, convert_param_type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_numeric_col(series):
    """Convierte una columna a numérico, manejando comas decimales."""
    return pd.to_numeric(
        series.astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )


def _apply_convert(df):
    return df.map(convert_param_type)


# ---------------------------------------------------------------------------
# Lectura de "Variables del Modelo"
# ---------------------------------------------------------------------------

def leer_variables_modelo(path: str, sheet_name: str = 'Variables del Modelo') -> dict:
    """
    Lee la hoja "Variables del Modelo" y devuelve un dict
    {nombre_variable: valor_convertido}.

    Estructura esperada:
      Col A: descripción (ignorada)
      Col B: valor
      Col C: nombre de variable interno
    """

    ### Anulo la lectura del excel
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)

    params = {}
    for _, row in df.iterrows():
        if len(row) < 3:
            continue
        var_name  = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
        raw_value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
        if not var_name or var_name.lower() in ('nan', 'variables del modelo'):
            continue
        # Convertir valor
        val = raw_value.replace(',', '.', 1)
        if val.lower() == 'true':
            params[var_name] = True
        elif val.lower() == 'false':
            params[var_name] = False
        elif val.isdigit():
            params[var_name] = int(val)
        else:
            try:
                params[var_name] = float(val)
            except ValueError:
                params[var_name] = raw_value  # dejar como string (ej. "SI")

    return params


# ---------------------------------------------------------------------------
# Lectura de "Parámetros Técnicos"
# ---------------------------------------------------------------------------

def leer_parametros_tecnicos(path: str, sheet_name: str = 'Parámetros Técnicos') -> dict:
    """
    Lee la hoja "Parámetros Técnicos" y devuelve el dict de tablas listo
    para pasar a calcular() de modelo_gf.

    Rangos fijos (igual que en el Colab original):
      a2:k14  → Costos de obras
      a17:c21 → Vida útil
      a24:d28 → Incremento de capacidad
      a31:h47 → Velocidad / carga por eje
      a50:h55 → Costos de mantenimiento
      a63:c66 → Pasos a nivel (cubi)
    """
    ### Anulo la lectura del excel
    df_full = pd.read_excel(path, sheet_name=sheet_name, header=None)

    def _slice(row_start, row_end, col_start, col_end):
        """Extrae un bloque del DataFrame (0-indexed, inclusive)."""
        block = df_full.iloc[row_start:row_end + 1, col_start:col_end + 1].copy()
        block.columns = range(block.shape[1])
        block = block.reset_index(drop=True)
        # Primera fila como header
        block.columns = [str(v).strip() for v in block.iloc[0]]
        block = block.iloc[1:].reset_index(drop=True)
        return block

    # Costos obra:    filas 1-13 (0-indexed), cols 0-10
    df_costo_obra = _slice(1, 13, 0, 10)
    # Vida útil:      filas 16-20, cols 0-2
    df_vida_util  = _slice(16, 20, 0, 2)
    # Incremento cap: filas 23-27, cols 0-3
    df_inc_cap    = _slice(23, 27, 0, 3)
    # Vel carga:      filas 30-46, cols 0-7
    df_vel_carga  = _slice(30, 46, 0, 7)
    # Mantenimiento:  filas 49-54, cols 0-7
    df_mantenimiento = _slice(49, 54, 0, 7)
    # PCT
    df_pct = _slice(57, 60, 0, 1)
    # Pasos a nivel:  filas 62-65, cols 0-2
    df_pasos_nivel = _slice(62, 65, 0, 2)

    # Renombrar columnas para que coincidan con lo que espera build_dicts_from_dataframes
    # Costos obra: la col 0 se llama "item", necesitamos tipo_inicial y tipo_obra
    # Mirando la estructura: cols son item, ancha, media, angosta, momento_vida_util,
    # plazo_int, rejuvenecimiento, limite_intervencion, tipo_obra, tipo_inicial, tipo_final
    # Ya vienen con esos nombres desde el Excel

    tablas = build_dicts_from_dataframes(
        df_costo_obra    = df_costo_obra,
        df_vida_util     = df_vida_util,
        df_incremento_cap = df_inc_cap,
        df_vel_carga     = df_vel_carga,
        df_costo_mantenimiento = df_mantenimiento,
        df_costopct = df_pct,
        df_pasosanivel   = df_pasos_nivel,
    )
    return tablas


# ---------------------------------------------------------------------------
# Lectura de "Listado de Tramos"
# ---------------------------------------------------------------------------

def leer_listado_tramos(path: str, sheet_name: str = 'Listado de Tramos') -> pd.DataFrame:
    """
    Lee la hoja "Listado de Tramos".
    - Primera fila: encabezados
    - Columnas tipo_trocha y tipo_via_* quedan como string
    - El resto se convierte a numérico
    """
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=0)
    except ValueError as e:
        if "Worksheet named" in str(e) and sheet_name in str(e):
            raise ValueError(f"La hoja '{sheet_name}' no existe en el archivo Excel.")
        raise

    required_columns = [
        "id_tramo", "long_tramo", "carga_util_teorica", "consumo_vida_util_actual", "barreras",
        "tipo_via_inicio", "tipo_via_final", "tipo_trocha"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Faltan las siguientes columnas en la hoja '{sheet_name}': {', '.join(missing_columns)}")
    
    # Validate long_tramo > 0
    if (df['long_tramo'] <= 0).any():
        raise ValueError("La columna 'long_tramo' debe tener valores mayores que cero.")
    
    # Validate carga_util_teorica > 0
    if (df['carga_util_teorica'] <= 0).any():
        raise ValueError("La columna 'carga_util_teorica' debe tener valores mayores que cero.")
    
    # Validate consumo_vida_util_actual >= 0
    if (df['consumo_vida_util_actual'] < 0).any():
        raise ValueError("La columna 'consumo_vida_util_actual' debe tener valores mayores o iguales a cero.")
    
    # Validate barreras >= 0
    if (df['barreras'] < 0).any():
        raise ValueError("La columna 'barreras' debe tener valores mayores o iguales a cero.")
    
    # Validate tipo_via_inicio not null and in ["I", "II", "III", "IV"]
    if df['tipo_via_inicio'].isnull().any():
        raise ValueError("La columna 'tipo_via_inicio' no puede tener valores nulos.")
    valid_via = ["I", "II", "III", "IV"]
    if not df['tipo_via_inicio'].isin(valid_via).all():
        raise ValueError(f"La columna 'tipo_via_inicio' solo puede contener los valores: {', '.join(valid_via)}")
    
    # Validate tipo_via_final not null and in ["I", "II", "III", "IV"]
    if df['tipo_via_final'].isnull().any():
        raise ValueError("La columna 'tipo_via_final' no puede tener valores nulos.")
    if not df['tipo_via_final'].isin(valid_via).all():
        raise ValueError(f"La columna 'tipo_via_final' solo puede contener los valores: {', '.join(valid_via)}")
    
    # Validate tipo_trocha not null and in ["angosta", "ancha", "media"]
    if df['tipo_trocha'].isnull().any():
        raise ValueError("La columna 'tipo_trocha' no puede tener valores nulos.")
    valid_trocha = ["angosta", "ancha", "media"]
    if not df['tipo_trocha'].str.lower().str.strip().isin(valid_trocha).all():
        raise ValueError(f"La columna 'tipo_trocha' solo puede contener los valores: {', '.join(valid_trocha)}")

    str_cols = [c for c in df.columns if c == 'tipo_trocha' or c.startswith('tipo_via')]
    num_cols = [c for c in df.columns if c not in str_cols]

    for col in num_cols:
        if df[col].dtype == object:
            df[col] = _to_numeric_col(df[col])

    # Normalizar tipo_trocha a minúsculas
    if 'tipo_trocha' in df.columns:
        df['tipo_trocha'] = df['tipo_trocha'].astype(str).str.lower().str.strip()

    return df


# ---------------------------------------------------------------------------
# Punto de entrada principal
# ---------------------------------------------------------------------------

def cargar_excel(path: str, path_tramos: str = None) -> tuple:
    """
    Carga todas las entradas del modelo desde el archivo Excel.

    Args:
        path        : archivo con "Variables del Modelo" y "Parámetros Técnicos"
        path_tramos : archivo con "Listado de Tramos" (si es None usa el mismo `path`)

    Returns:
        (params, tablas, df_tramos)
    """
    #params    = leer_variables_modelo(path)
    #tablas    = leer_parametros_tecnicos(path)
    df_tramos = leer_listado_tramos(path_tramos or path)
    #df_tramos = leer_listado_tramos(path_tramos or path)
    # Anule estas devoluciones params, tablas, 
    return df_tramos
