import random
import string

from .. import config


class SwachhataClient:
    def __init__(self):
        self.api_url = config.SWACHHATA_API_URL
        self.vendor_name = config.SWACHHATA_VENDOR
        self.access_key = config.SWACHHATA_ACCESS_KEY
        self.live = bool(self.vendor_name and self.access_key)

    def register_user(self, name, mobile):
        if not self.live:
            print(f"[Swachhata simulated] Registering {name} ({mobile})")
            return random.randint(100000, 999999)
        print(f"[Swachhata] Would register {name} at {self.api_url}")
        return random.randint(100000, 999999)

    def post_complaint(self, mobile, category_id, lat, lon, address, image_path):
        if not self.live:
            print(f"[Swachhata simulated] Complaint cat={category_id} at {address}")
            fake_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            return f"C{fake_id}"
        print(f"[Swachhata] Would post complaint for {mobile} using {image_path}")
        fake_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return f"C{fake_id}"
