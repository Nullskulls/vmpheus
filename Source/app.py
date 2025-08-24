from flask import Flask, jsonify, request
import sys
import json
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from datetime import datetime, timezone


def get_uptime(compute, rg, vm):
    iv = compute.virtual_machines.instance_view(rg, vm)
    start_time = None
    for s in iv.statuses:
        if s.code.startswith("PowerState/") and hasattr(s, "time") and s.time:
            start_time = s.time
    if start_time:
        # Azure gives datetime already timezone-aware
        delta = datetime.now(timezone.utc) - start_time
        return delta.total_seconds() // 3600  # hours
    return None


def get_power_state(compute, rg, vm):
    iv = compute.virtual_machines.instance_view(rg, vm)
    for s in iv.statuses:
        code = getattr(s, "code", "")
        if code.startswith("PowerState/"):
            return code.split("/", 1)[1]

def load_logs():
    with open('logs.txt', 'r') as f:
        data = f.read()
        return data


def save_requests(request):
    with open('requests.json', 'w') as outfile:
        json.dump(request, outfile)

def load_requests():
    with open('requests.json', 'r') as json_file:
        data = json.load(json_file)
    return data

def log_actions(action, user_name, uid):
    with open('logs.txt', 'a') as log:
        log.write(f"{action} | Preformed by {user_name} ({uid}) | {datetime.now().strftime("%Y-%m-%d %H:%M")}\n")

def save_config(cfg):
    with open('config.json', 'w') as outfile:
        json.dump(cfg, outfile)


def setup_state():
    try:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        with open('config.json', 'w') as config_file:
            template = {
                        "api_key": "ADD HERE",
                        "vm_names": ["ADD HERE"],
                        "resource_group": "ADD HERE",
                        "slack_api_key": "ENTER YOUR API KEY HERE",
                        "slack_signing_secret": "ENTER YOUR SIGNING SECRET HERE",
                        "azure_tenant_id": "ENTER YOUR TENANT ID HERE",
                        "azure_client_id": "ENTER YOUR CLIENT ID HERE",
                        "azure_client_secret": "ENTER YOUR SECRET HERE",
                        "azure_subscription_id": "ENTER YOUR SUBSCRIPTION ID HERE",
                        "admin_ids": ["ENTER YOUR ADMIN IDS HERE"],
                        "white_list": {"ADD UID": "ADD HERE VM NAME"},
                        "channel_id": "ENTER YOUR CHANNEL ID HERE",
                        "socket_id": "ENTER SOCKET ID"
                    }
            print("Please fill config.json and relaunch.")
            sys.exit()
    try:
        with open('logs.txt', 'r') as log_file:
            pass
    except FileNotFoundError:
        with open('logs.txt', 'w') as log_file:
            log_file.write("")
    try:
        with open('requests.json', 'r') as requests_file:
            pass
    except FileNotFoundError:
        with open('requests.json', 'w') as requests_file:
            requests_file.write("{}")
    return config

cfg = setup_state()

cred = ClientSecretCredential(
        tenant_id=cfg["azure_tenant_id"],
        client_id=cfg["azure_client_id"],
        client_secret=cfg["azure_client_secret"]
    )

compute = ComputeManagementClient(cred, cfg["azure_subscription_id"])

app = Flask(__name__)


API_KEY = cfg.get("api_key", "changeme123")  # add to your config.json

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({}), 405

@app.before_request
def require_api_key():
    if request.headers.get("key") != API_KEY:
        return jsonify({"bitchless": False, "error": "get fucked"}), 401

@app.post('/startvm')
def start_vm():
    data = request.get_json(force=True)
    client_uid = data.get("client_uid")
    vm = data.get("vm")
    client_name = data.get("client_name")
    poller = compute.virtual_machines.begin_start(cfg["resource_group"], vm)
    log_actions("StartVM ", client_name, client_uid)
    return jsonify({"ok": True, "status": "starting"}), 200

@app.post('/stopvm')
def stop_vm():
    data = request.get_json(force=True)
    client_uid = data.get("client_uid")
    vm = data.get("vm")
    client_name = data.get("client_name")
    poller = compute.virtual_machines.begin_deallocate(cfg["resource_group"], vm)
    log_actions("StopVM", client_name, client_uid)
    return jsonify({"ok": True, "status": "stopping"}), 200

@app.post('/addvm')
def add_vm():
    data = request.get_json(force=True)
    admin_uid = data.get("admin_uid")
    vm = data.get("vm")
    admin_name = data.get("admin_name")
    cfg["vm_names"].append(vm)
    save_config(cfg)
    log_actions("Added VM", admin_name, admin_uid)
    return jsonify({"ok": True, "status": "added"}), 200

@app.post('/removevm')
def remove_vm():
    data = request.get_json(force=True)
    admin_uid = data.get("admin_uid")
    vm = data.get("vm")
    admin_name = data.get("admin_name")
    cfg["vm_names"].remove(vm)
    save_config(cfg)
    log_actions("Removed VM", admin_name, admin_uid)
    return jsonify({"ok": True, "status": "removed"}), 200
@app.post('/deauth')
def deauth_user():
    data = request.get_json(force=True)
    admin_uid = data.get("admin_uid")
    client_uid = data.get("client_uid")
    admin_name = data.get("admin_name")
    del cfg["white_list"][client_uid]
    save_config(cfg)
    log_actions(f"Deauthorized user {client_uid} ", admin_name, admin_uid)
    return jsonify({"ok": True, "status": "deauthorized"}), 200

@app.post('/auth')
def auth_user():
    data = request.get_json(force=True)
    client_uid = data.get("client_uid")
    vm = data.get("vm")
    admin_uid = data.get("admin_uid")
    admin_name = data.get("admin_name")
    cfg["white_list"][client_uid] = vm
    save_config(cfg)
    log_actions(f"Added whitelisted user->({client_uid, vm}) ", admin_name, admin_uid)
    requests = load_requests()
    if client_uid in requests:
        del requests[client_uid]
        save_requests(requests)
    return jsonify({"ok": True, "status": "authorized"}), 200

@app.post('/registervm')
def register_vm():
    data = request.get_json(force=True)
    client_uid = data.get("client_uid")
    vm = data.get("vm_type")
    client_name = data.get("client_name")
    requests = load_requests()
    requests[client_uid] = [vm, client_name]
    log_actions(f"Applied for vm type {vm}", client_name, client_uid)
    save_requests(requests)
    return jsonify({"ok": True, "status": "registered"}), 200


@app.get('/getlogs')
def get_logs():
    action_logs = load_logs()
    return jsonify({"ok": True, "logs": action_logs, "status": "sent"}), 200

@app.post('/clearlogs')
def clear_logs():
    data = request.get_json(force=True)
    admin_uid = data.get("admin_uid")
    admin_name = data.get("admin_name")
    with open("vmbackend/logs.txt", "w") as log:
        log.write("")
    log_actions("Clear logs ", admin_name, admin_uid)
    return jsonify({"ok": True, "status": "cleared"}), 200

@app.get('/viewvms')
def view_vms():
    client_uid = request.args.get("client_uid")
    if client_uid in cfg["admin_ids"]:
        message = ''
        for vm in cfg["vm_names"]:
            message += f"{vm} | {get_power_state(compute, cfg["resource_group"], vm)} | {get_uptime(compute, cfg["resource_group"], vm)}\n\n"
    else:
        vm = cfg["white_list"][client_uid]
        message = f"{vm} | {get_power_state(compute, cfg["resource_group"], vm)} | {get_uptime(compute, cfg["resource_group"], vm)}\n\n"
    return jsonify({"ok": True, "vms": message}), 200

@app.post('/promote')
def promote_vm():
    data = request.get_json(force=True)
    admin_uid = data.get("admin_uid")
    client_uid = data.get("client_uid")
    admin_name = data.get("admin_name")
    cfg["admin_ids"].append(client_uid)
    save_config(cfg)
    log_actions(f"Promoted {client_uid}", admin_name, admin_uid)
    return jsonify({"ok": True, "status": "promoted"}), 200

@app.post('/demote')
def demote_vm():
    data = request.get_json(force=True)
    admin_uid = data.get("admin_uid")
    client_uid = data.get("client_uid")
    admin_name = data.get("admin_name")
    cfg["admin_ids"].remove(client_uid)
    save_config(cfg)
    log_actions(f"Demoted {client_uid}", admin_name, admin_uid)
    return jsonify({"ok": True, "status": "demoted"}), 200

@app.post('/requestutils')
def request_utils():
    data = request.get_json(force=True)
    client_uid = data.get("client_uid")
    requests = load_requests()
    requests[client_uid] = "utils"
    return jsonify({"ok": True, "status": "requested"}), 200

@app.get("/getconfig")
def get_config():
    return jsonify({"ok": True, "config": cfg, "status": "sent"}), 200

@app.get("/getrequests")
def get_requests():
    return jsonify({"ok": True, "requests": load_requests(), "status": "sent"}), 200

if __name__ == '__main__':
    app.run()
