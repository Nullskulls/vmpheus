from flask import Flask, jsonify, request
from helpers import get_auth
from db import close_ticket, get_closed_tickets, get_all_tickets, get_open_tickets
import subprocess
auth = get_auth()
app = Flask(__name__)


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({}), 405

@app.before_request
def require_api_key():
    if request.headers.get("key") != auth["key"]:
        return jsonify({"bitchless": False, "error": "get fucked"}), 401

@app.post("/api/v1/tickets/close/<ticket_id>")
def collapse_ticket(ticket_id):
    close_ticket(ticket_id)
    return jsonify({"ok": True})

@app.get("/api/v1/tickets/open")
def get_o_tickets():
    return jsonify({"tickets": get_open_tickets(), "ok": True})

@app.get("/api/v1/tickets/all")
def get_a_tickets():
    return jsonify({"tickets": get_all_tickets(), "ok": True})

@app.get("/api/v1/tickets/closed")
def get_c_tickets():
    return jsonify({"tickets": get_closed_tickets(), "ok": True})

@app.get("/api/v1/health")
def get_health():
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "vmpheus"],
        capture_output=True, text=True
    )
    return jsonify({
                    "api": True,
                    "bot": result.stdout.strip() == "active"
                    })
if __name__ == '__main__':
    app.run()
