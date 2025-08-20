from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import json
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient


def setup_state():
    try:
        with open('config.json', 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        with open('config.json', 'w') as config_file:
            template = {
                        "slack_api_key": "ENTER YOUR API KEY HERE",
                        "slack_signing_secret": "ENTER YOUR SIGNING SECRET HERE",
                        "azure_tenant_id": "ENTER YOUR TENANT ID HERE",
                        "azure_client_id": "ENTER YOUR CLIENT ID HERE",
                        "azure_client_secret": "ENTER YOUR SECRET HERE",
                        "azure_subscription_id": "ENTER YOUR SUBSCRIPTION ID HERE",
                        "admin_ids": ["ENTER YOUR ADMIN IDS HERE"],
                        "admin_commands": ["add", "remove", "start", "stop", "view"],
                        "white_list": ["ENTER WHITELIST HERE"],
                        "*": ["add", "remove", "view"],
                        "channel_id": "ENTER YOUR CHANNEL ID HERE",
                        "socket_id": "ENTER SOCKET ID"
                    }
            print("Please fill config.json and relaunch.")

def build_app(cfg):
    app = App(
        token=cfg['slack_api_key'],
        signing_secret=cfg['slack_signing_secret'],
    )

    @app.command("/startvm")
    def start_command(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if not text:
            respond(respond("why you messaging then ;-;"))
        elif text.lower() == "help":
            respond(respond("im a bot bro find a human to help u"))
        else:
            respond(respond("i dont speak gibbrish"))
    return app


if __name__ == "__main__":
    cfg = setup_state()
    app = build_app(cfg)
    # Start Socket Mode
    handler = SocketModeHandler(app, cfg["socket_id"])
    handler.start()