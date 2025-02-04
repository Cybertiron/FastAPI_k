from fastapi import FastAPI, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
from datetime import date

# --- Database setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./students.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency that will be used in each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- SQLAlchemy Model ---
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)
    grade = Column(String(1), nullable=False)
    enrollment_date = Column(Date)


Base.metadata.create_all(bind=engine)


# --- Pydantic Schema ---
class StudentModel(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=3, max_length=50)
    age: int
    # Only allow the grades A, B, C, D, or F (E is not allowed)
    grade: str = Field(..., pattern="^(A|B|C|D|F)$")
    enrollment_date: Optional[date] = None

    class Config:
        # Use from_attributes in Pydantic v2 instead of orm_mode
        from_attributes = True

# --- FastAPI App Setup ---
app = FastAPI()


# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI application!"}


# Create Student Endpoint (POST /students/)
@app.post("/students/", response_model=StudentModel)
def create_student(student: StudentModel, db: Session = Depends(get_db)):
    # Create a new Student instance using the validated data from StudentModel
    new_student = Student(
        name=student.name,
        age=student.age,
        grade=student.grade,
        enrollment_date=student.enrollment_date,
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


# Read Student Endpoint (GET /students/{student_id})
@app.get("/students/{student_id}", response_model=StudentModel)
def read_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# Update Student Endpoint (PUT /students/{student_id})
@app.put("/students/{student_id}", response_model=StudentModel)
def update_student(student_id: int, updated_student: StudentModel, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Update all fields
    student.name = updated_student.name
    student.age = updated_student.age
    student.grade = updated_student.grade
    student.enrollment_date = updated_student.enrollment_date

    db.commit()
    db.refresh(student)
    return student


# Partial Update Endpoint (PATCH /students/{student_id})
@app.patch("/students/{student_id}", response_model=StudentModel)
def partial_update_student(student_id: int, updates: dict, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Only update provided fields; ignore any keys that are not part of the allowed fields.
    allowed_fields = {"name", "age", "grade", "enrollment_date"}
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(student, key, value)

    db.commit()
    db.refresh(student)
    return student


# List Students Endpoint (GET /students/)
@app.get("/students/", response_model=List[StudentModel])
def list_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    return students


# Delete Student Endpoint (DELETE /students/{student_id})
@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return {"detail": "Student deleted successfully"}


# Search Feature (GET /students/search/?name=...)
@app.get("/students/search/", response_model=List[StudentModel])
def search_students(name: str, db: Session = Depends(get_db)):
    # Use case-insensitive search (ilike) for names containing the provided substring.
    students = db.query(Student).filter(Student.name.ilike(f"%{name}%")).all()
    return students
