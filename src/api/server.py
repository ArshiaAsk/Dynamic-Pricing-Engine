import uvicorn
from fastapi import FastAPI
from src.api.router import router

app = FastAPI(
    title="Dynamic Pricing API",
    version="1.0.0"
)

app.include_router(router, prefix="/v1")


if __name__ == "__main__":
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
