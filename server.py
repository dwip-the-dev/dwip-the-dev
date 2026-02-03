"""
ClipSync - Local Clipboard Sharing Server
==========================================

A simple WebSocket server for real-time clipboard sharing between devices.

SETUP:
------
1. Install dependencies:
   pip install flask flask-sock

2. Run the server:
   python server.py

3. Open the web app and connect to ws://YOUR_LOCAL_IP:5000

For LAN access, find your local IP:
  - Windows: ipconfig
  - Mac/Linux: ifconfig or ip addr

Then connect from other devices using ws://YOUR_IP:5000

"""

from flask import Flask, request
from flask_sock import Sock
import json
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
sock = Sock(app)

# Store active WebSocket connections per room
rooms = defaultdict(set)

# Store latest clipboard content per room
clipboard_data = {}


@app.after_request
def add_cors_headers(response):
    """Add CORS headers for cross-origin requests"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response


@app.route('/')
def index():
    """Health check endpoint"""
    return json.dumps({
        "status": "running",
        "message": "ClipSync server is running",
        "rooms_active": len(rooms),
        "timestamp": datetime.now().isoformat()
    }), 200, {'Content-Type': 'application/json'}


@sock.route('/ws/<room_id>')
def websocket(ws, room_id):
    """WebSocket handler for clipboard sync"""
    room_id = room_id.lower()
    rooms[room_id].add(ws)
    
    print(f"[+] Client joined room: {room_id} (total in room: {len(rooms[room_id])})")
    
    # Send current clipboard content if exists
    if room_id in clipboard_data:
        try:
            ws.send(json.dumps(clipboard_data[room_id]))
        except:
            pass
    
    try:
        while True:
            message = ws.receive()
            if message is None:
                break
            
            try:
                data = json.loads(message)
                
                if data.get('type') == 'clipboard':
                    # Update stored clipboard
                    clipboard_data[room_id] = {
                        "type": "clipboard",
                        "text": data.get('text', ''),
                        "timestamp": data.get('timestamp', datetime.now().isoformat())
                    }
                    
                    # Broadcast to all clients in room
                    dead_connections = set()
                    for client in rooms[room_id]:
                        if client != ws:
                            try:
                                client.send(json.dumps(clipboard_data[room_id]))
                            except:
                                dead_connections.add(client)
                    
                    # Clean up dead connections
                    rooms[room_id] -= dead_connections
                    
                    print(f"[~] Clipboard updated in room {room_id}: {len(data.get('text', ''))} chars")
                    
            except json.JSONDecodeError:
                print(f"[!] Invalid JSON received")
                
    except Exception as e:
        print(f"[!] WebSocket error: {e}")
    finally:
        rooms[room_id].discard(ws)
        print(f"[-] Client left room: {room_id} (remaining: {len(rooms[room_id])})")
        
        # Clean up empty rooms
        if not rooms[room_id]:
            del rooms[room_id]
            if room_id in clipboard_data:
                del clipboard_data[room_id]
            print(f"[x] Room {room_id} cleaned up")


if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════╗
║                   📋 ClipSync Server                      ║
╠═══════════════════════════════════════════════════════════╣
║  Running on: http://0.0.0.0:5000                          ║
║  WebSocket:  ws://localhost:5000/ws/<room_id>             ║
║                                                           ║
║  For LAN access, use your local IP address:               ║
║  - Windows: ipconfig                                      ║
║  - Mac/Linux: ifconfig or ip addr                         ║
║                                                           ║
║  Press Ctrl+C to stop                                     ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
