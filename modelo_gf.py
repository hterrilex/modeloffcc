"""
Modelo de Gestión Ferroviaria (GF) — v1
========================================
Módulo de cálculo puro, sin dependencias de Google Sheets ni Colab.

Punto de entrada principal:
    calcular(params, tablas, tramos) -> dict con df_salida y df_agregado

Estructura de parámetros:
    Ver ModeloParams y ModeloTablas más abajo.
"""

import pandas as pd
import numpy as np


# ==============================================================================
# UTILIDADES DE CONVERSIÓN
# ==============================================================================

def convert_param_type(value):
    """Convierte strings con '%', comas decimales, etc. al tipo Python correcto."""
    if isinstance(value, str):
        value = value.strip()
        if value.endswith('%'):
            try:
                return round(float(value[:-1].replace(',', '.')) / 100, 2)
            except ValueError:
                return value
        else:
            try:
                if '.' in value or ',' in value:
                    return float(value.replace(',', '.'))
                else:
                    return int(value)
            except ValueError:
                return value
    return value


# ==============================================================================
# FUNCIONES DE LOOKUP
# ==============================================================================

def get_velocidad_y_valor_trocha(tipo_via, vida_util_porc, tipo_trocha, vel_carga_dict):
    """
    Retorna (velocidad, carga_x_eje) según el tipo de vía, % vida útil y trocha.
    """
    for key, value in vel_carga_dict.items():
        tipo, desde, hasta = key
        try:
            desde_num = float(desde)
            hasta_num = float(hasta)
        except ValueError:
            continue
        if (tipo_via == tipo) and (desde_num < vida_util_porc <= hasta_num):
            velocidad = value['velocidad']
            valor_trocha = value.get(tipo_trocha, None)
            return velocidad, valor_trocha
    return None, None


def get_costo_obra(costo_obra_dict, tipo_via, obra, tipo_trocha):
    """Retorna el costo de una obra según tipo de vía, tipo de obra y trocha."""
    return costo_obra_dict[(tipo_via, obra)][tipo_trocha]


def get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte):
    """Limita la carga útil al tope de capacidad de transporte."""
    return min(carga_util_teorica, tope_capacidad_transporte)


def get_costo_desvio(carga_util_proyectada, flag, incremento_cap_dict, valor_primera_renovacion, anio):
  """
  Busca en el diccionario incremento_cap_dict el rango de carga útil proyectada
  y devuelve el valor asociado a la clave 'long'.

  Args:
    incremento_cap_dict: Diccionario con información de incremento de capacidad,
                         indexado por un valor que representa un punto de corte.
                         Cada valor asociado a la clave debe ser un diccionario
                         con al menos las claves 'ton_anio' y 'long'.
                         Se espera que 'ton_anio' esté ordenado de forma ascendente
                         por la clave del diccionario principal.
    carga_util_proyectada: La carga útil proyectada (valor numérico) para buscar.

  Returns:
    El valor de 'long' asociado al rango donde cae la carga_util_proyectada.
    Retorna 0 si la carga útil es menor que el primer rango o si no se encuentra
    ningún rango coincidente.
  """
  # Ordenar las claves del diccionario para iterar en el orden correcto de 'ton_anio'

  if flag == 99:
    return 0,98

  sorted_keys = sorted(incremento_cap_dict.keys())

  # Manejar el caso donde la carga proyectada es menor que el primer umbral
  if carga_util_proyectada < incremento_cap_dict[sorted_keys[0]]['ton_anio']:
      return 0,98

  costo_desvio1 = valor_primera_renovacion * 1.2 * 1 if anio > 0 else 0

  # Iterar a través de los rangos definidos en el diccionario
  for i in range(len(sorted_keys) - 1):
      lower_bound = incremento_cap_dict[sorted_keys[i]]['ton_anio']
      upper_bound = incremento_cap_dict[sorted_keys[i+1]]['ton_anio']

      # Verificar si la carga proyectada cae en el rango actual
      # (lower_bound <= carga_util_proyectada < upper_bound)
      if carga_util_proyectada > lower_bound and carga_util_proyectada <= upper_bound:
          desvio = incremento_cap_dict[sorted_keys[i]]['long']
          flg=i
          #print("1", carga_util_proyectada, flag, desvio, flg)
          #return desvio * costo_desvio1, i

  # Si la carga proyectada es mayor o igual al último umbral,
  # devolver el 'long' asociado al último rango
  if carga_util_proyectada > incremento_cap_dict[sorted_keys[-1]]['ton_anio']:
      desvio = 0
      #incremento_cap_dict[sorted_keys[-1]]['long']
      flg=-1
      #print("2", carga_util_proyectada, flag, desvio, flg)
      #return desvio * costo_desvio1

  if flag != flg:
    desvio = desvio * costo_desvio1
    #print("3", carga_util_proyectada, flag, desvio, flg)
    return desvio, flg
  else:
    return 0, flag

  # Retornar 0 si no se encuentra un rango (debería cubrirse por los casos anteriores
  # si el diccionario está bien formado y cubre todos los casos, pero como fallback)

  return 0,98



# ==============================================================================
# CONSTRUCCIÓN DE DICCIONARIOS DESDE DataFrames
# (usados cuando los datos vienen desde archivos en vez de Google Sheets)
# ==============================================================================

def build_dicts_from_dataframes(
    df_costo_obra,
    df_vida_util,
    df_incremento_cap,
    df_vel_carga,
    df_costo_mantenimiento,
    df_costopct,
    df_pasosanivel
):
    """
    Construye todos los diccionarios de parámetros a partir de DataFrames.
    Cada DataFrame debe venir con los mismos nombres de columnas que
    el Google Sheet original.

    Retorna: dict con todas las tablas listas para usar en calcular().
    """
    def apply_convert(df):
        return df.map(convert_param_type)

    costo_obra_dict = apply_convert(df_costo_obra).set_index(
        ['tipo_inicial', 'tipo_obra']
    ).to_dict(orient='index')

    vida_util_dict = apply_convert(df_vida_util).set_index('tipo').to_dict(orient='index')

    incremento_cap_dict = apply_convert(df_incremento_cap).set_index('indice').to_dict(orient='index')

    vel_carga_dict = apply_convert(df_vel_carga).set_index(
        ['tipo', 'desde', 'hasta']
    ).to_dict(orient='index')

    costo_mantenimiento_dict = apply_convert(df_costo_mantenimiento).set_index('tipo').to_dict(orient='index')

    costopct_dict = apply_convert(df_costopct).set_index(df_costopct.columns[0]).to_dict(orient='index')

    pasosanivel_dict = apply_convert(df_pasosanivel).set_index('pasos a nivel').to_dict(orient='index')

    return {
        'costo_obra_dict': costo_obra_dict,
        'vida_util_dict': vida_util_dict,
        'incremento_cap_dict': incremento_cap_dict,
        'vel_carga_dict': vel_carga_dict,
        'costo_mantenimiento_dict': costo_mantenimiento_dict,
        'costopct_dict': costopct_dict,
        'pasosanivel_dict': pasosanivel_dict,
    }


# ==============================================================================
# CARGA DE VARIABLES DESDE DICCIONARIOS DE TABLAS
# ==============================================================================

def load_variables_tramo(tipo_via_inicio, tipo_trocha, consumo_vida_util_actual, tablas):
    """
    Dado el tipo de vía, trocha y consumo actual de un tramo,
    extrae todas las variables necesarias para el cálculo del loop anual.

    Retorna: dict con todas las variables del tramo.
    """
    costo_obra_dict       = tablas['costo_obra_dict']
    vida_util_dict        = tablas['vida_util_dict']
    incremento_cap_dict   = tablas['incremento_cap_dict']
    costo_mantenimiento_dict = tablas['costo_mantenimiento_dict']
    pasosanivel_dict      = tablas['pasosanivel_dict']

    v = {}  # variables del tramo

    # Capacidad máxima de transporte
    v['tope_capacidad_transporte'] = incremento_cap_dict[max(incremento_cap_dict.keys())]['ton_anio']

    # Vida útil
    v['vida_util_renovada'] = vida_util_dict['I']['vida_util']
    v['vida_util_actual']   = vida_util_dict[tipo_via_inicio]['vida_util']
    v['vida_util_mejorada'] = vida_util_dict[tipo_via_inicio]['vida_util']

    # Obra renovación
    v['valor_primera_renovacion']  = costo_obra_dict[(tipo_via_inicio, 'RENOV')][tipo_trocha]
    v['anios_obra_renovacion']     = costo_obra_dict[(tipo_via_inicio, 'RENOV')]['plazo_int']
    v['disparo_obra_renovacion']   = costo_obra_dict[(tipo_via_inicio, 'RENOV')]['momento_vida_util']
    v['rejuve_obra_renovacion']    = costo_obra_dict[(tipo_via_inicio, 'RENOV')]['rejuvenecimiento']
    v['repe_obra_renov']           = costo_obra_dict[(tipo_via_inicio, 'RENOV')]['limite_intervencion'] - 1

    # Obra mejoramiento 1
    v['valor_primer_mejoramiento1'] = costo_obra_dict[(tipo_via_inicio, 'MEJOR1')][tipo_trocha]
    v['anios_obra_mejoramiento1']   = costo_obra_dict[(tipo_via_inicio, 'MEJOR1')]['plazo_int']
    v['disparo_obra_mejoramiento1'] = costo_obra_dict[(tipo_via_inicio, 'MEJOR1')]['momento_vida_util']
    v['rejuve_obra_mejoramiento1']  = costo_obra_dict[(tipo_via_inicio, 'MEJOR1')]['rejuvenecimiento']
    v['repe_obra_mejor1']           = costo_obra_dict[(tipo_via_inicio, 'MEJOR1')]['limite_intervencion'] - 1

    # Obra mejoramiento 2
    v['valor_primer_mejoramiento2'] = costo_obra_dict[(tipo_via_inicio, 'MEJOR2')][tipo_trocha]
    v['anios_obra_mejoramiento2']   = costo_obra_dict[(tipo_via_inicio, 'MEJOR2')]['plazo_int']
    v['disparo_obra_mejoramiento2'] = costo_obra_dict[(tipo_via_inicio, 'MEJOR2')]['momento_vida_util']
    v['rejuve_obra_mejoramiento2']  = costo_obra_dict[(tipo_via_inicio, 'MEJOR2')]['rejuvenecimiento']
    v['repe_obra_mejor2']           = costo_obra_dict[(tipo_via_inicio, 'MEJOR2')]['limite_intervencion'] - 1

    # Mantenimiento
    v['costo_fijo_conservacion'] = costo_mantenimiento_dict['FIJO'][tipo_trocha]
    v['costo_manten_inicial']    = costo_mantenimiento_dict[tipo_via_inicio][tipo_trocha]
    v['carga_ref_manten']        = costo_mantenimiento_dict[tipo_via_inicio]['carga_ref']
    v['tope_inicial_manten']     = costo_mantenimiento_dict[tipo_via_inicio]['tope']
    v['crec_manten']             = costo_mantenimiento_dict[tipo_via_inicio]['crec']

    v['mantenimiento_renovacion'] = costo_mantenimiento_dict['I'][tipo_trocha]
    v['carga_ref_renov']          = costo_mantenimiento_dict['I']['carga_ref']
    v['tope_inicial_renov']       = costo_mantenimiento_dict['I']['tope']
    v['crec_renov']               = costo_mantenimiento_dict['I']['crec']

    # Pasos a nivel
    v['carga_ref_pan1'] = pasosanivel_dict['Carga de Referencia <Ref 1']['carga_referencia']
    v['carga_ref_pan2'] = pasosanivel_dict['Carga de Referencia entre']['carga_referencia']
    v['cubi_pan1']      = pasosanivel_dict['Carga de Referencia <Ref 1']['cubi']
    v['cubi_pan2']      = pasosanivel_dict['Carga de Referencia entre']['cubi']
    v['cubi_pan3']      = pasosanivel_dict['Carga de Referencia >Ref 1']['cubi']

    # Estado inicial del tramo
    v['consumo_vida_util']  = vida_util_dict[tipo_via_inicio]['vida_util']
    v['vida_util_porc']     = consumo_vida_util_actual
    v['vida_util_resto']    = v['vida_util_actual'] * (1 - consumo_vida_util_actual)

    return v


# ==============================================================================
# CÁLCULO DE UN TRAMO — LOOP ANUAL
# ==============================================================================

def calcular_tramo(tramo, params, tablas):
    """
    Calcula la evolución de un tramo durante todo el horizonte del negocio.

    Args:
        tramo  : dict con los campos del tramo (id_tramo, tipo_via_inicio, etc.)
        params : dict con variables globales del modelo (duracion_anios_negocio,
                 crec_factor_inicial, periodo_anios_crec_inicial, crec_factor_final)
        tablas : dict con los diccionarios de parámetros técnicos

    Retorna: list de dicts, uno por año.
    """
    # -- Datos del tramo --
    id_tramo              = tramo['id_tramo']
    consumo_vida_util_actual = tramo['consumo_vida_util_actual']
    tipo_via_inicio       = tramo['tipo_via_inicio']
    carga_util_teorica    = tramo['carga_util_teorica'] / 1000
    tipo_trocha           = tramo['tipo_trocha']
    barreras              = tramo['barreras']
    long_tramo            = tramo['long_tramo']
    linea                 = tramo.get('linea', '')
    operador              = tramo.get('operador', '')
    division              = tramo.get('division', '')
    desde_km              = tramo.get('desde_km', 0)
    hasta_km              = tramo.get('hasta_km', 0)
    tipo_serv             = tramo.get('tipo_serv', '')

    # -- Variables globales del modelo --
    duracion_anios_negocio   = params.get('duracion_anios_negocio', 40)
    crec_factor_inicial      = params['crec_factor_inicial']
    periodo_anios_crec_inicial = params['periodo_anios_crec_inicial']
    crec_factor_final        = params['crec_factor_final']

    # -- Variables derivadas de tablas para este tramo --
    v = load_variables_tramo(tipo_via_inicio, tipo_trocha, consumo_vida_util_actual, tablas)

    tope_capacidad_transporte = v['tope_capacidad_transporte']
    vida_util_renovada        = v['vida_util_renovada']
    vida_util_mejorada        = v['vida_util_mejorada']
    consumo_vida_util         = v['consumo_vida_util']
    vida_util_porc            = v['vida_util_porc']
    vida_util_resto           = v['vida_util_resto']

    valor_primera_renovacion  = v['valor_primera_renovacion']
    anios_obra_renovacion     = v['anios_obra_renovacion']
    disparo_obra_renovacion   = v['disparo_obra_renovacion']
    rejuve_obra_renovacion    = v['rejuve_obra_renovacion']
    repe_obra_renov           = v['repe_obra_renov']

    valor_primer_mejoramiento1 = v['valor_primer_mejoramiento1']
    anios_obra_mejoramiento1   = v['anios_obra_mejoramiento1']
    disparo_obra_mejoramiento1 = v['disparo_obra_mejoramiento1']
    rejuve_obra_mejoramiento1  = v['rejuve_obra_mejoramiento1']
    repe_obra_mejor1           = v['repe_obra_mejor1']

    valor_primer_mejoramiento2 = v['valor_primer_mejoramiento2']
    anios_obra_mejoramiento2   = v['anios_obra_mejoramiento2']
    disparo_obra_mejoramiento2 = v['disparo_obra_mejoramiento2']
    rejuve_obra_mejoramiento2  = v['rejuve_obra_mejoramiento2']
    repe_obra_mejor2           = v['repe_obra_mejor2']

    costo_fijo_conservacion    = v['costo_fijo_conservacion']
    costo_manten_inicial       = v['costo_manten_inicial']
    carga_ref_manten           = v['carga_ref_manten']
    tope_inicial_manten        = v['tope_inicial_manten']
    crec_manten                = v['crec_manten']

    mantenimiento_renovacion   = v['mantenimiento_renovacion']
    carga_ref_renov            = v['carga_ref_renov']
    tope_inicial_renov         = v['tope_inicial_renov']
    crec_renov                 = v['crec_renov']

    carga_ref_pan1 = v['carga_ref_pan1']
    carga_ref_pan2 = v['carga_ref_pan2']
    cubi_pan1      = v['cubi_pan1']
    cubi_pan2      = v['cubi_pan2']
    cubi_pan3      = v['cubi_pan3']

    vel_carga_dict      = tablas['vel_carga_dict']
    incremento_cap_dict = tablas['incremento_cap_dict']
    costo_obra_dict     = tablas['costo_obra_dict']

    # -- Estado inicial de obra --
    obra = 0
    anios_obra_renov  = 0
    anios_obra_mejor1 = 0
    anios_obra_mejor2 = 0
    valor_obra        = 0
    anios_obra_rm     = 1

    marca_mejoramiento1 = ""
    marca_mejoramiento2 = ""
    marca_renovacion    = ""
    marca               = ""

    cant_obra_mejor1 = 0
    cant_obra_mejor2 = 0
    cant_obra_renov  = 0

    vida_util = v['vida_util_actual'] * consumo_vida_util_actual

    costo_desvio_aplicado = 0
    acum_obra             = 0
    costo_oper_infra_tramo = 0
    veloc                 = 0
    carga_eje             = 0
    costo_manten1         = 0
    costo_manten_renov    = 0
    costo_fijo            = 0
    flag_des              = 99

    # Sanitización longitud y barreras
    if long_tramo < 1:
        long_tramo = 1
    if barreras == 0 or (isinstance(barreras, float) and np.isnan(barreras)):
        barreras = 1

    salida_tramo = []

    for anio in range(0, duracion_anios_negocio + 1):

        # Tasa de crecimiento de la carga
        crecimiento = crec_factor_inicial if anio < periodo_anios_crec_inicial else crec_factor_final

        carga_util_proyectada = get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte)

        desvio = get_costo_desvio(
            carga_util_proyectada, flag_des, incremento_cap_dict,valor_primera_renovacion, anio)
        costo_desvio_aplicado = desvio[0]
        flag_des = desvio[1]

        # -- Clasificación del tipo de obra para la salida --
        if obra == 1:
            valor_obra_rn  = valor_obra
            anios_obra_rn  = anios_obra_rm
            valor_obra_mj  = 0
            anios_obra_mj  = 1
        elif obra == 2 or obra == 3:
            valor_obra_mj  = valor_obra
            anios_obra_mj  = anios_obra_rm
            valor_obra_rn  = 0
            anios_obra_rn  = 1
        else:
            valor_obra_rn  = 0
            valor_obra_mj  = 0
            anios_obra_rn  = 1
            anios_obra_mj  = 1

        salida_tramo.append({
            'id_tramo'    : id_tramo,
            'longitud'    : long_tramo,
            'tipo_trocha' : tipo_trocha,
            'tipo_via_inicio': tipo_via_inicio,
            'año'         : anio,
            'Carga útil teórica proyectada por año (q) (tn)': int(carga_util_teorica),
            'Carga proyectada por año (q) (tn) - LIMITADA'  : int(carga_util_proyectada),
            'Carga anual TN.KM'                             : round(float(carga_util_proyectada * long_tramo), 2),
            'Carga equiv. desde última intervención'        : int(vida_util),
            '% Vida útil consumida'                         : round(vida_util_porc, 2),
            'Obra de Renovación'                            : round(float(valor_obra_rn / anios_obra_rn), 2),
            'Obra de Mejoramiento'                          : round(float(valor_obra_mj / anios_obra_mj), 2),
            'Desvíos a construir'                           : round(float(costo_desvio_aplicado), 2),
            'Conservación costo fijo anual'                 : round(float(costo_fijo), 2),
            'Primer Tramo de Mantenimiento'                 : round(float(costo_manten1), 2),
            'Segundo Tramo de Mantenimiento'                : round(float(costo_manten_renov), 2),
            'Costo operación infraestructura del tramo'     : round(float(costo_oper_infra_tramo), 2),
            'Velocidad'   : int(veloc) if veloc else 0,
            'Carga x Eje' : int(carga_eje) if carga_eje else 0,
            'tipo_obra'   : int(obra),
            'marca'       : marca,
        })

        # -- Avance de carga y vida útil --
        carga_util_teorica = carga_util_teorica * (1 + crecimiento)
        vida_util          = vida_util + get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte)
        vida_util_porc     = vida_util / consumo_vida_util
        vida_util_resto    = vida_util_resto - get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte)

        # -- Reset de marcas --
        if marca in ("Comienzo Obra Mejoramiento", "Comienzo Obra Renovación",
                     "Comienzo Obra Mejoramiento 1", "Comienzo Obra Mejoramiento 2"):
            marca = ""
        if marca in ("Obra Finalizada", "Obra Renovación Finalizada"):
            anios_obra_rm = 1
            valor_obra    = 0
            marca         = ""

        # -- Lógica de obras --

        # Renovación
        if vida_util_porc >= disparo_obra_renovacion and cant_obra_renov <= repe_obra_renov and obra == 0:
            anios_obra_renov += 1
            marca = "Comienzo Obra Renovación"
            obra  = 1
            valor_obra    = valor_primera_renovacion
            anios_obra_rm = anios_obra_renovacion
            acum_obra     = valor_primera_renovacion / anios_obra_renovacion

        elif obra == 1 and anios_obra_renov >= anios_obra_renovacion:
            # Renovación completada → resetear vida útil
            vida_util       = get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte)
            vida_util_porc  = vida_util / consumo_vida_util
            vida_util_resto = vida_util_renovada - get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte)
            anios_obra_renov = 0
            cant_obra_renov += 1
            valor_obra      = 0
            obra            = 0
            marca           = "Obra Renovación Finalizada"
            tipo_via_inicio = 'I'
            consumo_vida_util = vida_util_renovada
            vida_util_porc  = vida_util / consumo_vida_util
            valor_primer_mejoramiento1 = get_costo_obra(costo_obra_dict, tipo_via_inicio, 'MEJOR1', tipo_trocha)
            valor_primer_mejoramiento2 = get_costo_obra(costo_obra_dict, tipo_via_inicio, 'MEJOR2', tipo_trocha)

        elif obra == 1 and anios_obra_renov < anios_obra_renovacion:
            marca = "... Sigue obra Renovación"
            anios_obra_renov += 1
            acum_obra = (valor_primera_renovacion / anios_obra_renovacion) * anios_obra_renov

        # Mejoramiento 1
        if vida_util_porc >= disparo_obra_mejoramiento1 and cant_obra_mejor1 <= repe_obra_mejor1 and obra == 0:
            anios_obra_mejor1 = 1
            marca = "Comienzo Obra Mejoramiento 1"
            obra  = 2
            valor_obra    = valor_primer_mejoramiento1
            anios_obra_rm = anios_obra_mejoramiento1

        elif obra == 2 and anios_obra_mejor1 >= anios_obra_mejoramiento1:
            vida_util = (
                (vida_util - get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte))
                * (1 - rejuve_obra_mejoramiento1)
                + get_carga_util_proyectada(carga_util_teorica, tope_capacidad_transporte)
            )
            vida_util_porc  = vida_util / consumo_vida_util
            vida_util_resto = vida_util_mejorada - vida_util
            obra            = 0
            anios_obra_mejor1 = 0
            cant_obra_mejor1 += 1
            valor_obra      = 0
            marca           = "Obra Finalizada"

        elif obra == 2 and anios_obra_mejor1 < anios_obra_mejoramiento1:
            anios_obra_mejor1 += 1
            marca = "... Sigue obra Mejoramiento 1"

        # Mejoramiento 2
        if vida_util_porc >= disparo_obra_mejoramiento2 and cant_obra_mejor2 <= repe_obra_mejor2 and obra == 0:
            anios_obra_mejor2 = 1
            marca = "Comienzo Obra Mejoramiento 2"
            obra  = 3
            valor_obra    = valor_primer_mejoramiento2
            anios_obra_rm = anios_obra_mejoramiento2

        elif obra == 3 and anios_obra_mejor2 >= anios_obra_mejoramiento2:
            vida_util = (
                (vida_util - carga_util_proyectada)
                * (1 - rejuve_obra_mejoramiento1)
                + carga_util_proyectada
            )
            vida_util_porc  = vida_util / consumo_vida_util
            vida_util_resto = vida_util_mejorada - vida_util
            obra            = 0
            anios_obra_mejor2 = 0
            cant_obra_mejor2 += 1
            valor_obra      = 0
            marca           = "Obra Finalizada"

        elif obra == 3 and anios_obra_mejor2 < anios_obra_mejoramiento2:
            anios_obra_mejor2 += 1
            marca = "... Sigue obra Mejoramiento 2"

        # -- Costo mantenimiento 1 --
        costo_manten1 = costo_manten_inicial * ((1 + crec_manten) ** (vida_util / carga_ref_manten))
        if costo_manten1 >= tope_inicial_manten:
            costo_manten1 = tope_inicial_manten
        if acum_obra > 0:
            costo_manten1 = costo_manten1 * ((valor_primera_renovacion - acum_obra) / valor_primera_renovacion)

        # -- Costo mantenimiento 2 (vía renovada) --
        if anios_obra_renov == 0 and acum_obra == 0:
            costo_manten_renov = 0
        elif anios_obra_renov > 0 and acum_obra > 0:
            factor_renov = acum_obra / valor_primera_renovacion
            costo_manten_renov = (
                mantenimiento_renovacion
                * ((1 + crec_renov) ** (carga_util_proyectada / carga_ref_renov))
                * factor_renov
            )
        elif anios_obra_renov == 0 and acum_obra > 0:
            factor_renov = acum_obra / valor_primera_renovacion
            costo_manten_renov = (
                mantenimiento_renovacion
                * ((1 + crec_renov) ** (vida_util / carga_ref_renov))
                * factor_renov
            )
        if costo_manten_renov > tope_inicial_renov:
            costo_manten_renov = tope_inicial_renov

        # -- Costo operación infraestructura (pasos a nivel) --
        if carga_util_proyectada < carga_ref_pan1:
            costo_infra_tramo = cubi_pan1
        elif carga_util_proyectada < carga_ref_pan2:
            costo_infra_tramo = cubi_pan2
        else:
            costo_infra_tramo = cubi_pan3

        costo_oper_infra_tramo = barreras * (costo_infra_tramo / long_tramo)
        costo_fijo = costo_fijo_conservacion

        # -- Velocidad y carga por eje --
        veltn     = get_velocidad_y_valor_trocha(tipo_via_inicio, vida_util_porc, tipo_trocha, vel_carga_dict)
        veloc     = veltn[0]
        carga_eje = veltn[1]

    return salida_tramo


# ==============================================================================
# FUNCIONES DE AGREGACIÓN DE SALIDA
# ==============================================================================

def calc_suma_simple_por_anio(df, campo_carga, hasta_anio=None):
    if hasta_anio is None:
        hasta_anio = df['año'].max()
    suma = df.groupby('año')[campo_carga].sum()
    full_index = pd.RangeIndex(start=0, stop=hasta_anio + 1, step=1, name='año')
    return suma.reindex(full_index, fill_value=0)


def calc_min_carga_por_anio(df, campo_carga, hasta_anio=None):
    if hasta_anio is None:
        hasta_anio = df['año'].max()
    mn = df.groupby('año')[campo_carga].min()
    full_index = pd.RangeIndex(start=1, stop=hasta_anio + 1, step=1, name='año')
    return mn.reindex(full_index, fill_value=0)


def calc_suma_producto(df, campo_carga, desde_anio_1=True, por_longitud=True, hasta_anio=None):
    """
    Suma ponderada por longitud (o no) de un campo, año a año.

    desde_anio_1: si True, excluye el año 0.
    por_longitud : si True, multiplica por longitud (sin dividir por total).
                   si False, promedia ponderando por total de longitud.
    """
    if hasta_anio is None:
        hasta_anio = df['año'].max()
    longitud_total = df[df['año'] == 0]['longitud'].sum()

    if desde_anio_1:
        df_f = df[df['año'] > 0].copy()
        full_index = pd.RangeIndex(start=1, stop=hasta_anio + 1, step=1, name='año')
    else:
        df_f = df.copy()
        full_index = pd.RangeIndex(start=0, stop=hasta_anio + 1, step=1, name='año')

    if por_longitud:
        df_f = df_f.copy()
        df_f['_wx'] = df_f[campo_carga] * df_f['longitud']
    else:
        df_f = df_f.copy()
        df_f['_wx'] = (df_f[campo_carga] * df_f['longitud']) / longitud_total

    resultado = df_f.groupby('año')['_wx'].sum()
    return round(resultado.reindex(full_index, fill_value=0), 2)


def calcular_df_agregado(df_salida):
    """Genera el resumen por tramo (df_agregado) a partir de df_salida."""
    df_agregado = df_salida.groupby('id_tramo').agg({
        'Carga útil teórica proyectada por año (q) (tn)': ['sum', 'mean'],
        'Carga proyectada por año (q) (tn) - LIMITADA'  : ['sum', 'mean'],
        'Carga anual TN.KM'                             : ['sum', 'mean'],
        'Carga equiv. desde última intervención'        : ['sum', 'mean'],
        'Obra de Renovación'                            : ['sum', 'mean'],
        'Obra de Mejoramiento'                          : ['sum', 'mean'],
        'Desvíos a construir'                           : ['sum', 'mean'],
        'Conservación costo fijo anual'                 : ['sum', 'mean'],
        'Primer Tramo de Mantenimiento'                 : ['sum', 'mean'],
        'Segundo Tramo de Mantenimiento'                : ['sum', 'mean'],
        'Costo operación infraestructura del tramo'     : ['sum', 'mean'],
        'Velocidad'   : 'mean',
        'Carga x Eje' : 'mean',
    })
    df_agregado.columns = ['_'.join(col).strip() for col in df_agregado.columns.values]

    df_anio_cero = (
        df_salida[df_salida['año'] == 0]
        [['id_tramo', 'longitud', 'tipo_trocha', 'tipo_via_inicio']]
        .set_index('id_tramo')
    )
    df_anio_cero['id_tramo'] = df_anio_cero.index
    cols = ['id_tramo'] + [c for c in df_anio_cero.columns if c != 'id_tramo']
    df_anio_cero = df_anio_cero[cols]

    return df_anio_cero.join(df_agregado)


# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================

def calcular(params: dict, tablas: dict, df_tramos: pd.DataFrame) -> dict:
    """
    Ejecuta el modelo completo para todos los tramos.

    Args:
        params    : dict con variables globales del modelo.
                    Claves requeridas:
                      - duracion_anios_negocio (int, default 40)
                      - crec_factor_inicial    (float)
                      - periodo_anios_crec_inicial (int)
                      - crec_factor_final      (float)

        tablas    : dict generado por build_dicts_from_dataframes() con:
                      costo_obra_dict, vida_util_dict, incremento_cap_dict,
                      vel_carga_dict, costo_mantenimiento_dict, pasosanivel_dict

        df_tramos : DataFrame con el listado de tramos. Columnas requeridas:
                      id_tramo, consumo_vida_util_actual, tipo_via_inicio,
                      carga_util_teorica, tipo_trocha, barreras, long_tramo
                    Columnas opcionales: linea, operador, division,
                                         desde_km, hasta_km, tipo_serv

    Retorna:
        {
          'df_salida'   : DataFrame con un registro por tramo × año,
          'df_agregado' : DataFrame con resumen por tramo,
        }
    """
    # Normalización de tipos en df_tramos
    df_tramos = df_tramos.copy()
    df_tramos['tipo_trocha'] = df_tramos['tipo_trocha'].str.lower()
    df_tramos['carga_util_teorica'] = pd.to_numeric(
        df_tramos['carga_util_teorica'], errors='coerce'
    ).astype(int)

    salida = []
    total  = len(df_tramos)

    for i, (_, row) in enumerate(df_tramos.iterrows()):
        tramo_dict = row.to_dict()
        registros  = calcular_tramo(tramo_dict, params, tablas)
        salida.extend(registros)
        print(f"  Tramo {i+1}/{total} — {tramo_dict.get('id_tramo', '')} ✓")

    df_salida   = pd.DataFrame(salida)
    df_agregado = calcular_df_agregado(df_salida)

    return {
        'df_salida'   : df_salida,
        'df_agregado' : df_agregado,
    }
