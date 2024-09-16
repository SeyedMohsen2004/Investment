from pydantic import BaseModel, Field

class UserCreateSchema(BaseModel):
    username: str = Field(..., min_length=4, max_length=80)
    password: str = Field(..., min_length=6, max_length=255)

    class Config:
        orm_mode = True
