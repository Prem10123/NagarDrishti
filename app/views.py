from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


CATEGORY_NAMES = {
    1: "Dead animal(s)",
    2: "Dustbins not cleaned",
    3: "Garbage dump",
    4: "Garbage vehicle not arrived",
    5: "Sweeping not done",
    6: "No electricity in public toilet",
    7: "No water supply in public toilet",
    8: "Public toilet blockage",
    9: "Public toilet cleaning",
    10: "Open Manholes / Potholes",
    11: "Overflow of Sewerage",
    12: "Stagnant Water",
    13: "Improper Disposal of Fecal Waste",
    14: "Debris Removal",
    15: "Burning Of Garbage",
    16: "Open Defecation",
    17: "Overflow of Septic Tanks",
    18: "Yellow Spot (Urination)",
}

# Categories the model can reasonably verify; mismatch requires an override.
STRICT_CATEGORIES = {1, 2, 3, 4, 10, 15}


@dataclass
class UserView:
    id: Any
    full_name: str
    mobile_number: str
    swachhata_user_id: Optional[Any] = None
    password_hash: Optional[str] = None


@dataclass
class ComplaintView:
    id: Any
    user_id: Any
    category_id: int
    latitude: float
    longitude: float
    address: str
    image_url: str
    description: Optional[str]
    status: str
    swachhata_complaint_id: Optional[str] = None
    created_at: Any = None
    owner: Optional[UserView] = None

    @property
    def category_name(self) -> str:
        return CATEGORY_NAMES.get(int(self.category_id), f"Category {self.category_id}")

    @property
    def photo_href(self) -> str:
        url = self.image_url or ""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        name = url.replace("\\", "/").rsplit("/", 1)[-1]
        if name:
            return "/media/" + name
        return ""

    @property
    def created_label(self) -> str:
        value = self.created_at
        if isinstance(value, datetime):
            return value.strftime("%d %b %Y, %I:%M %p")
        if isinstance(value, str) and value:
            return value.replace("T", " ")[:19]
        return ""
