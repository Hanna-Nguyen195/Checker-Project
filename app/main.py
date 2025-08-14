from fastapi import FastAPI
from app.api.v1.endpoints import auth, users
import logging
logging.getLogger("passlib").setLevel(logging.ERROR)

app = FastAPI(title="checker-project API", version="0.1.0")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
