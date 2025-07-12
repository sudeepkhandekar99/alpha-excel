from pydantic import BaseModel

# Define the request body schema
class Div(BaseModel):
    number1: float
    number2: float