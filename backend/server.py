import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from routes import route
from dotenv import load_dotenv
load_dotenv()

PORT = os.getenv('PORT')
print(PORT)


app = FastAPI()

# Register API Routes
app.include_router()


# Global Error Handler Middleware
@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request, err):
    print("Internal Server Error:", err)
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
    PORT = int(os.environ.get("PORT", 3000))
    print(f"Server listening on port {PORT}")
    uvicorn.run(app, port=PORT)
