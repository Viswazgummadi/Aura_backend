from contextlib import asynccontextmanager
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import get_settings
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Late imports to avoid circular deps if any, but clean design prefers top
from app.api.endpoints import router as api_router
from app.api.settings import router as settings_router
from app.api.threads import router as threads_router
from app.api.v1.debug import router as debug_router
from app.core.settings_manager import get_settings_manager
from app.database import init_db

logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database Tables
    await init_db()
    
    # Startup validation
    settings_manager = get_settings_manager()
    config = settings_manager.get_config()
    
    try:
        logger.info(f"Performing startup health check for model: {config.active_model_id}...")
        
        # Determine API Key: Settings override > Env Var
        api_key = settings_manager.get_active_key()
        
        if not api_key:
            logger.warning("No Google API Key found in settings or environment. Chat may fail.")
        
        # Use a safe init that handles potential import/registry errors
        resolved_model = settings_manager.get_active_model_resolved_id()
        model = ChatGoogleGenerativeAI(
            model=resolved_model, 
            google_api_key=api_key,
            temperature=0
        )
        # Verify connection with a minimal token generation. 
        # Note: We use a try/except block around invocation specifically.
        if api_key:
             await model.ainvoke([HumanMessage(content="Hello")])
             logger.info("Startup check PASSED: Gemini API is accessible.")
        else:
             logger.warning("Skipping startup connection check due to missing API Key.")
             
    except Exception as e:
        logger.critical(f"Startup check FAILED: Could not access Gemini model. Error: {e}")
        logger.warning(
            "APPLICATION STARTING IN DEGRADED MODE. "
            "Chat functionality may not work. Please check your GOOGLE_API_KEY and Model configuration."
        )
    
    yield

app = FastAPI(
    title="Aura API",
    description="Backend API for Aura Personal Assistant",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(threads_router, prefix="/api/v1/threads", tags=["threads"])
app.include_router(debug_router, prefix="/api/v1/debug", tags=["debug"])

@app.get("/")
async def root():
    return {"message": "Welcome to Aura Backend", "status": "online"}

