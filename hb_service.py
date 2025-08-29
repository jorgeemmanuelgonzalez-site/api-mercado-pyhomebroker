import os
import json
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import pandas as pd
from pyhomebroker import HomeBroker
from dotenv import load_dotenv

import Options_Helper_HM

# Configurar logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _read_json_if_exists(path: str) -> Optional[Dict[str, Any]]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None


def _parse_prefixes_env(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def _load_option_prefixes_from_config_file() -> List[str]:
    # Usa el mismo archivo de configuración que Options_Helper_HM
    from Options_Helper_HM import TICKERS_FILE  # lazy import
    cfg = _read_json_if_exists(TICKERS_FILE) or {}
    prefixes = cfg.get("options_prefixes") or []
    if isinstance(prefixes, list):
        return [str(p) for p in prefixes if str(p).strip()]
    return []


def _load_option_prefixes_env_then_file() -> List[str]:
    # 1) Env: HB_OPTIONS_PREFIXES=GFG,GAL,ALGO
    prefixes = _parse_prefixes_env(os.getenv("HB_OPTIONS_PREFIXES"))
    if prefixes:
        return prefixes
    # 2) Archivo tickers.json -> options_prefixes
    return _load_option_prefixes_from_config_file()


def _load_stock_prefixes_from_config_file() -> List[str]:
    # Usa el mismo archivo de configuración que Options_Helper_HM
    from Options_Helper_HM import TICKERS_FILE  # lazy import
    cfg = _read_json_if_exists(TICKERS_FILE) or {}
    prefixes = cfg.get("stock_prefixes") or []
    if isinstance(prefixes, list):
        return [str(p) for p in prefixes if str(p).strip()]
    return []


def _load_stock_prefixes_env_then_file() -> List[str]:
    # 1) Env: HB_STOCK_PREFIXES=GGAL,PAMP,YPF
    prefixes = _parse_prefixes_env(os.getenv("HB_STOCK_PREFIXES"))
    if prefixes:
        return prefixes
    # 2) Archivo tickers.json -> stock_prefixes
    return _load_stock_prefixes_from_config_file()


class HBService:
    """Servicio que mantiene conexión a HomeBroker y expone snapshots en memoria.

    - Inicializa los DataFrames a partir de los tickers definidos en Excel (solo lectura)
    - Actualiza `options`, `securities` (everything) y `cauciones` vía callbacks
    - Ofrece métodos thread-safe para leer los datos
    - Incluye funcionalidades para históricos y precios de acciones
    """

    def __init__(self) -> None:
        load_dotenv()  # Carga variables desde .env si existe

        self.broker_id = int(os.getenv("HB_BROKER", "0"))
        self.dni = os.getenv("HB_DNI", "")
        self.user = os.getenv("HB_USER", "")
        self.password = os.getenv("HB_PASSWORD", "")
        self.option_prefixes: List[str] = _load_option_prefixes_env_then_file()
        self.stock_prefixes: List[str] = _load_stock_prefixes_env_then_file()
        
        # Configuración de reconexión
        self.reconnect_interval = int(os.getenv("HB_RECONNECT_INTERVAL", "30"))  # segundos
        self.max_reconnect_attempts = int(os.getenv("HB_MAX_RECONNECT_ATTEMPTS", "5"))
        self.health_check_interval = int(os.getenv("HB_HEALTH_CHECK_INTERVAL", "60"))  # segundos

        # DataFrames en memoria
        acc = Options_Helper_HM.getAccionesList()
        bonos = Options_Helper_HM.getBonosList()
        letras = Options_Helper_HM.getLetrasList()
        ons = Options_Helper_HM.getONSList()
        panel_general = Options_Helper_HM.getPanelGeneralList()
        cedears = Options_Helper_HM.getCedearsList()
        self.options = Options_Helper_HM.getOptionsList().rename(
            columns={"bid_size": "bidsize", "ask_size": "asksize"}
        )
        self.everything = pd.concat([acc, bonos, letras, panel_general, ons, cedears])
        self.cauciones = Options_Helper_HM.cauciones.copy()

        # Sincronización y estado de conexión
        self._lock = threading.RLock()
        self._hb: Optional[HomeBroker] = None
        self._thread: threading.Thread | None = None
        self._health_thread: threading.Thread | None = None
        self._connected = False
        self._last_data_received = datetime.now()
        self._connection_attempts = 0
        self._should_stop = False

    # -----------------------
    # Callbacks de HomeBroker
    # -----------------------
    def _on_options(self, online, quotes):
        with self._lock:
            try:
                # Actualizar timestamp de última recepción de datos
                self._last_data_received = datetime.now()
                
                if quotes.empty:
                    return
                    
                this_data = quotes.copy()
                this_data = this_data.drop(["expiration", "strike", "kind"], axis=1, errors='ignore')
                this_data["change"] = this_data["change"] / 100
                this_data["datetime"] = pd.to_datetime(this_data["datetime"])
                this_data = this_data.rename(columns={"bid_size": "bidsize", "ask_size": "asksize"})
                
                # Filtrado por prefijos si están configurados
                if self.option_prefixes and not this_data.empty:
                    # Asegurar que el índice sea string para el filtrado
                    idx = this_data.index.astype(str)
                    mask = pd.Series(False, index=this_data.index)
                    for prefix in self.option_prefixes:
                        if prefix:
                            mask = mask | idx.str.startswith(prefix)
                    this_data = this_data[mask]
                
                if not this_data.empty:
                    # Agregar símbolos nuevos que cumplan el filtro
                    new_index = this_data.index.difference(self.options.index)
                    if len(new_index) > 0:
                        # Filtrar solo las filas que realmente tienen datos antes de concatenar
                        new_data = this_data.loc[new_index]
                        if not new_data.empty:
                            self.options = pd.concat([self.options, new_data], axis=0)
                    # Actualizar existentes
                    self.options.update(this_data)
                    logger.debug(f"Actualizadas {len(this_data)} opciones")
                    
            except Exception as e:
                logger.error(f"Error en _on_options: {e}")
                # Continuar sin fallar

    def _on_securities(self, online, quotes):
        with self._lock:
            try:
                # Actualizar timestamp de última recepción de datos
                self._last_data_received = datetime.now()
                
                if quotes.empty:
                    return
                    
                this_data = quotes.copy()
                this_data = this_data.reset_index()
                this_data["symbol"] = this_data["symbol"] + " - " + this_data["settlement"]
                this_data = this_data.drop(["settlement"], axis=1)
                this_data = this_data.set_index("symbol")
                this_data["change"] = this_data["change"] / 100
                this_data["datetime"] = pd.to_datetime(this_data["datetime"])
                self.everything.update(this_data)
                logger.debug(f"Actualizados {len(this_data)} securities")
                
            except Exception as e:
                logger.error(f"Error en _on_securities: {e}")
                # Continuar sin fallar

    def _on_repos(self, online, quotes):
        with self._lock:
            try:
                # Actualizar timestamp de última recepción de datos
                self._last_data_received = datetime.now()
                
                if quotes.empty:
                    return
                    
                this_data = quotes.copy()
                this_data = this_data.reset_index()
                this_data = this_data.set_index("symbol")
                this_data = this_data[["PESOS" in s for s in quotes.index]]
                this_data = this_data.reset_index()
                this_data["settlement"] = pd.to_datetime(this_data["settlement"])
                this_data = this_data.set_index("settlement")
                this_data["last"] = this_data["last"] / 100
                this_data["bid_rate"] = this_data["bid_rate"] / 100
                this_data["ask_rate"] = this_data["ask_rate"] / 100
                this_data = this_data.drop(
                    ["open", "high", "low", "volume", "operations", "datetime"], axis=1
                )
                this_data = this_data[
                    ["last", "turnover", "bid_amount", "bid_rate", "ask_rate", "ask_amount"]
                ]
                self.cauciones.update(this_data)
                logger.debug(f"Actualizadas {len(this_data)} cauciones")
                
            except Exception as e:
                logger.error(f"Error en _on_repos: {e}")
                # Continuar sin fallar

    def _on_error(self, online, error):
        """Manejo de errores de HomeBroker con reconexión automática"""
        logger.error(f"HomeBroker error: {error}")
        
        # Marcar como desconectado para que el health monitor lo detecte
        with self._lock:
            self._connected = False
        
        # El health monitor se encargará de la reconexión

    # -----------------------
    # Conexión
    # -----------------------
    def _connect_and_subscribe(self) -> bool:
        """Conecta a HomeBroker y se suscribe a los feeds. Retorna True si tuvo éxito."""
        try:
            logger.info("Iniciando conexión a HomeBroker...")
            
            # Desconectar conexión previa si existe
            if self._hb:
                try:
                    self._hb.online.disconnect()
                except Exception:
                    pass
            
            hb = HomeBroker(
                int(self.broker_id),
                on_options=self._on_options,
                on_securities=self._on_securities,
                on_repos=self._on_repos,
                on_error=self._on_error,
            )
            
            # Autenticación
            logger.info(f"Autenticando con DNI: {self.dni}")
            hb.auth.login(dni=self.dni, user=self.user, password=self.password, raise_exception=True)
            
            # Conexión online
            logger.info("Conectando online...")
            hb.online.connect()
            
            # Suscripciones
            logger.info("Suscribiendo a feeds de datos...")
            hb.online.subscribe_options()
            hb.online.subscribe_securities("bluechips", "24hs")
            hb.online.subscribe_securities("bluechips", "SPOT")
            hb.online.subscribe_securities("government_bonds", "24hs")
            hb.online.subscribe_securities("government_bonds", "SPOT")
            hb.online.subscribe_securities("cedears", "24hs")
            hb.online.subscribe_securities("general_board", "24hs")
            hb.online.subscribe_securities("short_term_government_bonds", "24hs")
            hb.online.subscribe_securities("corporate_bonds", "24hs")
            hb.online.subscribe_repos()

            with self._lock:
                self._hb = hb
                self._connected = True
                self._last_data_received = datetime.now()
                self._connection_attempts = 0
                
            logger.info("✅ Conexión a HomeBroker exitosa")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a HomeBroker: {e}")
            with self._lock:
                self._connected = False
                self._connection_attempts += 1
            return False

    def _health_monitor(self) -> None:
        """Monitor de salud que verifica la conexión y reconecta automáticamente"""
        logger.info("Iniciando monitor de salud...")
        
        while not self._should_stop:
            try:
                # Verificar si han pasado demasiado tiempo sin recibir datos
                time_since_last_data = datetime.now() - self._last_data_received
                
                # Si no hemos recibido datos en los últimos 5 minutos, reconectar
                if time_since_last_data > timedelta(minutes=5):
                    logger.warning(f"Sin datos por {time_since_last_data.seconds} segundos. Intentando reconexión...")
                    self._attempt_reconnection()
                
                # Si no estamos conectados, intentar reconectar
                elif not self._connected:
                    logger.warning("Conexión perdida. Intentando reconexión...")
                    self._attempt_reconnection()
                
                # Esperar antes del próximo chequeo
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error en health monitor: {e}")
                time.sleep(self.health_check_interval)
    
    def _attempt_reconnection(self) -> None:
        """Intenta reconectar hasta el límite máximo de intentos"""
        if self._connection_attempts >= self.max_reconnect_attempts:
            logger.error(f"Máximo de intentos de reconexión alcanzado ({self.max_reconnect_attempts})")
            time.sleep(self.reconnect_interval * 2)  # Esperar más tiempo antes de resetear
            self._connection_attempts = 0  # Resetear contador
            return
        
        logger.info(f"Intento de reconexión {self._connection_attempts + 1}/{self.max_reconnect_attempts}")
        
        if self._connect_and_subscribe():
            logger.info("🔄 Reconexión exitosa")
        else:
            logger.warning(f"Reconexión fallida. Reintentando en {self.reconnect_interval} segundos...")
            time.sleep(self.reconnect_interval)

    def start(self) -> None:
        """Inicia el servicio de HomeBroker con monitoreo automático"""
        logger.info("Iniciando servicio de HomeBroker...")
        
        # Resetear flag de parada
        self._should_stop = False
        
        # Iniciar conexión principal
        if not (self._thread and self._thread.is_alive()):
            self._thread = threading.Thread(target=self._connect_and_subscribe, name="hb-thread", daemon=False)
            self._thread.start()
        
        # Iniciar monitor de salud
        if not (self._health_thread and self._health_thread.is_alive()):
            self._health_thread = threading.Thread(target=self._health_monitor, name="hb-health", daemon=False)
            self._health_thread.start()

    def stop(self) -> None:
        """Detiene el servicio de HomeBroker completamente"""
        logger.info("Deteniendo servicio de HomeBroker...")
        
        self._should_stop = True
        
        with self._lock:
            if self._hb:
                try:
                    self._hb.online.disconnect()
                    logger.info("Desconectado de HomeBroker")
                except Exception as e:
                    logger.error(f"Error desconectando: {e}")
            self._connected = False

    # -----------------------
    # Lectura
    # -----------------------
    def get_options(self, prefix: Optional[str] = None, ticker: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene opciones con filtros opcionales.
        
        Args:
            prefix: Filtrar por prefijo (ej: 'GFG')
            ticker: Filtrar por ticker específico
        """
        with self._lock:
            df = self.options.copy()
            
            if ticker:
                # Filtrar por ticker exacto
                df = df[df.index.astype(str) == ticker.upper()]
            elif prefix:
                # Filtrar por prefijo
                df = df[df.index.astype(str).str.startswith(prefix.upper())]
            elif self.option_prefixes:
                # Aplicar filtros configurados por defecto SOLO si no se especifica nada
                # Esto permite acceso completo cuando se solicita explícitamente
                mask = pd.Series(False, index=df.index)
                for pref in self.option_prefixes:
                    if pref:
                        mask = mask | df.index.astype(str).str.startswith(pref.upper())
                df = df[mask]
            # Si no hay filtros, retornar TODAS las opciones disponibles
                
            return df

    def get_securities(self, ticker: Optional[str] = None, type: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene securities con filtros opcionales.
        
        Args:
            ticker: Filtrar por ticker
            type: Filtrar por tipo (acciones, bonos, cedears, etc.)
        """
        with self._lock:
            df = self.everything.copy()
            
            if ticker:
                # Filtrar por ticker (puede ser parcial)
                df = df[df.index.astype(str).str.contains(ticker.upper(), na=False)]
            elif type:
                # Filtrar por tipo basado en el índice
                type_mapping = {
                    'acciones': [' - 24hs', ' - SPOT'],
                    'bonos': [' - 24hs', ' - SPOT'],
                    'cedears': [' - 24hs', ' - SPOT'],
                    'letras': [' - 24hs', ' - SPOT'],
                    'ons': [' - 24hs', ' - SPOT'],
                    'panel_general': [' - 24hs', ' - SPOT']
                }
                if type in type_mapping:
                    suffixes = type_mapping[type]
                    mask = df.index.astype(str).str.contains('|'.join(suffixes), na=False)
                    df = df[mask]
            # Si no hay filtros, retornar TODOS los securities disponibles
                    
            return df

    def get_stocks(self, prefix: Optional[str] = None, ticker: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene acciones (stocks) con filtros opcionales, similar a get_options.
        
        Args:
            prefix: Filtrar por prefijo (ej: 'GGAL')
            ticker: Filtrar por ticker específico
        """
        with self._lock:
            # Filtrar solo acciones del DataFrame everything
            df = self.everything.copy()
            
            # Filtrar por acciones (que tengan sufijos de 24hs o SPOT)
            action_suffixes = [' - 24hs', ' - SPOT']
            mask = df.index.astype(str).str.contains('|'.join(action_suffixes), na=False)
            df = df[mask]
            
            if ticker:
                # Filtrar por ticker exacto (sin el sufijo)
                df = df[df.index.astype(str).str.replace(' - 24hs', '').str.replace(' - SPOT', '') == ticker.upper()]
            elif prefix:
                # Filtrar por prefijo (sin el sufijo)
                df = df[df.index.astype(str).str.replace(' - 24hs', '').str.replace(' - SPOT', '').str.startswith(prefix.upper())]
            elif self.stock_prefixes:
                # Aplicar filtros configurados por defecto SOLO si no se especifica nada
                # Esto permite acceso completo cuando se solicita explícitamente
                mask = pd.Series(False, index=df.index)
                for pref in self.stock_prefixes:
                    if pref:
                        clean_index = df.index.astype(str).str.replace(' - 24hs', '').str.replace(' - SPOT', '')
                        mask = mask | clean_index.str.startswith(pref.upper())
                df = df[mask]
            # Si no hay filtros, retornar TODAS las acciones disponibles
                
            return df

    def get_cauciones(self) -> pd.DataFrame:
        with self._lock:
            return self.cauciones.copy()

    def test_simple_dates(self) -> Dict[str, Any]:
        """
        Método de prueba simple para verificar fechas básicas.
        """
        try:
            # Crear fechas simples
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            
            result = {
                "now_type": type(now).__name__,
                "yesterday_type": type(yesterday).__name__,
                "now_str": now.strftime('%Y-%m-%d %H:%M:%S'),
                "yesterday_str": yesterday.strftime('%Y-%m-%d %H:%M:%S'),
                "difference_days": (now - yesterday).days
            }
            
            logger.info(f"Prueba simple de fechas: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error en prueba simple de fechas: {e}")
            return {"error": str(e)}

    def test_date_calculation(self, days: int = 30) -> Dict[str, Any]:
        """
        Método de prueba para verificar el cálculo de fechas.
        Útil para debugging de problemas de tipos de fecha.
        """
        try:
            # Usar datetime.now() directamente, no importar de nuevo
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            # Verificar tipos antes de hacer operaciones
            if not isinstance(to_date, datetime) or not isinstance(from_date, datetime):
                raise Exception(f"Tipos de fecha incorrectos: to_date={type(to_date)}, from_date={type(from_date)}")
            
            result = {
                "to_date": to_date.isoformat(),
                "to_date_type": type(to_date).__name__,
                "from_date": from_date.isoformat(),
                "from_date_type": type(from_date).__name__,
                "days_difference": (to_date - from_date).days,
                "from_date_str": from_date.strftime('%Y-%m-%d %H:%M:%S'),
                "to_date_str": to_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"Prueba de fechas: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error en prueba de fechas: {e}")
            return {"error": str(e)}

    def get_historical_data(self, symbol: str, days: int = 30, settlement: str = "24hs") -> pd.DataFrame:
        """
        Obtiene datos históricos de un símbolo específico.
        
        Args:
            symbol: Símbolo del instrumento (ej: 'GGAL', 'GFG24JAN17.50C')
            days: Número de días hacia atrás
            settlement: Tipo de liquidación ('24hs', 'SPOT', '48hs', etc.)
        """
        try:
            print(f"🔍 DEBUG: Iniciando get_historical_data para {symbol}")
            
            # Validar que el símbolo no sea una palabra reservada
            reserved_words = ['batch', 'all', 'options', 'stocks', 'securities', 'historical', 'intraday']
            if symbol.lower() in reserved_words:
                raise Exception(f"'{symbol}' es una palabra reservada y no puede ser un símbolo válido")
            
            print(f"🔍 DEBUG: Símbolo validado: {symbol}")
            
            if not self._hb or not self._connected:
                raise Exception("No hay conexión activa a HomeBroker")
            
            print(f"🔍 DEBUG: Conexión verificada: _hb={self._hb is not None}, connected={self._connected}")
            
            logger.info(f"Obteniendo histórico para {symbol} - {days} días - {settlement}")
            
            # Calcular fechas para get_daily_history
            # Usar datetime.now() directamente, no importar de nuevo
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            print(f"🔍 DEBUG: Fechas calculadas - to_date: {to_date} ({type(to_date)}), from_date: {from_date} ({type(from_date)})")
            
            # Verificar tipos antes de hacer operaciones
            if not isinstance(to_date, datetime) or not isinstance(from_date, datetime):
                raise Exception(f"Tipos de fecha incorrectos: to_date={type(to_date)}, from_date={type(from_date)}")
            
            # CONVERTIR A DATE para evitar el error de pyhomebroker
            from_date_date = from_date.date()
            to_date_date = to_date.date()
            
            print(f"🔍 DEBUG: Fechas convertidas a date - from_date: {from_date_date} ({type(from_date_date)}), to_date: {to_date_date} ({type(to_date_date)})")
            
            logger.info(f"Fechas calculadas: desde {from_date_date.strftime('%Y-%m-%d')} hasta {to_date_date.strftime('%Y-%m-%d')}")
            
            print(f"🔍 DEBUG: Llamando a self._hb.history.get_daily_history...")
            
            # Usar el método correcto que existe en pyhomebroker
            # get_daily_history requiere: symbol, from_date, to_date
            # PASAR FECHAS COMO DATE, NO COMO DATETIME
            df = self._hb.history.get_daily_history(symbol, from_date_date, to_date_date)
            
            print(f"🔍 DEBUG: Resultado de get_daily_history: {df is not None}, empty: {df.empty if df is not None else 'N/A'}")
            
            if df is not None and not df.empty:
                # Limpiar y formatear datos
                df = df.reset_index()
                
                # Asegurar que datetime existe y es válido
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df = df.sort_values('datetime')
                elif 'date' in df.columns:
                    df['datetime'] = pd.to_datetime(df['date'])
                    df = df.sort_values('datetime')
                
                # Convertir porcentajes si existen
                if 'change' in df.columns:
                    df['change'] = df['change'] / 100
                
                logger.info(f"✅ Histórico procesado exitosamente para {symbol}: {len(df)} registros")
                return df
            else:
                logger.warning(f"No se encontraron datos históricos para {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ ERROR en get_historical_data: {e}")
            print(f"❌ Tipo de error: {type(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            logger.error(f"Error obteniendo histórico para {symbol}: {e}")
            raise Exception(f"Error obteniendo histórico: {str(e)}")

    def get_historical_data_batch(self, symbols: List[str], days: int = 30, settlement: str = "24hs") -> Dict[str, pd.DataFrame]:
        """
        Obtiene datos históricos de múltiples símbolos en lote.
        
        Args:
            symbols: Lista de símbolos
            days: Número de días hacia atrás
            settlement: Tipo de liquidación para securities
        """
        results = {}
        
        for symbol in symbols:
            try:
                df = self.get_historical_data(symbol, days, settlement)
                if not df.empty:
                    results[symbol] = df
            except Exception as e:
                logger.error(f"Error obteniendo histórico para {symbol}: {e}")
                results[symbol] = pd.DataFrame()  # DataFrame vacío en caso de error
        
        return results

    def get_intraday_history(self, symbol: str) -> pd.DataFrame:
        """
        Obtiene datos históricos intraday (del día actual) de un símbolo específico.
        
        Args:
            symbol: Símbolo del instrumento (ej: 'GFG24JAN17.50C', 'GGAL')
        """
        try:
            if not self._hb or not self._connected:
                raise Exception("No hay conexión activa a HomeBroker")
            
            logger.info(f"Obteniendo histórico intraday para {symbol}")
            
            # Calcular fechas para get_intraday_history (día actual)
            # Usar datetime.now() directamente, no importar de nuevo
            to_date = datetime.now()
            from_date = to_date.replace(hour=0, minute=0, second=0, microsecond=0)  # Inicio del día
            
            # Verificar tipos antes de hacer operaciones
            if not isinstance(to_date, datetime) or not isinstance(from_date, datetime):
                raise Exception(f"Tipos de fecha incorrectos: to_date={type(to_date)}, from_date={type(from_date)}")
            
            # CONVERTIR A DATE para evitar el error de pyhomebroker
            from_date_date = from_date.date()
            to_date_date = to_date.date()
            
            logger.info(f"Fechas intraday: desde {from_date_date.strftime('%Y-%m-%d %H:%M:%S')} hasta {to_date_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Usar el método correcto que existe en pyhomebroker
            # get_intraday_history requiere: symbol, from_date, to_date
            # PASAR FECHAS COMO DATE, NO COMO DATETIME
            df = self._hb.history.get_intraday_history(symbol, from_date_date, to_date_date)
            
            if df is not None and not df.empty:
                # Limpiar y formatear datos
                df = df.reset_index()
                
                # Asegurar que datetime existe y es válido
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df = df.sort_values('datetime')
                elif 'date' in df.columns:
                    df['datetime'] = pd.to_datetime(df['date'])
                    df = df.sort_values('datetime')
                
                # Convertir porcentajes si existen
                if 'change' in df.columns:
                    df['change'] = df['change'] / 100
                
                logger.info(f"✅ Intraday procesado exitosamente para {symbol}: {len(df)} registros")
                return df
            else:
                logger.warning(f"No se encontraron datos intraday para {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error obteniendo histórico intraday para {symbol}: {e}")
            raise Exception(f"Error obteniendo histórico intraday: {str(e)}")

    def get_intraday_history_batch(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Obtiene datos históricos intraday de múltiples símbolos en lote.
        
        Args:
            symbols: Lista de símbolos
        """
        results = {}
        
        for symbol in symbols:
            try:
                df = self.get_intraday_history(symbol)
                if not df.empty:
                    results[symbol] = df
            except Exception as e:
                logger.error(f"Error obteniendo histórico intraday para {symbol}: {e}")
                results[symbol] = pd.DataFrame()  # DataFrame vacío en caso de error
        
        return results

    def is_connected(self) -> bool:
        """Verifica si la conexión está activa y recibiendo datos"""
        with self._lock:
            if not self._connected:
                return False
            
            # Verificar si hemos recibido datos recientemente
            time_since_last_data = datetime.now() - self._last_data_received
            return time_since_last_data < timedelta(minutes=10)  # 10 minutos es el límite
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Obtiene información detallada del estado de conexión"""
        with self._lock:
            time_since_last_data = datetime.now() - self._last_data_received
            
            return {
                "connected": self._connected,
                "receiving_data": time_since_last_data < timedelta(minutes=5),
                "last_data_received": self._last_data_received.isoformat(),
                "minutes_since_last_data": int(time_since_last_data.total_seconds() / 60),
                "connection_attempts": self._connection_attempts,
                "max_reconnect_attempts": self.max_reconnect_attempts,
                "reconnect_interval": self.reconnect_interval,
                "health_check_interval": self.health_check_interval
            }


# Instancia singleton para usar desde la API
hb_service = HBService()


def dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convierte DataFrame a lista de dicts con fechas serializadas a ISO-8601."""
    try:
        safe_df = df.reset_index()
        
        # Reemplaza valores problemáticos para JSON
        for col in safe_df.columns:
            if safe_df[col].dtype in ['float64', 'float32']:
                # Reemplaza inf, -inf, NaN por None
                safe_df[col] = safe_df[col].replace([float('inf'), float('-inf')], None)
                safe_df[col] = safe_df[col].where(pd.notna(safe_df[col]), None)
                
                # Reemplaza valores muy grandes por None
                safe_df[col] = safe_df[col].apply(
                    lambda x: None if isinstance(x, (int, float)) and (abs(x) > 1e15 or x == 0 and pd.isna(x)) else x
                )
            elif safe_df[col].dtype in ['int64', 'int32']:
                # Reemplaza valores muy grandes por None
                safe_df[col] = safe_df[col].apply(
                    lambda x: None if isinstance(x, (int, float)) and abs(x) > 1e15 else x
                )
        
        # Reemplaza NaN/NaT por None para JSON válido
        safe_df = safe_df.where(pd.notna(safe_df), None)
        
        result = safe_df.to_dict(orient="records")
        
        # Limpia valores problemáticos en el resultado final
        for row in result:
            for key, value in list(row.items()):
                if isinstance(value, pd.Timestamp):
                    row[key] = value.isoformat()
                elif isinstance(value, (int, float)):
                    if pd.isna(value) or value == float('inf') or value == float('-inf') or abs(value) > 1e15:
                        row[key] = None
                elif value == "nan" or value == "inf" or value == "-inf":
                    row[key] = None
                    
        return result
        
    except Exception as e:
        print(f"Error serializando DataFrame: {e}")
        # Retorna lista vacía en caso de error
        return []

    
    


