import tempfile

import requests,json, sys, os
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
    if event.get("subtype") and event.get("subtype") != "file_share":
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
    if channel == cfg["public_support"]:
        if event.get("subtype") != "file_share":
            if text[0] != '?':
                return
    text = text.lstrip('?')
    ticket = find_client_ticket(channel_id=channel, parent_ts=thread_ts)
    if ticket:
        if ticket["status"] == "open":
            dest = client.chat_postMessage(
                channel=ticket["admin_channel_id"],
                thread_ts=ticket["admin_parent_ts"],
                text = f"<@{event['user']}>: {text}"
            )
            save_message(channel, ts, dest["channel"], dest["ts"])
            media = relay_files(
                event=event,
                client=client,
                dest_channel=ticket["admin_channel_id"],
                dest_ts=ticket["admin_parent_ts"],
                bot_token=cfg["slack_api_key"]
            )
            for (dest_ch, dest_ts) in media:
                save_message(channel, ts, dest_ch, dest_ts)
        return

    ticket = find_admin_ticket(channel_id=channel, parent_ts=thread_ts)
    if ticket:
        if ticket["status"] == "open":
            sent = client.chat_postMessage(
                channel=ticket["client_channel_id"],
                thread_ts=ticket["client_parent_ts"],
                text=text
            )
            save_message(channel, ts, sent["channel"], sent["ts"])
            media = relay_files(
                event=event,
                client=client,
                dest_channel=ticket["client_channel_id"],
                dest_ts=ticket["client_parent_ts"],
                bot_token=cfg["slack_api_key"]
            )
            for (dest_ch, dest_ts) in media:
                save_message(event["channel"], event["ts"], dest_ch, dest_ts)
            client.chat_postEphemeral(
                channel = ticket["admin_channel_id"],
                user = event["user"],
                thread_ts=ticket["admin_parent_ts"],
                blocks= [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Message sent."
                        },
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Delete message"},
                            "style": "danger",
                            "value":  json.dumps({"ch": sent["channel"], "ts": sent["ts"]}),
                            "action_id": "delete_message"
                        }
                    }
                ]
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

def relay_files(event, client, dest_channel, dest_ts, bot_token):
    files = event.get("files") or []
    results = []
    for file in files:
        url = file["url_private_download"] or file["url_private"]
        if not url:
            continue
        tmp_path = None
        try:
            with requests.get(url, headers={"Authorization": f"Bearer {bot_token}"}, stream=True, timeout=15) as r:
                r.raise_for_status()
                suffix = os.path.splitext(file.get("name") or "")[1] or ""
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                with os.fdopen(fd, "wb") as out:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: out.write(chunk)
            up = client.files_upload_v2(
                channel=dest_channel,
                thread_ts=dest_ts,
                filename=file.get("name") or "file",
                file=tmp_path,
                initial_comment=None
            )
            dest_ts = None
            file_obj = up.get("file", {}) or {}
            shares = (file_obj.get("shares") or {}).get("shares") or {}
            if dest_channel in shares and shares[dest_channel]:
                dest_ts = shares[dest_channel]["ts"]
            if dest_ts:
                results.append((dest_channel, dest_ts))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    return results


