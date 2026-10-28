import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

from routes.routes import router
from utilities.db import pool

load_dotenv()

PORT = int(os.getenv("PORT", 5000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    yield
    await pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/db-check")
async def db_check():
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT 1")
        return {"ok": (await cur.fetchone())[0] == 1}


app.include_router(router)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request, err):
    print("HTTP Error:", err)
    return JSONResponse(
        status_code=err.status_code,
        content={"error": {"message": str(err.detail) or "Internal Server Error"}},
    )


@app.exception_handler(Exception)
async def global_error_handler(request, err):
    print("Internal Server Error:", err)
    return JSONResponse(
        status_code=500,
        content={"error": {"message": str(err) or "Internal Server Error"}},
    )


if __name__ == "__main__":
    print(f"Server listening on port {PORT}")
    uvicorn.run("server:app", port=PORT, reload=True)