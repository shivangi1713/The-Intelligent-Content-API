from typing import Optional

from pydantic import BaseModel


class ContentCreate(BaseModel):
    text: str


class ContentOut(BaseModel):
    id: int
    text: str
    summary: Optional[str] = None
    sentiment: Optional[str] = None

    class Config:
        from_attributes = True
