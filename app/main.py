import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import shutil
import numpy as np
from PIL import Image
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import tensorflow as tf
import traceback # Added for debugging

from . import models, database, swachhata_client

# 1. Initialize
models.Base.metadata.create_all(bind=database.engine)
print("Loading ResNet50 Model...")
model = tf.keras.applications.ResNet50(weights="imagenet")
print("AI Model Loaded.")

app = FastAPI(title="Nagardrishti")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
os.makedirs("static/uploads", exist_ok=True)

# Initialize Client (Now that we gave you the code for it!)
try:
    api_client = swachhata_client.SwachhataClient()
except Exception as e:
    print(f"Warning: API Client failed to load. {e}")
    api_client = None

# [cite_start]KEYWORDS LIST [cite: 128-145]
STRICT_CATEGORIES = {
    1: ["dog", "cat", "bird", "hen", "terrier", "beagle", "fox", "carcass", "animal", "shepherd", "retriever", "chihuahua", "corgi"],
    2: ["ashcan", "trash_can", "waste_container", "bucket", "basket", "bin", "barrel", "mailbox"],
    3: ["carton", "paper", "plastic_bag", "can", "bottle", "rubbish", "waste", "tissue", "packet", "wrapper", "crate", "box", "diaper"],
    4: ["garbage_truck", "trailer_truck", "truck", "minivan", "van", "vehicle", "pickup", "tow_truck", "streetcar", "harvester"],
    10: ["manhole", "sewer", "drain", "grate", "cover", "disk_brake", "strainer", "doormat", "stone", "concrete", "cliff", "hole", "puddle", "asphalt"],
    15: ["fire", "lighter", "match", "stove", "smoke", "flame", "grill"]
}

CATEGORY_NAMES = {
    1: "Dead animal(s)", 2: "Dustbins not cleaned", 3: "Garbage dump", 
    4: "Garbage vehicle not arrived", 10: "Open Manholes / Potholes", 15: "Burning Of Garbage"
}

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

def detect_category_from_image(image_path: str):
    try:
        # FIX: Use 'with' context manager to automatically close the file
        with Image.open(image_path) as img:
            img = img.convert('RGB').resize((224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img)
        
        # Now the file is closed, so we can process the array safely
        img_array = np.expand_dims(img_array, axis=0)
        img_array = tf.keras.applications.resnet50.preprocess_input(img_array)
        preds = model.predict(img_array)
        decoded = tf.keras.applications.resnet50.decode_predictions(preds, top=10)[0]
        
        for (code, label, score) in decoded:
            label = label.lower()
            if score < 0.02: continue
            for cat_id, keywords in STRICT_CATEGORIES.items():
                if any(k in label for k in keywords) or any(label in k for k in keywords):
                    return cat_id, CATEGORY_NAMES[cat_id]
        return None, None
    except Exception as e:
        print(f"AI Error: {e}")
        return None, None

# --- ROUTES ---

@app.get("/")
def home(request: Request):
    msg = request.query_params.get("msg", "Welcome to Nagardrishti")
    return templates.TemplateResponse("index.html", {"request": request, "message": msg})

@app.get("/register")
def show_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_user(request: Request, full_name: str = Form(...), mobile_number: str = Form(...), db: Session = Depends(get_db)):
    if not db.query(models.User).filter(models.User.mobile_number == mobile_number).first():
        new_user = models.User(full_name=full_name, mobile_number=mobile_number)
        if api_client:
            try: new_user.swachhata_user_id = api_client.register_user(full_name, mobile_number)
            except: pass
        db.add(new_user)
        db.commit()
    return RedirectResponse(url="/?msg=Registration+Successful!", status_code=303)

@app.post("/detect-category")
async def api_detect_category(file: UploadFile = File(...)):
    temp_path = f"static/uploads/temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    cat_id, cat_name = detect_category_from_image(temp_path)
    try: os.remove(temp_path)
    except: pass # Ignore cleanup errors in dev
    
    if cat_id is None: return {"suggested_id": None, "category_name": "Unknown"}
    return {"suggested_id": cat_id, "category_name": cat_name}

@app.get("/report")
def show_report_page(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})

@app.post("/report")
def submit_report(
    request: Request, 
    mobile_number: str = Form(...), 
    category_id: int = Form(...), 
    address: str = Form(...), 
    description: str = Form(""), 
    latitude: float = Form(0.0), 
    longitude: float = Form(0.0),
    file: UploadFile = File(...), 
    force_submit: bool = Form(False), 
    db: Session = Depends(get_db)
):
    try:
        # 1. User Validation
        user = db.query(models.User).filter(models.User.mobile_number == mobile_number).first()
        if not user:
            return RedirectResponse(url="/register?msg=Error:+Mobile+number+not+found", status_code=303)

        # 2. Save File
        file_location = f"static/uploads/{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. AI Check
        ai_id, ai_name = detect_category_from_image(file_location)
        submission_status = "Pending Sync"
        final_msg = "Report+Submitted+Successfully!"
        
        if ai_id and category_id in STRICT_CATEGORIES and ai_id != category_id:
            if force_submit:
                description = f"[AI Flag: Detected {ai_name}] " + description
                submission_status = "Flagged / Synced"
                final_msg = "Report+Submitted+(AI+Mismatch+Overridden)"
            else:
                try: os.remove(file_location)
                except: pass
                return RedirectResponse(
                    url=f"/report?msg=Error:+AI+sees+{ai_name}.+Check+box+to+force+submit.", 
                    status_code=303
                )

        # 4. Save to Database
        new_complaint = models.Complaint(
            user_id=user.id, category_id=category_id, 
            latitude=latitude, longitude=longitude, # Using real values now
            address=address, image_url=file_location, 
            description=description, status=submission_status
        )

        # 5. Sync with API
        if api_client:
            try:
                tid = api_client.post_complaint(user.mobile_number, category_id, latitude, longitude, address, file_location)
                new_complaint.swachhata_complaint_id = tid
                if submission_status == "Pending Sync":
                    new_complaint.status = "Synced"
            except Exception as e:
                print(f"API Sync Failed: {e}")

        db.add(new_complaint)
        db.commit()
        return RedirectResponse(url=f"/?msg={final_msg}", status_code=303)

    except Exception as e:
        # This prints the REAL error to your terminal
        print("CRITICAL ERROR IN SUBMIT_REPORT:")
        traceback.print_exc()
        return RedirectResponse(url="/report?msg=Internal+Server+Error.+Check+Terminal.", status_code=303)

@app.get("/admin")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    complaints = db.query(models.Complaint).order_by(models.Complaint.id.desc()).all()
    return templates.TemplateResponse("admin.html", {"request": request, "users": users, "complaints": complaints})