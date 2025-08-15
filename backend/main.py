import os
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .services.jupyter_gateway_service import JupyterGatewayService
from .services.jupyter_service import JupyterService
from .services.llm_service import LLMService
from .tools.tool_registry import ToolRegistry
from .api.routes import create_routes

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(title="LocalGPT Orchestrator", version="1.0.0")
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize services
    jupyter_gateway_service = JupyterGatewayService()
    jupyter_service = JupyterService(jupyter_gateway_service)
    tool_registry = ToolRegistry(jupyter_service)
    llm_service = LLMService(tool_registry)
    
    # Create and include API routes
    api_router = create_routes(llm_service)
    app.include_router(api_router, prefix="/api")
    
    # Serve static files for the frontend
    if os.path.exists(settings.FRONTEND_BUILD_DIR):
        app.mount("/", StaticFiles(directory=settings.FRONTEND_BUILD_DIR, html=True), name="frontend")
    
    # Background garbage collection
    def background_gc():
        while True:
            time.sleep(settings.GC_INTERVAL)
            jupyter_gateway_service.gc_idle()
    
    threading.Thread(target=background_gc, daemon=True).start()
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)