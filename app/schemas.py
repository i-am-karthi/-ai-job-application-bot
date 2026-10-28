from pydantic import BaseModel, HttpUrl, Field
class JobCreate(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    company:str=Field(min_length=1,max_length=200)
    location:str=""
    url:HttpUrl
    description:str=""
    source:str="manual"
class StatusUpdate(BaseModel):
    status:str
