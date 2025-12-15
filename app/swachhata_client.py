import uuid
import random

class SwachhataClient:
    """
    Handles communication with the Swachhata Platform API.
    """
    BASE_URL = "https://api.swachh.city/sbm/v1"
    VENDOR_NAME = "India"
    ACCESS_KEY = "TEST_KEY_123"

    def register_user(self, full_name, mobile_number):
        print(f"\n[API OUTGOING] Registering User: {mobile_number}")
        payload = {
            "vendor_name": self.VENDOR_NAME,
            "access_key": self.ACCESS_KEY,
            "mobileNumber": mobile_number,
            "deviceOs": "external",
            "location": "Nagardrishti Web",
            "lang": "en"
        }
        print(f"[API PAYLOAD] {payload}")
        mock_response_id = random.randint(100000, 999999)
        print(f"[API INCOMING] Success! Generated Swachhata ID: {mock_response_id}\n")
        return mock_response_id

    def post_complaint(self, mobile_number, category_id, lat, long, address, image_url):
        print(f"\n[API OUTGOING] Posting Complaint for User: {mobile_number}")
        payload = {
            "vendor_name": self.VENDOR_NAME,
            "access_key": self.ACCESS_KEY,
            "mobileNumber": mobile_number,
            "categoryId": category_id,
            "complaintLatitude": lat,
            "complaintLongitude": long,
            "complaintLocation": address,
            "file": f"http://myserver.com/{image_url}",
            "deviceOs": "external"
        }
        print(f"[API PAYLOAD] {payload}")
        mock_generic_id = f"W03000C{random.randint(100000, 999999)}"
        print(f"[API INCOMING] Success! Complaint Ticket: {mock_generic_id}\n")
        return mock_generic_id