import random
import string

class SwachhataClient:
    def __init__(self):
        self.api_url = "https://api.swachh.city/sbm/v1"
        # In a real app, you would load these from .env
        self.vendor_name = "India" 
        self.access_key = "8a34n9up"

    def register_user(self, name, mobile):
        # SIMULATION: Returns a fake user ID like the real API would
        print(f"[API] Registering User: {name} ({mobile})")
        return random.randint(100000, 999999)

    def post_complaint(self, mobile, category_id, lat, lon, address, image_path):
        # SIMULATION: Returns a fake complaint ID
        print(f"[API] Posting Complaint: Cat {category_id} at {address}")
        # In real integration, we would upload the 'image_path' here
        fake_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return f"C{fake_id}"