#models.py file
import datetime as _dt
import uuid, shortuuid
from database import _sql, _orm, Base
import passlib.hash as _hash


class User(Base):
    __tablename__ = "users"
    
    id = _sql.Column(_sql.String(100), default=lambda: str(uuid.uuid1()), primary_key=True, index=True)
    name = _sql.Column(_sql.String(255), unique=True, index=True)
    surname = _sql.Column(_sql.String(255), unique=True, index=True)
    email = _sql.Column(_sql.String(255), unique=True, index=True)
    hashed_password = _sql.Column(_sql.String(255))
    
    notifications = _orm.relationship("Notifications", back_populates="owner")
    accountbalance = _orm.relationship("AccountBalance", back_populates="owner")
    
    def verify_password(self, password: str):
        return _hash.bcrypt.verify(password, self.hashed_password)
    
class Notifications(Base):
    __tablename__ = "notifications"
    note_id = _sql.Column(_sql.String(255), default=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    user_id = _sql.Column(_sql.String(255), _sql.ForeignKey("users.id"))
    note_type = _sql.Column(_sql.String(40), default="normal")
    note_body = _sql.Column(_sql.String(255), default="")
    date_generated = _sql.Column(_sql.DateTime, default=_dt.datetime.utcnow)
    
    owner = _orm.relationship("User", back_populates="notifications")
    
class AccountBalance(Base):
    __tablename__ = "accountbalance"
    
    account_id = _sql.Column(_sql.String(255), default=lambda: str(shortuuid.uuid()), primary_key=True)
    user_id =  _sql.Column(_sql.String(255), _sql.ForeignKey("users.id"))
    balance = _sql.Column(_sql.Float, default=99.00, index=True)
    
    owner = _orm.relationship("User", back_populates="accountbalance")
    
class ParkingLots(Base):
    __tablename__ = "parkinglots"
    
    lot_id = _sql.Column(_sql.INTEGER, primary_key=True, index=True)
    lot_status = _sql.Column(_sql.String(50), default="vacant", index=True)
    
class Booking(Base):
    __tablename__ = "bookings"
    
    booking_id = _sql.Column(_sql.String(255), default=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    lot_id = _sql.Column(_sql.Integer, _sql.ForeignKey("parkinglots.lot_id"))
    user_id = _sql.Column(_sql.String(100), _sql.ForeignKey("users.id"))
    start_time = _sql.Column(_sql.DateTime)
    end_time = _sql.Column(_sql.DateTime)
