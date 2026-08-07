"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routes
from app.routes.forensic_analysis import router as forensic_router

app = FastAPI(title="IPC Perito API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(forensic_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
