import json
import sys, requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from db import *

def blacklist(client_uid, cfg, reason):
    cfg["blacklist"][client_uid] = reason

def get_admins(cfg):
    return cfg["admins"]

def is_admin(cfg, command):
    if command["user_id"] in cfg["admins"]:
        return True
    return False

def unblacklist(client_uid, cfg):
    del cfg["blacklist"][client_uid]


def save_config(cfg):
    with open('config.json', 'w') as outfile:
        json.dump(cfg, outfile)

def is_blacklisted(client_uid, cfg):
    if client_uid in cfg["blacklist"]:
        return True
    return False

def setup_state():
    try:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        with open('config.json', 'w') as config_file:
            template = {
                        "slack_api_key": "ENTER YOUR API KEY HERE",
                        "slack_signing_secret": "ENTER YOUR SIGNING SECRET HERE",
                        "channel_id": ["ENTER YOUR CHANNEL ID HERE"],
                        "socket_id": "ENTER SOCKET ID",
                        "blacklist": ["ADD HERE"],
                        "admins": ["ADD HERE"],
                        "support_channel": "ADD HERE"
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


def get_cfg(auth):
    return  setup_state()


def valid_channel(cfg, command):
    if command["channel_id"] in cfg["channel_id"]:
        return True
    return False

def is_valid(cfg, command):
    if valid_channel(cfg, command) and not is_blacklisted(cfg=cfg, client_uid = command["user_id"]):
        return True
    return False


def get_auth():
    try:
        with open('auth.json', 'r') as auth_file:
            json_data = json.load(auth_file)
            return json_data
    except FileNotFoundError:
        with open('auth.json', 'w') as auth_file:
            json.dump({"key": "ADD HERE",
                            "domain": "ADD HERE"
                            }, auth_file)
            sys.exit("please fill the file and continue.")

setup_ticket_db()

def build_app(slack_api_key, slack_signing_secret):
    app = App(
        token=slack_api_key,
        signing_secret=slack_signing_secret
    )
    auth = get_auth()
    @app.command("/sr")
    def admin_manage(ack, say, respond, command):
        ack()
        text = (command.get("text") or "").strip().split(" ")
        if not is_admin(cfg=cfg, command=command):
            respond("Sorry, you are not authorized to do that.")
            return
        if text[0] == "blacklist":

            if text[1] == "add":
                blacklist(text[2], cfg, " ".join(text[3:]))

            elif text[1] == "remove":
                unblacklist([text[2]], cfg)

            elif text[1] == "view":
                message = ""
                for person in cfg["blacklist"]:
                    message += f"{person} :     {cfg["blacklist"][person]}\n"
                respond(message)

        if text[0] == "say":
            message = " ".join(text[1:])
            say(message)

        elif text[0] == "admin":
            if text[1] == "add":
                payload = {
                    "action": "add",
                    "userName": " ".join(text[4:])
                }

                response = requests.post(
                    f"{auth["domain"]}/api/v1/admins/{text[2]}",
                    json=payload,
                    headers={"key": auth["key"],
                             "uid": command["user_id"]
                             }
                )
                if response.status_code == 403:
                    respond(json.loads(response.text)["error"])
                elif response.status_code == 200:
                    respond(json.loads(response.text)["message"])

            elif text[1] == "remove":
                payload = {}

                response = requests.post(
                    f"{auth["domain"]}/api/v1/admins/{text[2]}",
                    json=payload,
                    headers={"key": auth["key"],
                             "uid": command["user_id"]
                             }
                )
                if response.status_code == 403:
                    respond(json.loads(response.text)["error"])
                elif response.status_code == 200:
                    respond(json.loads(response.text)["message"])

        elif text[0] == "channels":
            if text[1] == "add":
                if len(text) == 2:
                    cfg["channel_id"].append(command["channel_id"])
                    respond(f"White listed current channel, Channel id -> {command['channel_id']}")
                else:
                    cfg["channel_id"].append(text[2])
                    respond(f"White listed channel id -> {text[2]}")
                save_config(cfg)

            elif text[1] == "view":
                respond(f"Channel ids -> {cfg['channel_id']}")

            elif text[1] == "remove":
                if len(text) == 2:
                    cfg["channel_id"].remove(command["channel_id"])
                    respond(f"Removed current channel from white list, Channel id -> {text[2]}")
                else:
                    cfg["channel_id"].remove(text[2])
                    respond(f"Removed channel id -> {text[2]}")
                save_config(cfg)
            elif text[1] == "support":
                cfg["support_channel"] = command["channel_id"]
        save_config(cfg)




    @app.command("/vm")
    def start_command(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip().split(" ")
        if not is_valid(cfg=cfg, command=command):
            return
        if text[0] == "start":
            if is_valid(cfg=cfg, command=command):
                response = requests.post(
                    f"{auth["domain"]}/api/v1/vms/{text[1]}",
                    json={"action": "start"},
                    headers={"key": auth["key"],
                             "uid": command["user_id"],}
                )
                if response.status_code == 403:
                    respond(json.loads(response.text)["error"])
                elif response.status_code == 200:
                    respond(json.loads(response.text)["message"])
        elif text[0] == "stop":
            if is_valid(cfg=cfg, command=command):
                response = requests.post(
                    f"{auth["domain"]}/api/v1/vms/{text[1]}",
                    json={"action": "stop"},
                    headers={"key": auth["key"],
                             "uid": command["user_id"]}
                )
                if response.status_code == 403:
                    respond(json.loads(response.text)["error"])
                elif response.status_code == 200:
                    respond(json.loads(response.text)["message"])
        elif text[0] == "list":
            if is_valid(cfg=cfg, command=command):
                respond("Calling Microsoft... :3 :loll:")
                message = ""
                response = json.loads(requests.get(
                    f"{auth['domain']}/api/v1/vms",
                    headers={"key": auth["key"],
                             "uid": command["user_id"]
                             },
                    params={}
                ).text)
                for responses in response:
                    message += f"{responses["name"]} | {responses["status"].title()} | {responses['osType']}\n"
                respond(text=message, replace_original=True)


        elif text[0] == "request":
            if is_valid(cfg=cfg, command=command):
                payload = {
                    "vmType": " ".join(text[1:]),
                    "requestType": "VM_ACCESS"
                }

                response = requests.post(
                    f"{auth["domain"]}/api/v1/requests/",
                    json=payload,
                    headers={"key": auth["key"],
                             "uid": command["user_id"]}
                )
                if response.status_code == 201:
                    respond(json.loads(response.text)["message"])
        elif text[0] == "help":
            pass


    @app.command("/utils")
    def request_utils(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if is_valid(cfg=cfg, command=command):
            payload = {
                "requestType": "UTILS_API_KEY"
            }

            response = requests.post(
                f"{auth["domain"]}/api/v1/requests/",
                json=payload,
                headers={"key": auth["key"],
                         "uid": command["user_id"]}
            )
            if response.status_code == 201:
                respond(json.loads(response.text)["message"])
    return app


if __name__ == "__main__":
    cfg = get_cfg(get_auth())
    app = build_app(cfg["slack_api_key"], cfg["slack_signing_secret"])
    # Start Socket Mode
    handler = SocketModeHandler(app, cfg["socket_id"])
    handler.start()