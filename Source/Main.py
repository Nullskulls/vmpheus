from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
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

def log_actions(action, command):
    with open('logs.txt', 'a') as log:
        log.write(f"{action} | Preformed by {command["user_name"]} ({command["user_id"]}) | {datetime.now().strftime("%Y-%m-%d %H:%M")}\n")

def save_config(cfg):
    with open('config.json', 'w') as outfile:
        json.dump(cfg, outfile)

def valid_vm(text, cfg, uid):
    if uid in cfg["admin_ids"] and text in cfg["vm_names"]:
        return True
    if text == cfg["white_list"][uid]:
        return True
    return False

def valid_channel(cfg, command):
    if cfg["channel_id"] == command["channel_id"]:
        return True
    return False

def is_valid(text, cfg, uid, command):
    if valid_vm(text, cfg, uid) and valid_channel(cfg, command):
        return True
    return False

def setup_state():
    try:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        with open('config.json', 'w') as config_file:
            template = {
                        "vm_names": ["ADD HERE"],
                        "resource_group": "ADD HERE",
                        "slack_api_key": "ENTER YOUR API KEY HERE",
                        "slack_signing_secret": "ENTER YOUR SIGNING SECRET HERE",
                        "azure_tenant_id": "ENTER YOUR TENANT ID HERE",
                        "azure_client_id": "ENTER YOUR CLIENT ID HERE",
                        "azure_client_secret": "ENTER YOUR SECRET HERE",
                        "azure_subscription_id": "ENTER YOUR SUBSCRIPTION ID HERE",
                        "admin_ids": ["ENTER YOUR ADMIN IDS HERE"],
                        "admin_commands": ["add", "remove", "start", "stop", "view"],
                        "white_list": {"ENTER WHITELIST HERE"},
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

def build_app(cfg):
    app = App(
        token=cfg['slack_api_key'],
        signing_secret=cfg['slack_signing_secret'],
    )
    cred = ClientSecretCredential(
        tenant_id=cfg["azure_tenant_id"],
        client_id=cfg["azure_client_id"],
        client_secret=cfg["azure_client_secret"]
    )
    compute = ComputeManagementClient(cred, cfg["azure_subscription_id"])
    @app.command("/startvm")
    def start_command(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if text.lower() == "help":
            respond("Contact VM admins for support.")
        elif is_valid(text, cfg, command["user_id"], command):
            respond("Starting this bad boy...")
            poller = compute.virtual_machines.begin_start(cfg["resource_group"], text)
            log_actions("StartVM", command)
            respond("VM started.")
        else:
            respond("Invalid input.")

    @app.command("/stopvm")
    def stop_command(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if text.lower() == "help":
            respond("Contact VM admins for support.")
        elif is_valid(text, cfg, command["user_id"], command):
            respond(f"Sopping this good boy...")
            poller = compute.virtual_machines.begin_deallocate(cfg["resource_group"], text)
            log_actions("StopVM", command)
            respond("VM stopped.")
        else:
            respond("Invalid input.")

    @app.command("/addvm")
    def add_vm(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            cfg["vm_names"].append(text)
            save_config(cfg)
            log_actions("Added VM", command)
            respond(f"Added {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/removevm")
    def remove_vm(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            cfg["vm_names"].remove(text)
            save_config(cfg)
            log_actions("Removed VM", command)
            respond(f"Removed {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/deauthorize")
    def deauthorize_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            del cfg["white_list"][text]
            save_config(cfg)
            log_actions(f"Deauthorized user {text} ", command)
            respond(f"Deauthorized user {text} ")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/authorize")
    def whitelist_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip().split(" ")
        if command["user_id"] in cfg["admin_ids"]:
            cfg["white_list"][text[0]] = text[1]
            save_config(cfg)
            log_actions(f"Added whitelisted user->({text[0], [text[1]]}) ", command)
            requests = load_requests()
            if command["user_id"] in requests:
                del requests[command["user_id"]]
                save_requests(requests)
            respond(f"Added {text[0]}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/removeuser")
    def remove_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            del cfg["white_list"][text]
            save_config(cfg)
            log_actions(f"Removed user->({text[0], [text[1]]}) ", command)
            respond(f"Removed {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/vmregister")
    def register_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            respond("You're already an admin what more could you want...")
        elif command["user_id"] in cfg["white_list"]:
            respond("User already registered.")
        elif command["channel_id"] in cfg["channel_id"]:
            requests = load_requests()
            if command["user_id"] in requests:
                respond("Please wait for a VM Admin DM :)")
            else:
                requests[command["user_id"]] = [text, command["user_name"]]
                log_actions(f"Applied for vm type {text}", command)
                save_requests(requests)
                respond(f"Applied for vm type {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/marryme")
    def marryme_command(ack, respond, command):
        ack()
        if command["user_id"] in cfg["admin_ids"]:
            respond("FUCK YEAHHH")
        elif command["channel_id"] in cfg["channel_id"]:
            respond("huh?")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/viewrequests")
    def view_requests(ack, respond, command):
        ack()
        if command["user_id"] in cfg["admin_ids"]:
            requests = load_requests()
            for request in requests:
                respond(f"{requests[request][1]} | {requests[request][0]} | {request}\n")
                log_actions("Viewed requests", command)
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/viewlogs")
    def view_logs(ack, respond, command):
        ack()
        if command["user_id"] in cfg["admin_ids"]:
            logs = load_logs()
            respond(logs)
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/clearlogs")
    def clear_logs(ack, respond, command):
        ack()
        if command["user_id"] in cfg["admin_ids"]:
            with open("logs.txt", "w") as log:
                log.write("")
            log_actions("Clear logs ", command)
            respond("ai ai capitan")
        else:
            respond("Invalid input or not authorized to preform this action.")


    @app.command("/viewvms")
    def view_vms(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            message = ""
            for vm in cfg["vm_names"]:
                message += f"{vm} | {get_power_state(compute, cfg["resource_group"], vm)} | {get_uptime(compute, cfg["resource_group"], vm)}\n\n"
            respond(message)
        elif command["user_id"] in cfg["white_list"]:
            vm = cfg["white_list"]
            respond(
                f"{vm} | {get_power_state(compute, cfg["resource_group"], vm)} | {get_uptime(compute, cfg["resource_group"], vm)}\n\n")
        else:
            respond("Invalid input or not authorized to preform this action.")


    @app.command("/promote")
    def promote_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            if text in cfg["admin_ids"]:
                respond("User is already an admin")
            else:
                cfg["admin_ids"].append(text)
                save_config(cfg)
                respond("User is now an admin.")
                log_actions(f"Promoted {text}", command)

    @app.command("/demote")
    def demote_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            if text in cfg["admin_ids"] and text != command["user_id"]:
                cfg["admin_ids"].remove(text)
                save_config(cfg)
                respond("User demoted.")
                log_actions(f"Demoted {text}", command)
            elif text == command["user_id"]:
                respond("demoting ourselves are we now")
            else:
                respond("User not an admin consider removing from whitelist or slack channel.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/requestutils")
    def request_utils(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            respond("just ask eric directly ;-;")
        elif command["channel_id"] == cfg["channel_id"]:
            requests = load_requests()
            requests[command["user_id"]] = "utils"
            respond("Be a good boy and wait now")
        else:
            respond("Invalid input or not authorized to preform this action.")
    return app


if __name__ == "__main__":
    cfg = setup_state()
    app = build_app(cfg)
    # Start Socket Mode
    handler = SocketModeHandler(app, cfg["socket_id"])
    handler.start()