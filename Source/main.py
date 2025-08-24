import json
import sys, requests

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

def get_cfg(auth):
    return  json.loads(requests.get(
                f"{auth['domain']}/getconfig",
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

    @app.command("vmgreet")
    def say_hi(ack, body, say):
        ack()
        cfg = get_cfg(auth)
        if body["user_id"] in cfg["admin_ids"]:
            say("hi ig", channel=cfg["channel_id"])


    @app.command("/startvm")
    def start_command(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        text = (command.get("text") or "").strip()
        if text.lower() == "help":
            respond("Contact VM admins for support.")
        elif is_valid(text, cfg, command["user_id"], command):
            respond("Starting this bad boy...")
            payload = {
                "client_uid": command["user_id"],
                "vm": text,
                "client_name": command["user_name"],
            }

            requests.post(
                f"{auth["domain"]}/startvm",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond("VM started.")
        else:
            respond("Invalid input.")

    @app.command("/stopvm")
    def stop_command(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        cfg = get_cfg(auth)
        if text.lower() == "help":
            respond("Contact VM admins for support.")
        elif is_valid(text, cfg, command["user_id"], command):
            respond(f"Sopping this good boy...")
            payload = {
                "client_uid": command["user_id"],
                "vm": text,
                "client_name": command["user_name"],
            }

            requests.post(
                f"{auth["domain"]}/stopvm",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond("VM stopped.")
        else:
            respond("Invalid input.")

    @app.command("/addvm")
    def add_vm(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            payload = {
                "admin_uid": command["user_id"],
                "vm": text,
                "admin_name": command["user_name"],
            }

            requests.post(
                f"{auth["domain"]}/addvm",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond(f"Added {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/removevm")
    def remove_vm(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            payload = {
                "admin_uid": command["user_id"],
                "vm": text,
                "admin_name": command["user_name"],
            }

            requests.post(
                f"{auth["domain"]}/removevm",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond(f"Removed {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/deauthorize")
    def deauthorize_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            payload = {
                "admin_uid": command["user_id"],
                "client_uid": text,
                "admin_name": command["user_name"],
            }

            requests.post(
                f"{auth["domain"]}/deauth",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond(f"Deauthorized user {text} ")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/authorize")
    def whitelist_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip().split(" ")
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            payload = {
                "admin_uid": command["user_id"],
                "client_uid": text[0],
                "vm": text[1],
                "admin_name": command["user_name"],
            }

            requests.post(
                f"{auth["domain"]}/auth",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond(f"Added {text[0]}.")
        else:
            respond("Invalid input or not authorized to preform this action.")


    @app.command("/vmregister")
    def register_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        cfg = get_cfg(auth)
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
                    "client_uid": command["user_id"],
                    "vm_type": text,
                    "client_name": command["user_name"]
                }

                requests.post(
                    f"{auth["domain"]}/registervm",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond(f"Applied for vm type {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/marryme")
    def marryme_command(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            respond("to be added if supervisor gives greenlight")
        elif command["channel_id"] in cfg["channel_id"]:
            respond("huh?")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/viewrequests")
    def view_requests(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            user_requests = json.loads(requests.get(
                f"{auth['domain']}/getrequests",
                headers={"key": auth["key"]},
                params={}
            ).text)["requests"]
            for request in user_requests:
                respond(f"{user_requests[request][1]} | {user_requests[request][0]} | {request}\n")

        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/viewlogs")
    def view_logs(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            logs = json.loads(requests.get(
                f"{auth['domain']}/getlogs",
                headers={"key": auth["key"]},
                params={}
            ).text)["logs"]
            respond(logs)
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/clearlogs")
    def clear_logs(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            payload = {
                "admin_uid": command["user_id"],
                "admin_name": command["user_name"]
            }

            requests.post(
                f"{auth["domain"]}/clearlogs",
                json=payload,
                headers={"key": auth["key"]}
            )
            respond("ai ai capitan")
        else:
            respond("Invalid input or not authorized to preform this action.")


    @app.command("/viewvms")
    def view_vms(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"] or command["user_id"] in cfg["white_list"]:
            message = json.loads(requests.get(
                f"{auth['domain']}/viewvms",
                headers={"key": auth["key"]},
                params={"client_uid": command["user_id"]}
            ).text)["vms"]
            respond(message)
        else:
            respond("Invalid input or not authorized to preform this action.")


    @app.command("/vmpromote")
    def promote_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            if text in cfg["admin_ids"]:
                respond("User is already an admin")
            else:
                payload = {
                    "admin_uid": command["user_id"],
                    "admin_name": command["user_name"],
                    "client_uid": text
                }

                requests.post(
                    f"{auth["domain"]}/promote",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond("User is now an admin.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/vmdemote")
    def demote_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            if text in cfg["admin_ids"] and text != command["user_id"]:
                payload = {
                    "admin_uid": command["user_id"],
                    "admin_name": command["user_name"],
                    "client_uid": text
                }

                requests.post(
                    f"{auth["domain"]}/demote",
                    json=payload,
                    headers={"key": auth["key"]}
                )
                respond("User demoted.")
            elif text == command["user_id"]:
                respond("demoting ourselves are we now")
            else:
                respond("User not an admin consider removing from whitelist or slack channel.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/requestutils")
    def request_utils(ack, respond, command):
        ack()
        cfg = get_cfg(auth)
        if command["user_id"] in cfg["admin_ids"]:
            respond("just ask eric directly ;-;")
        elif command["channel_id"] == cfg["channel_id"]:
            payload = {
                "client_uid": command["user_id"],
                "client_name": command["user_name"]
            }

            requests.post(
                f"{auth["domain"]}/registerutils",
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