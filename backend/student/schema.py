from pydantic import BaseModel


class StudentLoginRequest(BaseModel):
    name: str
    course: str

class StudentToken(BaseModel):
    access_token: str
    token_type: str
    student_id: int
    name: str

    class Config:
        orm_mode = True