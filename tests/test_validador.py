import io
import unittest
import pandas as pd
from modules.validador import ValidadorEsquema, ValidadorPreInstanciacion
from modules.lector_datos import detectar_formato, FactoryLectorDatos
from apps.modulo_validacion import COLUMNAS_CANONICAS, ATRIBUTOS_REQUERIDOS


class TestValidadorEsquemaAvanzado(unittest.TestCase):
    
    def setUp(self):
        """Prepara un DataFrame base válido y un mapeo estándar para las pruebas."""
        self.df_valido = pd.DataFrame({
            'code': ['V1', 'V2'],
            'dest': ['EZE', 'MIA'],
            'orig': ['MIA', 'EZE'],
            'c_orig': ['USA', 'ARG'],
            'c_dest': ['ARG', 'USA'],
            'f_orig': pd.to_datetime(['2026-10-01 08:00', '2026-10-02 08:00']),
            'f_dest': pd.to_datetime(['2026-10-01 10:00', '2026-10-02 10:00']),
            'f_orig_est': pd.to_datetime(['2026-10-01 08:00', '2026-10-02 08:00']),
            'f_dest_est': pd.to_datetime(['2026-10-01 10:00', '2026-10-02 10:00']),
            'status': ['exitoso', 'cancelado'],
            'cap_max': [200, 180],
            'cap_usada': [150, 180],
            'costo': [500.0, 450.0]
        })
        
        self.mapeo = {
            "id_vuelo": "code",
            "aeropuerto_destino": "dest",
            "aeropuerto_origen": "orig",
            "origen": "c_orig",
            "destino": "c_dest",
            "fechayhora_origen": "f_orig",
            "fechayhora_destino": "f_dest",
            "fechayhora_origen_estipulado": "f_orig_est",
            "fechayhora_destino_estipulado": "f_dest_est",
            "estado": "status",
            "capacidad_maxima_avion": "cap_max",
            "capacidad_usada_avion": "cap_usada",
            "precio": "costo"
        }
        
        self.requeridos = list(self.mapeo.keys())

    def test_contrato_exitoso(self):
        """Verifica que un DataFrame correcto pase todas las validaciones."""
        validador = ValidadorEsquema(self.df_valido, self.mapeo, self.requeridos)
        resultado = validador.validar()
        self.assertEqual(resultado, "Contrato validado exitosamente.")

    def test_falla_por_columna_completamente_vacia(self):
        """Verifica que lance ValueError si una columna obligatoria es full NaN."""
        df_error = self.df_valido.copy()
        df_error['cap_max'] = None
        
        validador = ValidadorEsquema(df_error, self.mapeo, self.requeridos)
        with self.assertRaises(ValueError) as ctx:
            validador.validar()
        self.assertIn("completamente vacías", str(ctx.exception))

    def test_falla_por_tipo_de_dato_incorrecto(self):
        """Verifica que la capacidad deba ser estrictamente un número entero."""
        df_error = self.df_valido.copy()
        df_error['cap_max'] = [200.5, 180.2]
        
        validador = ValidadorEsquema(df_error, self.mapeo, self.requeridos)
        with self.assertRaises(ValueError) as ctx:
            validador.validar()
        self.assertIn("números enteros", str(ctx.exception))

    def test_falla_por_precio_no_asignado(self):
        """Verifica que lance ValueError si no se asigna la variable obligatoria 'precio'."""
        mapeo_sin_precio = self.mapeo.copy()
        mapeo_sin_precio["precio"] = "(No asignar)"
        
        validador = ValidadorEsquema(self.df_valido, mapeo_sin_precio, self.requeridos)
        with self.assertRaises(ValueError) as ctx:
            validador.validar()
        self.assertIn("precio", str(ctx.exception).lower())

    def test_falla_por_cualquier_requerido_no_asignado(self):
        """Verifica la restricción absoluta de (No asignar) para cualquier atributo crítico."""
        for campo in ["aeropuerto_origen", "fechayhora_origen_estipulado", "capacidad_maxima_avion", "estado"]:
            mapeo_incompleto = self.mapeo.copy()
            mapeo_incompleto[campo] = "(No asignar)"
            validador = ValidadorEsquema(self.df_valido, mapeo_incompleto, self.requeridos)
            with self.assertRaises(ValueError) as ctx:
                validador.validar()
            self.assertIn(campo, str(ctx.exception))

    def test_validador_pre_instanciacion_exitoso(self):
        """Verifica que el ValidadorPreInstanciacion apruebe datos completamente limpios."""
        ValidadorPreInstanciacion.validar(self.df_valido, self.mapeo)

    def test_validador_pre_instanciacion_falla_por_precio_nulo_o_negativo(self):
        """Verifica rechazo de precios nulos o negativos antes de instanciar objetos."""
        df_nulo = self.df_valido.copy()
        df_nulo.loc[0, 'costo'] = None
        with self.assertRaises(ValueError) as ctx:
            ValidadorPreInstanciacion.validar(df_nulo, self.mapeo)
        self.assertIn("precio", str(ctx.exception).lower())

        df_neg = self.df_valido.copy()
        df_neg.loc[0, 'costo'] = -50.0
        with self.assertRaises(ValueError) as ctx:
            ValidadorPreInstanciacion.validar(df_neg, self.mapeo)
        self.assertIn("precio", str(ctx.exception).lower())

    def test_validador_pre_instanciacion_falla_por_capacidades_invalidas(self):
        """Verifica rechazo de capacidades negativas, nulas o con usada > maxima."""
        # Capacidad usada mayor a máxima
        df_inc = self.df_valido.copy()
        df_inc.loc[0, 'cap_usada'] = 300
        df_inc.loc[0, 'cap_max'] = 200
        with self.assertRaises(ValueError) as ctx:
            ValidadorPreInstanciacion.validar(df_inc, self.mapeo)
        self.assertIn("capacidad", str(ctx.exception).lower())

        # Capacidad negativa
        df_neg = self.df_valido.copy()
        df_neg.loc[0, 'cap_max'] = -10
        with self.assertRaises(ValueError) as ctx:
            ValidadorPreInstanciacion.validar(df_neg, self.mapeo)
        self.assertIn("capacidad", str(ctx.exception).lower())

    def test_validador_pre_instanciacion_falla_por_fechas_estipuladas_invalidas(self):
        """Verifica que las fechas estipuladas no sean nulas ni tengan destino anterior a origen."""
        df_fecha = self.df_valido.copy()
        df_fecha.loc[0, 'f_dest_est'] = pd.to_datetime('2026-10-01 05:00') # Salida 08:00, llegada 05:00
        with self.assertRaises(ValueError) as ctx:
            ValidadorPreInstanciacion.validar(df_fecha, self.mapeo)
        self.assertIn("cronología", str(ctx.exception).lower())

    def test_deteccion_delimitadores_independientes(self):
        """Verifica que detectar_formato identifique delimitadores de comas, punto y coma, tabs y pipes."""
        # 1. Comas
        f_csv = io.StringIO("a,b,c\n1,2,3\n4,5,6\n")
        sep, _ = detectar_formato(f_csv)
        self.assertEqual(sep, ',')

        # 2. Punto y coma
        f_sc = io.StringIO("a;b;c\n1;2;3\n4;5;6\n")
        sep, _ = detectar_formato(f_sc)
        self.assertEqual(sep, ';')

        # 3. Tabulaciones
        f_tab = io.StringIO("a\tb\tc\n1\t2\t3\n4\t5\t6\n")
        sep, _ = detectar_formato(f_tab)
        self.assertEqual(sep, '\t')

        # 4. Pipes
        f_pipe = io.StringIO("a|b|c\n1|2|3\n4|5|6\n")
        sep, _ = detectar_formato(f_pipe)
        self.assertEqual(sep, '|')

    def test_unificacion_multifile_con_nombres_diferentes(self):
        """Verifica la consolidación de 2 archivos con nombres de columnas distintos bajo las 13 canónicas."""
        df1 = pd.DataFrame({
            "aero_orig": ["EZE"],
            "aero_dest": ["COR"],
            "pais_orig": ["ARG"],
            "pais_dest": ["ARG"],
            "f_sal": ["2026-10-01 08:00"],
            "f_lleg": ["2026-10-01 09:30"],
            "f_sal_est": ["2026-10-01 08:00"],
            "f_lleg_est": ["2026-10-01 09:30"],
            "est": ["A tiempo"],
            "c_max": [180],
            "c_usd": [150],
            "costo": [200.0],
            "cod_v": ["AR100"]
        })

        df2 = pd.DataFrame({
            "aeropuerto_salida": ["MIA"],
            "aeropuerto_llegada": ["JFK"],
            "origen_pais": ["USA"],
            "destino_pais": ["USA"],
            "hora_salida": ["2026-10-02 12:00"],
            "hora_llegada": ["2026-10-02 15:00"],
            "hora_salida_programada": ["2026-10-02 12:00"],
            "hora_llegada_programada": ["2026-10-02 15:00"],
            "estado_vuelo": ["Exitoso"],
            "capacidad_total": [220],
            "capacidad_ocupada": [200],
            "tarifa": [450.0],
            "identificador": ["AA200"]
        })

        mapeo1 = {
            "aeropuerto_origen": "aero_orig",
            "aeropuerto_destino": "aero_dest",
            "origen": "pais_orig",
            "destino": "pais_dest",
            "fechayhora_origen": "f_sal",
            "fechayhora_destino": "f_lleg",
            "fechayhora_origen_estipulado": "f_sal_est",
            "fechayhora_destino_estipulado": "f_lleg_est",
            "estado": "est",
            "capacidad_maxima_avion": "c_max",
            "capacidad_usada_avion": "c_usd",
            "precio": "costo",
            "id_vuelo": "cod_v"
        }

        mapeo2 = {
            "aeropuerto_origen": "aeropuerto_salida",
            "aeropuerto_destino": "aeropuerto_llegada",
            "origen": "origen_pais",
            "destino": "destino_pais",
            "fechayhora_origen": "hora_salida",
            "fechayhora_destino": "hora_llegada",
            "fechayhora_origen_estipulado": "hora_salida_programada",
            "fechayhora_destino_estipulado": "hora_llegada_programada",
            "estado": "estado_vuelo",
            "capacidad_maxima_avion": "capacidad_total",
            "capacidad_usada_avion": "capacidad_ocupada",
            "precio": "tarifa",
            "id_vuelo": "identificador"
        }

        # Construcción unificada canónica
        dfs_canon = []
        for df_f, map_f in [(df1, mapeo1), (df2, mapeo2)]:
            df_canon = pd.DataFrame(index=df_f.index)
            for c in COLUMNAS_CANONICAS:
                df_canon[c] = df_f[map_f[c]].values
            dfs_canon.append(df_canon)

        df_unif = pd.concat(dfs_canon, axis=0, ignore_index=True)
        self.assertEqual(len(df_unif), 2)
        self.assertListEqual(list(df_unif.columns), COLUMNAS_CANONICAS)
        self.assertEqual(df_unif.loc[0, "aeropuerto_origen"], "EZE")
        self.assertEqual(df_unif.loc[1, "aeropuerto_origen"], "MIA")
        self.assertEqual(df_unif.loc[0, "precio"], 200.0)
        self.assertEqual(df_unif.loc[1, "precio"], 450.0)


if __name__ == '__main__':
    unittest.main()