#serveces.py file
import jwt, random
from main import _security, Depends, HTTPException
from database import _orm, engine, SessionLocal, Base
import models, schemas
import passlib.hash as _hash
import datetime as _dt

JWT_SECRET = "myjwtsecret"

oauth2schema = _security.OAuth2PasswordBearer(tokenUrl="/token")

def create_database():
    return Base.metadata.create_all(bind = engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
async def get_user_by_email(email: str, db: _orm.Session):
    return db.query(models.User).filter(models.User.email == email).first()

async def create_user(user: schemas.UserCreate, db: _orm.Session):
    try:
        hashed_password = _hash.bcrypt.hash(user.hashed_password)
        user_data = user.model_dump()
        user_data.pop('hashed_password')  # Remove hashed_password from user_data
        
        user_obj = models.User(hashed_password=hashed_password, **user_data)
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)
        
        user_account = models.AccountBalance(user_id=user_obj.id)
        db.add(user_account)
        db.commit()
        db.refresh(user_account)
        
        return user_obj
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Client error: {str(e)}")

async def authenticate_user(email:str, password:str, db: _orm.Session):
    user = await get_user_by_email(db=db, email=email)
    
    if not user:
        return False
    
    if not user.verify_password(password):
        return False
    
    return user

async def create_token(user: models.User):
    token_payload = {"id": str(user.id)}
    token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}

async def get_current_user(db: _orm.Session = Depends(get_db), token: str = Depends(oauth2schema)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = db.query(models.User).get(payload["id"])
        
        if user:
            user_details = schemas.UserDetails(id=user.id, name=user.name, surname=user.surname, email=user.email)
            return schemas.UserDetails.from_orm(user) 
        else:
            raise HTTPException(status_code=404, detail="User not found")
    
    except jwt.exceptions.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid Token")

async def get_notifications(user: schemas.Users, db: _orm.Session):
    note = db.query(models.Notifications).filter_by(user_id=user.id)
    
    return list(map(schemas.Notification.from_orm, note))

async def notification_selector(note_id: str, user: schemas.Users, db: _orm.Session):
    note =(
        db.query(models.Notifications)
        .filter_by(user_id = user.id)
        .filter(models.Notifications.note_id == note_id)
        .first()        
    )
    
    if note is None:
        raise HTTPException(status_code=404, detail="No Notifications Found!")
    
    return note

async def get_notification(note_id: str, user: schemas.Users, db):
    note = await notification_selector(note_id=note_id, user=user, db=db)
    
    return schemas.Notification.from_orm(note)

async def get_account(user: schemas.Users, db: _orm.Session):
    account = db.query(models.AccountBalance).filter_by(user_id=user.id)
    
    return list(map(schemas.AccountBalance.from_orm, account))

async def pay_for_Lot(amount: float, user: schemas.Users, db: _orm.Session):
    account = db.query(models.AccountBalance).filter_by(user_id=user.id).first()
    holder = db.query(models.User).filter_by(id=user.id).first()
    
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.balance == 0 or account.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient Credits to carry out this transaction")
    
    new_balance = account.balance - amount
    account.balance = new_balance
    
    db.commit()  # Commit the changes to update the balance in the database
    await generate_notification(db=db, user=user, note_type="normal", note_body=f"{holder.name}, Your transaction Was Successfdull")
    
    return {"message": "Transaction successful", "new_balance": new_balance}

async def book_parking_lot(user: schemas.Users, db: _orm.Session, hours: int, immediate_booking: bool):
    vacant_lots = db.query(models.ParkingLots).filter_by(lot_status="vacant").all()
    user_obj = db.query(models.User).filter(models.User.id == user.id).first()  # Fetch the user object
    
    if not vacant_lots:
        raise HTTPException(status_code=404, detail="No vacant parking lots available")
    
    selected_lot = random.choice(vacant_lots)
    
    # Assume the payment amount is based on the number of hours booked
    payment_amount = calculate_payment_amount(hours)
    
    try:
        if immediate_booking:
            payment_result = await pay_for_Lot(payment_amount, user=user, db=db)
            
            if "Insufficient Credits" in str(payment_result):
                raise HTTPException(status_code=400, detail="Insufficient Credits to carry out this transaction")
            
            booking_start_time = _dt.datetime.utcnow()
            booking_end_time = booking_start_time + _dt.timedelta(hours=hours)
            
            selected_lot.lot_status = "booked"
            
            booking = models.Booking(lot_id=selected_lot.lot_id, user_id=user.id, start_time=booking_start_time, end_time=booking_end_time)
            
            db.add(booking)
            db.commit()
            
            note_body = f"{user_obj.name}, You have successfully booked parking lot {selected_lot.lot_id} for {hours} hours for ${payment_amount}."
        else:
            note_body = f"{user_obj.name}, You have successfully reserved parking lot {selected_lot.lot_id} for {hours} hours."
        
        return await generate_notification(db=db, note_type="transaction", note_body=note_body, user=user)
    
    except HTTPException as e:
        # Undo changes if payment fails
        db.rollback()
        raise e

def calculate_payment_amount(hours: int):
    # Implement your logic to calculate the payment amount based on hours booked
    return hours * 10  # Assuming $10 per hour for parking

async def generate_notification(db: _orm.Session, note_type: str, note_body: str, user: schemas.Users):
    note_data = {"note_type": note_type, "note_body": note_body, "user_id": user.id}
        
    note = models.Notifications(**note_data)
        
    db.add(note)
    db.commit()
    db.refresh(note)
        
    return schemas.Notification.from_orm(note)

async def revoke_my_reservation(user: schemas.UserDetails, db: _orm.Session):
    # Find the booking based on the user's user_id
    booking = db.query(models.Booking).filter(models.Booking.user_id == user.id).first()

    if booking:
        lot_id = booking.lot_id

        # Update the lot_status for the identified lot_id to vacant
        parking_lot = db.query(models.ParkingLots).filter(models.ParkingLots.lot_id == lot_id).first()
        
        if parking_lot:
            parking_lot.lot_status = "vacant"
            db.delete(booking)
            db.commit()
            return f"Booking successfully unreserved. Parking lot {parking_lot.lot_id} is now vacant."
        else:
            return "Parking lot not found."
    else:
        return "Booking not found for the user."
    
async def lot_selector(user: schemas.Users, db: _orm.Session):
    booked_lot = db.query(models.Booking).filter(models.Booking.user_id == user.id).first()
    
    if not booked_lot:
        raise HTTPException(status_code=404, detail="No Lots For This User Found!, Please Consider Making A Reservation")
    note =(
        db.query(models.ParkingLots)
        .filter(models.ParkingLots.lot_id == booked_lot.lot_id)
        .first()        
    )
    
    if note is None:
        raise HTTPException(status_code=404, detail="No Lots For This User Found!, Please Consider Making A Reservation")
    
    return note

# async def generate_notifications(db: _orm.Session,note_type: str, note_body: str, user: schemas.Users = Depends(get_current_user)):
#     try:
#         message_data = {"note_type": note_type, "note_body": note_body, "user_id": user.id}
        
#         message = models.Message(**message_data)
        
#         db.add(message)
#         db.commit()
#         db.refresh(message)
        
#         return schemas.Message.from_orm(message)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Client error: {str(e)}")

# async def generate_notification(user: schemas.Users, db: _orm.Session, note: schemas.NotificationCreate):
#     try:
#         data = note.dict()
#         # message_data["date_generated"] = _dt.datetime.utcnow()  # Set the date_created field
        
#         notedata = models.Notifications(**data, user_id=user.id)
        
#         db.add(notedata)
#         db.commit()
#         db.refresh(notedata)
        
#         return schemas.Notification.from_orm(notedata)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Client error: {str(e)}")