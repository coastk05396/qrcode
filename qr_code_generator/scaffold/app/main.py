from fastapi import FastAPI

from .database import Base, engine
from .routes import router

# Create the SQLite tables the first time the app boots.
Base.metadata.create_all(bind=engine)

# Main FastAPI application object exposed to Uvicorn.
app = FastAPI(title="QR Code Generator Prototype")
# Register all API and redirect routes from routes.py.
app.include_router(router)
