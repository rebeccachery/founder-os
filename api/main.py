import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agents, data
from lib.db import init_db, seed_demo_data

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.getenv("SEED_DEMO_DATA", "true").lower() == "true":
        from lib.db import get_connection

        with get_connection() as conn:
            seed_demo_data(conn)
    yield


app = FastAPI(
    title="Founder OS",
    description="Internal operating system for solo founders",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(agents.router)


@app.get("/health")
def health():
    return {"status": "ok"}
