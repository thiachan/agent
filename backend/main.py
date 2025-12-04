# Set environment variables BEFORE any imports to suppress warnings
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_CLIENT_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Suppress pydub warnings
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, documents, chat, agents, upload, generate, models, knowledge_bases
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress ChromaDB telemetry errors - these are harmless but cluttering logs
chromadb_telemetry_logger = logging.getLogger("chromadb.telemetry.product.posthog")
chromadb_telemetry_logger.setLevel(logging.CRITICAL)
chromadb_telemetry_logger.disabled = True

# Also suppress other ChromaDB telemetry loggers
chromadb_logger = logging.getLogger("chromadb.telemetry")
chromadb_logger.setLevel(logging.CRITICAL)
chromadb_logger.disabled = True

app = FastAPI(
    title="GSSO AI Center API",
    description="GSSO AI-Powered Enterprise Platform Backend",
    version="1.0.0"
)

# CORS middleware - explicitly allow Authorization header
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # This should include Authorization
    expose_headers=["*"],
)

# Middleware to log Authorization header for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    auth_header = request.headers.get("Authorization")
    if auth_header:
        logger.info(f"Request to {request.url.path} has Authorization header: {auth_header[:20]}...")
    else:
        logger.warning(f"Request to {request.url.path} has NO Authorization header")
    response = await call_next(request)
    return response

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(models.router, prefix="/api/models", tags=["Models"])
app.include_router(knowledge_bases.router, prefix="/api/knowledge-bases", tags=["Knowledge Bases"])

@app.get("/")
async def root():
    return {"message": "GSSO AI Center API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

