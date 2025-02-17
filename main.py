# main.py (located in myproject/)

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.api import route  # Importing the router from the backend package

app = FastAPI(title="QR Code Generator")

# CORS Configuration (if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production use
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routes under the /qr prefix.
app.include_router(route.router, prefix="/qr", tags=["QR Code"])

# Determine the path to the frontend folder (which is in the root, sibling to backend)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")

# Option 1: Mount the frontend folder as static files (assets will be available at /static)
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Option 2: Serve the index.html at a dedicated endpoint (e.g., /home)
@app.get("/home", include_in_schema=False)
def get_index():
    index_file = os.path.join(frontend_path, "index.html")
    return FileResponse(index_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
