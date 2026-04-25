import asyncio
import threading
import requests
import time
import os
from flask import Flask, request
from nio import AsyncClient, MatrixRoom, RoomMessageText

# --- CONFIGURATION ---
HOMESERVER     = os.environ.get("MATRIX_HOMESERVER", "https://your.matrix.server")
MATRIX_USER    = os.environ.get("MATRIX_USER",       "@james:your.matrix.server")
ACCESS_TOKEN   = os.environ.get("MATRIX_TOKEN",      "your-access-token")
ROOM_ID        = os.environ.get("MATRIX_ROOM_ID",    "!yourRoomId:your.matrix.server")

AMP_BASE_URL   = os.environ.get("AMP_BASE_URL",      "http://your-amp-server:8080")
AMP_USER       = os.environ.get("AMP_USER",          "your-amp-user")
AMP_PASS       = os.environ.get("AMP_PASS",          "your-amp-password")
INSTANCE_UUID  = os.environ.get("AMP_INSTANCE_UUID", "your-instance-uuid")

# Display name of the server (used in bot messages only)
SERVER_NAME    = os.environ.get("SERVER_NAME",        "My Game Server")

# --- SETUP ---
app = Flask(__name__)
client = AsyncClient(HOMESERVER, MATRIX_USER)

# --- PART 1: AMP ---
def send_amp_command(command):
    print(f"📡 Dispatching {command} command to AMP...", flush=True)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # All commands are routed through the ADS proxy to the instance
    instance_url = f"{AMP_BASE_URL}/API/ADSModule/Servers/{INSTANCE_UUID}/API/Core"

    try:
        # Login directly to the instance (via ADS proxy)
        r = requests.post(
            f"{instance_url}/Login",
            json={"username": AMP_USER, "password": AMP_PASS, "token": "", "rememberMe": False},
            headers=headers, timeout=10
        )
        response_data = r.json()

        if not response_data.get("success"):
            return f"Login refused: {response_data.get('resultReason', '?')}"

        session_id = response_data.get("sessionID")

        if command == "Start":
            endpoint = "Start"
        elif command == "Stop":
            endpoint = "Stop"
        elif command == "Update":
            endpoint = "UpdateApplication"
        else:
            return f"Unknown command: {command}"

        resp = requests.post(
            f"{instance_url}/{endpoint}",
            json={"SESSIONID": session_id},
            headers=headers, timeout=10
        )
        result = resp.json()
        # Debug logging (uncomment for troubleshooting):
        #print(f"AMP response: {result}", flush=True)

        if result.get("Status"):
            return f"✅ {command} executed successfully."
        else:
            return f"❌ Error: {result.get('Reason', '?')}"

    except Exception as e:
        print(f"❌ AMP error: {e}", flush=True)
        return f"Technical error: {str(e)}"

# --- PART 2: MATRIX ---
async def send_to_matrix(text):
    await client.room_send(
        room_id=ROOM_ID,
        message_type="m.room.message",
        content={"msgtype": "m.text", "body": f"🎩 James: {text}"}
    )

async def message_callback(room: MatrixRoom, event: RoomMessageText):
    # Echo protection: ignore messages older than 30 seconds
    current_time_ms = int(time.time() * 1000)
    if current_time_ms - event.server_timestamp > 30000:
        return

    # Ignore own messages
    if event.sender == MATRIX_USER:
        return

    msg = event.body.strip().lower()

    if "james" in msg:
        print(f"📩 INCOMING from {event.sender}: '{event.body}'", flush=True)

        if "start" in msg:
            await send_to_matrix(f"Very good, sir. I shall start the instance on {SERVER_NAME} forthwith.")
            result = send_amp_command("Start")
            print(f"Result: {result}", flush=True)

        elif "stop" in msg or "shut" in msg:
            await send_to_matrix(f"As you wish. I shall bring the server on {SERVER_NAME} to a graceful halt. Good night.")
            result = send_amp_command("Stop")
            print(f"Result: {result}", flush=True)

        elif "update" in msg:
            await send_to_matrix(f"Certainly, sir. I shall commence the update of the instance on {SERVER_NAME} at once.")
            result = send_amp_command("Update")
            print(f"Result: {result}", flush=True)

        elif "status" in msg:
            await send_to_matrix(f"I am at your service, sir. The connection to {SERVER_NAME} is in fine order.")

        elif "help" in msg:
            await send_to_matrix(
                "I am at your disposal, sir. The commands I recognise are as follows:\n"
                "• **james start** – Start the game server\n"
                "• **james stop** – Shut down the game server\n"
                "• **james update** – Update the game server\n"
                "• **james status** – Enquire after my readiness"
            )

# --- PART 3: WEBHOOKS ---
# AMP can notify James of status changes via webhook.
# Example payload in AMP Schedule:
# {"message": "The server {@InstanceName} is now {@State}"}
@app.route('/webhook', methods=['POST'])
def webhook():
    raw = request.data.decode('utf-8')
    try:
        import json
        data = json.loads(raw)
        msg = data.get("message", f"An event has been reported on {SERVER_NAME}.")
    except Exception:
        msg = raw
    # Debug logging (uncomment for troubleshooting):
    #print(f"WEBHOOK RAW: {raw}", flush=True)
    asyncio.run_coroutine_threadsafe(send_to_matrix(msg), loop)
    return "OK", 200

async def main_matrix():
    print(f"📡 James is verifying the connection to {SERVER_NAME}...", flush=True)
    try:
        requests.get(f"{AMP_BASE_URL}/API/Core/GetAPISpec", timeout=5)
        print(f"✅ {SERVER_NAME} is reachable.", flush=True)
    except Exception:
        print(f"⚠️ Warning: {SERVER_NAME} is not responding immediately.", flush=True)

    print(f"🎩 James is logging in to Matrix...", flush=True)
    try:
        client.access_token = ACCESS_TOKEN
        client.user_id = MATRIX_USER
        client.add_event_callback(message_callback, RoomMessageText)

        print(f"🎩 James is joining room: {ROOM_ID}", flush=True)
        await client.join(ROOM_ID)

        print("🎩 James is now in attendance...", flush=True)
        while True:
            await client.sync(timeout=30000, full_state=True)

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}", flush=True)
        await asyncio.sleep(10)

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    try:
        loop.run_until_complete(main_matrix())
    except KeyboardInterrupt:
        pass
