# app/main.py
import random
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
import os

# === Настройки подключения к БД ===
DATABASE_URL = "postgresql://smarthome_user:securepassword123@postgres:5432/smarthome_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="Smart Home Sensor API", version="1.0")

# === Pydantic модели ===
class SensorBase(BaseModel):
    name: str
    type: str
    location: str
    unit: str

class SensorCreate(SensorBase):
    pass

class SensorUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    unit: Optional[str] = None

class SensorValueUpdate(BaseModel):
    value: Optional[float] = None
    status: Optional[str] = None

class Sensor(SensorBase):
    id: int
    value: Optional[float] = None
    status: str

    class Config:
        from_attributes = True  # Pydantic v2: замена orm_mode

# === SQLAlchemy модель (должна быть определена до создания таблиц) ===
from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class SensorDB(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="active")

# === Зависимость для получения сессии БД ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Инициализация БД при старте ===
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# === Health Check ===
@app.get("/health")
def health():
    return {"status": "ok"}

# === CRUD: Сенсоры ===
@app.post("/api/v1/sensors", response_model=Sensor, status_code=201)
def create_sensor(sensor: SensorCreate, db: Session = Depends(get_db)):
    db_sensor = SensorDB(**sensor.dict(), value=None, status="active")
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@app.get("/api/v1/sensors", response_model=List[Sensor])
def get_all_sensors(db: Session = Depends(get_db)):
    sensors = db.query(SensorDB).all()
    # Автообновление температуры только для сенсоров типа "temperature"
    for sensor in sensors:
        if sensor.type.lower() == "temperature":
            sensor.value = round(random.uniform(-15.0, 30.0), 2)
    return sensors

@app.get("/api/v1/sensors/{sensor_id}", response_model=Sensor)
def get_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(SensorDB).filter(SensorDB.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Обновляем значение температуры при каждом запросе (если это датчик температуры)
    if sensor.type.lower() == "temperature":
        sensor.value = round(random.uniform(-15.0, 30.0), 2)
        db.commit()  # Сохраняем новое значение в БД (опционально)

    return sensor

@app.put("/api/v1/sensors/{sensor_id}")
def update_sensor(sensor_id: int, sensor_update: SensorUpdate, db: Session = Depends(get_db)):
    sensor = db.query(SensorDB).filter(SensorDB.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    for key, value in sensor_update.dict(exclude_unset=True).items():
        setattr(sensor, key, value)
    db.commit()
    return sensor

@app.delete("/api/v1/sensors/{sensor_id}")
def delete_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(SensorDB).filter(SensorDB.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    db.delete(sensor)
    db.commit()
    return {"detail": "Sensor deleted"}

@app.patch("/api/v1/sensors/{sensor_id}/value")
def update_sensor_value(sensor_id: int, update: SensorValueUpdate, db: Session = Depends(get_db)):
    sensor = db.query(SensorDB).filter(SensorDB.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    if update.value is not None:
        sensor.value = update.value
    if update.status is not None:
        sensor.status = update.status
    db.commit()
    return sensor

# === Эндпоинт: имитация датчика температуры (опционально, можно оставить) ===
@app.get("/temperature")
def get_temperature(location: str):
    temp = round(random.uniform(-15.0, 30.0), 2)
    return {"location": location, "temperature": temp, "unit": "°C"}