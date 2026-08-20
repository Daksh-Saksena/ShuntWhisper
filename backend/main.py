import uvicorn
from server import app

if __name__ == "__main__":
    print("Starting ShuntWhisper Production Backend...")
    # Run the FastAPI server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
