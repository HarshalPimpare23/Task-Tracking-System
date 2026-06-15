import requests
from loguru import logger
from jsonhandler import Jsonopr

HOSTURL = "http://127.0.0.1:8000"
LOGINAPI = "/api/login/"
TASKAPI = "/api/task/"
UPDATELOGSTATUS = "/api/login-status/"
SCREENSHOTURL = "/api/send-screenshot/"

USERDB = "./localdb/user.json"
TASKDB = "./localdb/task.json"

SCREENSHOT = r"sceenShort/sone.png"
FACESHOT = r"sceenShort/face.png"
CONVERTIMG = r"sceenShort/newone.png"
key_mouse_event = False

user_data_handler = Jsonopr()

logger.info(f"FocusTrack App initialized - Server: {HOSTURL}")


def update_login_status(log_status):
    """Update user login status on the server."""
    try:
        user_data = user_data_handler.redjson(USERDB)
        user_id = user_data["user"]['id']
        url = f"{HOSTURL}{UPDATELOGSTATUS}{user_id}/"
        payload = {"log_status": log_status}
        files = []
        headers = {}
        
        logger.info(f"Updating login status: {log_status} for user {user_id}")
        response = requests.request("POST", url, headers=headers, data=payload, files=files)
        logger.debug(f"Status update response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to update login status: {e}", exc_info=True)


def logout():
    """Log out the current user."""
    update_login_status("OFF")
    logger.info("User logged out")