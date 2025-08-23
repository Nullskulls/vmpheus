from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

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


def build_app(cfg):
    app = App(
        token=cfg['slack_api_key'],
        signing_secret=cfg['slack_signing_secret'],
    )
    @app.command("/startvm")
    def start_command(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if text.lower() == "help":
            respond("Contact VM admins for support.")
        elif is_valid(text, cfg, command["user_id"], command):
            respond("Starting this bad boy...")
            #add request here
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
            #add request here
            respond("VM stopped.")
        else:
            respond("Invalid input.")

    @app.command("/addvm")
    def add_vm(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            #add request here
            respond(f"Added {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/removevm")
    def remove_vm(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            #add request here
            respond(f"Removed {text}.")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/deauthorize")
    def deauthorize_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            #add request here
            respond(f"Deauthorized user {text} ")
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/authorize")
    def whitelist_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip().split(" ")
        if command["user_id"] in cfg["admin_ids"]:
            #add request here
            respond(f"Added {text[0]}.")
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
                #add request here
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
            requests = #add request here
            for request in requests:
                respond(f"{requests[request][1]} | {requests[request][0]} | {request}\n")
                log_actions("Viewed requests", command)
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/viewlogs")
    def view_logs(ack, respond, command):
        ack()
        if command["user_id"] in cfg["admin_ids"]:
            logs = #request here
            respond(logs)
        else:
            respond("Invalid input or not authorized to preform this action.")

    @app.command("/clearlogs")
    def clear_logs(ack, respond, command):
        ack()
        if command["user_id"] in cfg["admin_ids"]:
            #add request
            respond("ai ai capitan")
        else:
            respond("Invalid input or not authorized to preform this action.")


    @app.command("/viewvms")
    def view_vms(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            #message = add request
            respond(message)
        elif command["user_id"] in cfg["white_list"]:
            #message = add request
            respond()
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
                #add request
                respond("User is now an admin.")

    @app.command("/demote")
    def demote_user(ack, respond, command):
        ack()
        text = (command.get("text") or "").strip()
        if command["user_id"] in cfg["admin_ids"]:
            if text in cfg["admin_ids"] and text != command["user_id"]:
                #add request
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
        if command["user_id"] in cfg["admin_ids"]:
            respond("just ask eric directly ;-;")
        elif command["channel_id"] == cfg["channel_id"]:
            #add request here
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