import re
from abc import ABC, abstractmethod
import pandas as pd


class InspectorTipos:
    """Provee métodos estáticos de inspección y tolerancia sobre datos de pandas."""

    @staticmethod
    def es_patron_error_o_vacio(valor) -> bool:
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

    @staticmethod
    def obtener_tipo_general(serie: pd.Series) -> str:
        """
        Clasifica una serie en su categoría semántica general:
        'texto', 'numerico', 'fecha' u 'otro'.
        """
        if pd.api.types.is_string_dtype(serie) or serie.dtype == object:
            return "texto"
        if pd.api.types.is_numeric_dtype(serie):
            return "numerico"
        if pd.api.types.is_datetime64_any_dtype(serie):
            return "fecha"
        return "otro"


class ReglaValidacion(ABC):
    """Interfaz abstracta para cualquier regla de contrato de esquema."""

    @abstractmethod
    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        pass


class ReglaCamposRequeridos(ReglaValidacion):
    """Comprueba asignaciones obligatorias y que no existan columnas completamente vacías."""

    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        # 1. Variables requeridas no asignadas o marcadas como (No asignar)
        faltantes = [
            attr for attr in requeridos
            if not mapeo.get(attr) or mapeo.get(attr) == "(No asignar)" or str(mapeo.get(attr)).strip() == ""
        ]
        if faltantes:
            raise ValueError(
                f"Asignación obligatoria incompleta: Los siguientes campos críticos no pueden quedar sin asignar ('(No asignar)'): "
                f"{', '.join(faltantes)}. Por favor, asigne una columna válida a cada campo obligatorio para continuar."
            )

        # 2. Columnas obligatorias 100% vacías o inexistentes
        vacias = []
        for atributo in requeridos:
            col = mapeo[atributo]
            if col in df.columns:
                serie_limpia = df[col].dropna().astype(str).str.strip()
                if serie_limpia.empty or (serie_limpia == "").all():
                    vacias.append(atributo)
            else:
                vacias.append(atributo)
        if vacias:
            raise ValueError(f"Las siguientes columnas obligatorias están completamente vacías o no existen en el dataset: {', '.join(vacias)}")


class ReglaCapacidadesYPrecio(ReglaValidacion):
    """Verifica integridad de capacidades de aeronave y consistencia de precios."""

    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        c_max = mapeo.get("capacidad_maxima_avion")
        c_usada = mapeo.get("capacidad_usada_avion")

        if c_max and c_max != "(No asignar)" and c_max in df.columns:
            self._validar_enteros_tolerante(df[c_max], "capacidad_maxima_avion")
        if c_usada and c_usada != "(No asignar)" and c_usada in df.columns:
            self._validar_enteros_tolerante(df[c_usada], "capacidad_usada_avion")

        # Comparación fila por fila ignorando errores admitidos
        if (c_max and c_usada and c_max != "(No asignar)" and c_usada != "(No asignar)"
                and c_max in df.columns and c_usada in df.columns):
            s_max = pd.to_numeric(df[c_max], errors="coerce")
            s_usada = pd.to_numeric(df[c_usada], errors="coerce")

            # Verificar no negatividad si son numéricos
            if (s_max.dropna() < 0).any() or (s_usada.dropna() < 0).any():
                raise ValueError("Inconsistencia detectada: Las capacidades de la aeronave no pueden ser números negativos.")

            mascara_ambas = s_max.notna() & s_usada.notna()
            if (s_usada[mascara_ambas] > s_max[mascara_ambas]).any():
                raise ValueError("Inconsistencia detectada: Hay registros donde la 'capacidad usada' es mayor a la 'capacidad máxima'.")

        c_precio = mapeo.get("precio")
        if not c_precio or c_precio == "(No asignar)":
            raise ValueError("El atributo 'precio' es estrictamente obligatorio para validar el contrato.")
        if c_precio not in df.columns:
            raise ValueError("La columna asignada al atributo 'precio' no existe en el conjunto de datos.")
        self._validar_numerica_tolerante(df[c_precio], "precio")

        s_precio = pd.to_numeric(df[c_precio], errors="coerce")
        if (s_precio.dropna() < 0).any():
            raise ValueError("Inconsistencia detectada: El atributo 'precio' contiene valores numéricos negativos.")

    @staticmethod
    def _validar_enteros_tolerante(serie: pd.Series, nombre_campo: str):
        for valor in serie:
            if InspectorTipos.es_patron_error_o_vacio(valor):
                continue
            try:
                val_num = float(valor)
                if not val_num.is_integer():
                    raise ValueError
            except (ValueError, TypeError):
                raise ValueError(
                    f"El atributo '{nombre_campo}' contiene el valor inválido '{valor}'. "
                    f"Solo se admiten números enteros, valores vacíos o etiquetas de error (ej. 'error_498', 'ERROR')."
                )

    @staticmethod
    def _validar_numerica_tolerante(serie: pd.Series, nombre_campo: str):
        for valor in serie:
            if InspectorTipos.es_patron_error_o_vacio(valor):
                continue
            try:
                float(valor)
            except (ValueError, TypeError):
                raise ValueError(
                    f"El atributo '{nombre_campo}' contiene el valor inválido '{valor}'. "
                    f"Solo se admiten números, valores vacíos o etiquetas de error (ej. 'error_498', 'ERROR')."
                )


class ReglaParidadFormatos(ReglaValidacion):
    """Garantiza compatibilidad semántica entre campos pareados (origen / destino)."""

    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        self._comparar_par(df, mapeo, "origen", "destino")
        self._comparar_par(df, mapeo, "aeropuerto_origen", "aeropuerto_destino")

    @staticmethod
    def _comparar_par(df: pd.DataFrame, mapeo: dict, campo_a: str, campo_b: str):
        col_a = mapeo.get(campo_a)
        col_b = mapeo.get(campo_b)
        if col_a and col_a != "(No asignar)" and col_b and col_b != "(No asignar)":
            if col_a in df.columns and col_b in df.columns:
                tipo_a = InspectorTipos.obtener_tipo_general(df[col_a])
                tipo_b = InspectorTipos.obtener_tipo_general(df[col_b])
                if tipo_a != tipo_b:
                    raise ValueError(
                        f"Los atributos '{campo_a}' ({tipo_a}) y '{campo_b}' ({tipo_b}) "
                        f"deben compartir el mismo tipo de dato general."
                    )


class ReglaCronologiaFechas(ReglaValidacion):
    """Verifica que la fecha y hora de llegada sea siempre posterior a la de salida."""

    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        self._comparar_fechas(df, mapeo, "fechayhora_origen", "fechayhora_destino")
        self._comparar_fechas(df, mapeo, "fechayhora_origen_estipulado", "fechayhora_destino_estipulado")

    @staticmethod
    def _comparar_fechas(df: pd.DataFrame, mapeo: dict, campo_salida: str, campo_llegada: str):
        col_salida = mapeo.get(campo_salida)
        col_llegada = mapeo.get(campo_llegada)

        if col_salida and col_salida != "(No asignar)" and col_llegada and col_llegada != "(No asignar)":
            if col_salida in df.columns and col_llegada in df.columns:
                # Convertir a datetime omitiendo errores temporales
                s_salida = pd.to_datetime(df[col_salida], errors="coerce")
                s_llegada = pd.to_datetime(df[col_llegada], errors="coerce")

                # Validar filas donde ambas fechas son válidas (no nulas)
                mask_validas = s_salida.notna() & s_llegada.notna()
                if (s_salida[mask_validas] >= s_llegada[mask_validas]).any():
                    raise ValueError(
                        f"Inconsistencia detectada: Existen registros donde '{campo_salida}' "
                        f"es igual o posterior a '{campo_llegada}'."
                    )


class ValidadorEsquema:
    """Orquestador que agrupa y ejecuta el conjunto de reglas de validación."""

    def __init__(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        self.df = df
        self.mapeo = mapeo
        self.requeridos = requeridos
        self.reglas: list[ReglaValidacion] = [
            ReglaCamposRequeridos(),
            ReglaCapacidadesYPrecio(),
            ReglaParidadFormatos(),
            ReglaCronologiaFechas(),
        ]

    def validar(self) -> str:
        """Ejecuta secuencialmente todas las reglas de contrato."""
        for regla in self.reglas:
            regla.ejecutar(self.df, self.mapeo, self.requeridos)

        return "Contrato validado exitosamente."

    @staticmethod
    def validar_estructura_tabular(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validación estructural previa al retorno o persistencia del DataFrame:
        - Asegura que sea un DataFrame tabular y consistente.
        - Asegura que los nombres de columnas sean cadenas limpias y únicas.
        - Utiliza pandera si está disponible en el entorno; de lo contrario aplica
          reglas directas de validación e integridad.
        """
        return validar_estructura_tabular(df)


def validar_estructura_tabular(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validación estructural previa al retorno o persistencia del DataFrame:
    - Asegura que sea un DataFrame tabular y consistente.
    - Asegura que los nombres de columnas sean cadenas limpias y únicas.
    - Utiliza pandera si está disponible en el entorno; de lo contrario aplica
      reglas directas de validación e integridad.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Se esperaba una instancia de pd.DataFrame, recibido: {type(df)}")

    if df.empty:
        return df

    # Reset de índice para garantizar continuidad tabular
    df = df.reset_index(drop=True)

    # Validar que los nombres de columnas sean strings sin espacios redundantes y únicos
    cols = [str(c).strip() for c in df.columns]
    if len(cols) != len(set(cols)):
        vistas = set()
        dedup_cols = []
        for c in cols:
            cand = c
            k = 2
            while cand in vistas:
                cand = f"{c}_{k}"
                k += 1
            vistas.add(cand)
            dedup_cols.append(cand)
        df.columns = dedup_cols
    else:
        df.columns = cols

    try:
        try:
            import pandera.pandas as pa
        except (ImportError, AttributeError):
            import pandera as pa
        schema = pa.DataFrameSchema(
            columns={c: pa.Column(required=False, nullable=True) for c in df.columns},
            strict=False,
            coerce=False
        )
        df = schema.validate(df)
    except ImportError:
        pass
    except Exception:
        pass

    return df


class ValidadorPreInstanciacion:
    # Validador que corre luego de la limpieza antes de crear las intancias de vuelo.
    """
    Verifica de forma estricta tipos, rangos y completitud de campos obligatorios
    inmediatamente antes de la instanciación de objetos Vuelo:
    - Asegura que ningún campo obligatorio pase como None, vacío o nulo sin haber sido tratado:
      * precio
      * capacidad_maxima_avion
      * capacidad_usada_avion
      * fechayhora_origen_estipulado
      * fechayhora_destino_estipulado
    - Valida tipos numéricos y rangos:
      * precio: numérico, >= 0
      * capacidad_maxima_avion: entero, >= 0
      * capacidad_usada_avion: entero, >= 0, y capacidad_usada <= capacidad_maxima
    - Valida fechas estipuladas:
      * parseables a datetime
      * fechayhora_destino_estipulado >= fechayhora_origen_estipulado
    """

    CAMPOS_OBLIGATORIOS = [
        "precio",
        "capacidad_maxima_avion",
        "capacidad_usada_avion",
        "fechayhora_origen_estipulado",
        "fechayhora_destino_estipulado",
    ]

    @classmethod
    def validar(cls, df: pd.DataFrame, mapeo: dict = None) -> None:
        if df is None or df.empty:
            raise ValueError("No se puede realizar la pre-validación: el conjunto de datos está vacío o es nulo.")

        mapeo = mapeo or {}

        def _obtener_columna(campo: str) -> str:
            col = mapeo.get(campo)
            if col and col != "(No asignar)" and col in df.columns:
                return col
            if campo in df.columns:
                return campo
            raise ValueError(
                f"Error de pre-instanciación: El campo obligatorio '{campo}' no se encuentra presente en el dataset ni en el mapeo."
            )

        col_precio = _obtener_columna("precio")
        col_cmax = _obtener_columna("capacidad_maxima_avion")
        col_cusada = _obtener_columna("capacidad_usada_avion")
        col_fest_orig = _obtener_columna("fechayhora_origen_estipulado")
        col_fest_dest = _obtener_columna("fechayhora_destino_estipulado")

        columnas_a_validar = {
            "precio": col_precio,
            "capacidad_maxima_avion": col_cmax,
            "capacidad_usada_avion": col_cusada,
            "fechayhora_origen_estipulado": col_fest_orig,
            "fechayhora_destino_estipulado": col_fest_dest,
        }

        # 1. Comprobar que ningún campo obligatorio tenga valores nulos o sin tratar
        for nombre_campo, col_real in columnas_a_validar.items():
            serie = df[col_real]
            es_nulo = serie.apply(InspectorTipos.es_patron_error_o_vacio)
            if es_nulo.any():
                n_nulos = int(es_nulo.sum())
                primeros_indices = list(df.index[es_nulo][:3])
                raise ValueError(
                    f"Error de pre-instanciación: El campo obligatorio '{nombre_campo}' contiene {n_nulos} valores nulos, "
                    f"vacíos o sin tratar (en filas con índices: {primeros_indices}). Todos los campos obligatorios deben ser "
                    f"saneados e imputados antes de instanciar los objetos Vuelo."
                )

        # 2. Validación de Precio (numérico, >= 0)
        serie_precio = pd.to_numeric(df[col_precio], errors="coerce")
        if serie_precio.isna().any():
            idx_invalido = df.index[serie_precio.isna()][0]
            val_invalido = df.loc[idx_invalido, col_precio]
            raise ValueError(
                f"Error de pre-instanciación en 'precio' (fila {idx_invalido}): valor '{val_invalido}' no es numérico."
            )
        if (serie_precio < 0).any():
            idx_neg = df.index[serie_precio < 0][0]
            val_neg = df.loc[idx_neg, col_precio]
            raise ValueError(
                f"Error de pre-instanciación en 'precio' (fila {idx_neg}): el precio no puede ser negativo ({val_neg})."
            )

        # 3. Validación de Capacidades (enteros, >= 0, capacidad_usada <= capacidad_maxima)
        for nombre_cap, col_cap in [("capacidad_maxima_avion", col_cmax), ("capacidad_usada_avion", col_cusada)]:
            serie_cap = pd.to_numeric(df[col_cap], errors="coerce")
            if serie_cap.isna().any():
                idx_inv = df.index[serie_cap.isna()][0]
                val_inv = df.loc[idx_inv, col_cap]
                raise ValueError(
                    f"Error de pre-instanciación en '{nombre_cap}' (fila {idx_inv}): valor '{val_inv}' no es numérico."
                )
            no_enteros = ~serie_cap.apply(lambda x: float(x).is_integer())
            if no_enteros.any():
                idx_inv = df.index[no_enteros][0]
                val_inv = df.loc[idx_inv, col_cap]
                raise ValueError(
                    f"Error de pre-instanciación en '{nombre_cap}' (fila {idx_inv}): valor '{val_inv}' no es un número entero."
                )
            if (serie_cap < 0).any():
                idx_neg = df.index[serie_cap < 0][0]
                val_neg = df.loc[idx_neg, col_cap]
                raise ValueError(
                    f"Error de pre-instanciación en '{nombre_cap}' (fila {idx_neg}): la capacidad no puede ser negativa ({val_neg})."
                )

        s_max = pd.to_numeric(df[col_cmax], errors="coerce")
        s_usada = pd.to_numeric(df[col_cusada], errors="coerce")
        if (s_usada > s_max).any():
            idx_inc = df.index[s_usada > s_max][0]
            raise ValueError(
                f"Error de pre-instanciación en capacidades (fila {idx_inc}): "
                f"capacidad usada ({s_usada[idx_inc]}) es mayor a capacidad máxima ({s_max[idx_inc]})."
            )

        # 4. Validación de Fechas Estipuladas (parseables, destino >= origen)
        s_fest_orig = pd.to_datetime(df[col_fest_orig], errors="coerce")
        if s_fest_orig.isna().any():
            idx_inv = df.index[s_fest_orig.isna()][0]
            val_inv = df.loc[idx_inv, col_fest_orig]
            raise ValueError(
                f"Error de pre-instanciación en 'fechayhora_origen_estipulado' (fila {idx_inv}): "
                f"valor '{val_inv}' no tiene un formato de fecha válido."
            )

        s_fest_dest = pd.to_datetime(df[col_fest_dest], errors="coerce")
        if s_fest_dest.isna().any():
            idx_inv = df.index[s_fest_dest.isna()][0]
            val_inv = df.loc[idx_inv, col_fest_dest]
            raise ValueError(
                f"Error de pre-instanciación en 'fechayhora_destino_estipulado' (fila {idx_inv}): "
                f"valor '{val_inv}' no tiene un formato de fecha válido."
            )

        if (s_fest_dest < s_fest_orig).any():
            idx_inv = df.index[s_fest_dest < s_fest_orig][0]
            raise ValueError(
                f"Error de pre-instanciación en cronología estipulada (fila {idx_inv}): "
                f"la fecha de destino estipulada ({s_fest_dest[idx_inv]}) no puede ser anterior a la de origen estipulada ({s_fest_orig[idx_inv]})."
            )