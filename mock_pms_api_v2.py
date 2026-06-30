# -*- coding: utf-8 -*-
"""
Callisto Cruise Base PMS REST Integration Engine
Provides mock functions for 100% of specified inbound/outbound REST specifications.
"""

import time
import requests
from datetime import datetime
from flask import Flask, jsonify, request, Response

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
        "guestID": "1234",
        "firstName": "George",
        "lastName": "Washington",
        "cabinNumber": "1",
        "checkInDate": "202606251510",
        "checkOutDate": "202606251515",
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
        "checkInDate": "202606251200",
        "checkOutDate": "202606261200",
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
        "checkInDate": "202606251200",
        "checkOutDate": "202606261200",
        "language": "EN",
        "greeting": "Mr",
        "mainGuest": "0",
        "type": "P",
        "voyageID": "CRUISE-01",
        "enabled": "1"
    }
]

def make_xml_response(request_name, response_text):
    """Compiles a strict iso-8859-1 payload matching Callisto document specifications."""
    xml_data = f"""<?xml version="1.0" encoding="iso-8859-1" ?>
<Callisto>
    <Request>{request_name}</Request>
    <Response>{response_text}</Response>
</Callisto>"""
    return Response(xml_data, mimetype='application/xml')

# =====================================================================
# INBOUND ROUTING INTERFACES (CALLISTO -> MOCK SERVER)
# =====================================================================

# --- SPEC 1: Full Manifest / Individual Profile Driver (Pull) ---
@app.route('/API/mxp_rc.exe/Guest', methods=['GET'])
def pms_get_guest_manifest():
    ship_code = request.args.get('ship_code') or VALID_SHIP_CODE
    incoming_id = request.args.get('account_id') or request.args.get('passenger_id') or request.args.get('guestID')
    
    if incoming_id:
        print(f"👥 [XML-PULL]: Callisto target validation pass for ID: {incoming_id}")
        matched = next((x for x in mock_passengers if x["guestID"] == incoming_id), None)
        if matched:
            single_xml = f'<?xml version="1.0" encoding="UTF-8"?><Callisto><Status>Success</Status><Passenger><guestID>{matched["guestID"]}</guestID><firstName>{matched["firstName"]}</firstName><lastName>{matched["lastName"]}</lastName><cabinNumber>{matched["cabinNumber"]}</cabinNumber><checkInDate>{matched["checkInDate"]}</checkInDate><checkOutDate>{matched["checkOutDate"]}</checkOutDate><language>{matched["language"]}</language><greeting>{matched["greeting"]}</greeting><mainGuest>{matched["mainGuest"]}</mainGuest><type>{matched["type"]}</type><voyageID>{ship_code}</voyageID><enabled>{matched["enabled"]}</enabled></Passenger></Callisto>'
            return Response(single_xml, mimetype='application/xml')

    print(f"👥 [XML-PULL]: Callisto downloading Full Manifest for Ship: {ship_code}")
    elements = "".join([f'<Passenger><guestID>{x["guestID"]}</guestID><firstName>{x["firstName"]}</firstName><lastName>{x["lastName"]}</lastName><cabinNumber>{x["cabinNumber"]}</cabinNumber><checkInDate>{x["checkInDate"]}</checkInDate><checkOutDate>{x["checkOutDate"]}</checkOutDate><language>{x["language"]}</language><greeting>{x["greeting"]}</greeting><mainGuest>{x["mainGuest"]}</mainGuest><type>{x["type"]}</type><voyageID>{ship_code}</voyageID><enabled>{x["enabled"]}</enabled></Passenger>' for x in mock_passengers])
    master_xml = f'<?xml version="1.0" encoding="UTF-8"?><Callisto><Status>Success</Status><ShipCode>{ship_code}</ShipCode><TotalRecords>{len(mock_passengers)}</TotalRecords><Manifest>{elements}</Manifest></Callisto>'
    return Response(master_xml, mimetype='application/xml')

# --- SPEC 2: Inbound Real-Time Guest Check-In Listener ---
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
        print("❌ [CHECK-IN REJECT]: Missing parameters.")
        return make_xml_response("checkIn", "PARAMETER_MISSING")

    passenger_payload = {
        "guestID": guest_id, "firstName": first_name, "lastName": last_name, "cabinNumber": cabin_number,
        "checkInDate": check_in_date, "checkOutDate": check_out_date, "language": language,
        "greeting": request.form.get('greeting', 'Mr'), "mainGuest": request.form.get('mainGuest', '1'),
        "type": request.form.get('type', 'P'), "voyageID": request.form.get('voyageID', VALID_SHIP_CODE),
        "enabled": request.form.get('enabled', '1')
    }

    global mock_passengers
    mock_passengers = [x for x in mock_passengers if x["guestID"] != guest_id]
    mock_passengers.append(passenger_payload)
    print(f"📥 [REAL-TIME CHECK-IN]: Registered {first_name} {last_name} to Cabin {cabin_number} (ID: {guest_id}).")
    return make_xml_response("checkIn", "OK")

# --- SPEC 3: Inbound Real-Time Guest Check-Out Listener ---
@app.route('/rest/checkOut.asp', methods=['POST'])
@app.route('/API/checkOut', methods=['POST'])
def inbound_guest_checkout():
    guest_id = request.form.get('guestID') or request.form.get('guestId')
    if not guest_id: return make_xml_response("checkOut", "PARAMETER_MISSING")

    global mock_passengers
    target_match = next((x for x in mock_passengers if x["guestID"] == guest_id), None)
    if not target_match: return make_xml_response("checkOut", "NOT_FOUND")

    mock_passengers = [x for x in mock_passengers if x["guestID"] != guest_id]
    print(f"🏃 [REAL-TIME CHECK-OUT]: Checked out Guest ID {guest_id} from Cabin {target_match['cabinNumber']}.")
    return make_xml_response("checkOut", "OK")

# --- SPEC 4: Guest Room Move Handler ---
@app.route('/rest/cabinMove.asp', methods=['POST'])
@app.route('/API/cabinMove', methods=['POST'])
def inbound_cabin_move():
    guest_id = request.form.get('guestID')
    new_cabin = request.form.get('newCabinNumber')
    if not guest_id or not new_cabin: return make_xml_response("cabinMove", "PARAMETER_MISSING")
        
    g = next((x for x in mock_passengers if x["guestID"] == guest_id), None)
    if not g: return make_xml_response("cabinMove", "NOT_FOUND")
        
    g["cabinNumber"] = new_cabin
    print(f"✅ [CABIN MOVE SUCCESS]: Moved Guest ID {guest_id} to Cabin extension {new_cabin}.")
    return make_xml_response("cabinMove", "OK")

# --- SPEC 5: Disable Phone External Call Routing Lines ---
@app.route('/rest/disablePhone.asp', methods=['POST'])
@app.route('/API/disablePhone', methods=['POST'])
def inbound_disable_phone():
    cabin = request.form.get('cabinNumber')
    if not cabin: return make_xml_response("disablePhone", "PARAMETER_MISSING")
    print(f"🔒 [PHONE BAR]: Barred calls for Cabin: {cabin}")
    return make_xml_response("disablePhone", "OK")

# --- SPEC 6: Enable Phone External Call Routing Lines ---
@app.route('/rest/enablePhone.asp', methods=['POST'])
@app.route('/API/enablePhone', methods=['POST'])
def inbound_enable_phone():
    cabin = request.form.get('cabinNumber')
    if not cabin: return make_xml_response("enablePhone", "PARAMETER_MISSING")
    print(f"🔓 [PHONE UNBAR]: Allowed calls for Cabin: {cabin}")
    return make_xml_response("enablePhone", "OK")

# --- SPEC 7: Set Wakeup Alarm Timer ---
@app.route('/rest/setWakeup.asp', methods=['POST'])
@app.route('/API/setWakeup', methods=['POST'])
def inbound_set_wakeup():
    cabin = request.form.get('cabinNumber')
    w_time = request.form.get('wakeupTime')
    group = request.form.get('groupID')
    if not w_time or (not cabin and not group): return make_xml_response("setWakeup", "PARAMETER_MISSING")
    print(f"⏰ [WAKEUP SET]: Alarm at {w_time} in Cabin: {cabin} / Group: {group}")
    return make_xml_response("setWakeup", "OK")

# --- SPEC 8: Delete Wakeup Alarm Timer ---
@app.route('/rest/deleteWakeup.asp', methods=['POST'])
@app.route('/API/deleteWakeup', methods=['POST'])
def inbound_delete_wakeup():
    cabin = request.form.get('cabinNumber')
    group = request.form.get('groupID')
    if not cabin and not group: return make_xml_response("deleteWakeup", "PARAMETER_MISSING")
    print(f"🚫 [WAKEUP CLEAR]: Purged alarm for Cabin: {cabin} / Group: {group}")
    return make_xml_response("deleteWakeup", "OK")

# --- SPEC 9: Post Call Telephone Ledger Accounting Hooks ---
@app.route('/API/postCall', methods=['POST'])
@app.route('/rest/postCall', methods=['POST'])
def inbound_post_call_charge():
    cabin = request.form.get('cabinNumber')
    amount = request.form.get('amount')
    call_id = request.form.get('callID')
    if not cabin or not amount or not call_id: return make_xml_response("postCall", "PARAMETER_MISSING")
    print(f"📞 [TELEPHONY POST]: Billed ${amount} to Cabin {cabin} (Call ID: {call_id})")
    return make_xml_response("postCall", "OK")

# --- SPEC 10: Housekeeping/Cabin State Updates ---
@app.route('/API/cabinStatus', methods=['POST'])
def inbound_cabin_status_change():
    cabin = request.form.get('cabinNumber')
    code=request.form.get('status',"").upper()
    if not cabin or not code:
        return make_xml_response("cabinStatus","PARAMETER_MISSING")
    print(f" [HOUSE_KEEPING LOG]: Cabin {cabin} assigned state code: {code}")
    return make_xml_response("cabinStatus","OK")

# =====================================================================
# UTILITIES: Baseline System Support
# =====================================================================
@app.route('/API/mxp_api.exe/GetShipStatus', methods=['GET'])
def mxp_get_ship_status():
    return jsonify(
    {"status": "Success", 
    "ship_code": VALID_SHIP_CODE, 
    "system_status": "Online"})

@app.route('/API/mxp_rc.exe/Cruise/', methods=['GET'])
def mxp_get_cruise_manifest():
    return jsonify(
    {"status": "Success", 
     "data": {"ship": VALID_SHIP_CODE,
     "status": "Active"}})

@app.route('/API/mxp_api.exe/EmployeePhoneDirectory/', methods=['GET'])
def pms_get_employee_directory():
    return jsonify(
    {"status": "Success", 
     "contacts": [{
     "name": "Medical Center",
     "extension": "4000"}]})
#=====================================================================
#OUTBOUND PUSH SCHEDULERS (MOCK SERVER -> CALLISTO)
#=====================================================================
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
        "voyageID": passenger.get("voyageID")}
    
    headers = {"accept": "application/xml"}
    print(f"ðŸš€ [PUSH TASK]: Forwarding {payload['firstName']} to Callisto...")
    try:
        response = requests.post(url, data=payload, auth=(username, password), headers=headers, timeout=5)
        return response.text, response.status_code
    except Exception as e:
        return f"Network Error: {e}", 500

def checkout_passenger_from_callisto(guest_id, callisto_ip, username, password):
    url = f"http://{callisto_ip}/Applications/startup/cruise%20Base/rest/checkOut.asp"
    headers = {"accept": "application/xml"}
    print(f"ðŸƒ [CHECKOUT TASK]: Requesting checkout for Guest ID: {guest_id}...")
    try:
        response = requests.post(url, data={"guestID": guest_id}, auth=(username, password), headers=headers, timeout=5)
        return response.text, response.status_code
    except Exception as e:
        return f"Network Error: {e}", 500

@app.route('/pms/push/<guest_id>', methods=['GET'])
def trigger_push_endpoint(guest_id):
    passenger = next((g for g in mock_passengers if g["guestID"] == guest_id), None)
    if not passenger:
        return jsonify({"error": f"ID {guest_id} not found"}), 404
    xml_response, status_code = push_passenger_to_callisto(passenger, CALLISTO_IP, CALLISTO_USER, CALLISTO_PASS)
    return jsonify({"info": f"Pushed ID {guest_id}", "callisto_http_status": status_code, "callisto_xml_output": xml_response})

@app.route('/pms/checkout/<guest_id>', methods=['GET'])
def trigger_checkout_endpoint(guest_id):
    global mock_passengers
    xml_response, status_code = checkout_passenger_from_callisto(guest_id, CALLISTO_IP, CALLISTO_USER, CALLISTO_PASS)
    if status_code == 200 and "OK" in xml_response:
        mock_passengers = [g for g in mock_passengers if g["guestID"] != guest_id]
    return jsonify({"info": f"Checked out ID {guest_id}", "callisto_http_status": status_code, "callisto_xml_output": xml_response})

    

# =====================================================================
# SYSTEM MAIN ENGINE STARTUP (IDE OPTIMIZED)
# =====================================================================
if __name__ == '__main__':
    print("🚀 Modular Mock PMS Server Engine Initializing...")
    print("👉 Serving 100% of system REST functions locally on Port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
