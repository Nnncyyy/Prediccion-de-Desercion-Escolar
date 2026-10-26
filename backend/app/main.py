from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Base, engine, SessionLocal, get_db
from app.models import User, Student, Subject, Enrollment, PredictionLog
from app.schemas import StudentCreate, StudentOut, SubjectCreate, SubjectOut, EnrollmentCreate, EnrollmentOut, LoginInput, MLPredictInput
from app.security import hash_password, verify_password, create_token, current_user
from app.services.risk import academic_alert
from app.services.ml import predict

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.jwt_secret or settings.jwt_secret.startswith('CAMBIAR') or len(settings.jwt_secret)<24:
        raise RuntimeError('Configura JWT_SECRET seguro en backend/.env')
    if not settings.admin_email or not settings.admin_password or settings.admin_password.startswith('CAMBIAR'):
        raise RuntimeError('Configura ADMIN_EMAIL y ADMIN_PASSWORD en backend/.env')
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email==settings.admin_email)):
            db.add(User(email=settings.admin_email,password_hash=hash_password(settings.admin_password),role='admin'))
            db.commit()
    yield

app = FastAPI(title='SIPDE API',version='0.1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

@app.get('/api/health')
def health(): return {'status':'ok','service':'SIPDE'}

@app.post('/api/auth/login')
def login(body: LoginInput, db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==body.email))
    if not user or not user.active or not verify_password(body.password,user.password_hash):raise HTTPException(401,'Credenciales incorrectas')
    return {'access_token':create_token(user),'token_type':'bearer','role':user.role}

@app.get('/api/students',response_model=list[StudentOut])
def list_students(db:Session=Depends(get_db),_user:User=Depends(current_user)):
    return db.scalars(select(Student).order_by(Student.id.desc())).all()

@app.post('/api/students',response_model=StudentOut,status_code=201)
def create_student(body:StudentCreate,db:Session=Depends(get_db),_user:User=Depends(current_user)):
    obj=Student(**body.model_dump());db.add(obj)
    try:db.commit();db.refresh(obj)
    except IntegrityError:db.rollback();raise HTTPException(409,'Matrícula duplicada')
    return obj

@app.get('/api/students/{student_id}',response_model=StudentOut)
def get_student(student_id:int,db:Session=Depends(get_db),_user:User=Depends(current_user)):
    obj=db.get(Student,student_id)
    if not obj:raise HTTPException(404,'Estudiante no encontrado')
    return obj

@app.get('/api/subjects',response_model=list[SubjectOut])
def list_subjects(db:Session=Depends(get_db),_user:User=Depends(current_user)):
    return db.scalars(select(Subject).order_by(Subject.name)).all()

@app.post('/api/subjects',response_model=SubjectOut,status_code=201)
def create_subject(body:SubjectCreate,db:Session=Depends(get_db),_user:User=Depends(current_user)):
    obj=Subject(**body.model_dump());db.add(obj)
    try:db.commit();db.refresh(obj)
    except IntegrityError:db.rollback();raise HTTPException(409,'Código de materia duplicado')
    return obj

@app.post('/api/enrollments',response_model=EnrollmentOut,status_code=201)
def add_enrollment(body:EnrollmentCreate,db:Session=Depends(get_db),_user:User=Depends(current_user)):
    if not db.get(Student,body.student_id) or not db.get(Subject,body.subject_id):raise HTTPException(404,'Alumno o materia inexistente')
    obj=Enrollment(**body.model_dump());db.add(obj)
    try:db.commit();db.refresh(obj)
    except IntegrityError:db.rollback();raise HTTPException(409,'Inscripción ya registrada para el periodo')
    return obj

@app.get('/api/students/{student_id}/enrollments',response_model=list[EnrollmentOut])
def student_enrollments(student_id:int,db:Session=Depends(get_db),_user:User=Depends(current_user)):
    if not db.get(Student,student_id):raise HTTPException(404,'Estudiante no encontrado')
    return db.scalars(select(Enrollment).where(Enrollment.student_id==student_id).order_by(Enrollment.id.desc())).all()

@app.get('/api/students/{student_id}/alert')
def student_alert(student_id:int,db:Session=Depends(get_db),_user:User=Depends(current_user)):
    student=db.get(Student,student_id)
    if not student:raise HTTPException(404,'Estudiante no encontrado')
    grades=list(db.scalars(select(Enrollment.grade).where(Enrollment.student_id==student_id)).all())
    return {'student_id':student_id,**academic_alert(student,grades)}

@app.get('/api/dashboard')
def dashboard(db:Session=Depends(get_db),_user:User=Depends(current_user)):
    return {'students':db.scalar(select(func.count()).select_from(Student)) or 0,
            'subjects':db.scalar(select(func.count()).select_from(Subject)) or 0,
            'enrollments':db.scalar(select(func.count()).select_from(Enrollment)) or 0}

@app.post('/api/ml/predict')
def ml_predict(body:MLPredictInput,_user:User=Depends(current_user)):
    return predict(body.features)
