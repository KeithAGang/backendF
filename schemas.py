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

class UserDetails(_UserBase):
    id: str
    name: str
    surname: str
    
    class Config:
        orm_mode = True
        from_attributes = True
        
class _NotificationBase(BaseModel):
    note_type: str = Field(default="normal")
    note_body: str
    
class NotificationCreate(_NotificationBase):
    pass

class Notification(_NotificationBase):
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
    
class ParkingLots(BaseModel):
    pass

class Booking(BaseModel):
    lot_id: int
    user_id: str
    start_time: _dt.datetime
    end_time: _dt.datetime
    
    class Config:
        from_attributes = True
        orm_mode = True
