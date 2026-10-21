"""
Suite exhaustiva de pruebas unitarias para el paquete de Análisis Estadístico
y Simulación de Precios (modules.Estadistica).

Cumple estrictamente con:
- Aislamiento absoluto (sin acceso a disco ni archivos físicos).
- Exclusión total de UI y dependencias de Streamlit.
- Cobertura integral (>= 70%, buscando >= 95%): casos normales, casos borde (n=0,
  colecciones mínimas, divisiones por cero, 100% nulos/desconocidos) y manejo de errores.
"""

from datetime import datetime
from unittest.mock import MagicMock
import pytest
import pandas as pd
from typing import List, Dict, Any, Optional

from modules.Vuelos import Vuelo
from modules.Estadistica.motor_analisis_base import MotorAnalisisBase
from modules.Estadistica.motor_estadistico_descriptivo import (
    MotorEstadisticoDescriptivo,
    MotorEstadisticoVuelos,
)
from modules.Estadistica.simulador_precios import SimuladorPreciosDinamicos


# =====================================================================
# Fixtures y Funciones Auxiliares en Memoria
# =====================================================================

def crear_vuelo_dummy(
    id_vuelo: str = "FL-001",
    aeropuerto_origen: str = "EZE",
    aeropuerto_destino: str = "MIA",
    fechayhora_origen: Optional[datetime] = datetime(2026, 10, 21, 8, 30),
    fechayhora_destino: Optional[datetime] = datetime(2026, 10, 21, 14, 30),
    fechayhora_origen_estipulado: Optional[datetime] = datetime(2026, 10, 21, 8, 30),
    fechayhora_destino_estipulado: Optional[datetime] = datetime(2026, 10, 21, 14, 30),
    estado: str = "A tiempo",
    capacidad_maxima_avion: int = 200,
    capacidad_usada_avion: int = 150,
    precio: float = 100.0,
    origen: Optional[str] = "Buenos Aires",
    destino: Optional[str] = "Miami",
) -> Vuelo:
    """Crea una instancia en memoria de Vuelo con parámetros controlados."""
    return Vuelo(
        aeropuerto_origen=aeropuerto_origen,
        aeropuerto_destino=aeropuerto_destino,
        fechayhora_origen=fechayhora_origen,
        fechayhora_destino=fechayhora_destino,
        fechayhora_origen_estipulado=fechayhora_origen_estipulado,
        fechayhora_destino_estipulado=fechayhora_destino_estipulado,
        estado=estado,
        capacidad_maxima_avion=capacidad_maxima_avion,
        capacidad_usada_avion=capacidad_usada_avion,
        precio=precio,
        id_vuelo=id_vuelo,
        origen=origen,
        destino=destino,
    )


class MotorAnalisisConcretoStub(MotorAnalisisBase):
    """Subclase mínima concreta para probar MotorAnalisisBase de forma aislada."""

    def calcular_metricas_segmento(
        self,
        ruta: Optional[str] = None,
        franja: Optional[str] = None,
        ocupacion: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {"stub": True, "total": len(self.filtrar_vuelos(ruta, franja, ocupacion))}


@pytest.fixture
def coleccion_vuelos_diversos() -> List[Vuelo]:
    """
    Retorna un conjunto representativo de vuelos con distintas rutas,
    franjas horarias, niveles de ocupación y estados operativos.
    """
    return [
        # Vuelo 1: Madrugada, EZE -> MAD, Ocupación 85% (Alta), A tiempo
        crear_vuelo_dummy(
            id_vuelo="FL-001",
            aeropuerto_origen="EZE",
            aeropuerto_destino="MAD",
            fechayhora_origen_estipulado=datetime(2026, 10, 21, 3, 0),
            fechayhora_origen=datetime(2026, 10, 21, 3, 0),
            estado="A tiempo",
            capacidad_maxima_avion=200,
            capacidad_usada_avion=170,  # 85%
            precio=500.0,
        ),
        # Vuelo 2: Mañana, EZE -> MIA, Ocupación 60% (Media), Atrasado
        crear_vuelo_dummy(
            id_vuelo="FL-002",
            aeropuerto_origen="EZE",
            aeropuerto_destino="MIA",
            fechayhora_origen_estipulado=datetime(2026, 10, 21, 9, 0),
            fechayhora_origen=datetime(2026, 10, 21, 9, 30),
            estado="Atrasado",
            capacidad_maxima_avion=200,
            capacidad_usada_avion=120,  # 60%
            precio=300.0,
        ),
        # Vuelo 3: Tarde, COR -> BRC, Ocupación 40% (Baja), Cancelado
        crear_vuelo_dummy(
            id_vuelo="FL-003",
            aeropuerto_origen="COR",
            aeropuerto_destino="BRC",
            fechayhora_origen_estipulado=datetime(2026, 10, 21, 15, 0),
            fechayhora_origen=None,
            fechayhora_destino=None,
            estado="Cancelado",
            capacidad_maxima_avion=100,
            capacidad_usada_avion=40,  # 40%
            precio=150.0,
        ),
        # Vuelo 4: Noche, EZE -> MIA, Ocupación 90% (Alta), Exitoso
        crear_vuelo_dummy(
            id_vuelo="FL-004",
            aeropuerto_origen="EZE",
            aeropuerto_destino="MIA",
            fechayhora_origen_estipulado=datetime(2026, 10, 21, 22, 0),
            fechayhora_origen=datetime(2026, 10, 21, 22, 0),
            estado="Exitoso",
            capacidad_maxima_avion=250,
            capacidad_usada_avion=225,  # 90%
            precio=400.0,
        ),
        # Vuelo 5: Desconocido en origen/destino y sin horario para verificar filtrados extremos
        crear_vuelo_dummy(
            id_vuelo="FL-005",
            aeropuerto_origen="Desconocido",
            aeropuerto_destino="MIA",
            fechayhora_origen_estipulado=None,
            fechayhora_origen=None,
            origen=None,
            destino=None,
            estado="Desconocido",
            capacidad_maxima_avion=100,
            capacidad_usada_avion=50,
            precio=100.0,
        ),
    ]


# =====================================================================
# 1. Pruebas para MotorAnalisisBase
# =====================================================================

class TestMotorAnalisisBase:
    """Pruebas del contrato base, colecciones, filtrados y casos borde."""

    def test_no_permite_instanciacion_directa_clase_abstracta(self):
        """Verifica que MotorAnalisisBase es abstracta pura y no se instancia directamente."""
        with pytest.raises(TypeError):
            MotorAnalisisBase([crear_vuelo_dummy()])

    def test_rechaza_coleccion_vacia_de_vuelos(self):
        """No se puede inicializar el motor con lista vacía."""
        with pytest.raises(ValueError, match="No se puede inicializar el motor estadístico con una colección vacía"):
            MotorAnalisisConcretoStub([])

    def test_inicializacion_correcta(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        assert motor.total_vuelos == 5
        assert len(motor.vuelos) == 5

    def test_obtener_rutas_disponibles_excluye_desconocido(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        rutas = motor.obtener_rutas_disponibles()
        # Debe contener las rutas válidas ordenadas
        assert "COR -> BRC" in rutas
        assert "EZE -> MAD" in rutas
        assert "EZE -> MIA" in rutas
        # La ruta del Vuelo 5 contiene 'Desconocido' y no debe figurar
        assert not any("desconocido" in r.lower() for r in rutas)
        assert rutas == sorted(rutas)

    def test_obtener_franjas_disponibles(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        franjas = motor.obtener_franjas_disponibles()
        assert len(franjas) == 4
        assert "Madrugada (00:00 - 06:00)" in franjas
        assert "Mañana (06:00 - 12:00)" in franjas
        assert "Tarde (12:00 - 18:00)" in franjas
        assert "Noche (18:00 - 24:00)" in franjas

    def test_obtener_ocupaciones_disponibles(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        ocupaciones = motor.obtener_ocupaciones_disponibles()
        assert ocupaciones == ["Baja (< 50%)", "Media (50% - 80%)", "Alta (> 80%)"]

    def test_filtrar_vuelos_sin_filtros_retorna_todos(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        res = motor.filtrar_vuelos()
        assert len(res) == 5

        res_sentinels = motor.filtrar_vuelos(
            ruta="Todas las rutas",
            franja="Todas las franjas",
            ocupacion="Cualquier ocupación"
        )
        assert len(res_sentinels) == 5

    def test_filtrar_vuelos_por_ruta(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        res = motor.filtrar_vuelos(ruta="EZE -> MIA")
        assert len(res) == 2
        assert all(v.obtener_ruta() == "EZE -> MIA" for v in res)

    def test_filtrar_vuelos_por_franja(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        res = motor.filtrar_vuelos(franja="Mañana (06:00 - 12:00)")
        assert len(res) == 1
        assert res[0].id_vuelo == "FL-002"

    def test_filtrar_vuelos_por_ocupacion(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        res_alta = motor.filtrar_vuelos(ocupacion="Alta (> 80%)")
        assert len(res_alta) == 2  # FL-001 (85%) y FL-004 (90%)

        res_baja = motor.filtrar_vuelos(ocupacion="Baja (< 50%)")
        assert len(res_baja) == 1
        assert res_baja[0].id_vuelo == "FL-003"

    def test_filtrar_vuelos_combinado(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        res = motor.filtrar_vuelos(
            ruta="EZE -> MIA",
            franja="Noche (18:00 - 24:00)",
            ocupacion="Alta (> 80%)"
        )
        assert len(res) == 1
        assert res[0].id_vuelo == "FL-004"

    def test_filtrar_vuelos_sin_coincidencias_retorna_lista_vacia(self, coleccion_vuelos_diversos):
        motor = MotorAnalisisConcretoStub(coleccion_vuelos_diversos)
        res = motor.filtrar_vuelos(ruta="RUTA -> INEXISTENTE")
        assert res == []


# =====================================================================
# 2. Pruebas para MotorEstadisticoDescriptivo (Marginales y Condicionales)
# =====================================================================

class TestMotorEstadisticoDescriptivo:
    """Pruebas del motor estadístico descriptivo: probabilidades marginales, tablas y métricas."""

    def test_calcular_conteos_marginales(self, coleccion_vuelos_diversos):
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        conteos = motor.calcular_conteos_marginales()
        assert conteos == {
            "Atrasado": 1,
            "A tiempo": 1,
            "Exitoso": 1,
            "Cancelado": 1,
        }

    def test_calcular_probabilidades_marginales_normales(self, coleccion_vuelos_diversos):
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        probs = motor.calcular_probabilidades_marginales()
        # Hay 4 válidos en total (1 de cada uno), cada uno debe ser 0.25
        assert probs["Atrasado"] == pytest.approx(0.25)
        assert probs["A tiempo"] == pytest.approx(0.25)
        assert probs["Exitoso"] == pytest.approx(0.25)
        assert probs["Cancelado"] == pytest.approx(0.25)
        assert sum(probs.values()) == pytest.approx(1.0)

    def test_calcular_probabilidades_marginales_sin_validos(self):
        """Caso borde: todos los vuelos tienen estado Desconocido (total_validos == 0)."""
        vuelo_desconocido = crear_vuelo_dummy(estado="Desconocido")
        motor = MotorEstadisticoDescriptivo([vuelo_desconocido])
        probs = motor.calcular_probabilidades_marginales()
        assert probs == {
            "Atrasado": 0.0,
            "A tiempo": 0.0,
            "Exitoso": 0.0,
            "Cancelado": 0.0,
        }

    def test_generar_tabla_condicional_vacia_si_todo_es_desconocido(self):
        """Caso borde: si la función de dimensión retorna 'Desconocido' para todos los vuelos."""
        vuelo = crear_vuelo_dummy(aeropuerto_origen="Desconocido", aeropuerto_destino="Desconocido")
        motor = MotorEstadisticoDescriptivo([vuelo])
        df_res = motor.calcular_probabilidades_condicionales_ruta()
        assert isinstance(df_res, pd.DataFrame)
        assert df_res.empty

    def test_calcular_probabilidades_condicionales_franja(self, coleccion_vuelos_diversos):
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        df_franja = motor.calcular_probabilidades_condicionales_franja()

        assert not df_franja.empty
        assert "Franja Horaria" in df_franja.columns
        assert "Total Vuelos" in df_franja.columns
        assert "% Atrasado" in df_franja.columns
        assert "% A tiempo" in df_franja.columns
        assert "% Exitoso" in df_franja.columns
        assert "% Cancelado" in df_franja.columns
        assert "Precio Promedio ($)" in df_franja.columns
        assert "Ocupación Media (%)" in df_franja.columns

        # Debe estar ordenado descendentemente por Total Vuelos
        totales = list(df_franja["Total Vuelos"])
        assert totales == sorted(totales, reverse=True)

    def test_calcular_probabilidades_condicionales_ruta(self, coleccion_vuelos_diversos):
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        df_ruta = motor.calcular_probabilidades_condicionales_ruta()

        assert not df_ruta.empty
        assert "Ruta" in df_ruta.columns
        # EZE -> MIA tiene 2 vuelos, debe figurar primero
        assert df_ruta["Ruta"].iloc[0] == "EZE -> MIA"
        assert df_ruta["Total Vuelos"].iloc[0] == 2
        # Precios: 300 y 400 -> promedio = 350.0
        assert df_ruta["Precio Promedio ($)"].iloc[0] == pytest.approx(350.0)

    def test_calcular_probabilidades_condicionales_ocupacion(self, coleccion_vuelos_diversos):
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        df_ocup = motor.calcular_probabilidades_condicionales_ocupacion()

        assert not df_ocup.empty
        assert "Nivel de Ocupación" in df_ocup.columns
        # 'Alta (> 80%)' tiene 2 vuelos (85% y 90%)
        fila_alta = df_ocup[df_ocup["Nivel de Ocupación"] == "Alta (> 80%)"].iloc[0]
        assert fila_alta["Total Vuelos"] == 2
        assert fila_alta["Ocupación Media (%)"] == pytest.approx(87.5, 0.1)

    def test_calcular_metricas_segmento_muestra_vacia(self, coleccion_vuelos_diversos):
        """Caso borde: filtro sin vuelos coincidentes (n=0)."""
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        metricas = motor.calcular_metricas_segmento(ruta="RUTA -> INEXISTENTE")

        assert metricas["muestra_tamano"] == 0
        assert metricas["es_estimacion_global"] is True
        assert metricas["p_atrasado"] == 0.0
        assert metricas["p_cancelado"] == 0.0
        assert metricas["p_atiempo"] == 0.0
        assert metricas["p_exitoso"] == 0.0
        assert metricas["precio_promedio"] == 0.0
        assert metricas["ocupacion_promedio"] == 0.0
        assert metricas["capacidad_maxima_media"] == 0
        assert metricas["capacidad_usada_media"] == 0

    def test_calcular_metricas_segmento_muestra_valida(self, coleccion_vuelos_diversos):
        """Camino feliz: cálculo de probabilidades condicionales y promedios en segmento."""
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        # Filtramos por EZE -> MIA (Vuelos FL-002 y FL-004)
        # FL-002: Atrasado, precio 300, ocupacion 60%, cap_max 200, cap_usada 120
        # FL-004: Exitoso, precio 400, ocupacion 90%, cap_max 250, cap_usada 225
        metricas = motor.calcular_metricas_segmento(ruta="EZE -> MIA")

        assert metricas["muestra_tamano"] == 2
        assert metricas["es_estimacion_global"] is False
        assert metricas["p_atrasado"] == pytest.approx(0.5)
        assert metricas["p_exitoso"] == pytest.approx(0.5)
        assert metricas["p_atiempo"] == 0.0
        assert metricas["p_cancelado"] == 0.0
        assert metricas["precio_promedio"] == pytest.approx(350.0)
        assert metricas["ocupacion_promedio"] == pytest.approx(75.0)
        assert metricas["capacidad_maxima_media"] == 225  # (200 + 250) // 2
        assert metricas["capacidad_usada_media"] == 172   # int((120 + 225) / 2) = int(172.5) = 172

    def test_alias_retrocompatibilidad_motor_estadistico_vuelos(self):
        """Verifica que MotorEstadisticoVuelos es alias idéntico de MotorEstadisticoDescriptivo."""
        assert MotorEstadisticoVuelos is MotorEstadisticoDescriptivo


# =====================================================================
# 3. Pruebas para SimuladorPreciosDinamicos
# =====================================================================

class TestSimuladorPreciosDinamicos:
    """Pruebas del simulador comercial con DIP, cálculo de riesgo, demanda y márgenes."""

    def test_inicializacion_recibe_motor_base_dip(self, coleccion_vuelos_diversos):
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        simulador = SimuladorPreciosDinamicos(motor)
        assert simulador.motor is motor

    def test_simulacion_con_precio_historico_y_demanda_alta(self):
        """
        Escenario con ocupación >= 80% (+12% demanda),
        con riesgo logístico de atraso (25%) y cancelación (60%).
        """
        mock_motor = MagicMock(spec=MotorAnalisisBase)
        mock_motor.calcular_metricas_segmento.return_value = {
            "muestra_tamano": 10,
            "es_estimacion_global": False,
            "p_atrasado": 0.20,
            "p_cancelado": 0.10,
            "p_atiempo": 0.50,
            "p_exitoso": 0.20,
            "precio_promedio": 100.0,
            "ocupacion_promedio": 85.0,  # >= 80 -> factor_demanda = +0.12
            "capacidad_maxima_media": 200,
            "capacidad_usada_media": 170,
        }

        simulador = SimuladorPreciosDinamicos(mock_motor)
        res = simulador.simular(
            costo_retraso_pct=0.25,
            costo_cancelacion_pct=0.60,
            margen_comercial_pct=0.10,
        )

        # 1. Riesgo logístico: 0.20 * 0.25 + 0.10 * 0.60 = 0.05 + 0.06 = 0.11 (11%)
        assert res["riesgo_logistico_pct"] == pytest.approx(11.0)
        assert res["recargo_riesgo_monetario"] == pytest.approx(11.0)  # 100 * 0.11

        # 2. Demanda alta (+12%)
        assert res["etiqueta_demanda"] == "Alta demanda (+12%)"

        # 3. Precio final sugerido:
        # base (100) * (1 + 0.11) = 111.0
        # 111.0 * (1 + 0.12) = 124.32
        # 124.32 * (1 + 0.10) = 136.752 -> round 136.75
        assert res["precio_sugerido"] == pytest.approx(136.75, 0.02)
        assert res["tipo_precio_base"] == "Promedio histórico del segmento"
        assert res["asientos_ocupados_media"] == 170
        assert res["ingreso_base_vuelo"] == pytest.approx(17000.0)
        assert res["fondo_contingencia_vuelo"] == pytest.approx(11.0 * 170)

    def test_simulacion_con_demanda_baja(self):
        """Escenario con ocupación < 50% (-8% descuento promocional)."""
        mock_motor = MagicMock(spec=MotorAnalisisBase)
        mock_motor.calcular_metricas_segmento.return_value = {
            "muestra_tamano": 5,
            "es_estimacion_global": False,
            "p_atrasado": 0.0,
            "p_cancelado": 0.0,
            "p_atiempo": 1.0,
            "p_exitoso": 0.0,
            "precio_promedio": 200.0,
            "ocupacion_promedio": 35.0,  # < 50 -> factor_demanda = -0.08
            "capacidad_maxima_media": 100,
            "capacidad_usada_media": 35,
        }

        simulador = SimuladorPreciosDinamicos(mock_motor)
        res = simulador.simular(margen_comercial_pct=0.0)

        assert res["etiqueta_demanda"] == "Baja demanda / Estimulación (-8%)"
        # 200 * 1.0 (sin riesgo) * 0.92 = 184.0
        assert res["precio_sugerido"] == pytest.approx(184.0)

    def test_simulacion_con_demanda_moderada(self):
        """Escenario con ocupación moderada entre 50% y 80% (tarifa neutra 0%)."""
        mock_motor = MagicMock(spec=MotorAnalisisBase)
        mock_motor.calcular_metricas_segmento.return_value = {
            "muestra_tamano": 8,
            "es_estimacion_global": False,
            "p_atrasado": 0.0,
            "p_cancelado": 0.0,
            "p_atiempo": 1.0,
            "p_exitoso": 0.0,
            "precio_promedio": 100.0,
            "ocupacion_promedio": 65.0,  # entre 50 y 80 -> 0%
            "capacidad_maxima_media": 100,
            "capacidad_usada_media": 65,
        }

        simulador = SimuladorPreciosDinamicos(mock_motor)
        res = simulador.simular(margen_comercial_pct=0.10)

        assert res["etiqueta_demanda"] == "Demanda moderada (Tarifa neutra)"
        # 100 * 1.0 * 1.0 * 1.10 = 110.0
        assert res["precio_sugerido"] == pytest.approx(110.0)

    def test_simulacion_con_precio_manual_valido(self):
        """El usuario ingresa un precio manual > 0 que debe anular el precio histórico."""
        mock_motor = MagicMock(spec=MotorAnalisisBase)
        mock_motor.calcular_metricas_segmento.return_value = {
            "muestra_tamano": 5,
            "es_estimacion_global": False,
            "p_atrasado": 0.0,
            "p_cancelado": 0.0,
            "p_atiempo": 1.0,
            "p_exitoso": 0.0,
            "precio_promedio": 50.0,  # precio histórico ignorado
            "ocupacion_promedio": 60.0,
            "capacidad_maxima_media": 100,
            "capacidad_usada_media": 60,
        }

        simulador = SimuladorPreciosDinamicos(mock_motor)
        res = simulador.simular(precio_base_manual=250.0, margen_comercial_pct=0.0)

        assert res["precio_base"] == 250.0
        assert res["tipo_precio_base"] == "Ingresado manualmente por el usuario"
        assert res["precio_sugerido"] == 250.0

    def test_simulacion_con_precio_manual_invalido_o_cero_usa_historico(self):
        """Si precio_base_manual es <= 0, debe recurrir al promedio histórico."""
        mock_motor = MagicMock(spec=MotorAnalisisBase)
        mock_motor.calcular_metricas_segmento.return_value = {
            "muestra_tamano": 5,
            "es_estimacion_global": False,
            "p_atrasado": 0.0,
            "p_cancelado": 0.0,
            "p_atiempo": 1.0,
            "p_exitoso": 0.0,
            "precio_promedio": 120.0,
            "ocupacion_promedio": 60.0,
            "capacidad_maxima_media": 100,
            "capacidad_usada_media": 60,
        }

        simulador = SimuladorPreciosDinamicos(mock_motor)
        res = simulador.simular(precio_base_manual=0.0)
        assert res["precio_base"] == 120.0
        assert res["tipo_precio_base"] == "Promedio histórico del segmento"

    def test_simulacion_caso_borde_precio_base_cero(self):
        """
        Caso borde: sin precio histórico (precio_promedio == 0.0) y sin precio manual.
        Verifica que ajuste_porcentual_total no produzca ZeroDivisionError.
        """
        mock_motor = MagicMock(spec=MotorAnalisisBase)
        mock_motor.calcular_metricas_segmento.return_value = {
            "muestra_tamano": 0,
            "es_estimacion_global": True,
            "p_atrasado": 0.0,
            "p_cancelado": 0.0,
            "p_atiempo": 0.0,
            "p_exitoso": 0.0,
            "precio_promedio": 0.0,
            "ocupacion_promedio": 0.0,
            "capacidad_maxima_media": 0,
            "capacidad_usada_media": 0,
        }

        simulador = SimuladorPreciosDinamicos(mock_motor)
        res = simulador.simular()

        assert res["precio_base"] == 0.0
        assert res["ajuste_porcentual_total"] == 0.0
        assert res["precio_sugerido"] == 0.0
        # Asientos ocupados tiene piso en 1
        assert res["asientos_ocupados_media"] == 1

    def test_integracion_completa_simulador_con_motor_real(self, coleccion_vuelos_diversos):
        """Prueba de integración directa entre Simulador y MotorEstadisticoDescriptivo."""
        motor = MotorEstadisticoDescriptivo(coleccion_vuelos_diversos)
        simulador = SimuladorPreciosDinamicos(motor)

        res = simulador.simular(
            ruta="EZE -> MIA",
            franja="Todas las franjas",
            ocupacion="Cualquier ocupación",
            costo_retraso_pct=0.20,
            costo_cancelacion_pct=0.50,
            margen_comercial_pct=0.15,
        )

        assert res["ruta"] == "EZE -> MIA"
        assert res["muestra_tamano"] == 2
        assert res["p_atrasado_pct"] == 50.0
        assert res["precio_base"] == 350.0
        assert res["precio_sugerido"] > res["precio_base"]


# =====================================================================
# 4. Pruebas para Métodos del Modelo Vuelo (Soporte al Análisis)
# =====================================================================

class TestVueloOperativo:
    """Pruebas unitarias para la entidad Vuelo y sus métodos de cálculo operativo."""

    def test_validacion_precio_obligatorio_y_positivo(self):
        with pytest.raises(ValueError, match="El atributo 'precio' es obligatorio"):
            crear_vuelo_dummy(precio=None)

        with pytest.raises(ValueError, match="no es numérico válido"):
            crear_vuelo_dummy(precio="no_numerico")

        with pytest.raises(ValueError, match="El precio no puede ser negativo"):
            crear_vuelo_dummy(precio=-10.0)

    def test_calcular_duraciones_estipulada_y_real(self):
        vuelo = crear_vuelo_dummy(
            fechayhora_origen_estipulado=datetime(2026, 10, 21, 10, 0),
            fechayhora_destino_estipulado=datetime(2026, 10, 21, 12, 30),
            fechayhora_origen=datetime(2026, 10, 21, 10, 10),
            fechayhora_destino=datetime(2026, 10, 21, 12, 45),
        )
        assert vuelo.calcular_duracion_estipulada_minutos() == 150.0
        assert vuelo.calcular_duracion_real_minutos() == 155.0

        # Caso nulos
        vuelo_sin_fechas = crear_vuelo_dummy(
            fechayhora_origen_estipulado=None,
            fechayhora_destino_estipulado=None,
            fechayhora_origen=None,
            fechayhora_destino=None,
        )
        assert vuelo_sin_fechas.calcular_duracion_estipulada_minutos() == 0.0
        assert vuelo_sin_fechas.calcular_duracion_real_minutos() is None

    def test_calcular_retrasos_y_es_retrasado(self):
        vuelo = crear_vuelo_dummy(
            fechayhora_origen_estipulado=datetime(2026, 10, 21, 10, 0),
            fechayhora_origen=datetime(2026, 10, 21, 10, 25),  # 25 min demora
            fechayhora_destino_estipulado=datetime(2026, 10, 21, 12, 0),
            fechayhora_destino=datetime(2026, 10, 21, 12, 20), # 20 min demora
        )
        assert vuelo.calcular_retraso_salida_minutos() == 25.0
        assert vuelo.calcular_retraso_llegada_minutos() == 20.0
        assert vuelo.es_retrasado(umbral_tolerancia_minutos=15.0) is True
        assert vuelo.es_retrasado(umbral_tolerancia_minutos=30.0) is False

        # Caso sin demora (adelantado)
        vuelo_adelantado = crear_vuelo_dummy(
            fechayhora_origen_estipulado=datetime(2026, 10, 21, 10, 0),
            fechayhora_origen=datetime(2026, 10, 21, 9, 50),
            fechayhora_destino_estipulado=datetime(2026, 10, 21, 12, 0),
            fechayhora_destino=datetime(2026, 10, 21, 11, 55),
        )
        assert vuelo_adelantado.calcular_retraso_salida_minutos() == 0.0
        assert vuelo_adelantado.calcular_retraso_llegada_minutos() == 0.0

        # Caso fechas ausentes
        vuelo_sin_fechas = crear_vuelo_dummy(
            fechayhora_origen=None,
            fechayhora_origen_estipulado=None,
            fechayhora_destino=None,
            fechayhora_destino_estipulado=None,
        )
        assert vuelo_sin_fechas.calcular_retraso_salida_minutos() == 0.0
        assert vuelo_sin_fechas.calcular_retraso_llegada_minutos() == 0.0

    def test_factor_ocupacion_e_ingresos_estimados(self):
        vuelo = crear_vuelo_dummy(
            capacidad_maxima_avion=200,
            capacidad_usada_avion=150,
            precio=100.0,
        )
        assert vuelo.calcular_factor_ocupacion() == 75.0
        assert vuelo.calcular_ingresos_estimados() == 15000.0

        # Caso capacidad maxima <= 0
        vuelo_cero_cap = crear_vuelo_dummy(capacidad_maxima_avion=0, capacidad_usada_avion=0)
        assert vuelo_cero_cap.calcular_factor_ocupacion() == 0.0

    def test_obtener_franja_horaria_casos_borde(self):
        # Fecha en formato string válido
        vuelo_str_date = crear_vuelo_dummy(
            fechayhora_origen_estipulado="2026-10-21 07:15:00",
            fechayhora_origen=None
        )
        assert vuelo_str_date.obtener_franja_horaria() == "Mañana (06:00 - 12:00)"

        # String inválido no parseable
        vuelo_bad_str = crear_vuelo_dummy(
            fechayhora_origen_estipulado="fecha_invalida",
            fechayhora_origen=None
        )
        assert vuelo_bad_str.obtener_franja_horaria() == "Sin horario"

        # Objeto sin atributo hour
        vuelo_sin_hour = crear_vuelo_dummy(
            fechayhora_origen_estipulado=12345,  # int no tiene .hour
            fechayhora_origen=None
        )
        assert vuelo_sin_hour.obtener_franja_horaria() == "Sin horario"

    def test_normalizar_estado_sin_estado(self):
        vuelo = crear_vuelo_dummy(estado="")
        assert vuelo.normalizar_estado() == "Desconocido"
        vuelo_none = crear_vuelo_dummy(estado=None)
        assert vuelo_none.normalizar_estado() == "Desconocido"

    def test_repr_vuelo(self):
        vuelo = crear_vuelo_dummy(id_vuelo="IB-500", precio=250.0)
        rep = repr(vuelo)
        assert "IB-500" in rep
        assert "$250.00" in rep

        vuelo_sin_id = crear_vuelo_dummy(id_vuelo=None, precio=100.0)
        assert "Sin ID" in repr(vuelo_sin_id)

