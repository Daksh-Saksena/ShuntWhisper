import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List

from physics_engine import FluidAcousticSimulator
from dsp_pipeline import AcousticDSP
from ml_engine import ShuntAnomalyDetector
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ShuntWhisper Edge-AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator = FluidAcousticSimulator(sample_rate=16000)
dsp = AcousticDSP(sample_rate=16000)
ml_model = ShuntAnomalyDetector(input_dim=10)

clients: List[WebSocket] = []

class ObstructionLevel(BaseModel):
    obstruction_level: float

@app.post("/api/set-obstruction")
async def set_obstruction(data: ObstructionLevel):
    simulator.set_obstruction(data.obstruction_level)
    return {"status": "success", "level": simulator.obstruction_level}

@app.post("/api/calibrate")
async def calibrate():
    # Trigger 10-second synthetic run of baseline laminar flow
    print("Starting calibration phase...")
    old_level = simulator.obstruction_level
    simulator.set_obstruction(0.0) # Laminar baseline
    
    # 10 seconds of data at 16000 Hz, frame size 1024
    num_frames = int((10 * 16000) / 1024)
    normal_features = []
    
    for _ in range(num_frames):
        frame, _ = simulator.generate_frame()
        dsp_result = dsp.process_frame(frame)
        normal_features.append(dsp_result["features"])
        
    ml_model.train_patient_baseline(normal_features)
    simulator.set_obstruction(old_level) # Restore
    
    print(f"Calibration complete. Calculated Threshold: {ml_model.threshold:.6f}")
    return {"status": "success", "threshold": ml_model.threshold}

@app.get("/api/export-c-header")
async def export_c_header():
    header_content = ml_model.export_to_c_array()
    return {"c_header": header_content}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            # Wait for any incoming messages from client (keep-alive)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        clients.remove(websocket)

async def telemetry_loop():
    while True:
        # Generate new physics data and process if anyone is listening
        if len(clients) > 0:
            frame, state = simulator.generate_frame()
            dsp_result = dsp.process_frame(frame)
            status, anomaly_score, mse = ml_model.predict(dsp_result["features"])
            
            # Downsample raw waveform for UI performance
            raw_waveform = frame.tolist()[::16] 
            
            payload = {
                "raw_waveform": raw_waveform,
                "fft_spectrum": dsp_result["fft_spectrum"],
                "status": status,
                "anomaly_score": anomaly_score,
                "reconstruction_loss": mse,
                "fluid_state": state,
                "obstruction_level": simulator.obstruction_level
            }
            
            # Broadcast to all clients
            for client in clients:
                try:
                    await client.send_json(payload)
                except Exception:
                    pass
                    
        # Refresh rate approx 30 Hz
        await asyncio.sleep(0.033)

@app.on_event("startup")
async def startup_event():
    # Initial fast calibration to warm up the model
    await calibrate()
    # Start the background telemetry streaming loop
    asyncio.create_task(telemetry_loop())
