import requests,json, sys
from db import *

def get_shipwright():
    shipwrights = []
    auth = get_auth()
    data = json.loads(requests.get(
        f"{auth['domain']}/api/v1/shipwrights",
        headers={"key": auth["key"]},
        params={}
    ).text)
    for shipwright in data["shipwrights"]:
        shipwrights.append(shipwright["slackId"])
    return shipwrights


def is_shipwright(uid):
    if uid in get_shipwright():
        return True
    return False

def blacklist(client_uid, cfg, reason):
    cfg["blacklist"][client_uid] = reason

def get_admins():
    admins = []
    auth = get_auth()
    data = json.loads(requests.get(
        f"{auth['domain']}/api/v1/admins",
        headers={"key": auth["key"]},
        params={}
    ).text)
    for admin in data["admins"]:
        admins.append(admin["slackId"])
    return admins

def is_admin(uid):
    if uid in get_admins():
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
                        "support_channel": "ADD HERE",
                        "public_support": "ADD HERE",
                        "public_help":  "ADD HERE",
                        "not_supported": ["ADD HERE"],
                        "holder_ts": "NO TOUCH"
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


def handle_replies(event, client, logger, cfg):
    if event.get("subtype"):
        return
    if event.get("bot_id"):
        return
    if event["user"] in cfg["not_supported"]:
        return
    ts = event.get("ts")
    thread_ts = event.get("thread_ts")
    if not ts or not thread_ts or thread_ts == ts:
        return
    logger.info(f"[relay] incoming ch={event['channel']} parent={thread_ts}")
    channel = event["channel"]
    text = event.get("text", "")
    ticket = find_client_ticket(channel_id=channel, parent_ts=thread_ts)
    if ticket:
        if ticket["status"] == "open":
            client.chat_postMessage(
                channel=ticket["admin_channel_id"],
                thread_ts=ticket["admin_parent_ts"],
                text = f"<@{event['user']}>: {text}"
            )
        return

    ticket = find_admin_ticket(channel_id=channel, parent_ts=thread_ts)
    if ticket:
        if ticket["status"] == "open":
            client.chat_postMessage(
                channel=ticket["client_channel_id"],
                thread_ts=ticket["client_parent_ts"],
                text=text
            )

def handle_message_sent(event, client, cfg):
    if event.get("thread_ts") and event["thread_ts"] != event["ts"]:
        return
    if event["channel"] == cfg["public_help"]:
        if cfg["holder_ts"] != "NO TOUCH":
            client.chat_delete(channel=cfg["public_help"], ts=cfg["holder_ts"])
        cfg["holder_ts"] = client.chat_postMessage(
            channel=cfg["public_help"],
            text=f"Use `/sos <question>` to get help from verified shipwrights! or use `/complaint <complaint>` to send the shipwrights anonymous complaints!"
        )["ts"]
        save_config(cfg)
    return