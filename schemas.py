#schemas.py file
from models import _dt

from pydantic import BaseModel, Field

class _UserBase(BaseModel):
    email: str

class UserCreate(_UserBase):
    hashed_password: str
    name: str
    surname: str
    
    class Config:
        orm_mode = True
        
class Users(_UserBase):
    id: str
    
    
    class Config:
        orm_mode = True
        from_attributes = True
        
        
class _MessageBase(BaseModel):
    msg_type: str = Field(default="normal")
    msg_body: str
    
class MessageCreate(_MessageBase):
    pass

class Message(_MessageBase):
    user_id: str
    date_generated: _dt.datetime
    
    class Config:
        orm_mode = True
        from_attributes = True

class _Account(BaseModel):
    account_id: str
    
    
class AccountBalance(_Account):
    user_id: str
    balance: float = Field(default=99.00)
    
    class Config:
        orm_mode = True
        from_attributes = True
    
class payment(BaseModel):
    user_id: str
    amount: str
    
