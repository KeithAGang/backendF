#main.py file
from fastapi import FastAPI, Depends, HTTPException
import fastapi.security as _security
from typing import List
from schemas import *
import services
import models
from database import engine, _orm


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post("/users")
async def create_user(user: UserCreate, db: _orm.Session = Depends(services.get_db)):
    db_user = await services.get_user_by_email(user.email, db)
    
    if db_user:
        raise HTTPException(status_code=400, detail="Email Already In Use")
    
    created_user = await services.create_user(user, db)
    
    return await services.create_token(created_user)


@app.post("/token")
async def generate_token(form_data: _security.OAuth2PasswordRequestForm = Depends(), db: _orm.Session = Depends(services.get_db)):
    user = await services.authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Credential!")
    
    return await services.create_token(user)

@app.get("/users/me", response_model=Users)
async def get_user(current_user: Users = Depends(services.get_current_user)): # Update the dependency name
    return current_user

# @app.post("/notifications", response_model=)
# async def create_message(message: MessageCreate, user: Users = Depends(services.get_current_user), db: _orm.Session = Depends(services.get_db)):
#     return await services.generate_message(user=user, db=db, message=message)

@app.get("/notifications", response_model=List[Notification])
async def get_notifications(user: Users = Depends(services.get_current_user), db: _orm.Session = Depends(services.get_db)):
    return await services.generate_notification(user=user, db=db)

@app.get("/notification/{msg_id}", status_code=200)
async def get_specific_notification(msg_id: str, user: Users = Depends(services.get_current_user), db: _orm.Session = Depends(services.get_db)):
    return await services.get_notification(msg_id, user, db)

@app.get("/my_account", response_model=List[AccountBalance])
async def get_my_account(user: Users = Depends(services.get_current_user), db:_orm.Session = Depends(services.get_db)):
    return await services.get_account(user=user, db=db)

@app.put("/pay_now/{amount}", status_code=200)
async def pay_for_parking_now(amount: float, user: Users = Depends(services.get_current_user), db: _orm.Session = Depends(services.get_db)):
    return await services.pay_for_Lot(amount=amount, user=user, db=db)    

@app.post("/book_parking/{hours}", status_code=200)
async def book_parking_lot(hours: int, immediate_booking: bool = True, user: UserDetails = Depends(services.get_current_user), db: _orm.Session = Depends(services.get_db)):
    return await services.book_parking_lot(user=user, db=db, hours=hours, immediate_booking=immediate_booking)

@app.get("/revoke_my_resrvation")
async def revoke_my_parking_lot(user: UserDetails = Depends(services.get_current_user), db: _orm.Session = Depends(services.get_db)):
    return await services.revoke_my_reservation(user=user, db=db)

@app.get("/my_parkinglot")
async def get_me_parking_lot(user: UserDetails = Depends(services.get_current_user), db: _orm.Session = Depends(services.get_db)):
    return await services.lot_selector(user=user, db=db)


#if you want to add lots to the db, uncommnet the code below
# @app.get("/populate_lots")
# def populate_the_lots(db:_orm.Session = Depends(services.get_db)):
#     for x in range(1, 51):
#         lot = models.ParkingLots(lot_id=x)
#         db.add(lot)
#         db.commit()
#         db.refresh(lot)
#     return models.ParkingLots