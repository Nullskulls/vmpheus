import json
import sys, requests

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

def get_cfg(auth):
    return  json.loads(requests.get(
                f"{auth['domain']}/api/v1/data/get/config",
                headers={"key": auth["key"]},
                params={}
            ).text)['config']


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

def build_app(slack_api_key, slack_signing_secret):
    app = App(
        token=slack_api_key,
        signing_secret=slack_signing_secret
    )
    auth = get_auth()
    @app.command("/sr")
    def admin_manage(ack, say, respond, command):
        ack()
        cfg = get_cfg(auth)
        text = (command.get("text") or "").strip().split(" ")
        if command["user_id"] not in cfg["admin_ids"]:
            respond("who r u")
        if text[0] == "say":
            message = " ".join(text[1:])
            say(message)
        elif text[0] == "vm":
            if text[1] == "add":
                payload = {
                    "admin_uid": command["user_id"],
                    "admin_name": command["user_name"]
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/admin/manage/addvm/{text[2]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond(f"Added {text[2]}.")

            elif text[1] == "remove":
                payload = {
                    "admin_uid": command["user_id"],
                    "admin_name": command["user_name"]
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/admin/manage/removevm/{text[2]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond(f"Removed {text[2]}.")

            elif text[1] == "deauth":
                payload = {
                    "admin_uid": command["user_id"],
                    "admin_name": command["user_name"]
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/admin/actions/deauth/{text[2]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond(f"Deauthorized {text[2]}.")

            elif text[1] == "auth":
                payload = {
                    "admin_uid": command["user_id"],
                    "vm": text[3],
                    "admin_name": command["user_name"]
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/admin/actions/auth/{text[2]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond(f"authorized {text[2]} for use of {text[3]}.")

        elif text[0] == "logs":
            logs = json.loads(requests.get(
                f"{auth['domain']}/api/v1/data/get/logs",
                headers={"key": auth["key"]},
                params={}
            ).text)["logs"]
            respond(logs)

        elif text[0] == "requests":
            user_requests = json.loads(requests.get(
                f"{auth['domain']}/api/v1/data/get/requests",
                headers={"key": auth["key"]},
                params={}
            ).text)["requests"]
            for request in user_requests:
                respond(f"{user_requests[request][1]} | {user_requests[request][0]} | {request}\n")
        elif text[0] == "remove":
            if text[1] in cfg["admin_ids"] and text[1] != command["user_id"]:
                payload = {
                    "admin_uid": command["user_id"],
                    "admin_name": command["user_name"],
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/admin/actions/demote/{text[1]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond("User demoted.")
            elif text[1] == command["user_id"]:
                respond("demoting ourselves are we now")
            else:
                respond("User not an admin consider removing from whitelist or slack channel.")

        elif text[0] == "add":
            if text[1] in cfg["admin_ids"]:
                respond("User is already an admin")
            else:
                payload = {
                    "admin_uid": command["user_id"],
                    "admin_name": command["user_name"],
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/admin/actions/promote/{text[1]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond("User is now an admin.")





    @app.command("/vm")
    def start_command(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        text = (command.get("text") or "").strip().split(" ")
        if is_valid(text[1], cfg, command["user_id"], command):
            if text[0] == "start":
                respond("Starting this bad boy...")
                payload = {
                    "client_uid": command["user_id"],
                    "client_name": command["user_name"]
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/users/manage/startvm/{text[1]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond("VM started.")
            elif text[0] == "stop":
                respond("Sopping this good boy...")
                payload = {
                    "client_uid": command["user_id"],
                    "client_name": command["user_name"]
                }

                requests.post(
                    f"{auth["domain"]}/api/v1/users/manage/stopvm/{text[1]}",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond("VM stopped.")
        if text[0] == "list":
            message = json.loads(requests.get(
                f"{auth['domain']}/api/v1/actions/viewvms/{command['user_id']}",
                headers={"key": auth["key"]},
                params={}
            ).text)["vms"]
            respond(message)
        elif text[0] == "request":
            if command["user_id"] in cfg["admin_ids"]:
                respond("You're already an admin what more could you want...")
            elif command["user_id"] in cfg["white_list"]:
                respond("User already registered.")
            elif command["channel_id"] in cfg["channel_id"]:
                user_requests = requests.get(
                    f"{auth['domain']}/getrequests",
                    headers={"key": auth["key"]},
                    params={}
                )

                if command["user_id"] in user_requests:
                    respond("Please wait for a VM Admin DM :)")
                else:
                    payload = {
                        "vm_type": text,
                        "client_name": command["user_name"]
                    }

                    requests.post(
                        f"{auth["domain"]}/api/v1/users/{command["client_id"]}/request/vm",
                        json=payload,
                        headers={"key": auth["key"]}
                    )
                    respond(f"Applied for vm type {text}.")
        else:
            respond("Invalid input.")



    @app.command("/utils")
    def request_utils(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            respond("just ask eric directly ;-;")
        elif command["channel_id"] == cfg["channel_id"]:
            payload = {
                "client_name": command["user_name"]
            }

            requests.post(
                f"{auth["domain"]}/api/v1/users/{command["user_id"]}/request/utils",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond("Be a good boy and wait now")
        else:
            respond("Invalid input or not authorized to preform this action.")
    return app


if __name__ == "__main__":
    cfg = get_cfg(get_auth())
    app = build_app(cfg["slack_api_key"], cfg["slack_signing_secret"])
    # Start Socket Mode
    handler = SocketModeHandler(app, cfg["socket_id"])
    handler.start()