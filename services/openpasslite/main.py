import logging
import toml
from AnafiController import AnafiController
import threading
import importlib
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

# Load configuration
config_path = Path("/app/config.toml")
if not config_path.exists():
    config_path = Path(__file__).parent.parent.parent / "config.toml"
config = toml.load(config_path)
openpasslite_config = config["openpasslite"]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(openpasslite_config["logfile_path"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("openpasslite")

# Global mission state
mission_thread = None
stop_mission_flag = threading.Event()

def run_mission_background(mission_name: str, lat: Optional[str], long: Optional[str]):
    """Execute mission in background thread"""
    global stop_mission_flag
    try:
        if stop_mission_flag.is_set():
            logger.info(f"Mission {mission_name} stopped before execution")
            return
        
        logger.info(f"Starting mission: {mission_name}")
        mission_module = importlib.import_module(f"mission.{mission_name}")

        drone = AnafiController()
        
        if hasattr(mission_module, 'run'):
            logger.info(f"Executing mission {mission_name}")
            mission_module.run(drone)
            logger.info(f"Mission {mission_name} completed")
        else:
            raise Exception(f"'run(drone)' not defined in mission.{mission_name}")
            
    except Exception as e:
        logger.error(f"Mission {mission_name} failed: {str(e)}")
    finally:
        stop_mission_flag.clear()
        logger.info(f"Mission {mission_name} thread finished")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OpenPassLite service starting up")
    yield
    logger.info("OpenPassLite service shutting down")
    # Ensure any running mission is stopped on shutdown
    global mission_thread, stop_mission_flag
    if mission_thread and mission_thread.is_alive():
        logger.info("Stopping running mission during shutdown")
        stop_mission_flag.set()
        mission_thread.join(timeout=5.0)

app = FastAPI(
    title="OpenPassLite Service",
    description="OpenPassLite drone control service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[openpasslite_config["cors_origin"]],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Serve the main HTML interface"""
    logger.info("Root endpoint accessed - serving index.html")
    html_path = Path(__file__).parent / "index.html"
    logger.info(html_path)
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    return {"message": "OpenPassLite Service", "status": "running"}

@app.get("/missions")
async def get_missions():
    """Get list of available missions from mission folder"""
    logger.info("Missions endpoint accessed")
    
    try:
        mission_dir = Path(__file__).parent / "mission"
        
        if not mission_dir.exists():
            logger.error("Mission directory not found")
            return []
        
        missions = []
        for file in mission_dir.glob("*.py"):
            if file.name != "__init__.py":
                mission_name = file.stem
                missions.append(mission_name)
        
        logger.info(f"Found {len(missions)} missions: {missions}")
        return sorted(missions)
        
    except Exception as e:
        logger.error(f"Failed to get missions: {str(e)}")
        return ["takeoff", "land"]  # fallback missions

@app.post("/start_mission")
async def start_mission(name: str, lat: Optional[str] = None, long: Optional[str] = None):
    """Start a mission by name with optional coordinates"""
    logger.info(f"Start mission endpoint accessed - Mission: {name}")
    
    global mission_thread, stop_mission_flag
    
    if not name:
        logger.error("Mission name is required")
        raise HTTPException(status_code=400, detail="Mission name is required")
    
    if mission_thread and mission_thread.is_alive():
        logger.error("Mission already running")
        raise HTTPException(status_code=400, detail="Mission already running")
    
    try:
        # Clear any previous stop flag and start new mission
        stop_mission_flag.clear()
        mission_thread = threading.Thread(
            target=run_mission_background, 
            args=(name, lat, long),
            name=f"Mission-{name}"
        )
        mission_thread.start()
        
        logger.info(f"Mission {name} started successfully")
        return {
            "status": "success", 
            "message": f"Mission '{name}' started",
            "mission_name": name,
            "coordinates": {"lat": lat, "long": long} if lat and long else None
        }
        
    except Exception as e:
        logger.error(f"Failed to start mission {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start mission: {str(e)}")

@app.post("/stop_mission")
async def stop_mission():
    """Stop the currently running mission"""
    logger.info("Stop mission endpoint accessed")
    
    global mission_thread, stop_mission_flag
    
    if not mission_thread or not mission_thread.is_alive():
        logger.error("No mission currently running")
        raise HTTPException(status_code=400, detail="No mission currently running")
    
    try:
        stop_mission_flag.set()
        logger.info("Mission stop signal sent")
        return {
            "status": "success", 
            "message": "Mission stop requested"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop mission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop mission: {str(e)}")

@app.get("/mission_status")
async def mission_status():
    """Get current mission status"""
    global mission_thread, stop_mission_flag
    
    if mission_thread and mission_thread.is_alive():
        status = "running"
        if stop_mission_flag.is_set():
            status = "stopping"
    else:
        status = "idle"
    
    return {
        "status": status,
        "thread_alive": mission_thread.is_alive() if mission_thread else False,
        "stop_requested": stop_mission_flag.is_set()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=openpasslite_config["host"],
        port=openpasslite_config["port"],
        reload=openpasslite_config["debug"],
        access_log=True
    )