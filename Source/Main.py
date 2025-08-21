from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import json
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

def valid_vm(text, cfg, uid):
    if uid in cfg["admin_ids"]:
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
            return json.load(config_file)
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
            respond(respond("Contact VM admins for support."))
        elif is_valid(text, cfg, command["user_id"], command):
            poller = compute.virtual_machines.begin_start(cfg["resource_group"], text)
            respond(respond(f"VM started: {poller.result}"))
        else:
            respond(respond("Invalid input."))

    @app.command("/stopvm")
    def stop_command(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if text.lower() == "help":
            respond(respond("Contact VM admins for support."))
        elif is_valid(text, cfg, command["user_id"], command):
            poller = compute.virtual_machines.begin_deallocate(cfg["resource_group"], text)
            respond(respond(f"VM stopped: {poller.result()}"))
        else:
            respond(respond("Invalid input."))
    return app


if __name__ == "__main__":
    cfg = setup_state()
    app = build_app(cfg)
    # Start Socket Mode
    handler = SocketModeHandler(app, cfg["socket_id"])
    handler.start()