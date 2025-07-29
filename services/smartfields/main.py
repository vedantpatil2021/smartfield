import logging
import toml
import json
import time
import requests
import threading
import asyncio
import os
from typing import Optional, Dict, List, Tuple
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

# Load configuration
config_path = Path(__file__).parent.parent.parent / "config.toml"
config = toml.load(config_path)
smartfields_config = config["smartfields"]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(smartfields_config["logfile_path"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("smartfields")

# Global pipeline state
lat = None
lon = None
pipeline_running = False

# Service discovery configuration
def get_services():
    """Get service endpoints from environment variables with DNS fallback"""
    return {
        "openpasslite": os.getenv("OPENPASSLITE_URL", "openpasslite:8000"),
        "wildwings": os.getenv("WILDWINGS_URL", "wildwings:8001")
    }

async def call_service(services: Dict[str, str], service_name: str, endpoint: str, mission_name: Optional[str] = None) -> bool:
    """Call a service endpoint with appropriate parameters"""
    try:
        url = f"http://{services[service_name]}{endpoint}"
        
        # Add parameters for openpasslite service
        if service_name == "openpasslite" and endpoint == "/start_mission":
            params = {
                'name': mission_name,
                'lat': lat,
                'lon': lon
            }
            response = requests.post(url, params=params, timeout=30)
        else:
            response = requests.post(url, timeout=30)
        
        logger.info(f"Called {service_name}{endpoint} - Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error calling {service_name}{endpoint}: {e}")
        return False

async def wait_for_completion(services: Dict[str, str], service_name: str) -> bool:
    """Wait for service to complete by polling its logs endpoint"""
    logger.info(f"Waiting for {service_name} to complete...")
    
    while True:
        try:
            url = f"http://{services[service_name]}/logs"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logs = response.json()
                status = logs.get('status')
                if status == 'completed':
                    logger.info(f"{service_name} completed successfully")
                    return True
                elif status == 'failed':
                    logger.error(f"{service_name} failed")
                    return False
                # Continue waiting if still running
        except Exception as e:
            logger.warning(f"Error checking {service_name} status: {e}")
        
        await asyncio.sleep(5)

async def execute_pipeline() -> bool:
    """Execute the agricultural monitoring pipeline"""
    global pipeline_running
    try:
        pipeline_running = True
        logger.info("Starting pipeline execution")
        
        # Get service configuration
        services = get_services()
        logger.info(f"Using services: {services}")
        
        # Define pipeline flow
        flow: List[Tuple[str, str, Optional[str]]] = [
            ("openpasslite", "/start_mission", "takeoff"),
            # ("wildwings", "/start_mission", None), 
            ("openpasslite", "/start_mission", "land")
        ]
        
        # Execute each step in the pipeline
        for service, endpoint, mission_name in flow:
            logger.info(f"Starting {service}{endpoint} with mission: {mission_name}")
            
            # Call the service
            if not await call_service(services, service, endpoint, mission_name):
                logger.error(f"Failed to start {service}")
                pipeline_running = False
                return False
            
            # Wait for completion
            if not await wait_for_completion(services, service):
                logger.error(f"{service} mission failed")
                pipeline_running = False
                return False
            
            logger.info(f"{service} completed successfully")
        
        logger.info("Pipeline completed successfully")
        pipeline_running = False
        return True
        
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}")
        pipeline_running = False
        return False

def run_pipeline_background():
    """Run pipeline in background thread with async support"""
    asyncio.run(execute_pipeline())

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SmartFields service starting up")
    yield
    logger.info("SmartFields service shutting down")
    # Stop any running pipeline
    global pipeline_running
    if pipeline_running:
        logger.info("Stopping pipeline during shutdown")
        pipeline_running = False

app = FastAPI(
    title="SmartFields Service",
    description="SmartFields agricultural monitoring service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[smartfields_config["cors_origin"]],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "SmartFields Service", "status": "running"}

@app.get("/initiate_process")
async def initiate_process(
    lat: str = Query(..., description="Latitude coordinate"), 
    lon: str = Query(..., description="Longitude coordinate"), 
    camid: Optional[str] = Query(None, description="Camera trap ID")
):
    """Initiate the agricultural monitoring pipeline with coordinates"""
    global pipeline_running
    
    logger.info(f"Process initiation requested - lat: {lat}, lon: {lon}, camid: {camid}")
    
    # Check if pipeline is already running
    if pipeline_running:
        logger.warning('Pipeline request rejected - pipeline already running')
        raise HTTPException(
            status_code=409, 
            detail="Pipeline is currently running. Please wait for it to complete."
        )
    
    # Validate parameters
    try:
        float(lat)
        float(lon)
    except ValueError:
        logger.error(f'Invalid coordinates: lat={lat}, lon={lon}')
        raise HTTPException(
            status_code=400, 
            detail="lat and lon must be valid numbers"
        )
    
    # Store coordinates globally and in file
    globals()['lat'] = lat
    globals()['lon'] = lon
    
    logger.info(f'Process initiated with camera_id: {camid} and coordinates: lat={lat}, lon={lon}')
    
    # Start pipeline execution in background
    logger.info('Starting pipeline execution')
    threading.Thread(target=run_pipeline_background, name="Pipeline-Thread").start()
    
    return {
        "message": f"Process initiated with coordinates: {lat},{lon}. Pipeline started.",
        "status": "pipeline_started",
        "coordinates": {"lat": lat, "lon": lon},
        "camera_id": camid
    }

@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    """View application logs"""
    try:
        log_file = Path(smartfields_config["logfile_path"])
        if log_file.exists():
            with open(log_file, 'r') as f:
                content = f.read()
            return f'<pre>{content}</pre>'
        else:
            return '<pre>No logs yet</pre>'
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return f'<pre>Error reading logs: {e}</pre>'

@app.get("/pipeline_status")
async def pipeline_status():
    """Get current pipeline status - Production monitoring endpoint"""
    return {
        "pipeline_running": pipeline_running,
        "coordinates": {"lat": lat, "lon": lon} if lat and lon else None,
        "status": "running" if pipeline_running else "idle"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for production monitoring"""
    try:
        # Check if services are configured
        services = get_services()
        
        return {
            "status": "healthy",
            "pipeline_running": pipeline_running,
            "services_configured": list(services.keys()),
            "service": "smartfields"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/start_mission")
async def start_mission():
    logger.info("Start mission endpoint accessed")
    raise HTTPException(
        status_code=400, 
        detail="Use /initiate_process endpoint with lat, lon, and camid parameters"
    )

@app.post("/stop_mission")
async def stop_mission():
    """Stop all running missions across services"""
    logger.info("Stop mission endpoint accessed")
    
    try:
        # Load service configuration
        with open('target_ips.json', 'r') as f:
            services = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Service configuration not found")
    
    stopped_services = []
    failed_services = []
    
    # Stop missions on all services
    for service_name, ip in services.items():
        try:
            url = f"http://{ip}/stop_mission"
            response = requests.post(url, timeout=10)
            if response.status_code == 200:
                stopped_services.append(service_name)
                logger.info(f'Successfully stopped {service_name}')
            else:
                failed_services.append(service_name)
                logger.error(f'Failed to stop {service_name}: {response.status_code}')
        except Exception as e:
            failed_services.append(service_name)
            logger.error(f'Error stopping {service_name}: {e}')
    
    # Update pipeline state
    global pipeline_running
    pipeline_running = False
    
    if stopped_services:
        return {
            "message": f"Stopped missions: {', '.join(stopped_services)}",
            "stopped_services": stopped_services,
            "failed_services": failed_services,
            "status": "success"
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail="No missions were stopped"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=smartfields_config["host"],
        port=smartfields_config["port"],
        reload=smartfields_config["debug"],
        access_log=True
    )