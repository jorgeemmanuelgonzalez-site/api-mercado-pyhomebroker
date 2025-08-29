#!/usr/bin/env python3
"""
Configuración para uvicorn con opciones optimizadas para desarrollo y producción.
"""

import uvicorn
from api import app

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Hot reload para desarrollo
        workers=1,    # Un worker para evitar problemas con HomeBroker
        log_level="info",
        access_log=True,
        use_colors=True
    )
