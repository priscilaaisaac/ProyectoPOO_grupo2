import unittest
import pandas as pd
from libs.validador import ValidadorEsquema

class TestValidadorEsquemaAvanzado(unittest.TestCase):
    
    def setUp(self):
        """Prepara un DataFrame base válido y un mapeo estándar para las pruebas."""
        self.df_valido = pd.DataFrame({
            'code': ['V1', 'V2'],
            'dest': ['EZE', 'MIA'],
            'orig': ['MIA', 'EZE'],
            'c_orig': ['USA', 'ARG'],
            'c_dest': ['ARG', 'USA'],
            'f_orig': pd.to_datetime(['2026-10-01', '2026-10-02']),
            'f_dest': pd.to_datetime(['2026-10-01 10:00', '2026-10-02 10:00']),
            'f_orig_est': pd.to_datetime(['2026-10-01', '2026-10-02']),
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
        self.requeridos.remove("precio") # El precio es opcional

    def test_contrato_exitoso(self):
        """Verifica que un DataFrame correcto pase todas las validaciones."""
        validador = ValidadorEsquema(self.df_valido, self.mapeo, self.requeridos)
        resultado = validador.validar()
        self.assertEqual(resultado, "Contrato validado exitosamente.")

    def test_falla_por_columna_completamente_vacia(self):
        """Verifica que lance ValueError si una columna obligatoria es full NaN."""
        df_error = self.df_valido.copy()
        df_error['cap_max'] = None # Llena toda la columna de nulos
        
        validador = ValidadorEsquema(df_error, self.mapeo, self.requeridos)
        with self.assertRaises(ValueError) as ctx:
            validador.validar()
        self.assertIn("completamente vacías", str(ctx.exception))

    def test_falla_por_tipo_de_dato_incorrecto(self):
        """Verifica que la capacidad deba ser estrictamente un número entero."""
        df_error = self.df_valido.copy()
        df_error['cap_max'] = [200.5, 180.2] # Float en lugar de Int
        
        validador = ValidadorEsquema(df_error, self.mapeo, self.requeridos)
        with self.assertRaises(ValueError) as ctx:
            validador.validar()
        self.assertIn("números enteros", str(ctx.exception))

    def test_degradacion_elegante_sin_precio(self):
        """Verifica que emita advertencia si no se asigna la variable opcional 'precio'."""
        mapeo_sin_precio = self.mapeo.copy()
        mapeo_sin_precio["precio"] = "(No asignar)"
        
        validador = ValidadorEsquema(self.df_valido, mapeo_sin_precio, self.requeridos)
        resultado = validador.validar()
        self.assertIn("Advertencia", resultado)

if __name__ == '__main__':
    unittest.main()