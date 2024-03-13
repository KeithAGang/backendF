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
        user_obj = models.User(email = user.email, hashed_password=_hash.bcrypt.hash(user.hashed_password))
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
    except jwt.exceptions.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid Token")
    
    return schemas.Users.from_orm(user) 

async def generate_message(user: schemas.Users, db: _orm.Session, message: schemas.MessageCreate):
    try:
        message_data = message.dict()
        # message_data["date_generated"] = _dt.datetime.utcnow()  # Set the date_created field
        
        message = models.Message(**message_data, user_id=user.id)
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return schemas.Message.from_orm(message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Client error: {str(e)}")

async def get_messages(user: schemas.Users, db: _orm.Session):
    message = db.query(models.Message).filter_by(user_id=user.id)
    
    return list(map(schemas.Message.from_orm, message))

async def message_selector(msg_id: str, user: schemas.Users, db: _orm.Session):
    message =(
        db.query(models.Message)
        .filter_by(user_id = user.id)
        .filter(models.Message.msg_id == msg_id)
        .first()        
    )
    
    if message is None:
        raise HTTPException(status_code=404, detail="No Message Found!")
    
    return message

async def get_message(msg_id: str, user: schemas.Users, db):
    message = await message_selector(msg_id=msg_id, user=user, db=db)
    
    return schemas.Message.from_orm(message)

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
    generate_messages(db=db, msg_type="normal", msg_body=f"{holder.name}, Your transaction Was Successfdull")
    
    return {"message": "Transaction successful", "new_balance": new_balance}

async def generate_messages(db: _orm.Session,msg_type: str, msg_body: str, user: schemas.Users = Depends(get_current_user)):
    try:
        message_data = {"msg_type": msg_type, "msg_body": msg_body, "user_id": user.id}
        
        message = models.Message(**message_data)
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return schemas.Message.from_orm(message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Client error: {str(e)}")

async def book_parking_lot(user: schemas.Users, db: _orm.Session, hours: int):
    vacant_lots = db.query(models.ParkingLots).filter_by(lot_status="vacant").all()
    user_obj = db.query(models.User).filter(models.User.id == user.id).first()  # Fetch the user object
    
    if not vacant_lots:
        raise HTTPException(status_code=404, detail="No vacant parking lots available")
    
    selected_lot = random.choice(vacant_lots)
    
    # Assume the payment amount is based on the number of hours booked
    payment_amount = calculate_payment_amount(hours)
    
    try:
        payment_result = await pay_for_Lot(payment_amount, user=user, db=db)
        
        if "Insufficient Credits" in str(payment_result):
            raise HTTPException(status_code=400, detail="Insufficient Credits to carry out this transaction")
        
        booking_start_time = _dt.datetime.utcnow()
        booking_end_time = booking_start_time + _dt.timedelta(hours=hours)
        
        selected_lot.lot_status = "booked"
        
        booking = models.Booking(lot_id=selected_lot.lot_id, user_id=user.id, start_time=booking_start_time, end_time=booking_end_time)
        
        db.add(booking)
        db.commit()
        
        message_body = f"You have successfully reserved parking lot {selected_lot.lot_id} for ${payment_amount}."
        
        return await generate_notification(db=db, msg_type="transaction", msg_body=message_body, user=user)
    
    except HTTPException as e:
        # Undo changes if payment fails
        db.rollback()
        raise e


def calculate_payment_amount(hours: int):
    # Implement your logic to calculate the payment amount based on hours booked
    return hours * 10  # Assuming $10 per hour for parking

async def generate_notification(db: _orm.Session, msg_type: str, msg_body: str, user: schemas.Users):
    message_data = {"msg_type": msg_type, "msg_body": msg_body, "user_id": user.id}
        
    message = models.Message(**message_data)
        
    db.add(message)
    db.commit()
    db.refresh(message)
        
    return schemas.Message.from_orm(message)

