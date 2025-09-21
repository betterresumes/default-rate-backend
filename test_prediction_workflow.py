#!/usr/bin/env python3

import requests
import json

# Test the complete prediction workflow
base_url = "http://localhost:8000"

def test_prediction_workflow():
    # Login as an organization member
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
    
    # Test annual prediction creation
    print("Creating annual prediction...")
    annual_data = {
        "company_symbol": "TESTCO3",
        "company_name": "Test Company 3",
        "market_cap": 10000000.00,
        "sector": "Technology",
        "reporting_year": "2024",
        "reporting_quarter": "Q1",
        "long_term_debt_to_total_capital": 0.25,
        "total_debt_to_ebitda": 2.5,
        "net_income_margin": 0.15,
        "ebit_to_interest_expense": 5.0,
        "return_on_assets": 0.08
    }
    
    annual_response = requests.post(f"{base_url}/api/v1/predictions/annual", json=annual_data, headers=headers)
    print(f"Annual creation status: {annual_response.status_code}")
    if annual_response.status_code == 200:
        response_json = annual_response.json()
        print("Annual prediction created successfully!")
        print(f"Company ID: {response_json['prediction'].get('company_id', 'Missing')}")
        print(f"Organization Access: {response_json['prediction'].get('organization_access', 'Missing')}")
        print(f"Financial Ratios Included: {bool('long_term_debt_to_total_capital' in response_json['prediction'])}")
    else:
        print(f"Annual creation failed: {annual_response.text}")
    
    # Test quarterly prediction creation
    print("\nCreating quarterly prediction...")
    quarterly_data = {
        "company_symbol": "TESTCO4",
        "company_name": "Test Company 4",
        "market_cap": 20000000.00,
        "sector": "Finance",
        "reporting_year": "2024",
        "reporting_quarter": "Q2",
        "total_debt_to_ebitda": 1.8,
        "sga_margin": 0.12,
        "long_term_debt_to_total_capital": 0.30,
        "return_on_capital": 0.10
    }
    
    quarterly_response = requests.post(f"{base_url}/api/v1/predictions/quarterly", json=quarterly_data, headers=headers)
    print(f"Quarterly creation status: {quarterly_response.status_code}")
    if quarterly_response.status_code == 200:
        response_json = quarterly_response.json()
        print("Quarterly prediction created successfully!")
        print(f"Company ID: {response_json['prediction'].get('company_id', 'Missing')}")
        print(f"Organization Access: {response_json['prediction'].get('organization_access', 'Missing')}")
        print(f"Financial Ratios Included: {bool('total_debt_to_ebitda' in response_json['prediction'])}")
    else:
        print(f"Quarterly creation failed: {quarterly_response.text}")
    
    # Test GET endpoints with data
    print("\nTesting GET endpoints with data...")
    annual_get_response = requests.get(f"{base_url}/api/v1/predictions/annual", headers=headers)
    print(f"Annual GET status: {annual_get_response.status_code}")
    if annual_get_response.status_code == 200:
        predictions = annual_get_response.json()["predictions"]
        print(f"Annual predictions found: {len(predictions)}")
        if predictions:
            pred = predictions[0]
            print(f"Organization access: {pred.get('organization_access', 'Missing')}")
    
    quarterly_get_response = requests.get(f"{base_url}/api/v1/predictions/quarterly", headers=headers)
    print(f"Quarterly GET status: {quarterly_get_response.status_code}")
    if quarterly_get_response.status_code == 200:
        predictions = quarterly_get_response.json()["predictions"]
        print(f"Quarterly predictions found: {len(predictions)}")
        if predictions:
            pred = predictions[0]
            print(f"Organization access: {pred.get('organization_access', 'Missing')}")

if __name__ == "__main__":
    test_prediction_workflow()
