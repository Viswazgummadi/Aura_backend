from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import traceback
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import get_settings
from app.core.settings_manager import get_settings_manager

router = APIRouter()

class DebugLog(BaseModel):
    step: str
    status: str
    details: str
    timestamp: float

class DiagnoseResponse(BaseModel):
    env_api_key_present: bool
    active_model_id: str
    logs: List[Dict[str, Any]]
    success: bool

@router.get("/diagnose", response_model=DiagnoseResponse)
async def diagnose_system():
    import time
    logs = []
    
    def log(step, status, details=""):
        logs.append({
            "step": step,
            "status": status,
            "details": str(details),
            "timestamp": time.time()
        })

    # 1. Check Environment
    settings = get_settings()
    has_env_key = bool(settings.GOOGLE_API_KEY)
    log("Check Env API Key", "OK" if has_env_key else "MISSING", f"Present: {has_env_key}")

    # 2. Check Settings Manager
    try:
        settings_manager = get_settings_manager()
        config = settings_manager.get_config()
        active_model = config.active_model_id
        log("Load User Config", "OK", f"Active Model: {active_model}")
        
        # Determine effective key
        api_key = settings_manager.get_active_key()
        if not api_key:
            log("Resolve API Key", "FAIL", "No API Key found in Settings or Env")
            return DiagnoseResponse(
                env_api_key_present=has_env_key,
                active_model_id=active_model,
                logs=logs,
                success=False
            )
        else:
            masked_key = f"{api_key[:5]}...{api_key[-4:]}" if len(api_key) > 10 else "***"
            log("Resolve API Key", "OK", f"Key: {masked_key}")

    except Exception as e:
        log("Load User Config", "FAIL", traceback.format_exc())
        return DiagnoseResponse(
            env_api_key_present=has_env_key,
            active_model_id="unknown",
            logs=logs,
            success=False
        )

    # 3. Test Model Connection (Standard Invoke)
    try:
        resolved_model = settings_manager.get_active_model_resolved_id()
        log(f"Initialize Model ({resolved_model})", "START", "Attempting initialization...")
        llm = ChatGoogleGenerativeAI(
            model=resolved_model,
            google_api_key=api_key,
            temperature=0
        )
        log(f"Initialize Model ({active_model})", "OK", "Object created")
        
        log(f"Test Invoke ({active_model})", "START", "Sending 'Hello'...")
        response = await llm.ainvoke("Hello, are you online?")
        log(f"Test Invoke ({active_model})", "SUCCESS", f"Response: {response.content}")
        
    except Exception as e:
        err_str = str(e)
        status = "FAIL"
        if "429" in err_str:
            status = "QUOTA_EXCEEDED"
        elif "404" in err_str:
            status = "NOT_FOUND"
        
        log(f"Test Invoke ({active_model})", status, err_str)
        
        # 4. Try Fallback Probe if primary failed
        log("Fallback Probe", "START", "Testing gemini-1.5-flash as fallback check...")
        try:
            fallback_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash", 
                google_api_key=api_key
            )
            res = await fallback_llm.ainvoke("Ping")
            log("Fallback Probe (gemini-1.5-flash)", "SUCCESS", f"Response: {res.content}")
        except Exception as fallback_e:
            log("Fallback Probe (gemini-1.5-flash)", "FAIL", str(fallback_e))

    return DiagnoseResponse(
        env_api_key_present=has_env_key,
        active_model_id=active_model,
        logs=logs,
        success=logs[-1]["status"] == "SUCCESS" or logs[-2]["status"] == "SUCCESS" # Rough check
    )
