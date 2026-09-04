from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .. import config
from ..views import ComplaintView, UserView

_LOCAL_FILE = re.compile(r"^[a-fA-F0-9]{32}\.jpg$")


def _user_from_row(row: dict) -> UserView:
    return UserView(
        id=row["id"],
        full_name=row.get("full_name") or "",
        mobile_number=row.get("mobile_number") or "",
        swachhata_user_id=row.get("swachhata_user_id"),
        password_hash=row.get("password_hash"),
    )


def _complaint_from_row(row: dict, owner: Optional[UserView] = None, image_url: Optional[str] = None) -> ComplaintView:
    return ComplaintView(
        id=row["id"],
        user_id=row.get("user_id"),
        category_id=int(row["category_id"]),
        latitude=float(row.get("latitude") or 0),
        longitude=float(row.get("longitude") or 0),
        address=row.get("address") or "",
        image_url=image_url if image_url is not None else (row.get("image_url") or ""),
        description=row.get("description"),
        status=row.get("status") or "Pending Sync",
        swachhata_complaint_id=row.get("swachhata_complaint_id"),
        created_at=row.get("created_at"),
        owner=owner,
    )


class LocalStore:
    is_cloud = False

    def get_user_by_mobile(self, mobile: str) -> Optional[UserView]:
        from .. import database, models

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
        from .. import database, models

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
        from .. import database, models

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
        name = f"{uuid4().hex}{suffix}"
        path = config.UPLOAD_DIR / name
        path.write_bytes(image_bytes)
        return name

    def create_complaint(self, **kwargs) -> ComplaintView:
        from .. import database, models

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
        from .. import database, models

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
        from .. import database, models

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
        from .. import database, models

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

    def user_can_view_image(self, user_id, filename: str) -> bool:
        from .. import database, models

        if not _LOCAL_FILE.fullmatch(filename):
            return False
        db = database.SessionLocal()
        try:
            row = (
                db.query(models.Complaint)
                .filter(models.Complaint.user_id == user_id)
                .filter(
                    (models.Complaint.image_url == filename)
                    | (models.Complaint.image_url.endswith("/" + filename))
                )
                .first()
            )
            return bool(row)
        finally:
            db.close()

    def image_exists(self, filename: str) -> bool:
        from .. import database, models

        if not _LOCAL_FILE.fullmatch(filename):
            return False
        db = database.SessionLocal()
        try:
            row = (
                db.query(models.Complaint)
                .filter(
                    (models.Complaint.image_url == filename)
                    | (models.Complaint.image_url.endswith("/" + filename))
                )
                .first()
            )
            return bool(row)
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
        return path

    def _storage_path(self, stored: str) -> str:
        if not stored:
            return ""
        if stored.startswith("http://") or stored.startswith("https://"):
            marker = f"/object/public/{self.bucket}/"
            if marker in stored:
                return stored.split(marker, 1)[1].split("?")[0]
            sign_marker = f"/object/sign/{self.bucket}/"
            if sign_marker in stored:
                return stored.split(sign_marker, 1)[1].split("?")[0]
            return stored
        return stored

    def _signed_url(self, stored: str) -> str:
        path = self._storage_path(stored)
        if not path:
            return ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        try:
            res = self.client.storage.from_(self.bucket).create_signed_url(path, 60 * 60)
            return res.get("signedURL") or res.get("signedUrl") or ""
        except Exception as exc:
            print(f"Signed URL failed: {exc}")
            return ""

    def create_complaint(self, **kwargs) -> ComplaintView:
        payload = {key: value for key, value in kwargs.items() if value is not None}
        res = self.client.table("complaints").insert(payload).execute()
        row = res.data[0]
        return _complaint_from_row(row, image_url=self._signed_url(row.get("image_url") or ""))

    def list_complaints_for_user(self, user_id) -> list[ComplaintView]:
        res = (
            self.client.table("complaints")
            .select("*")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .execute()
        )
        return [
            _complaint_from_row(row, image_url=self._signed_url(row.get("image_url") or ""))
            for row in (res.data or [])
        ]

    def list_all_users(self) -> list[UserView]:
        res = self.client.table("users").select("id, full_name, mobile_number, swachhata_user_id").execute()
        return [_user_from_row(row) for row in (res.data or [])]

    def list_all_complaints(self) -> list[ComplaintView]:
        res = self.client.table("complaints").select("*").order("id", desc=True).execute()
        users = {u.id: u for u in self.list_all_users()}
        out = []
        for row in res.data or []:
            owner = users.get(row.get("user_id"))
            out.append(
                _complaint_from_row(
                    row,
                    owner=owner,
                    image_url=self._signed_url(row.get("image_url") or ""),
                )
            )
        return out

    def user_can_view_image(self, user_id, filename: str) -> bool:
        return False

    def image_exists(self, filename: str) -> bool:
        return False


_store = None


def get_store():
    global _store
    if _store is not None:
        return _store
    if config.CLOUD_ENABLED:
        try:
            _store = CloudStore()
            print("Storage: Supabase cloud", flush=True)
            return _store
        except Exception as exc:
            print(f"Cloud store failed, using local SQLite. {exc}", flush=True)
            _store = LocalStore()
            return _store
    print("Storage: local SQLite (set SUPABASE_URL to sync across devices)", flush=True)
    _store = LocalStore()
    return _store
