from fastapi import FastAPI


app = FastAPI(title="GDGOC Suffa API", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "Hello World from GDGOC Suffa Backend!"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

