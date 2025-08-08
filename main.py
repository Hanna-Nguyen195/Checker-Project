from fastapi import FastAPI

app = FastAPI(
    title="Checker Project",
    description="check document",
    version="0.1.0"
)

@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
