#!/usr/bin/env python3

import requests
import json

# Test the GET endpoints to see the exact error
base_url = "http://localhost:8000"

def test_get_predictions():
    # First login to get token
    login_data = {
        "email": "analyst1@fintech-solutions.com", 
        "password": "Analyst123!"
    }
    
    login_response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data)
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test annual predictions GET
    print("Testing annual predictions GET...")
    annual_response = requests.get(f"{base_url}/api/v1/predictions/annual", headers=headers)
    print(f"Annual GET status: {annual_response.status_code}")
    print(f"Annual GET response: {annual_response.text}")
    
    # Test quarterly predictions GET
    print("\nTesting quarterly predictions GET...")
    quarterly_response = requests.get(f"{base_url}/api/v1/predictions/quarterly", headers=headers)
    print(f"Quarterly GET status: {quarterly_response.status_code}")
    print(f"Quarterly GET response: {quarterly_response.text}")

if __name__ == "__main__":
    test_get_predictions()
