from db import get_all_tickets
from helpers import get_cfg
from slack_sdk import WebClient
import time
import datetime

def stale_tickets():
    stale_ticket_list = []
    for ticket in get_all_tickets():
        if ticket["status"] == "open":
             timestamp = ticket["created_at"]
             dt = datetime.datetime.fromisoformat(timestamp)
             if datetime.datetime.now() - dt > datetime.timedelta(days=2):
                 stale_ticket_list.append(ticket)
    return stale_ticket_list

def notify():
    cfg = get_cfg("")
    client = WebClient(token=cfg["slack_api_key"])
    while True:
        i=1
        message = "*STALE TICKETS*\n"
        tickets = stale_tickets()
        for ticket in tickets:
            link = client.chat_getPermalink(channel=ticket["admin_channel_id"], message_ts=ticket["admin_parent_ts"])
            message += f"{i}- <{link['permalink']}|{ticket["client_title"]}> by <@{ticket["client_uid"]}>\n"
            i+=1
        client.chat_postMessage(
            channel = cfg["public_support"],
            text = message
        )
        time.sleep(86400)
