import requests

from utils.db_operations import DBOperations

pbx_db = DBOperations("pbx-prod")


fcm_request_headers = {
    "Authorization": "key=AAAAj1LHXIA:APA91bEcbVTN35-VQezAR6C5HZzO7QyW_Z8w8vW_MwnXJ81VH2wmJpNVr8hj-AnwdS4ThXALQIatgBU0tPrpnllq5piHzA80psis8f4AI8SWC7EZxhg16HgTbvu2X4fbMW03hjcivXmt",
}


def fcm_notification_send(user_uuid, notification_body, notification_data={}):
    fcm_token_list = []
    get_user_fcm_token_list = pbx_db.select_query("k_fcm_device", ["registration_id"], condition="user_uuid=%s", params=(user_uuid, )).get("result", [])
    for user_fcm_token in get_user_fcm_token_list:
        fcm_token_list.append(user_fcm_token["registration_id"])
    
    if fcm_token_list:
        fcm_body_data = {
            "registration_ids": fcm_token_list,
            "notification": notification_body
        }
        if notification_data:
            fcm_body_data["data"] = notification_data
        
        print("fcm_body_data", fcm_body_data)
        fcm_request = requests.post("https://fcm.googleapis.com/fcm/send", 
                                    headers=fcm_request_headers, json=fcm_body_data)
        print(fcm_request.text)
    
