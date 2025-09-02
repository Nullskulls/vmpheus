from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from db import *
from helpers import *

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
        if not is_admin(uid=command["user_id"]):
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
                    message += f"{person} :     {cfg['blacklist'][person]}\n"
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
                    save_config(cfg)
                else:
                    cfg["channel_id"].remove(text[2])
                    respond(f"Removed channel id -> {text[2]}")
                    save_config(cfg)
            elif text[1] == "admin_support":
                cfg["support_channel"] = command["channel_id"]
                save_config(cfg)
            elif text[1] == "public_support":
                cfg["public_support"] = command["channel_id"]
                save_config(cfg)
            elif text[1] == "public_help":
                cfg["public_help"] = command["channel_id"]
                save_config(cfg)
        elif text[0] == "tickets":
            if text[1] == "close":
                close_ticket(text[2])
                respond("Ticket closed.")



    @app.command("/vm")
    def start_command(ack, respond, say, command, client):
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
                    "osType": " ".join(text[1:]),
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
            ticket_id = new_id()
            details = " ".join(text[1:]).capitalize()
            client_message = client.chat_postMessage(
                channel=command["channel_id"],
                text=details or "No details for some reason ;-;"
            )

            admin_message = client.chat_postMessage(
                channel=cfg["support_channel"],
                text=f"{details} from <@{command['user_id']}> ({ticket_id})"
            )
            client.chat_postMessage(
                channel=client_message["channel"],
                thread_ts=client_message["ts"],
                text=f"Created ticket, Your ticked id is ({ticket_id}), Someone will respond soon. <@{command['user_id']}>"
            )
            client.chat_postMessage(
                channel=command["channel_id"],
                thread_ts=client_message["ts"],
                text=f"Controls for ticket {ticket_id}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Close ticket {ticket_id}"
                        },
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Close Ticket"},
                            "style": "primary",
                            "value": ticket_id,
                            "action_id": "close_ticket"
                        }
                    }
                ]
            )
            client.chat_postMessage(
                channel=cfg["support_channel"],
                thread_ts=admin_message["ts"],
                text=f"Controls for ticket {ticket_id}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Close ticket {ticket_id}"
                        },
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Close Ticket"},
                            "style": "primary",
                            "value": ticket_id,
                            "action_id": "close_ticket"
                        }
                    }
                ]
            )
            create_ticket(ticket_id, 'open', command["user_id"], command["channel_id"], client_message["ts"], cfg["support_channel"], admin_message["ts"], " ".join(text[1:]))

    @app.command("/sos")
    def support(ack, command, client, logger, respond):
        ack()
        if command["channel_id"] != cfg["public_help"]:
            respond("Please use this command in the designated channel :/")
        text = (command.get("text") or "").strip() or "(no details)"
        ticket_id = new_id()
        client_message = client.chat_postMessage(
            channel=command["channel_id"],
            text=text
        )
        admin_message = client.chat_postMessage(
            channel=cfg["public_support"],
            text=f"{text} from <@{command['user_id']}>"
        )
        client.chat_postMessage(
            channel=client_message["channel"],
            thread_ts=client_message["ts"],
            text=f"Ticket {ticket_id} opened for <@{command['user_id']}>",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Your query has been received someone will shortly be with you <@{command['user_id']}> ID: `{ticket_id}`"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Close Ticket"},
                        "style": "primary",
                        "value": ticket_id,
                        "action_id": "close_public_ticket"
                    }
                }
            ]
        )
        client.chat_postMessage(
            channel=cfg["public_support"],
            thread_ts=admin_message["ts"],
            text=f"Close ticket {ticket_id}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Close ticket ID: `{ticket_id}`"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Close Ticket"},
                        "style": "primary",
                        "value": ticket_id,
                        "action_id": "close_public_ticket"
                    }
                }
            ]
        )
        create_ticket(ticket_id, 'open', command["user_id"], command["channel_id"], client_message["ts"],
                      cfg["public_support"], admin_message["ts"], text)
        if cfg["holder_ts"] != "NO TOUCH":
            client.chat_delete(channel=cfg["public_help"], ts=cfg["holder_ts"])
        cfg["holder_ts"] = client.chat_postMessage(
            channel=cfg["public_help"],
            text=f"Use `/sos <question>` to get help from verified shipwrights! or use `/complaint <complaint>` to send the shipwrights anonymous complaints!"
        )["ts"]
        save_config(cfg)
        logger.info(f"[sos:new] client=({command['channel_id']},{client_message['ts']}) "
                    f"admin=({cfg['public_support']},{admin_message['ts']}) id={ticket_id}")



    @app.event("message")
    def handle_messages(body, client, logger):
        event = (body or {}).get("event", {}) or {}
        handle_replies(event, client, logger, cfg)
        handle_message_sent(event, client, cfg)



    @app.command("/complaint")
    def complaint(ack, respond, client, command):
        ack()
        text = (command.get("text") or "").strip() or "(no details)"
        respond("Anonymous complain received.")
        client.chat_postMessage(
            channel=cfg["public_support"],
            text=f"Anonymous complaint: {text}"
        )


    @app.action("close_public_ticket")
    def close_public_ticket(body, client, ack):
        ack()
        ticket_id = body["actions"][0]["value"]
        ticket = find_ticket_id(ticket_id)
        if ticket:
            if not (is_shipwright(body["user"]["id"]) or body["user"]["id"] == ticket["client_uid"]):
                client.chat_postEphemeral(
                    channel = body["channel"]["id"],
                    user = body["user"]["id"],
                    text = "Not allowed to close this ticket :/"
                )
                return
            if ticket["status"] == "closed":
                return
            close_ticket(ticket_id)
            client.chat_postMessage(
                channel=ticket["admin_channel_id"],
                thread_ts=ticket["admin_parent_ts"],
                text = f"Ticket {ticket_id} was closed by <@{body['user']['id']}>."
            )
            client.chat_postMessage(
                channel=ticket["client_channel_id"],
                thread_ts=ticket["client_parent_ts"],
                text=f"Ticket {ticket_id} was closed by <@{body['user']['id']}>."
            )
        else:
            return
    @app.action("close_ticket")
    def close_ticket_action(body, client, ack):
        ack()
        ticket_id = body["actions"][0]["value"]

        ticket = find_ticket_id(ticket_id)

        if ticket:
            if not (is_admin(body["user"]["id"]) or body["user"]["id"] == ticket["client_uid"]):
                client.chat_postEphemeral(
                    channel = body["channel"]["id"],
                    user = body["user"]["id"],
                    text = "Not allowed to preform this action :/"
                )
                return
            if ticket["status"] == "closed":
                return
            close_ticket(ticket_id)
            client.chat_postMessage(
                channel = ticket["admin_channel_id"],
                thread_ts=ticket["admin_parent_ts"],
                text = f"Ticket {ticket_id} was closed by <@{body['user']['id']}>."
            )
            client.chat_postMessage(
                channel = ticket["client_channel_id"],
                thread_ts=ticket["client_parent_ts"],
                text=f"Ticket {ticket_id} was closed by <@{body['user']['id']}>."
            )
        else:
            return



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