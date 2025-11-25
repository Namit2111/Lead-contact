from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.auth_routes import router as auth_router
from api.routes.provider_routes import router as provider_router
from api.routes.contact_routes import router as contact_router
from api.routes.template_routes import router as template_router
from api.routes.campaign_routes import router as campaign_router
from api.routes.internal_routes import router as internal_router
from api.webhooks.trigger_webhooks import router as trigger_webhook_router
from db.mongodb.connection import mongodb_connection
from utils.logger import logger
import uvicorn


# Create FastAPI app
app = FastAPI(
    title="Lead Contact API",
    description="OAuth integration for email marketing campaigns",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("Starting Lead Contact API...")
    await mongodb_connection.connect()
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down Lead Contact API...")
    await mongodb_connection.disconnect()
    logger.info("Application shutdown complete")


# Include routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(provider_router, tags=["Providers"])
app.include_router(contact_router, tags=["Contacts"])
app.include_router(template_router, tags=["Templates"])
app.include_router(campaign_router, tags=["Campaigns"])
app.include_router(internal_router, tags=["Internal"])
app.include_router(trigger_webhook_router, tags=["Webhooks"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Lead Contact API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
