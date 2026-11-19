from datetime import date, time
from pydantic import BaseModel, Field

class EventInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    event_type: str
    event_date: date
    location: str = Field(min_length=1, max_length=200)
    guest_count: int = Field(ge=1, le=5000)
    budget: int = Field(gt=0)
    preferences: str = ""
    additional_requirements: str = ""
    food_preference: str = ""
    decoration_style: str = ""
    start_time: time = time(17, 0)
    user_id: str = "local-user"

class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

