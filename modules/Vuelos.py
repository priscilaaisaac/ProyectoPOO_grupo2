from datetime import datetime
from typing import Optional


class Vuelo:
    """
    Representa una operación de vuelo individual con cálculo autónomo
    de métricas operativas y temporales.
    """

    def __init__(
        self,
        aeropuerto_origen: str,
        aeropuerto_destino: str,
        fechayhora_origen: datetime,
        fechayhora_destino: datetime,
        fechayhora_origen_estipulado: datetime,
        fechayhora_destino_estipulado: datetime,
        estado: str,
        capacidad_maxima_avion: int,
        capacidad_usada_avion: int,
        precio: Optional[float] = None,
        id_vuelo: Optional[str] = None,
        origen: Optional[str] = None,
        destino: Optional[str] = None,
    ):
        # Identificadores y ubicaciones
        self.id_vuelo = id_vuelo
        self.aeropuerto_origen = aeropuerto_origen
        self.aeropuerto_destino = aeropuerto_destino
        self.origen = origen
        self.destino = destino

        # Fechas y tiempos (reales y estipulados)
        self.fechayhora_origen = fechayhora_origen
        self.fechayhora_destino = fechayhora_destino
        self.fechayhora_origen_estipulado = fechayhora_origen_estipulado
        self.fechayhora_destino_estipulado = fechayhora_destino_estipulado

        # Capacidades y estado
        self.estado = estado
        self.capacidad_maxima_avion = int(capacidad_maxima_avion)
        self.capacidad_usada_avion = int(capacidad_usada_avion)

        # Variables comerciales
        self.precio = float(precio) if precio is not None else None

    # ----------------------------------------------------------------------
    # Cálculos Autónomos de Duración (REQ-06)
    # ----------------------------------------------------------------------

    def calcular_duracion_estipulada_minutos(self) -> float:
        """Calcula la duración programada del vuelo en minutos."""
        diferencia = self.fechayhora_destino_estipulado - self.fechayhora_origen_estipulado
        return max(0.0, diferencia.total_seconds() / 60.0)

    def calcular_duracion_real_minutos(self) -> Optional[float]:
        """Calcula la duración efectiva del vuelo en minutos si completó el trayecto."""
        if not self.fechayhora_origen or not self.fechayhora_destino:
            return None
        diferencia = self.fechayhora_destino - self.fechayhora_origen
        return max(0.0, diferencia.total_seconds() / 60.0)

    # ----------------------------------------------------------------------
    # Cálculos Autónomos de Retraso (REQ-06)
    # ----------------------------------------------------------------------

    def calcular_retraso_salida_minutos(self) -> float:
        """
        Retorna los minutos de demora al momento del despegue respecto
        a la hora estipulada. Si despegó a tiempo o antes, retorna 0.
        """
        if not self.fechayhora_origen or not self.fechayhora_origen_estipulado:
            return 0.0
        demora = self.fechayhora_origen - self.fechayhora_origen_estipulado
        return max(0.0, demora.total_seconds() / 60.0)

    def calcular_retraso_llegada_minutos(self) -> float:
        """
        Retorna los minutos de demora al aterrizar respecto
        a la hora estipulada. Si aterrizó a tiempo o antes, retorna 0.
        """
        if not self.fechayhora_destino or not self.fechayhora_destino_estipulado:
            return 0.0
        demora = self.fechayhora_destino - self.fechayhora_destino_estipulado
        return max(0.0, demora.total_seconds() / 60.0)

    def es_retrasado(self, umbral_tolerancia_minutos: float = 15.0) -> bool:
        """Evalúa si el vuelo incurrió en retraso de llegada superando el margen admisible."""
        return self.calcular_retraso_llegada_minutos() > umbral_tolerancia_minutos

    # ----------------------------------------------------------------------
    # Métricas Operativas Adicionales
    # ----------------------------------------------------------------------

    def calcular_factor_ocupacion(self) -> float:
        """Retorna el porcentaje (0 a 100) de ocupación de asientos en la aeronave."""
        if self.capacidad_maxima_avion <= 0:
            return 0.0
        return (self.capacidad_usada_avion / self.capacidad_maxima_avion) * 100.0

    def calcular_ingresos_estimados(self) -> Optional[float]:
        """Calcula el ingreso total generado por pasajes vendidos si existe precio."""
        if self.precio is None:
            return None
        return self.precio * self.capacidad_usada_avion

    def __repr__(self) -> str:
        identificador = self.id_vuelo if self.id_vuelo else "Sin ID"
        return f"<Vuelo {identificador}: {self.aeropuerto_origen} -> {self.aeropuerto_destino} | Estado: {self.estado}>"