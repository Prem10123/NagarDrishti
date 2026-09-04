from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from . import config
from .views import ComplaintView, UserView


def _user_from_row(row: dict) -> UserView:
    return UserView(
        id=row["id"],
        full_name=row.get("full_name") or "",
        mobile_number=row.get("mobile_number") or "",
        swachhata_user_id=row.get("swachhata_user_id"),
        password_hash=row.get("password_hash"),
    )


def _complaint_from_row(row: dict, owner: Optional[UserView] = None) -> ComplaintView:
    return ComplaintView(
        id=row["id"],
        user_id=row.get("user_id"),
        category_id=int(row["category_id"]),
        latitude=float(row.get("latitude") or 0),
        longitude=float(row.get("longitude") or 0),
        address=row.get("address") or "",
        image_url=row.get("image_url") or "",
        description=row.get("description"),
        status=row.get("status") or "Pending Sync",
        swachhata_complaint_id=row.get("swachhata_complaint_id"),
        created_at=row.get("created_at"),
        owner=owner,
    )


class LocalStore:
    is_cloud = False

    def get_user_by_mobile(self, mobile: str) -> Optional[UserView]:
        from . import database, models

        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.mobile_number == mobile).first()
            if not user:
                return None
            return UserView(
                id=user.id,
                full_name=user.full_name,
                mobile_number=user.mobile_number,
                swachhata_user_id=user.swachhata_user_id,
                password_hash=user.password_hash,
            )
        finally:
            db.close()

    def get_user_by_id(self, user_id) -> Optional[UserView]:
        from . import database, models

        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                return None
            return UserView(
                id=user.id,
                full_name=user.full_name,
                mobile_number=user.mobile_number,
                swachhata_user_id=user.swachhata_user_id,
                password_hash=user.password_hash,
            )
        finally:
            db.close()

    def create_user(self, full_name: str, mobile: str, password_hash: str, swachhata_user_id=None) -> UserView:
        from . import database, models

        db = database.SessionLocal()
        try:
            user = models.User(
                full_name=full_name,
                mobile_number=mobile,
                password_hash=password_hash,
                swachhata_user_id=swachhata_user_id,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return UserView(
                id=user.id,
                full_name=user.full_name,
                mobile_number=user.mobile_number,
                swachhata_user_id=user.swachhata_user_id,
                password_hash=user.password_hash,
            )
        finally:
            db.close()

    def save_image(self, image_bytes: bytes, suffix: str = ".jpg") -> str:
        import os

        os.makedirs("static/uploads", exist_ok=True)
        name = f"{uuid4().hex}{suffix}"
        path = os.path.join("static", "uploads", name)
        with open(path, "wb") as handle:
            handle.write(image_bytes)
        return path.replace("\\", "/")

    def create_complaint(self, **kwargs) -> ComplaintView:
        from . import database, models

        db = database.SessionLocal()
        try:
            row = models.Complaint(**kwargs)
            db.add(row)
            db.commit()
            db.refresh(row)
            owner = row.owner
            owner_view = None
            if owner:
                owner_view = UserView(
                    id=owner.id,
                    full_name=owner.full_name,
                    mobile_number=owner.mobile_number,
                    swachhata_user_id=owner.swachhata_user_id,
                )
            return ComplaintView(
                id=row.id,
                user_id=row.user_id,
                category_id=row.category_id,
                latitude=row.latitude,
                longitude=row.longitude,
                address=row.address,
                image_url=row.image_url,
                description=row.description,
                status=row.status,
                swachhata_complaint_id=row.swachhata_complaint_id,
                created_at=row.created_at,
                owner=owner_view,
            )
        finally:
            db.close()

    def list_complaints_for_user(self, user_id) -> list[ComplaintView]:
        from . import database, models

        db = database.SessionLocal()
        try:
            rows = (
                db.query(models.Complaint)
                .filter(models.Complaint.user_id == user_id)
                .order_by(models.Complaint.id.desc())
                .all()
            )
            return [
                ComplaintView(
                    id=row.id,
                    user_id=row.user_id,
                    category_id=row.category_id,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    address=row.address,
                    image_url=row.image_url,
                    description=row.description,
                    status=row.status,
                    swachhata_complaint_id=row.swachhata_complaint_id,
                    created_at=row.created_at,
                )
                for row in rows
            ]
        finally:
            db.close()

    def list_all_users(self) -> list[UserView]:
        from . import database, models

        db = database.SessionLocal()
        try:
            rows = db.query(models.User).all()
            return [
                UserView(
                    id=u.id,
                    full_name=u.full_name,
                    mobile_number=u.mobile_number,
                    swachhata_user_id=u.swachhata_user_id,
                )
                for u in rows
            ]
        finally:
            db.close()

    def list_all_complaints(self) -> list[ComplaintView]:
        from . import database, models

        db = database.SessionLocal()
        try:
            rows = db.query(models.Complaint).order_by(models.Complaint.id.desc()).all()
            result = []
            for row in rows:
                owner = None
                if row.owner:
                    owner = UserView(
                        id=row.owner.id,
                        full_name=row.owner.full_name,
                        mobile_number=row.owner.mobile_number,
                        swachhata_user_id=row.owner.swachhata_user_id,
                    )
                result.append(
                    ComplaintView(
                        id=row.id,
                        user_id=row.user_id,
                        category_id=row.category_id,
                        latitude=row.latitude,
                        longitude=row.longitude,
                        address=row.address,
                        image_url=row.image_url,
                        description=row.description,
                        status=row.status,
                        swachhata_complaint_id=row.swachhata_complaint_id,
                        created_at=row.created_at,
                        owner=owner,
                    )
                )
            return result
        finally:
            db.close()


class CloudStore:
    is_cloud = True

    def __init__(self):
        from supabase import create_client

        self.client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        self.bucket = config.STORAGE_BUCKET

    def get_user_by_mobile(self, mobile: str) -> Optional[UserView]:
        res = (
            self.client.table("users")
            .select("*")
            .eq("mobile_number", mobile)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return _user_from_row(res.data[0])

    def get_user_by_id(self, user_id) -> Optional[UserView]:
        res = self.client.table("users").select("*").eq("id", user_id).limit(1).execute()
        if not res.data:
            return None
        return _user_from_row(res.data[0])

    def create_user(self, full_name: str, mobile: str, password_hash: str, swachhata_user_id=None) -> UserView:
        payload = {
            "full_name": full_name,
            "mobile_number": mobile,
            "password_hash": password_hash,
        }
        if swachhata_user_id is not None:
            payload["swachhata_user_id"] = swachhata_user_id
        res = self.client.table("users").insert(payload).execute()
        return _user_from_row(res.data[0])

    def save_image(self, image_bytes: bytes, suffix: str = ".jpg") -> str:
        path = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4().hex}{suffix}"
        self.client.storage.from_(self.bucket).upload(
            path,
            image_bytes,
            file_options={"content-type": "image/jpeg", "x-upsert": "false"},
        )
        public = self.client.storage.from_(self.bucket).get_public_url(path)
        return public

    def create_complaint(self, **kwargs) -> ComplaintView:
        payload = {key: value for key, value in kwargs.items() if value is not None}
        res = self.client.table("complaints").insert(payload).execute()
        return _complaint_from_row(res.data[0])

    def list_complaints_for_user(self, user_id) -> list[ComplaintView]:
        res = (
            self.client.table("complaints")
            .select("*")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .execute()
        )
        return [_complaint_from_row(row) for row in (res.data or [])]

    def list_all_users(self) -> list[UserView]:
        res = self.client.table("users").select("id, full_name, mobile_number, swachhata_user_id").execute()
        return [_user_from_row(row) for row in (res.data or [])]

    def list_all_complaints(self) -> list[ComplaintView]:
        res = self.client.table("complaints").select("*").order("id", desc=True).execute()
        users = {u.id: u for u in self.list_all_users()}
        out = []
        for row in res.data or []:
            owner = users.get(row.get("user_id"))
            out.append(_complaint_from_row(row, owner=owner))
        return out


def get_store():
    if config.CLOUD_ENABLED:
        try:
            return CloudStore()
        except Exception as exc:
            print(f"Cloud store failed, using local SQLite. {exc}")
            return LocalStore()
    return LocalStore()
