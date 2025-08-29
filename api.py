import os
from fastapi import FastAPI, HTTPException, Query, Depends, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pydantic import BaseModel

from hb_service import hb_service, dataframe_to_records


load_dotenv()


class BatchRequest(BaseModel):
    symbols: List[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    hb_service.start()
    yield
    # Shutdown
    hb_service.stop()


app = FastAPI(title="HB API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de seguridad - API PÚBLICA
# Para habilitar autenticación, descomenta las siguientes líneas:
# security = HTTPBearer()
# API_TOKEN = os.getenv("API_TOKEN", "default-secure-token-12345")

# Logging para debug
import logging
logger = logging.getLogger(__name__)
logger.info("API configurada en modo PÚBLICO - sin autenticación requerida")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica que el token de autorización sea válido.
    DESHABILITADO: Esta API es completamente pública.
    """
    # API pública - no se requiere autenticación
    return "public-access"


@app.get("/")
def root():
    return {
        "message": "HB API funcionando", 
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "options": "/options",
            "options_by_prefix": "/options/prefix/{prefix}",
            "options_by_ticker": "/options/ticker/{ticker}",
            "options_all": "/options/all",
            "stocks": "/stocks",
            "stocks_by_prefix": "/stocks/prefix/{prefix}",
            "stocks_by_ticker": "/stocks/ticker/{ticker}",
            "stocks_all": "/stocks/all",
            "securities": "/securities",
            "securities_by_ticker": "/securities/ticker/{ticker}",
            "securities_all": "/securities/all",
            "historical": "/historical/{symbol}",
            "historical_batch": "/historical/batch",
            "intraday": "/intraday/{symbol}",
            "intraday_batch": "/intraday/batch",
            "cauciones": "/cauciones",
            "config": "/config",
            "docs": "/docs"
        },
        "authentication": "API PÚBLICA - No se requiere autenticación"
    }


@app.get("/health")
def health():
    """Endpoint mejorado de health check con información detallada"""
    connection_status = hb_service.get_connection_status()
    
    # Determinar estado general
    if connection_status["connected"] and connection_status["receiving_data"]:
        status = "healthy"
    elif connection_status["connected"]:
        status = "connected_but_stale"
    else:
        status = "disconnected"
    
    return {
        "status": status,
        "connected": connection_status["connected"],
        "receiving_data": connection_status["receiving_data"],
        "last_data_received": connection_status["last_data_received"],
        "minutes_since_last_data": connection_status["minutes_since_last_data"],
        "connection_attempts": connection_status["connection_attempts"]
    }


@app.get("/options")
def get_options(
    prefix: Optional[str] = Query(None, description="Filtrar opciones por prefijo"),
    ticker: Optional[str] = Query(None, description="Filtrar opciones por ticker específico")
):
    """
    Obtiene todas las opciones o filtra por prefijo/ticker.
    
    - Sin parámetros: retorna todas las opciones (aplicando filtros por defecto)
    - prefix: filtra opciones que empiecen con el prefijo (ej: GFG)
    - ticker: filtra opciones por ticker específico
    """
    try:
        df = hb_service.get_options(prefix=prefix, ticker=ticker)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo opciones: {str(e)}")


@app.get("/options/prefix/{prefix}")
def get_options_by_prefix(prefix: str):
    """
    Obtiene opciones filtradas por prefijo específico.
    
    Ejemplo: /options/prefix/GFG retorna todas las opciones que empiecen con "GFG"
    """
    try:
        df = hb_service.get_options(prefix=prefix)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo opciones por prefijo: {str(e)}")


@app.get("/options/ticker/{ticker}")
def get_options_by_ticker(ticker: str):
    """
    Obtiene opciones por ticker específico.
    
    Ejemplo: /options/ticker/GFG24JAN17.50C retorna solo esa opción
    """
    try:
        df = hb_service.get_options(ticker=ticker)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo opción por ticker: {str(e)}")


@app.get("/options/all")
def get_all_options():
    """
    Obtiene TODAS las opciones disponibles sin filtros.
    
    Este endpoint retorna todas las opciones que están siendo monitoreadas,
    independientemente de los prefijos configurados en tickers.json.
    """
    try:
        # Pasar None para obtener todas las opciones sin filtros
        df = hb_service.get_options(prefix=None, ticker=None)
        return {
            "message": f"Todas las opciones disponibles ({len(df)} instrumentos)",
            "total_count": len(df),
            "data": dataframe_to_records(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo todas las opciones: {str(e)}")


@app.get("/stocks")
def get_stocks(
    prefix: Optional[str] = Query(None, description="Filtrar acciones por prefijo"),
    ticker: Optional[str] = Query(None, description="Filtrar acciones por ticker específico")
):
    """
    Obtiene todas las acciones o filtra por prefijo/ticker.
    
    - Sin parámetros: retorna todas las acciones (aplicando filtros por defecto)
    - prefix: filtra acciones que empiecen con el prefijo (ej: GGAL)
    - ticker: filtra acciones por ticker específico
    """
    try:
        df = hb_service.get_stocks(prefix=prefix, ticker=ticker)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo acciones: {str(e)}")


@app.get("/stocks/prefix/{prefix}")
def get_stocks_by_prefix(prefix: str):
    """
    Obtiene acciones filtradas por prefijo específico.
    
    Ejemplo: /stocks/prefix/GGAL retorna todas las acciones que empiecen con "GGAL"
    """
    try:
        df = hb_service.get_stocks(prefix=prefix)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo acciones por prefijo: {str(e)}")


@app.get("/stocks/ticker/{ticker}")
def get_stocks_by_ticker(ticker: str):
    """
    Obtiene acciones por ticker específico.
    
    Ejemplo: /stocks/ticker/GGAL retorna solo esa acción
    """
    try:
        df = hb_service.get_stocks(ticker=ticker)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo acción por ticker: {str(e)}")


@app.get("/stocks/all")
def get_all_stocks():
    """
    Obtiene TODAS las acciones disponibles sin filtros.
    
    Este endpoint retorna todas las acciones que están siendo monitoreadas,
    independientemente de los prefijos configurados en tickers.json.
    """
    try:
        # Pasar None para obtener todas las acciones sin filtros
        df = hb_service.get_stocks(prefix=None, ticker=None)
        return {
            "message": f"Todas las acciones disponibles ({len(df)} instrumentos)",
            "total_count": len(df),
            "data": dataframe_to_records(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo todas las acciones: {str(e)}")


@app.get("/securities")
def get_securities(
    ticker: Optional[str] = Query(None, description="Filtrar securities por ticker específico"),
    type: Optional[str] = Query(None, description="Tipo de security: acciones, bonos, cedears, letras, ons, panel_general")
):
    """
    Obtiene todos los securities o filtra por ticker/tipo.
    
    - Sin parámetros: retorna todos los securities
    - ticker: filtra por ticker específico
    - type: filtra por tipo de instrumento
    """
    try:
        df = hb_service.get_securities(ticker=ticker, type=type)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo securities: {str(e)}")


@app.get("/securities/ticker/{ticker}")
def get_securities_by_ticker(ticker: str):
    """
    Obtiene securities por ticker específico.
    
    Ejemplo: /securities/ticker/GGAL retorna todos los securities de GGAL
    """
    try:
        df = hb_service.get_securities(ticker=ticker)
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo securities por ticker: {str(e)}")


@app.get("/securities/all")
def get_all_securities():
    """
    Obtiene TODOS los securities disponibles sin filtros.
    
    Este endpoint retorna todos los securities que están siendo monitoreados,
    independientemente de los tipos configurados en tickers.json.
    """
    try:
        # Pasar None para obtener todos los securities sin filtros
        df = hb_service.get_securities(ticker=None, type=None)
        return {
            "message": f"Todos los securities disponibles ({len(df)} instrumentos)",
            "total_count": len(df),
            "data": dataframe_to_records(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo todos los securities: {str(e)}")


@app.get("/cauciones")
def get_cauciones():
    """
    Obtiene datos de cauciones.
    """
    try:
        df = hb_service.get_cauciones()
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo cauciones: {str(e)}")


@app.get("/status/connection")
def get_connection_status():
    """
    Obtiene el estado de conexión a HomeBroker.
    """
    try:
        status = hb_service.get_connection_status()
        return {
            "message": "Estado de conexión",
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado de conexión: {str(e)}")


@app.get("/test/simple-dates")
def test_simple_dates():
    """
    Endpoint de prueba simple para verificar fechas básicas.
    """
    try:
        result = hb_service.test_simple_dates()
        return {
            "message": "Prueba simple de fechas",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en prueba simple de fechas: {str(e)}")


@app.get("/test/dates")
def test_date_calculation(
    days: int = Query(30, description="Número de días para probar", ge=1, le=365)
):
    """
    Endpoint de prueba para verificar el cálculo de fechas.
    Útil para debugging de problemas de tipos de fecha.
    """
    try:
        result = hb_service.test_date_calculation(days)
        return {
            "message": f"Prueba de fechas para {days} días",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en prueba de fechas: {str(e)}")


@app.get("/historical/{symbol}")
def get_historical_data(
    symbol: str,
    days: int = Query(30, description="Número de días hacia atrás", ge=1, le=365),
    settlement: str = Query("24hs", description="Tipo de liquidación")
):
    """
    Obtiene datos históricos de un símbolo específico.
    
    Args:
        symbol: Símbolo del instrumento (ej: 'GGAL', 'GFG24JAN17.50C')
        days: Número de días hacia atrás (1-365)
        settlement: Tipo de liquidación ('24hs', 'SPOT', '48hs', etc.)
    """
    try:
        print(f"🔍 DEBUG: Iniciando endpoint histórico para {symbol}")
        print(f"🔍 DEBUG: Parámetros: days={days}, settlement={settlement}")
        
        # Verificar estado de conexión primero
        connection_status = hb_service.get_connection_status()
        print(f"🔍 DEBUG: Estado de conexión: {connection_status}")
        
        if not connection_status.get("connected", False):
            raise HTTPException(
                status_code=503, 
                detail="No hay conexión activa a HomeBroker. Verifica el estado en /status/connection"
            )
        
        # Obtener datos históricos
        print(f"🔍 DEBUG: Llamando a get_historical_data...")
        df = hb_service.get_historical_data(symbol, days, settlement)
        print(f"🔍 DEBUG: DataFrame obtenido: {len(df)} registros")
        
        if df.empty:
            return {
                "message": f"No se encontraron datos históricos para {symbol}",
                "symbol": symbol,
                "days": days,
                "settlement": settlement,
                "data": []
            }
        
        # Convertir a formato JSON
        print(f"🔍 DEBUG: Convirtiendo a JSON...")
        records = dataframe_to_records(df)
        print(f"🔍 DEBUG: JSON generado: {len(records)} registros")
        
        return {
            "message": f"Histórico obtenido exitosamente para {symbol}",
            "symbol": symbol,
            "days": days,
            "settlement": settlement,
            "total_records": len(records),
            "data": records
        }
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        print(f"❌ ERROR en endpoint histórico: {e}")
        print(f"❌ Tipo de error: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo histórico para {symbol}: {str(e)}")


@app.post("/historical/batch")
def get_historical_data_batch(
    request: BatchRequest,
    days: int = Query(30, description="Número de días hacia atrás", ge=1, le=365),
    settlement: str = Query("24hs", description="Tipo de liquidación (24hs, SPOT, 48hs, etc.)")
):
    """
    Obtiene datos históricos de múltiples símbolos en lote.
    
    Args:
        request: Body con lista de símbolos
        days: Número de días hacia atrás (1-365)
        settlement: Tipo de liquidación para securities
    """
    try:
        results = hb_service.get_historical_data_batch(request.symbols, days, settlement)
        
        # Convertir DataFrames a records
        formatted_results = {}
        for symbol, df in results.items():
            if not df.empty:
                formatted_results[symbol] = dataframe_to_records(df)
            else:
                formatted_results[symbol] = []
        
        return {
            "message": f"Históricos obtenidos para {len(request.symbols)} símbolos",
            "data": formatted_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo históricos en lote: {str(e)}")


@app.get("/intraday/{symbol}")
def get_intraday_data(
    symbol: str
):
    """
    Obtiene datos históricos intraday (del día actual) de un símbolo específico.
    
    Args:
        symbol: Símbolo del instrumento (ej: 'GGAL', 'GFG24JAN17.50C')
        
    Nota: Este endpoint retorna datos del día actual en tiempo real/intraday.
    """
    try:
        df = hb_service.get_intraday_history(symbol)
        if df.empty:
            return {"message": f"No se encontraron datos intraday para {symbol}", "data": []}
        return dataframe_to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo histórico intraday para {symbol}: {str(e)}")


@app.post("/intraday/batch")
def get_intraday_data_batch(
    request: BatchRequest
):
    """
    Obtiene datos históricos intraday de múltiples símbolos en lote.
    
    Args:
        request: Body con lista de símbolos
        
    Nota: Este endpoint retorna datos del día actual en tiempo real/intraday.
    """
    try:
        results = hb_service.get_intraday_history_batch(request.symbols)
        
        # Convertir DataFrames a records
        formatted_results = {}
        for symbol, df in results.items():
            if not df.empty:
                formatted_results[symbol] = dataframe_to_records(df)
            else:
                formatted_results[symbol] = []
        
        return {
            "message": f"Históricos intraday obtenidos para {len(request.symbols)} símbolos",
            "data": formatted_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo históricos intraday en lote: {str(e)}")


@app.get("/config")
def get_config():
    """
    Obtiene la configuración actual de la API con información detallada de conexión.
    """
    try:
        connection_status = hb_service.get_connection_status()
        return {
            "broker_id": hb_service.broker_id,
            "option_prefixes": hb_service.option_prefixes,
            "stock_prefixes": hb_service.stock_prefixes,
            "options_count": len(hb_service.options),
            "stocks_count": len(hb_service.get_stocks()),
            "securities_count": len(hb_service.everything),
            "cauciones_count": len(hb_service.cauciones),
            "tickers_file": os.getenv("HB_TICKERS_FILE", "tickers.json"),
            "connection_status": connection_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración: {str(e)}")


@app.post("/reconnect")
def force_reconnect():
    """
    Fuerza una reconexión manual a HomeBroker.
    Útil cuando se detecta que los datos están desactualizados.
    """
    try:
        # Marcar como desconectado para que el health monitor reconecte
        with hb_service._lock:
            hb_service._connected = False
            hb_service._connection_attempts = 0  # Resetear contador
            
        return {
            "message": "Reconexión forzada iniciada. El sistema intentará reconectar automáticamente.",
            "status": "reconnecting"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error forzando reconexión: {str(e)}")


