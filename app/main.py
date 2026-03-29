from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from core.agent import plan_trip

app = FastAPI(title="TouristGuide Agent API")


class TripRequest(BaseModel):
    city: Optional[str] = None
    budget: Optional[float] = None
    from_currency: Optional[str] = None
    to_currency: Optional[str] = "USD"
    message: Optional[str] = None   # natural language input (uses LLM planner)


@app.get("/")
def root():
    return {"message": "TouristGuide API is running"}


@app.post("/plan-trip")
def create_trip(request: TripRequest):
    result = plan_trip(request.model_dump(exclude_none=True))
    return result
