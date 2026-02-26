import requests
import os

# Configuration
API_URL = "http://localhost:8001/api/v1/scan/solve"
TEST_IMAGE = "/Users/arthurgao/code/edu/edu-scan-app/backend/tests/test_image.jpg"

def verify_scan():
    print(f"Testing Scan & Solve: {API_URL}")
    
    if not os.path.exists(TEST_IMAGE):
        with open(TEST_IMAGE, "w") as f:
            f.write("dummy image data")
            
    with open(TEST_IMAGE, "rb") as image_file:
        files = {"image": ("test_image.jpg", image_file, "image/jpeg")}
        data = {
            "subject": "math",
            "grade_level": "high school",
            "ai_provider": "claude"
        }
        
        try:
            response = requests.post(API_URL, files=files, data=data)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Response JSON:")
                import json
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    verify_scan()
