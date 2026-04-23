# Migración de Python a Streamlit
_Exported on 4/16/2026 at 03:20:22 GMT-3 from Cursor (3.1.15)_

---

**User**

Tengo que realizar una migración de python a streamlit, para ello quiero que analices todos los archivos *.py de esta carpeta. En la misma tambien hay un excel que tiene las hojas que son entrada de datos ('Variables del Modelo`, `Parámetros Técnicos` y `Listado de Tramos`) y las hojas que son salidas de los datos procesados por modelo_gf.py. Las hojas de salida son 'consolidado2', 'resumen de tramos' y 'tramos'. modelo_gf.py debe tomar esos datos de entrada y generar las salidas. 

---

**Cursor**

Analizando los archivos `.py` del proyecto y la relación con el Excel para documentar la arquitectura y qué implicaría migrar a Streamlit.



Aquí va un análisis consolidado de los tres `.py` de la carpeta y cómo encajan con tu Excel y una futura app Streamlit.

## Archivos y responsabilidades

| Archivo | Rol |
|--------|-----|
| **`modelo_gf.py`** | Núcleo del modelo: diccionarios desde tablas, `calcular_tramo`, agregados y funciones para el consolidado (`calc_suma_producto`, etc.). **No toca Excel.** |
| **`leer_excel.py`** | Entradas: lee el `.xlsx` y arma `params`, `tablas`, `df_tramos` para `calcular()`. |
| **`escribir_excel.py`** | Salidas: escribe resultados en el libro con **openpyxl** (y opcionalmente copia el archivo si cambias `path_salida`). |

## Flujo de datos (alineado con tu descripción)

1. **Entradas** (hojas que mencionas):
   - **`Variables del Modelo`** → diccionario `params` (col B valor, col C nombre interno; convierte bool, int, float, string).
   - **`Parámetros Técnicos`** → bloques fijos en filas/columnas (costos obra, vida útil, incremento capacidad, vel/carga, mantenimiento, pasos a nivel) → `build_dicts_from_dataframes()` en `modelo_gf.py` → `tablas`.
   - **`Listado de Tramos`** → `DataFrame` con cabecera en fila 1; columnas numéricas salvo `tipo_trocha` y `tipo_via*`.

2. **Cálculo**  
   `modelo_gf.calcular(params, tablas, df_tramos)` devuelve:
   - **`df_salida`**: una fila por **tramo × año** (columnas como carga limitada, TN·km, obras, mantenimiento, velocidad, carga por eje, etc.).
   - **`df_agregado`**: resumen **por `id_tramo`** (join con datos del año 0).

3. **Salidas en Excel** (lo que implementa `escribir_resultados`):
   - **`Tramos`** (nombre con mayúscula inicial): todo `df_salida`.
   - **`Resumen Tramos`**: `df_agregado` (en tu mensaje dijiste “resumen de tramos”; en código la hoja es **`Resumen Tramos`**).
   - **`consolidado2`**: series **verticales** año a año (41 años para algunas columnas, 40 para las que empiezan en año 1), usando las mismas funciones de agregación que el modelo.
   - Además existe **`Copia de Consolidado`**: mismo tipo de series pero en **layout horizontal** y conservando lógica de fórmulas en otras columnas; no la nombraste como salida principal pero sí está en el flujo actual.

**Nota:** No hay un `.xlsx` en el repo (búsqueda sin resultados); el diseño asume que el libro ya tiene esas hojas o que se crean vacías al escribir.

## Dependencias entre módulos

- `leer_excel` importa `build_dicts_from_dataframes` y `convert_param_type` desde `modelo_gf`.
- `escribir_excel` importa `calc_suma_simple_por_anio`, `calc_suma_producto`, `calc_min_carga_por_anio` desde `modelo_gf`.

El **contrato útil para Streamlit** es: **`calcular(params, tablas, df_tramos)`**; Excel es solo I/O.

## Implicaciones para migrar a Streamlit

1. **Reutilizar `modelo_gf.py` tal cual** (o casi): la app solo debe construir los mismos `params`, `tablas` y `df_tramos` que hoy salen de `cargar_excel`.
2. **Entradas en Streamlit**:
   - `st.file_uploader` para `.xlsx` y llamar a la misma lógica de `leer_excel` pasando un path temporal o `BytesIO` (haría falta una variante de `cargar_excel` que acepte buffer, o guardar el archivo subido en un temporal).
   - Opcional: `st.data_editor` para editar el listado de tramos o tablas técnicas sin Excel.
3. **Salidas en Streamlit**:
   - Mostrar `df_salida` y `df_agregado` con `st.dataframe` / descarga CSV o Excel.
   - El consolidado (`consolidado2`) hoy se **deriva** de `df_salida` en `escribir_excel`; en Streamlit puedes **reutilizar las mismas funciones** de `modelo_gf` y pintar gráficos o tablas sin volver a escribir el libro, salvo que quieras “Exportar Excel” → entonces llamar a `escribir_resultados` sobre una plantilla.
4. **Inconsistencia menor a tener en cuenta**: en `escribir_excel`, `reset_index(drop='id_tramo' in df_agregado.columns)` usa un booleano como `drop` de `reset_index`; en pandas lo habitual es `drop=False` y manejar el índice aparte. Conviene revisarlo cuando toques esa hoja.

Si el siguiente paso es implementar la app, puedo proponerte la estructura mínima de `streamlit_app.py` (upload → `calcular` → tabs de resultados + descarga) sin tocar la lógica de `modelo_gf.py`.

---

**User**

ok

---

**Cursor**

Implementando la app Streamlit mínima: comprobando dependencias y creando los archivos necesarios.



Creando `requirements.txt` y `streamlit_app.py` con carga de Excel, ejecución del modelo y descarga de resultados.



Mejorando la limpieza de archivos temporales y corrigiendo el bloque `write_template`.



Listo. Añadí lo mínimo para poder usar el modelo desde Streamlit.

## Qué hay nuevo

1. **`requirements.txt`** — `pandas`, `numpy`, `openpyxl`, `streamlit`.

2. **`streamlit_app.py`** — Flujo:
   - Subida de `.xlsx`
   - **Ejecutar modelo** → `cargar_excel` + `calcular`
   - Pestañas: detalle **Tramos**, **Resumen por tramo**, **Consolidado** (misma lógica que la hoja `consolidado2`)
   - **Descargar resultados (.xlsx)** — solo hojas de salida generadas en memoria
   - Opcional: **Tras calcular, volcar también al libro** — usa `escribir_resultados` sobre una copia de tu archivo (incluye **Copia de Consolidado** como en el script)

Los temporales del upload se borran tras leer; los de la exportación “libro completo” también.

## Cómo arrancar

```powershell
cd c:\Users\hterrile\Documents\0github\gferreav4
streamlit run streamlit_app.py
```

Si quieres, el siguiente paso puede ser afinar la UI (parámetros editables sin Excel, gráficos por año, etc.).

---

**User**

todo lo que esta en escribir_excel.py debe ser escrito en el mismo excel que se subio, al cual al descargaserlo se le debe cambiar el nombre agregandole [FECHA HORA]. Ese excel tiene las hojas para escribir esos resultados. Además hay una función al final que debe ser refactorizado para escribir en se excel en la hoja 'Copia de Consolidado'  

---

**Cursor**


Revisando `escribir_excel.py` y `streamlit_app.py` para alinear la escritura con el Excel subido, el nombre de descarga con fecha/hora y refactorizar la función de 'Copia de Consolidado'.




Eliminando el bloque duplicado al final de `escribir_excel.py` y refactorizando: extrayendo el cálculo compartido de series y añadiendo `escribir_resultados_bytes` para que Streamlit escriba en el mismo libro subido y descargue con el nombre `[fecha hora]`.




Refactorizando `escribir_excel.py`: extrayendo el cálculo compartido de series, eliminando el bloque duplicado al final y añadiendo `escribir_resultados_bytes`. Actualizando `streamlit_app.py` para una sola descarga con timestamp.




Resumen de lo hecho:

## `escribir_excel.py`

1. **Cálculo único** — `_series_consolidado_desde_df(df_salida)` arma todas las series (año 0 y año 1+) que usan **consolidado2** y **Copia de Consolidado**, sin duplicar `calc_suma_producto` / `calc_min_carga_por_anio`.

2. **`_escribir_consolidado2`** — Solo escribe usando ese diccionario (columnas D–M y N como antes; K sigue sin datos = Costo PCT).

3. **`_escribir_copia_consolidado`** — Refactorizada: misma fuente de datos, tablas `_FILA_COPIA_OBRAS` y `_COL_CONSOLIDADO2_OBRAS` para mapear filas/columnas. Comportamiento equivalente al layout que tenías (B1, fila 7 años, D8–D10, E12–E29, etc.).

4. **Eliminado** el bloque suelto `escribir_resultados_gsheet` y el código tipo Google Sheets que estaba al final del archivo (era código suelto, no una función válida).

5. **`escribir_resultados_bytes(xlsx_bytes, df_salida, df_agregado)`** — Escribe en una copia temporal del **mismo** libro (bytes subidos), llama a `escribir_resultados` y devuelve el `.xlsx` completo en memoria.

6. **Imports** — Quitados `os` y `get_column_letter` (no se usaban).

## `streamlit_app.py`

- Tras calcular, genera el archivo con **`escribir_resultados_bytes`** (Tramos, Resumen Tramos, consolidado2, Copia de Consolidado).
- Un solo botón de descarga con nombre  
  **`nombreOriginal_[YYYY-MM-DD_HH-MM-SS].xlsx`**  
  (fecha y hora local entre corchetes).
- Eliminado el checkbox de “plantilla” / segunda descarga.

Si quieres otro formato de fecha (por ejemplo solo `HHMMSS` o sin guiones por compatibilidad con algo externo), se puede ajustar en `_nombre_descarga`.

