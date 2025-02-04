from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import List, Optional
from datetime import date

# Duomenų bazės konfigūracija
DUOMENU_BAZES_URL = "sqlite:///./studentai.db"
variklis = create_engine(DUOMENU_BAZES_URL, connect_args={"check_same_thread": False})
SesiijosSukurejas = sessionmaker(autocommit=False, autoflush=False, bind=variklis)
BazinisModelis = declarative_base()


# SQLAlchemy modelis: Studentas
class Studentas(BazinisModelis):
    __tablename__ = "studentai"
    id = Column(Integer, primary_key=True, index=True)
    vardas = Column(String(50), nullable=False)
    amzius = Column(Integer, nullable=False)
    pazymys = Column(String(1), nullable=False)
    registracijos_data = Column(Date)


BazinisModelis.metadata.create_all(bind=variklis)


# Pydantic modelis: StudentoModelis
class StudentoModelis(BaseModel):
    id: Optional[int] = None
    vardas: str = Field(..., min_length=3, max_length=50)
    amzius: int
    # Leidžiami tik pažymiai: A, B, C, D, F
    pazymys: str = Field(..., pattern="^(A|B|C|D|F)$")
    registracijos_data: Optional[date] = None

    class Config:
        from_attributes = True


# FastAPI aplikacija
app = FastAPI()


# Funkcija, kuri sukuria duomenų bazės sesiją (priklausomybių injekcija)
def gauti_sesija():
    sesija = SesiijosSukurejas()
    try:
        yield sesija
    finally:
        sesija.close()


# Sukurti naują studentą (POST /studentai/)
@app.post("/studentai/", response_model=StudentoModelis)
def sukurti_studenta(studentas: StudentoModelis, sesija: Session = Depends(gauti_sesija)):
    naujas_studentas = Studentas(
        vardas=studentas.vardas,
        amzius=studentas.amzius,
        pazymys=studentas.pazymys,
        registracijos_data=studentas.registracijos_data,
    )
    sesija.add(naujas_studentas)
    sesija.commit()
    sesija.refresh(naujas_studentas)
    return naujas_studentas


# Gauti studento informaciją pagal ID (GET /studentai/{studento_id})
@app.get("/studentai/{studento_id}", response_model=StudentoModelis)
def gauti_studenta(studento_id: int, sesija: Session = Depends(gauti_sesija)):
    studentas = sesija.query(Studentas).filter(Studentas.id == studento_id).first()
    if not studentas:
        raise HTTPException(status_code=404, detail="Studentas nerastas")
    return studentas


# Atnaujinti visą studento informaciją (PUT /studentai/{studento_id})
@app.put("/studentai/{studento_id}", response_model=StudentoModelis)
def atnaujinti_studenta(studento_id: int, atnaujintas_studentas: StudentoModelis,
                        sesija: Session = Depends(gauti_sesija)):
    studentas = sesija.query(Studentas).filter(Studentas.id == studento_id).first()
    if not studentas:
        raise HTTPException(status_code=404, detail="Studentas nerastas")

    studentas.vardas = atnaujintas_studentas.vardas
    studentas.amzius = atnaujintas_studentas.amzius
    studentas.pazymys = atnaujintas_studentas.pazymys
    studentas.registracijos_data = atnaujintas_studentas.registracijos_data

    sesija.commit()
    sesija.refresh(studentas)
    return studentas


# Dalinai atnaujinti studento informaciją (PATCH /studentai/{studento_id})
@app.patch("/studentai/{studento_id}", response_model=StudentoModelis)
def dalinai_atnaujinti_studenta(studento_id: int, atnaujinimai: dict, sesija: Session = Depends(gauti_sesija)):
    studentas = sesija.query(Studentas).filter(Studentas.id == studento_id).first()
    if not studentas:
        raise HTTPException(status_code=404, detail="Studentas nerastas")

    leistini_poliai = {"vardas", "amzius", "pazymys", "registracijos_data"}
    for laukas, reiksme in atnaujinimai.items():
        if laukas in leistini_poliai:
            setattr(studentas, laukas, reiksme)

    sesija.commit()
    sesija.refresh(studentas)
    return studentas


# Gauti visų studentų sąrašą (GET /studentai/)
@app.get("/studentai/", response_model=List[StudentoModelis])
def gauti_visus_studentus(sesija: Session = Depends(gauti_sesija)):
    studentai = sesija.query(Studentas).all()
    return studentai


# Ištrinti studentą (DELETE /studentai/{studento_id})
@app.delete("/studentai/{studento_id}")
def istrinti_studenta(studento_id: int, sesija: Session = Depends(gauti_sesija)):
    studentas = sesija.query(Studentas).filter(Studentas.id == studento_id).first()
    if not studentas:
        raise HTTPException(status_code=404, detail="Studentas nerastas")
    sesija.delete(studentas)
    sesija.commit()
    return {"detail": "Studentas sėkmingai ištrintas"}


# Ieškoti studentų pagal vardą (GET /studentai/ieskoti/?vardas=...)
@app.get("/studentai/ieskoti/", response_model=List[StudentoModelis])
def ieskoti_studentu(vardas: str, sesija: Session = Depends(gauti_sesija)):
    studentai = sesija.query(Studentas).filter(Studentas.vardas.ilike(f"%{vardas}%")).all()
    return studentai
