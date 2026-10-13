import pandas as pd
from typing import List
from modules.Vuelos import Vuelo


class FabricaVuelos:
    """Construye colecciones de objetos Vuelo a partir de un DataFrame saneado."""

    @staticmethod
    def instanciar_desde_dataframe(df_limpio: pd.DataFrame, mapeo: dict) -> List[Vuelo]:
        """
        Convierte cada una de las filas del DataFrame en un objeto Vuelo.
        El atributo 'precio' es estrictamente obligatorio. Si algún registro no cuenta
        con un precio numérico válido, se lanza un ValueError bloqueando el proceso.
        """
        if df_limpio is None or df_limpio.empty:
            return []

        vuelos: List[Vuelo] = []
        df_trabajo = df_limpio.copy()

        # Aseguramos parseo de columnas temporales a objetos datetime reales
        cols_fecha = [
            "fechayhora_origen",
            "fechayhora_destino",
            "fechayhora_origen_estipulado",
            "fechayhora_destino_estipulado",
        ]

        for col_sistema in cols_fecha:
            col_real = mapeo.get(col_sistema)
            if col_real and col_real in df_trabajo.columns:
                df_trabajo[col_real] = pd.to_datetime(df_trabajo[col_real], errors="coerce")
            elif col_sistema in df_trabajo.columns:
                df_trabajo[col_sistema] = pd.to_datetime(df_trabajo[col_sistema], errors="coerce")

        for idx, fila in df_trabajo.iterrows():
            def obtener_valor(attr_sistema):
                col_real = mapeo.get(attr_sistema)
                if col_real and col_real != "(No asignar)" and col_real in df_trabajo.columns:
                    val = fila[col_real]
                elif attr_sistema in df_trabajo.columns:
                    val = fila[attr_sistema]
                else:
                    return None
                return None if pd.isna(val) else val

            precio_val = obtener_valor("precio")
            if precio_val is None or pd.isna(precio_val):
                id_v = obtener_valor("id_vuelo") or f"fila #{idx}"
                raise ValueError(
                    f"Error de instanciación en {id_v}: el registro no cuenta con un 'precio' válido. "
                    "El precio es estrictamente obligatorio para todos los objetos Vuelo."
                )

            try:
                precio_float = float(precio_val)
                if precio_float < 0:
                    raise ValueError(f"Precio negativo detectado ({precio_float})")
            except Exception as e:
                id_v = obtener_valor("id_vuelo") or f"fila #{idx}"
                raise ValueError(f"Error de precio en {id_v}: '{precio_val}' no es válido ({e})")

            # Parsing robusto de capacidades
            try:
                c_max = int(float(obtener_valor("capacidad_maxima_avion") or 0))
            except Exception:
                c_max = 0
            try:
                c_usada = int(float(obtener_valor("capacidad_usada_avion") or 0))
            except Exception:
                c_usada = 0

            vuelo = Vuelo(
                aeropuerto_origen=str(obtener_valor("aeropuerto_origen") or "Desconocido"),
                aeropuerto_destino=str(obtener_valor("aeropuerto_destino") or "Desconocido"),
                fechayhora_origen=obtener_valor("fechayhora_origen"),
                fechayhora_destino=obtener_valor("fechayhora_destino"),
                fechayhora_origen_estipulado=obtener_valor("fechayhora_origen_estipulado"),
                fechayhora_destino_estipulado=obtener_valor("fechayhora_destino_estipulado"),
                estado=str(obtener_valor("estado") or "Desconocido"),
                capacidad_maxima_avion=c_max,
                capacidad_usada_avion=c_usada,
                precio=precio_float,
                id_vuelo=str(obtener_valor("id_vuelo")) if obtener_valor("id_vuelo") is not None else None,
                origen=str(obtener_valor("origen")) if obtener_valor("origen") is not None else None,
                destino=str(obtener_valor("destino")) if obtener_valor("destino") is not None else None,
            )
            vuelos.append(vuelo)

        if len(vuelos) != len(df_trabajo):
            raise ValueError(
                f"Inconsistencia en la fábrica: se instanciaron {len(vuelos)} vuelos "
                f"de {len(df_trabajo)} registros procesados."
            )

        return vuelos