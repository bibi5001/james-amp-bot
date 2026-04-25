# 🎩 James – A Matrix Bot for CubeCoders AMP

James is a Matrix bot that allows you to control game server instances in [CubeCoders AMP](https://cubecoders.com/AMP) directly from your Matrix chat — with the dignified composure of a proper English butler.

## Features

- 🟢 **Start the server** – `james start`
- 🔴 **Stop the server** – `james stop`
- 🔄 **Update the server** – `james update`
- 📊 **Status enquiry** – `james status`
- ❓ **List commands** – `james help`
- 🔔 **Webhook notifications** – AMP reports status changes automatically to the chat

## Example

```
You:   james start
James: Very good, sir. I shall start the instance on Castle IX forthwith.

You:   james stop
James: As you wish. I shall bring the server on Castle IX to a graceful halt. Good night.

You:   james status
James: I am at your service, sir. The connection to Castle IX is in fine order.
```

## Prerequisites

- Docker & Docker Compose
- A Matrix account for the bot (e.g. on your own Synapse server)
- CubeCoders AMP with an ADS master and at least one instance
- An AMP user with sufficient permissions (`Core.AppManagement.*`)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/james-amp-bot.git
cd james-amp-bot
```

### 2. Create your `.env` file

```bash
cp .env.example .env
nano .env
```

| Variable | Description |
|---|---|
| `MATRIX_HOMESERVER` | URL of your Matrix server |
| `MATRIX_USER` | Matrix user ID of the bot (`@james:your.server`) |
| `MATRIX_TOKEN` | Access token of the bot account |
| `MATRIX_ROOM_ID` | Room ID where James should be active |
| `AMP_BASE_URL` | URL of the AMP ADS master (`http://ip:8080`) |
| `AMP_USER` | AMP username |
| `AMP_PASS` | AMP password |
| `AMP_INSTANCE_UUID` | UUID of the instance to be controlled |
| `SERVER_NAME` | Display name of the server (e.g. `Castle IX`) |

### 3. Find your Instance UUID

First, obtain a session ID:

```bash
SESSION=$(curl -s -X POST http://YOUR-AMP-URL:8080/API/Core/Login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR-USER","password":"YOUR-PASS","token":"","rememberMe":false}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['sessionID'])")
```

Then list all instances:

```bash
curl -s -X POST http://YOUR-AMP-URL:8080/API/ADSModule/GetInstances \
  -H "Content-Type: application/json" \
  -d "{\"SESSIONID\":\"$SESSION\"}" \
  | python3 -m json.tool | grep -E '"InstanceName"|"InstanceID"'
```

Copy the `InstanceID` value for your desired instance into `AMP_INSTANCE_UUID`.

### 4. Start James

```bash
docker compose up -d
docker logs -f amp-bot
```

## Setting up AMP Webhooks (optional)

To have James announce status changes automatically:

1. Open the desired instance in AMP
2. Navigate to **Schedule → Add New Trigger → Event Trigger**
3. Select the event: `Application State Changed`
4. Add a task: **Network – Make a POST request**
5. URI: `https://your-webhook-url/webhook`
6. Content-Type: `application/json`
7. Payload:
```json
{"message": "The server {@InstanceName} is now {@State}"}
```

## Obtaining a Matrix Access Token

```bash
curl -X POST https://YOUR-MATRIX-SERVER/_matrix/client/r0/login \
  -H "Content-Type: application/json" \
  -d '{"type":"m.login.password","user":"james","password":"YOUR-PASSWORD"}'
```

The `access_token` field in the response is what you need for `MATRIX_TOKEN`.

## Notes

- James ignores messages older than 30 seconds upon restart (echo protection)
- A fresh AMP session is created for every command — no session timeout issues
- For debugging, uncomment the `print` lines in `amp-bot.py`
- The bot responds to any message containing the word **james**

## Licence

MIT
