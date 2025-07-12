from fastapi import FastAPI
from schema import *

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

@app.post("/div")
def divsion(data: Div):
    try:
        val = data.number1 / data.number2
        return {"status":200, "Response": val}
    except:
        return {"status":400, "Response": "Bad data!"}