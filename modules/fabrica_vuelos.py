import pandas as pd
from typing import List
from modules.Vuelos import Vuelo


class FabricaVuelos:
    """Construye colecciones de objetos Vuelo a partir de un DataFrame saneado."""

    @staticmethod
    def instanciar_desde_dataframe(df_limpio: pd.DataFrame, mapeo: dict) -> List[Vuelo]:
        vuelos: List[Vuelo] = []

        # Aseguramos parseo de columnas temporales a objetos datetime reales
        cols_fecha = [
            "fechayhora_origen",
            "fechayhora_destino",
            "fechayhora_origen_estipulado",
            "fechayhora_destino_estipulado",
        ]
        df_trabajo = df_limpio.copy()

        for col_sistema in cols_fecha:
            col_real = mapeo.get(col_sistema)
            if col_real and col_real in df_trabajo.columns:
                df_trabajo[col_real] = pd.to_datetime(df_trabajo[col_real], errors="coerce")

        for _, fila in df_trabajo.iterrows():
            def obtener_valor(attr_sistema):
                col_real = mapeo.get(attr_sistema)
                if not col_real or col_real == "(No asignar)" or col_real not in df_trabajo.columns:
                    return None
                val = fila[col_real]
                return None if pd.isna(val) else val

            vuelo = Vuelo(
                aeropuerto_origen=str(obtener_valor("aeropuerto_origen")),
                aeropuerto_destino=str(obtener_valor("aeropuerto_destino")),
                fechayhora_origen=obtener_valor("fechayhora_origen"),
                fechayhora_destino=obtener_valor("fechayhora_destino"),
                fechayhora_origen_estipulado=obtener_valor("fechayhora_origen_estipulado"),
                fechayhora_destino_estipulado=obtener_valor("fechayhora_destino_estipulado"),
                estado=str(obtener_valor("estado")),
                capacidad_maxima_avion=obtener_valor("capacidad_maxima_avion") or 0,
                capacidad_usada_avion=obtener_valor("capacidad_usada_avion") or 0,
                precio=obtener_valor("precio"),
                id_vuelo=str(obtener_valor("id_vuelo")) if obtener_valor("id_vuelo") else None,
                origen=str(obtener_valor("origen")) if obtener_valor("origen") else None,
                destino=str(obtener_valor("destino")) if obtener_valor("destino") else None,
            )
            vuelos.append(vuelo)

        return vuelos