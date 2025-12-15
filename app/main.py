from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import shutil
import os
from . import models, database, swachhata_client

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Nagardrishti")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
os.makedirs("static/uploads", exist_ok=True)

# Initialize API Client
api_client = swachhata_client.SwachhataClient()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home(request: Request):
    message = request.query_params.get("msg", "Welcome to Nagardrishti")
    return templates.TemplateResponse("index.html", {"request": request, "message": message})

@app.get("/register")
def show_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_user(request: Request, full_name: str = Form(...), mobile_number: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.mobile_number == mobile_number).first()
    if existing_user:
        return RedirectResponse(url="/?msg=Welcome+back%2C+"+existing_user.full_name, status_code=303)
    
    new_user = models.User(full_name=full_name, mobile_number=mobile_number)
    
    # Sync with Govt API
    try:
        govt_id = api_client.register_user(full_name, mobile_number)
        new_user.swachhata_user_id = govt_id
    except Exception as e:
        print(f"Sync Failed: {e}")

    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/?msg=Registration+Successful!", status_code=303)

@app.get("/report")
def show_report_page(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})

@app.post("/report")
def submit_report(request: Request, mobile_number: str = Form(...), category_id: int = Form(...), address: str = Form(...), description: str = Form(""), latitude: float = Form(0.0), longitude: float = Form(0.0), file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.mobile_number == mobile_number).first()
    if not user:
        return RedirectResponse(url="/register?msg=Error:+Mobile+number+not+found", status_code=303)

    file_location = f"static/uploads/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_complaint = models.Complaint(
        user_id=user.id, category_id=category_id, latitude=latitude, longitude=longitude,
        address=address, image_url=file_location, description=description, status="Pending Sync"
    )

    # Sync with Govt API
    try:
        ticket_id = api_client.post_complaint(user.mobile_number, category_id, latitude, longitude, address, file_location)
        new_complaint.swachhata_complaint_id = ticket_id
        new_complaint.status = "Synced"
    except Exception as e:
        print(f"Sync Failed: {e}")

    db.add(new_complaint)
    db.commit()
    return RedirectResponse(url="/?msg=Report+Submitted+Successfully!", status_code=303)

@app.get("/admin")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    complaints = db.query(models.Complaint).order_by(models.Complaint.id.desc()).all()
    return templates.TemplateResponse("admin.html", {"request": request, "users": users, "complaints": complaints})