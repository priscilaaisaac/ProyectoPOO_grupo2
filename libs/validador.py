import pandas as pd
import numpy as np
import re

class ValidadorEsquema:
    def __init__(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        self.df = df
        self.mapeo = mapeo
        self.requeridos = requeridos

    @staticmethod
    def _es_patron_error_o_vacio(valor) -> bool:
        """Determina si un valor es nulo, vacío o representa un código de error admitido."""
        if pd.isna(valor):
            return True
        
        texto = str(valor).strip().lower()
        if texto in {"", "none", "null", "nan", "n/a", "na", "error"}:
            return True
        
        # Reconoce patrones como 'error_498', 'error123', 'err_01', etc.
        if re.match(r"^err(or)?([_\-\s]?\d+)?$", texto):
            return True
        
        return False

    def _validar_columna_enteros_tolerante(self, serie: pd.Series, nombre_campo: str):
        """
        Verifica que los valores válidos (excluyendo errores y nulos) sean estrictamente enteros.
        """
        for valor in serie:
            if self._es_patron_error_o_vacio(valor):
                continue
            
            # Intento de conversión a entero
            try:
                val_num = float(valor)
                if not val_num.is_integer():
                    raise ValueError
            except (ValueError, TypeError):
                raise ValueError(
                    f"El atributo '{nombre_campo}' contiene el valor inválido '{valor}'. "
                    f"Solo se admiten números enteros, valores vacíos o etiquetas de error (ej. 'error_498', 'ERROR')."
                )

    def _validar_columna_numerica_tolerante(self, serie: pd.Series, nombre_campo: str):
        """
        Verifica que los valores válidos (excluyendo errores y nulos) sean números reales/decimales.
        """
        for valor in serie:
            if self._es_patron_error_o_vacio(valor):
                continue
            
            try:
                float(valor)
            except (ValueError, TypeError):
                raise ValueError(
                    f"El atributo '{nombre_campo}' contiene el valor inválido '{valor}'. "
                    f"Solo se admiten números, valores vacíos o etiquetas de error (ej. 'error_498', 'ERROR')."
                )

    def validar(self):
        """
        Ejecuta las reglas de contrato y precondiciones tolerando errores conocidos y nulos.
        """
        # 1. Validación de faltantes críticos en la asignación
        faltantes = [attr for attr in self.requeridos if self.mapeo.get(attr) == "(No asignar)"]
        if faltantes:
            raise ValueError(f"Faltan asignar variables críticas: {', '.join(faltantes)}")

        # 2. Validación de columnas completamente vacías en campos obligatorios
        vacias = []
        for atributo in self.requeridos:
            col = self.mapeo[atributo]
            # Si todos los registros son nulos o cadenas vacías
            serie_limpia = self.df[col].dropna().astype(str).str.strip()
            if serie_limpia.empty or (serie_limpia == "").all():
                vacias.append(atributo)
        if vacias:
            raise ValueError(f"Las siguientes columnas obligatorias están completamente vacías: {', '.join(vacias)}")

        # 3. Validación tolerante de campos numéricos / enteros
        c_max = self.mapeo["capacidad_maxima_avion"]
        c_usada = self.mapeo["capacidad_usada_avion"]
        self._validar_columna_enteros_tolerante(self.df[c_max], "capacidad_maxima_avion")
        self._validar_columna_enteros_tolerante(self.df[c_usada], "capacidad_usada_avion")

        # Convertimos a formato numérico (ignorando temporalmente los textos de 'error' convirtiéndolos en nulos)
        s_max = pd.to_numeric(self.df[c_max], errors='coerce')
        s_usada = pd.to_numeric(self.df[c_usada], errors='coerce')
        
        # Comparamos fila por fila si la usada supera a la máxima
        if (s_usada > s_max).any():
            raise ValueError("Inconsistencia detectada: Hay registros donde la 'capacidad usada' es mayor a la 'capacidad máxima'.")

        c_precio = self.mapeo.get("precio")
        if not c_precio or c_precio == "(No asignar)":
            raise ValueError("El atributo 'precio' es obligatorio.")
        self._validar_columna_numerica_tolerante(self.df[c_precio], "precio")

        # 4. Paridad de formatos (Origen / Destino)
        c_origen = self.mapeo.get("origen")
        c_destino = self.mapeo.get("destino")
        if c_origen and c_origen != "(No asignar)" and c_destino and c_destino != "(No asignar)":
            if self.df[c_origen].dtype != self.df[c_destino].dtype:
                raise ValueError("Los atributos 'origen' y 'destino' deben compartir el mismo formato base.")

        c_aero_orig = self.mapeo.get("aeropuerto_origen")
        c_aero_dest = self.mapeo.get("aeropuerto_destino")
        if c_aero_orig and c_aero_orig != "(No asignar)" and c_aero_dest and c_aero_dest != "(No asignar)":
            if self.df[c_aero_orig].dtype != self.df[c_aero_dest].dtype:
                raise ValueError("Los atributos 'aeropuerto_origen' y 'aeropuerto_destino' deben compartir el mismo formato base.")

        return "Contrato validado exitosamente."