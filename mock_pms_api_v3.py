# -*- coding: utf-8 -*-
"""
Callisto Cruise Base PMS REST Integration Engine - Production Master v3.1
Fixes JSONDecodeError crashes, updates expired mock dates, and ensures Callisto synchronization.
"""

import os
import json
import requests
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
app.url_map.strict_slashes = False

# --- CONFIGURATION SETTINGS ---
VALID_SHIP_CODE = "CRUISE-01"
CALLISTO_IP = "10.101.4.136"
CALLISTO_USER = "restadmin"
CALLISTO_PASS = "callisto"
DATA_FILE = "passengers.json"

# --- FUTURE-DATED MANIFEST (Ensures guests stay active inside Callisto cabins) ---
INITIAL_MOCK_DATA = [
    {
        "guestID": "1234",
        "firstName": "George",
        "lastName": "Washington",
        "cabinNumber": "1",
        "checkInDate": "202606291700",
        "checkOutDate": "202607152200",
        "language": "EN",
        "greeting": "Mr",
        "mainGuest": "1",
        "type": "P",
        "voyageID": "CRUISE-01",
        "enabled": "1"
    },
    {
        "guestID": "5678",
        "firstName": "Martha",
        "lastName": "Washington",
        "cabinNumber": "2",
        "checkInDate": "202606291800",
        "checkOutDate": "202607152200",
        "language": "EN",
        "greeting": "Mrs",
        "mainGuest": "1",
        "type": "P",
        "voyageID": "CRUISE-01",
        "enabled": "1"
    },
    {
        "guestID": "1111",
        "firstName": "Cyril",
        "lastName": "Jacinth",
        "cabinNumber": "2",
        "checkInDate": "202606291700",
        "checkOutDate": "202607152200",
        "language": "EN",
        "greeting": "Mr",
        "mainGuest": "0",
        "type": "P",
        "voyageID": "CRUISE-01",
        "enabled": "1"
    }
]

# =====================================================================
# SELF-HEALING DATABASE ENGINE (Prevents JSONDecodeError Crashes)
# =====================================================================

def load_passengers():
    """Reads data from disk with automated crash prevention fallbacks."""
    if not os.path.exists(DATA_FILE):
        print("⚠️ [DB_INIT]: passengers.json missing. Generating pristine dataset...")
        save_passengers(INITIAL_MOCK_DATA)
        return INITIAL_MOCK_DATA
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print("⚠️ [DB_EMPTY]: File was empty. Re-seeding baseline data.")
                save_passengers(INITIAL_MOCK_DATA)
                return INITIAL_MOCK_DATA
            return json.loads(content)
    except Exception as e:
        print(f"🚨 [JSON CORRUPTION DETECTED]: {e}. Overwriting file with healthy baseline state.")
        save_passengers(INITIAL_MOCK_DATA)
        return INITIAL_MOCK_DATA

def save_passengers(passengers_list):
    """Safely commits database array changes directly back to disk storage."""
    print(f"💾 [DB_WRITE]: Synchronizing {len(passengers_list)} profiles to disk storage.")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(passengers_list, f, indent=4)

def make_xml_response(request_name, response_text):
    """Compiles a strict iso-8859-1 response matching Callisto document rules."""
    xml_data = f"""<?xml version="1.0" encoding="iso-8859-1" ?>
<Callisto>
    <Request>{request_name}</Request>
    <Response>{response_text}</Response>
</Callisto>"""
    return Response(xml_data, mimetype='application/xml')

# =====================================================================
# INBOUND ROUTING INTERFACES (CALLISTO -> MOCK SERVER)
# =====================================================================

@app.route('/API/mxp_rc.exe/Guest', methods=['GET'])
@app.route('/API/mxp_rc.exe/Guest/', methods=['GET'])
def pms_get_guest_manifest():
    ship_code = request.args.get('ship_code') or VALID_SHIP_CODE
    incoming_id = request.args.get('account_id') or request.args.get('passenger_id') or request.args.get('guestID')
    passengers = load_passengers()
    
    if incoming_id:
        print(f"👥 [XML-PULL]: Callisto target validation for Guest ID: {incoming_id}")
        matched = next((x for x in passengers if x.get("guestID") == incoming_id), None)
        if matched:
            single_xml = f'<?xml version="1.0" encoding="UTF-8"?><Callisto><Status>Success</Status><Passenger><guestID>{matched["guestID"]}</guestID><firstName>{matched["firstName"]}</firstName><lastName>{matched["lastName"]}</lastName><cabinNumber>{matched["cabinNumber"]}</cabinNumber><checkInDate>{matched["checkInDate"]}</checkInDate><checkOutDate>{matched["checkOutDate"]}</checkOutDate><language>{matched["language"]}</language><greeting>{matched["greeting"]}</greeting><mainGuest>{matched["mainGuest"]}</mainGuest><type>{matched["type"]}</type><voyageID>{ship_code}</voyageID><enabled>{matched["enabled"]}</enabled></Passenger></Callisto>'
            return Response(single_xml, mimetype='application/xml; charset=utf-8')

    print(f"👥 [XML-PULL]: Generating uncompressed background manifest loop for Ship: {ship_code}")
    elements = "".join([f'<Passenger><guestID>{x["guestID"]}</guestID><firstName>{x["firstName"]}</firstName><lastName>{x["lastName"]}</lastName><cabinNumber>{x["cabinNumber"]}</cabinNumber><checkInDate>{x["checkInDate"]}</checkInDate><checkOutDate>{x["checkOutDate"]}</checkOutDate><language>{x["language"]}</language><greeting>{x["greeting"]}</greeting><mainGuest>{x["mainGuest"]}</mainGuest><type>{x["type"]}</type><voyageID>{ship_code}</voyageID><enabled>{x["enabled"]}</enabled></Passenger>' for x in passengers])
    master_xml = f'<?xml version="1.0" encoding="UTF-8"?><Callisto><Status>Success</Status><ShipCode>{ship_code}</ShipCode><TotalRecords>{len(passengers)}</TotalRecords><Manifest>{elements}</Manifest></Callisto>'
    return Response(master_xml, mimetype='application/xml; charset=utf-8')

@app.route('/rest/checkIn.asp', methods=['POST'])
@app.route('/API/checkIn', methods=['POST'])
def inbound_guest_checkin():
    guest_id = request.form.get('guestID')
    first_name = request.form.get('firstName')
    last_name = request.form.get('lastName')
    cabin_number = request.form.get('cabinNumber')
    check_in_date = request.form.get('checkInDate')
    check_out_date = request.form.get('checkOutDate')
    language = request.form.get('language')
    
    if not all([guest_id, first_name, last_name, cabin_number, check_in_date, check_out_date, language]):
        print("❌ [CHECK-IN REJECT]: Dropped inbound connection due to incomplete parameters.")
        return make_xml_response("checkIn", "PARAMETER_MISSING")

    passenger_payload = {
        "guestID": guest_id, "firstName": first_name, "lastName": last_name, "cabinNumber": cabin_number,
        "checkInDate": check_in_date, "checkOutDate": check_out_date, "language": language,
        "greeting": request.form.get('greeting', 'Mr'), "mainGuest": request.form.get('mainGuest', '1'),
        "type": request.form.get('type', 'P'), "voyageID": request.form.get('voyageID', VALID_SHIP_CODE),
        "enabled": request.form.get('enabled', '1')
    }

    passengers = load_passengers()
    passengers = [x for x in passengers if x.get("guestID") != guest_id]
    passengers.append(passenger_payload)
    save_passengers(passengers)
    
    print(f"📥 [REAL-TIME CHECK-IN]: Registered {first_name} {last_name} into Cabin {cabin_number}.")
    return make_xml_response("checkIn", "OK")

@app.route('/rest/checkOut.asp', methods=['POST'])
@app.route('/API/checkOut', methods=['POST'])
def inbound_guest_checkout():
    guest_id = request.form.get('guestID') or request.form.get('guestId')
    if not guest_id: return make_xml_response("checkOut", "PARAMETER_MISSING")

    passengers = load_passengers()
    target_match = next((x for x in passengers if x.get("guestID") == guest_id), None)
    if not target_match: return make_xml_response("checkOut", "NOT_FOUND")

    passengers = [x for x in passengers if x.get("guestID") != guest_id]
    save_passengers(passengers)
    
    print(f"🏃 [REAL-TIME CHECK-OUT]: Checked out Guest ID {guest_id} from Cabin {target_match.get('cabinNumber')}.")
    return make_xml_response("checkOut", "OK")

# --- OTHER INTEGRATION SPECS RESTORED ---
@app.route('/rest/cabinMove.asp', methods=['POST'])
@app.route('/API/cabinMove', methods=['POST'])
def inbound_cabin_move():
    guest_id = request.form.get('guestID')
    new_cabin = request.form.get('newCabinNumber')
    if not guest_id or not new_cabin: return make_xml_response("cabinMove", "PARAMETER_MISSING")
    passengers = load_passengers()
    g = next((x for x in passengers if x["guestID"] == guest_id), None)
    if not g: return make_xml_response("cabinMove", "NOT_FOUND")
    g["cabinNumber"] = new_cabin
    save_passengers(passengers)
    return make_xml_response("cabinMove", "OK")

@app.route('/rest/disablePhone.asp', methods=['POST'])
@app.route('/API/disablePhone', methods=['POST'])
def inbound_disable_phone():
    return make_xml_response("disablePhone", "OK")

@app.route('/rest/enablePhone.asp', methods=['POST'])
@app.route('/API/enablePhone', methods=['POST'])
def inbound_enable_phone():
    return make_xml_response("enablePhone", "OK")

@app.route('/rest/setWakeup.asp', methods=['POST'])
@app.route('/API/setWakeup', methods=['POST'])
def inbound_set_wakeup():
    return make_xml_response("setWakeup", "OK")

@app.route('/rest/deleteWakeup.asp', methods=['POST'])
@app.route('/API/deleteWakeup', methods=['POST'])
def inbound_delete_wakeup():
    return make_xml_response("deleteWakeup", "OK")

@app.route('/API/postCall', methods=['POST'])
@app.route('/rest/postCall', methods=['POST'])
def inbound_post_call_charge():
    return make_xml_response("postCall", "OK")

@app.route('/API/cabinStatus', methods=['POST'])
def inbound_cabin_status_change():
    return make_xml_response("cabinStatus", "OK")

# =====================================================================
# REST UTILITIES (JSON baseline formats format)
# =====================================================================

@app.route('/API/mxp_api.exe/GetShipStatus', methods=['GET'])
def mxp_get_ship_status():
    return jsonify({"status": "Success", "ship_code": VALID_SHIP_CODE, "system_status": "Online"})

@app.route('/API/mxp_rc.exe/Cruise/', methods=['GET'])
@app.route('/API/mxp_rc.exe/Cruise', methods=['GET'])
def mxp_get_cruise_manifest():
    return jsonify({"status": "Success", "data": {"ship": VALID_SHIP_CODE, "status": "Active"}})

@app.route('/API/mxp_api.exe/EmployeePhoneDirectory/', methods=['GET'])
@app.route('/API/mxp_api.exe/EmployeePhoneDirectory', methods=['GET'])
def pms_get_employee_directory():
    return jsonify({"status": "Success", "contacts": [{"name": "Medical Center", "extension": "4000"}]})

# =====================================================================
# OUTBOUND SYSTEM WORKFLOW TRIGGERS (MOCK -> CALLISTO)
# =====================================================================

def push_passenger_to_callisto(passenger, callisto_ip, username, password):
    url = f"http://{callisto_ip}/Applications/startup/cruise%20Base/rest/checkIn.asp"
    payload = {
        "guestID": passenger.get("guestID"),
        "firstName": passenger.get("firstName"),
        "lastName": passenger.get("lastName"),
        "cabinNumber": passenger.get("cabinNumber"),
        "checkInDate": passenger.get("checkInDate"),
        "checkOutDate": passenger.get("checkOutDate"),
        "language": passenger.get("language", "EN"),
        "greeting": passenger.get("greeting", "Mr"),
        "mainGuest": passenger.get("mainGuest", "1"),
        "type": passenger.get("type", "P"),
        "voyageID": passenger.get("voyageID", VALID_SHIP_CODE),
        "enabled": passenger.get("enabled", "1")
    }
    headers = {
       "Accept": "application/xml",
       "Content-Type": "application/x-www-form-urlencoded"
       }
    print(f"🚀 [PUSH TASK]: Shipping check-in context for {payload['firstName']} to Callisto Core Server...")
    try:
        from requests.auth import HTTPBasicAuth
        response = requests.post(url, data=payload, auth=HTTPBasicAuth(username, password), headers=headers, timeout=5)
        return response.text, response.status_code
    except Exception as e:
        return f"Network Error: {e}", 500

def checkout_passenger_from_callisto(guest_id, callisto_ip, username, password):
    url = f"http://{callisto_ip}/Applications/startup/cruise%20Base/rest/checkOut.asp"
    headers = {"accept": "application/xml"}
    print(f"🏃 [CHECKOUT TASK]: Requesting checkout context for Guest ID: {guest_id} over to Callisto...")
    try:
        from requests.auth import HTTPBasicAuth
        response = requests.post(url, data={"guestID": guest_id}, auth=HTTPBasicAuth(username, password), headers=headers, timeout=5)
        return response.text, response.status_code
    except Exception as e:
        return f"Network Error: {e}", 500

@app.route('/pms/push/<guest_id>', methods=['GET'])
def trigger_push_endpoint(guest_id):
    passengers = load_passengers()
    passenger = next((g for g in passengers if g.get("guestID") == guest_id), None)
    if not passenger:
        return jsonify({"error": f"ID {guest_id} not found in database"}), 404
        
    xml_response, status_code = push_passenger_to_callisto(passenger, CALLISTO_IP, CALLISTO_USER, CALLISTO_PASS)
    return jsonify({"info": f"Pushed ID {guest_id}", "callisto_http_status": status_code, "callisto_xml_output": xml_response})

@app.route('/pms/checkout/<guest_id>', methods=['GET'])
def trigger_checkout_endpoint(guest_id):
    print(f"\n--- INITIATING MANUAL CHECKOUT FOR ID: {guest_id} ---")
    xml_response, status_code = checkout_passenger_from_callisto(guest_id, CALLISTO_IP, CALLISTO_USER, CALLISTO_PASS)
    
    if status_code == 200 and "OK" in xml_response:
        print("✅ [NETWORK_SUCCESS]: Callisto accepted checkout. Updating local database.")
        passengers = load_passengers()
        passengers = [g for g in passengers if g.get("guestID") != guest_id]
        save_passengers(passengers)
    else:
        print("⚠️ [NETWORK_WARN]: Callisto did not process a successful 'OK' response.")
        
    return jsonify({"info": f"Checkout context sent for ID {guest_id}", "callisto_http_status": status_code, "callisto_xml_output": xml_response})

@app.route('/pms/reset', methods=['GET'])
def force_database_reset():
    """Manual trigger to completely refresh data states back to standard values."""
    save_passengers(INITIAL_MOCK_DATA)
    return jsonify({"status": "Database cleared and re-seeded with future dates."})

# =====================================================================
# SYSTEM STARTUP RUNNER
# =====================================================================
if __name__ == '__main__':
    print("🚀 Running Modular Mock PMS Production Core Engine v3.1...")
    load_passengers() 
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)