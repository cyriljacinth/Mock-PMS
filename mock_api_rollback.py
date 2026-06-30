# -*- coding: utf-8 -*-
"""
Callisto Cruise Base PMS XML Integration Mock Engine
Optimized for stable local network hardware sandbox validation testing.
"""

import time
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
app.url_map.strict_slashes = False

# --- CONFIGURATION SETTINGS ---
VALID_SHIP_CODE = "CRUISE-01"
CALLISTO_IP = "10.101.4.136"
CALLISTO_USER = "restadmin"
CALLISTO_PASS = "callisto"

# --- CORE DATA INVENTORY (Strictly Matching Callisto Parameter Hierarchy) ---
mock_passengers = [
    {
        "PassengerId": "1234",
        "CabinNumber": "1",
        "FirstName": "George",
        "LastName": "Washington",
        "CheckInDate": "2026-06-25",
        "CheckOutDate": "2026-06-26",
        "Status": "CheckedIn",
        "Language": "EN",
        "Type": "P"
    },
    {
        "PassengerId": "5678",
        "CabinNumber": "2",
        "FirstName": "Martha",
        "LastName": "Washington",
        "CheckInDate": "2026-06-25",
        "CheckOutDate": "2026-06-26",
        "Status": "CheckedIn",
        "Language": "EN",
        "Type": "P"
    }
]

# =====================================================================
# INBOUND ROUTING INTERFACES (CALLISTO -> MOCK SERVER)
# =====================================================================

@app.route('/API/mxp_api.exe/GetShipStatus', methods=['GET'])
def mxp_get_ship_status():
    ship_code = request.args.get('ship_code') or VALID_SHIP_CODE
    print(f"🚢 [MXP]: Callisto requested Ship Status. Resolved Code: {ship_code}")
    return jsonify({
        "status": "Success",
        "ship_code": ship_code,
        "system_status": "Online",
        "pms_version": "v14.2.1"
    })

@app.route('/API/mxp_rc.exe/Cruise/', methods=['GET'])
def mxp_get_cruise_manifest():
    ship_code = request.args.get('ship_code') or VALID_SHIP_CODE
    print(f"📋 [MXP]: Callisto requesting Cruise Sync. Resolved Code: {ship_code}")
    return jsonify({
        "status": "Success",
        "data": {"ship": ship_code, "status": "Active"}
    })

@app.route('/API/mxp_api.exe/EmployeePhoneDirectory/', methods=['GET'])
def mxp_get_employee_directory():
    print("📞 [MXP]: Callisto requested the Employee Phone Directory.")
    return jsonify({
        "status": "Success",
        "contacts": [
            {"name": "Medical Center", "extension": "4000"},
            {"name": "Guest Services Desk", "extension": "0"},
            {"name": "Housekeeping", "extension": "4001"}
        ]
    })

@app.route('/API/mxp_rc.exe/Guest/', methods=['GET'])
def mxp_get_guest_manifest():
    ship_code = request.args.get('ship_code') or VALID_SHIP_CODE
    incoming_id = request.args.get('account_id') or request.args.get('passenger_id') or request.args.get('guestID')
    
    # -----------------------------------------------------------------
    # PROFILE LAYER A: INDIVIDUAL TARGET FALLBACK ENGINE
    # -----------------------------------------------------------------
    if incoming_id:
        print(f"👥 [MXP]: Callisto validating explicit profile for Guest ID: {incoming_id}")
        raw_match = next((g for g in mock_passengers if g["PassengerId"] == incoming_id), None)
        
        if raw_match:
            translated_profile = {
                "guestID": raw_match["PassengerId"],
                "firstName": raw_match["FirstName"],
                "lastName": raw_match["LastName"],
                "cabinNumber": raw_match["CabinNumber"],
                "checkInDate": "202606251200",
                "checkOutDate": "202606261200",
                "language": raw_match["Language"],
                "greeting": "Mr",
                "mainGuest": "1",
                "type": raw_match["Type"],
                "voyageID": ship_code,
                "enabled": "1"
            }
            return jsonify({
                "Status": "Success",
                "status": "Success",
                "Data": [translated_profile],
                "data": [translated_profile]
            })

    # -----------------------------------------------------------------
    # PROFILE LAYER B: PRODUCTION BULK INTERACTION MANIFEST ENGINE
    # -----------------------------------------------------------------
    print(f"👥 [MXP]: Callisto downloading Full Guest Manifest for Ship: {ship_code}")
    return jsonify({
        "Status": "Success",
        "TotalRecords": len(mock_passengers),
        "Data": {
            "ShipCode": ship_code,
            "Manifest": mock_passengers  
        }
    })

# =====================================================================
# OUTBOUND PUSH SCHEDULERS (MOCK SERVER -> CALLISTO)
# =====================================================================
def push_passenger_to_callisto(passenger, callisto_ip, username, password):
    url = f"http://{callisto_ip}/Applications/startup/cruise%20Base/rest/checkIn.asp"
    
    # Format the payload values cleanly using fallback defaults matching specification schemas
    payload = {
        "guestID": passenger.get("PassengerId"),
        "firstName": passenger.get("FirstName"),
        "lastName": passenger.get("LastName"),
        "cabinNumber": passenger.get("CabinNumber"),
        "checkInDate": "202606251200",
        "checkOutDate": "202606261200",
        "language": passenger.get("Language", "EN"),
        "greeting": "Mr",
        "mainGuest": "1",
        "type": passenger.get("Type", "P"),
        "voyageID": VALID_SHIP_CODE
    }
    headers = {"accept": "application/xml"}
    print(f"🚀 [PUSH TASK]: Forwarding {payload['firstName']} (ID: {payload['guestID']}) to Callisto listener...")
    try:
        response = requests.post(url, data=payload, auth=(username, password), headers=headers, timeout=5)
        return response.text, response.status_code
    except Exception as e:
        return f"Network Error: {e}", 500

@app.route('/pms/push/<guest_id>', methods=['GET'])
def trigger_push_endpoint(guest_id):
    passenger = next((g for g in mock_passengers if g["PassengerId"] == guest_id), None)
    if not passenger:
        return jsonify({"error": f"Passenger ID {guest_id} not found"}), 404
    xml_response, status_code = push_passenger_to_callisto(passenger, CALLISTO_IP, CALLISTO_USER, CALLISTO_PASS)
    return jsonify({
        "info": f"Executed dynamic payload forward for ID {guest_id}",
        "callisto_http_status": status_code,
        "callisto_xml_output": xml_response
    })

# =====================================================================
# OUTBOUND CHECKOUT SCHEDULERS (MOCK SERVER -> CALLISTO)
# =====================================================================
def checkout_passenger_from_callisto(guest_id, callisto_ip, username, password):
    url = f"http://{callisto_ip}/Applications/startup/cruise%20Base/rest/checkOut.asp"
    payload = {
        "guestID": guest_id,
        "guestId": guest_id
    }
    headers = {"accept": "application/xml"}
    print(f"🏃 [CHECKOUT TASK]: Requesting checkout for Guest ID: {guest_id} from Callisto listener...")
    try:
        response = requests.post(url, data=payload, auth=(username, password), headers=headers, timeout=5)
        return response.text, response.status_code
    except Exception as e:
        return f"Network Error: {e}", 500

# --- REPAIRED ADMINISTRATIVE TRIGGER ENDPOINT ---
@app.route('/pms/checkout/<guest_id>', methods=['GET'])
def trigger_checkout_endpoint(guest_id):
    global mock_passengers
    xml_response, status_code = checkout_passenger_from_callisto(guest_id, CALLISTO_IP, CALLISTO_USER, CALLISTO_PASS)
    
    # Clear matching element from memory storage array tracking lists if found
    mock_passengers = [g for g in mock_passengers if g["PassengerId"] != guest_id]
    
    return jsonify({
        "info": f"Executed checkout execution pass for ID {guest_id}",
        "callisto_http_status": status_code,
        "callisto_xml_output": xml_response,
        "current_cached_count": len(mock_passengers)
    })

# =====================================================================
# SYSTEM MAIN ENGINE STARTUP
# =====================================================================
if __name__ == '__main__':
    print("🚀 PMS Mock Server starting up...")
    print(f"👉 Serving background workflows on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True,use_reloader=False)
