# -*- coding: utf-8 -*-
"""
Callisto Cruise Base PMS REST Integration Engine
Provides mock functions for 100% of specified inbound/outbound REST specifications.
"""

import time
from datetime import datetime
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
app.url_map.strict_slashes = False

VALID_SHIP_CODE = "CRUISE-01"

# Memory Warehouse
mock_passengers = [
    {"guestID": "1234", "firstName": "George", "lastName": "Washington", "cabinNumber": "1", "checkInDate": "202606251200", "checkOutDate": "202606261200", "language": "EN", "greeting": "Mr", "mainGuest": "1", "type": "P", "voyageID": "CRUISE-01", "enabled": "1"},
    {"guestID": "5678", "firstName": "Martha", "lastName": "Washington", "cabinNumber": "2", "checkInDate": "202606251200", "checkOutDate": "202606261200", "language": "EN", "greeting": "Mrs", "mainGuest": "1", "type": "P", "voyageID": "CRUISE-01", "enabled": "1"},
    {"guestID": "1111", "firstName": "Cyril", "lastName": "Jacinth", "cabinNumber": "2", "checkInDate": "202606251200", "checkOutDate": "202606261200", "language": "EN", "greeting": "Mr", "mainGuest": "0", "type": "P", "voyageID": "CRUISE-01", "enabled": "1"}
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
# MANDATORY SPECIFICATION DIRECT FUNCTIONS (CALLISTO -> MOCK SERVER)
# =====================================================================

# --- SPEC 1: Full Manifest / Individual Profile Driver (Pull) ---
@app.route('/API/mxp_rc.exe/Guest', methods=['GET'])
def pms_get_guest_manifest():
    ship_code = request.args.get('ship_code') or VALID_SHIP_CODE
    incoming_id = request.args.get('account_id') or request.args.get('passenger_id') or request.args.get('guestID')
    
    if incoming_id:
        print(f"👥 [PULL MATCH]: Filtering data asset profiles for Guest ID: {incoming_id}")
        g = next((x for x in mock_passengers if x["guestID"] == incoming_id), None)
        if g:
            single_xml = f'<?xml version="1.0" encoding="UTF-8"?><Callisto><Status>Success</Status><Passenger><guestID>{g["guestID"]}</guestID><firstName>{g["firstName"]}</firstName><lastName>{g["lastName"]}</lastName><cabinNumber>{g["cabinNumber"]}</cabinNumber><checkInDate>{g["checkInDate"]}</checkInDate><checkOutDate>{g["checkOutDate"]}</checkOutDate><language>{g["language"]}</language><greeting>{g["greeting"]}</greeting><mainGuest>{g["mainGuest"]}</mainGuest><type>{g["type"]}</type><voyageID>{ship_code}</voyageID><enabled>{g["enabled"]}</enabled></Passenger></Callisto>'
            return Response(single_xml, mimetype='application/xml')

    print(f"👥 [PULL FULL]: Compiling background bulk database synchronization matrix array...")
    elements = "".join([f'<Passenger><guestID>{x["guestID"]}</guestID><firstName>{x["firstName"]}</firstName><lastName>{x["lastName"]}</lastName><cabinNumber>{x["cabinNumber"]}</cabinNumber><checkInDate>{x["checkInDate"]}</checkInDate><checkOutDate>{x["checkOutDate"]}</checkOutDate><language>{x["language"]}</language><greeting>{x["greeting"]}</greeting><mainGuest>{x["mainGuest"]}</mainGuest><type>{x["type"]}</type><voyageID>{ship_code}</voyageID><enabled>{x["enabled"]}</enabled></Passenger>' for x in mock_passengers])
    master_xml = f'<?xml version="1.0" encoding="UTF-8"?><Callisto><Status>Success</Status><ShipCode>{ship_code}</ShipCode><TotalRecords>{len(mock_passengers)}</TotalRecords><Manifest>{elements}</Manifest></Callisto>'
    return Response(master_xml, mimetype='application/xml')

# --- SPEC 2: Guest Room Move Handler ---
@app.route('/rest/cabinMove.asp', methods=['POST'])
@app.route('/API/cabinMove', methods=['POST'])
def inbound_cabin_move():
    guest_id = request.form.get('guestID')
    new_cabin = request.form.get('newCabinNumber')
    print(f"🔄 [CABIN MOVE REQ]: Processing move request packet for ID: {guest_id} to Cabin: {new_cabin}")
    
    if not guest_id or not new_cabin:
        return make_xml_response("cabinMove", "PARAMETER_MISSING")
        
    g = next((x for x in mock_passengers if x["guestID"] == guest_id), None)
    if not g:
        return make_xml_response("cabinMove", "NOT_FOUND")
        
    g["cabinNumber"] = new_cabin
    print(f"✅ [CABIN MOVE SUCCESS]: Relocated Guest ID {guest_id} cleanly to Cabin extension slot {new_cabin}.")
    return make_xml_response("cabinMove", "OK")

# --- SPEC 3: Disable Phone External Call Routing Lines ---
@app.route('/rest/disablePhone.asp', methods=['POST'])
@app.route('/API/disablePhone', methods=['POST'])
def inbound_disable_phone():
    cabin = request.form.get('cabinNumber')
    print(f"🔒 [PHONE BAR]: Request to bar satellite trunk routing links for Cabin: {cabin}")
    if not cabin: return make_xml_response("disablePhone", "PARAMETER_MISSING")
    return make_xml_response("disablePhone", "OK")

# --- SPEC 4: Enable Phone External Call Routing Lines ---
@app.route('/rest/enablePhone.asp', methods=['POST'])
@app.route('/API/enablePhone', methods=['POST'])
def inbound_enable_phone():
    cabin = request.form.get('cabinNumber')
    print(f"🔓 [PHONE UNBAR]: Request to allow satellite trunk routing links for Cabin: {cabin}")
    if not cabin: return make_xml_response("enablePhone", "PARAMETER_MISSING")
    return make_xml_response("enablePhone", "OK")

# --- SPEC 5: Set Wakeup Alarm Timer ---
@app.route('/rest/setWakeup.asp', methods=['POST'])
@app.route('/API/setWakeup', methods=['POST'])
def inbound_set_wakeup():
    cabin = request.form.get('cabinNumber')
    w_time = request.form.get('wakeupTime')
    group = request.form.get('groupID')
    print(f"⏰ [WAKEUP SET]: Request for Alarm at {w_time} in Cabin: {cabin} / Group: {group}")
    
    if not w_time or (not cabin and not group):
        return make_xml_response("setWakeup", "PARAMETER_MISSING")
    return make_xml_response("setWakeup", "OK")

# --- SPEC 6: Delete Wakeup Alarm Timer ---
@app.route('/rest/deleteWakeup.asp', methods=['POST'])
@app.route('/API/deleteWakeup', methods=['POST'])
def inbound_delete_wakeup():
    cabin = request.form.get('cabinNumber')
    group = request.form.get('groupID')
    print(f"🚫 [WAKEUP CLEAR]: Request to purge alarm configurations for Cabin: {cabin} / Group: {group}")
    
    if not cabin and not group:
        return make_xml_response("deleteWakeup", "PARAMETER_MISSING")
    return make_xml_response("deleteWakeup", "OK")

# --- SPEC 7: Post Call Telephone Ledger Accounting Hooks ---
@app.route('/API/postCall', methods=['POST'])
@app.route('/rest/postCall', methods=['POST'])
def inbound_post_call_charge():
    cabin = request.form.get('cabinNumber')
    amount = request.form.get('amount')
    call_id = request.form.get('callID')
    
    if not cabin or not amount or not call_id:
        return make_xml_response("postCall", "PARAMETER_MISSING")
        
    try:
        if float(amount) >= 0:
            print(f"📞 [TELEPHONY POST]: Billed ${amount} to Cabin {cabin} (Call ID: {call_id})")
        else:
            print(f"💰 [TELEPHONY POST]: Processed credit refund of ${amount} to Cabin {cabin}")
    except ValueError:
        return make_xml_response("postCall", "ERROR")
        
    return make_xml_response("postCall", "OK")

# --- SPEC 8: Housekeeping/Cabin State Updates ---
@app.route('/API/cabinStatus', methods=['POST'])
def inbound_cabin_status_change():
    cabin = request.form.get('cabinNumber')
    code = request.form.get('status', '').upper()
    if not cabin or not code: return make_xml_response("cabinStatus", "PARAMETER_MISSING")
    print(f"🧹 [HOUSEKEEPING LOG]: Cabin {cabin} assigned state code: {code}")
    return make_xml_response("cabinStatus", "OK")

# --- SPEC 9: Support Baseline System Utilities ---
@app.route('/API/mxp_api.exe/GetShipStatus', methods=['GET'])
def mxp_get_ship_status():
    return jsonify({"status": "Success", "ship_code": VALID_SHIP_CODE, "system_status": "Online"})

@app.route('/API/mxp_rc.exe/Cruise/', methods=['GET'])
def mxp_get_cruise_manifest():
    return jsonify({"status": "Success", "data": {"ship": VALID_SHIP_CODE, "status": "Active"}})

@app.route('/API/mxp_api.exe/EmployeePhoneDirectory/', methods=['GET'])
def mxp_get_employee_directory():
    return jsonify({"status": "Success", "contacts": [{"name": "Medical Center", "extension": "4000"}]})

# =====================================================================
# SYSTEM MAIN ENGINE STARTUP (IDE OPTIMIZED)
# =====================================================================
if __name__ == '__main__':
    print("🚀 Modular Mock PMS Server Engine Initializing...")
    print("👉 Serving 100% of system REST functions locally on Port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
