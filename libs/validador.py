import pandas as pd

class ValidadorEsquema:
    def __init__(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        self.df = df
        self.mapeo = mapeo
        self.requeridos = requeridos

    def validar(self):
        """
        Ejecuta todas las reglas de contrato y precondiciones.
        Lanza ValueError si alguna regla se rompe.
        Retorna una advertencia si hay degradación elegante.
        """
        # 1. Validación de faltantes críticos
        faltantes = [attr for attr in self.requeridos if self.mapeo.get(attr) == "(No asignar)"]
        if faltantes:
            raise ValueError(f"Faltan asignar variables críticas: {', '.join(faltantes)}")

        # 2. Validación de columnas completamente vacías
        vacias = []
        for atributo in self.requeridos:
            col = self.mapeo[atributo]
            if self.df[col].isnull().all():
                vacias.append(atributo)
        if vacias:
            raise ValueError(f"Las siguientes columnas obligatorias están completamente vacías: {', '.join(vacias)}")

        # 3. Validación de Tipos de Datos (Dtypes) y Restricciones
        c_id = self.mapeo["id_vuelo"]
        if not pd.api.types.is_string_dtype(self.df[c_id]) and not pd.api.types.is_object_dtype(self.df[c_id]):
            raise ValueError("El atributo 'id_vuelo' debe contener únicamente texto (string).")

        c_max = self.mapeo["capacidad_maxima_avion"]
        c_usada = self.mapeo["capacidad_usada_avion"]
        if not pd.api.types.is_integer_dtype(self.df[c_max]) or not pd.api.types.is_integer_dtype(self.df[c_usada]):
            raise ValueError("Las capacidades del avión deben ser números enteros.")

        c_precio = self.mapeo.get("precio")
        if c_precio and c_precio != "(No asignar)":
            if not pd.api.types.is_numeric_dtype(self.df[c_precio]):
                raise ValueError("El atributo 'precio' admite únicamente números.")

        # 4. Paridad de formatos (Origen / Destino)
        if self.df[self.mapeo["origen"]].dtype != self.df[self.mapeo["destino"]].dtype:
            raise ValueError("Los atributos 'origen' y 'destino' deben compartir el mismo formato.")

        if self.df[self.mapeo["aeropuerto_origen"]].dtype != self.df[self.mapeo["aeropuerto_destino"]].dtype:
            raise ValueError("Los atributos 'aeropuerto_origen' y 'aeropuerto_destino' deben compartir el mismo formato.")

        # 5. Evaluación de Degradación Elegante
        if not c_precio or c_precio == "(No asignar)":
            return "Advertencia: No se asignó la variable 'precio'. Módulos financieros deshabilitados."
        
        return "Contrato validado exitosamente."