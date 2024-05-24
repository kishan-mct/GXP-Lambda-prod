import json
import jwt
import sys
import uuid
import os

from datetime import datetime, timedelta, timezone

from utils.db_operations import DBOperations
from utils.common_functions import (
    convert_empty_strings_to_none,
    decrypt_data,
    generate_random_number,
    render_jinja_template,
    send_mail_wia_smtp2go,
    send_msg_wia_bulk_vs_sms,
    json_serializer
)
from passlib.hash import pbkdf2_sha256

gxp_db = DBOperations("gxp-dev")

JWT_SECRET = os.environ.get('JWT_SECRET')


def get_user_access_token_by_login(user_id, remote_ip, is_last_login_update=False, hotel_id=None):
    jti = str(uuid.uuid4())
    
    update_last_login_data = {
        "jti": jti,
        "ip_address": remote_ip
    }
    
    if is_last_login_update:
        update_last_login_data["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        
    gxp_db.update_query("users_user", update_last_login_data, condition="id=%s", params=(user_id,))
    user_columns = ["id", "is_gxp_staff", "first_name", "last_name", "email", "mobile", "user_type", "is_active", "date_joined", "profile_picture", "last_login"]
    get_user = gxp_db.get_query("users_user", user_columns, condition="id=%s AND is_active=True", params=(user_id,)).get("data")
    
    access_token_exp_time = 60 * 1000 # Access token expiration time is 1 hours 40 minutes
    refresh_token_exp_time = 60 * 1200  # Refresh token expiration time is 2 hours
        
    # Generate access token
    access_token_payload = {
        "user_id": user_id,
        "is_gxp_staff": get_user["is_gxp_staff"],
        "email": get_user["email"],
        "user_type": get_user["user_type"],
        "exp": datetime.now() + timedelta(seconds=access_token_exp_time),
        "hotel_id": hotel_id
    }

    # Generate refresh token
    refresh_token_payload = {
        "jti": jti,  # Unique identifier for the refresh token
        "exp": datetime.now() + timedelta(seconds=refresh_token_exp_time),
        "hotel_id": hotel_id
    }

    access_token = jwt.encode(access_token_payload, JWT_SECRET, algorithm="HS256")
    refresh_token = jwt.encode(refresh_token_payload, JWT_SECRET, algorithm="HS256")

    response_body = {
        "status": True,
        "message": "",
        "data": {
            "user": get_user,
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    }
    
    return response_body


def userAuthLogin(event, context):
    status_code = 200
    response_body = {"status": False, "message": "", "data": {}}
    http_method = event['httpMethod']
    remote_ip = event['headers'].get('X-Forwarded-For', '').split(',')[0].strip()

    try:
        if http_method == 'POST':
            request_body_data = convert_empty_strings_to_none(json.loads(event['body']))
            request_body = decrypt_data(request_body_data.get('data'))

            email = request_body.get("email", None)
            mobile_number = request_body.get("mobile", None)
            password = request_body.get("password", None)
            otp_number = request_body.get("otp_number", None)
            auth_verification_otp_id = request_body.get("auth_verification_otp_id", None)
            device_data = request_body.get("device_data", {})

            if email:
                get_user = gxp_db.get_query("users_user", ["id", "password"], 
                                            condition="LOWER(email)=LOWER(%s) AND is_active=True",
                                            params=(email,)).get("data")
            elif mobile_number:
                get_user = gxp_db.get_query("users_user", ["id", "password"], 
                                            condition="mobile_number=%s AND is_active=True", 
                                            params=(mobile_number,)).get("data")
            else:
                get_user = None
                response_body["message"] = 'Email or Mobile number is required.'

            print("get_user", get_user)
            if get_user:
                user_id = get_user['id']
                if password:
                    if pbkdf2_sha256.verify(password, get_user["password"]):
                        response_body = get_user_access_token_by_login(user_id, remote_ip, is_last_login_update=True)
                    else:   
                        response_body["message"] = "Incorrect password"
                        status_code = 401
                        
                elif otp_number and auth_verification_otp_id:
                    auth_verification_otp_data = gxp_db.get_query("users_authverificationotp", columns=["otp_number", "created_at"], condition="user_id=%s AND id=%s", 
                                                                  params=(user_id, auth_verification_otp_id)).get("data")
                    
                    auth_otp_send_at = datetime.strptime(auth_verification_otp_data["created_at"], "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(timezone.utc)
                    
                    last_otp_send_seconds = int((datetime.now(timezone.utc) - auth_otp_send_at).total_seconds())
                    if len(str(otp_number)) == 6 and last_otp_send_seconds < 90:
                        if otp_number and str(otp_number) == str(auth_verification_otp_data["otp_number"]):
                            response_body = get_user_access_token_by_login(user_id, remote_ip, is_last_login_update=True)
                        else:
                            response_body['message'] = "OTP invalid"
                    else:
                        response_body['message'] = "OTP expired"
                        
                else:
                    last_auth_otp_send = gxp_db.select_query("users_authverificationotp", columns=["created_at"], condition="user_id=%s",
                                                                params=(user_id,), order_by="created_at DESC", page_size=1).get("data")
                    
                     # Convert current datetime to UTC timezone
                    current_datetime = datetime.now(timezone.utc)
                    
                    if not last_auth_otp_send:
                        last_auth_otp_send_at = current_datetime - timedelta(seconds=125)
                    else:
                        last_auth_otp_send_at = datetime.strptime(last_auth_otp_send[0]["created_at"], "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(timezone.utc)

                    # Calculate the difference in seconds
                    last_otp_send_seconds = int((current_datetime - last_auth_otp_send_at).total_seconds())
                    
                    if last_otp_send_seconds > 90:
                        send_otp_number = generate_random_number(6)
                        opt_send_status = False
                        if email:
                            rendered_email_msg = render_jinja_template("user/loing_email_otp.html", {'otp_number': send_otp_number})
                            email_subject = f"GuestXP App OTP: {send_otp_number}"
                            reply_to = "GuestXP APP <support@guestxp.com>"
                            mail_resp = send_mail_wia_smtp2go([email], reply_to, email_subject, rendered_email_msg)
                            print("MAIL_RESP", mail_resp)
                            if mail_resp.get('data', {}).get('succeeded', 0) == 1:
                                opt_send_status = True
                                response_body["message"] = f"OTP number send to your {email} email"
                            else:
                                response_body["message"] = mail_resp.get('data', {}).get('failures', [])

                        if mobile_number:
                            from_number = "16506007010"
                            sms_resp = send_msg_wia_bulk_vs_sms(from_number, [mobile_number], "GuestXP app verification otp number is: " + send_otp_number)
                            print("SMS_RESP", sms_resp)
                            if sms_resp['status']:
                                opt_send_status = True
                                response_body["message"] = "OTP number send to your mobile"
                            else:
                                response_body["message"] =  f"{mobile_number} Mobile number is not valid"

                        if opt_send_status:
                            users_authverificationotp_data = {
                                "id": str(uuid.uuid4()),
                                "user_id": user_id,
                                "email": email,
                                "mobile": mobile_number,
                                "otp_number": send_otp_number,
                                "ip_address": remote_ip,
                                "device_data": json.dumps(device_data)
                            }
                            response_body = gxp_db.insert_query("users_authverificationotp", users_authverificationotp_data)
                            if response_body["status"]:
                                response_body["data"] = {
                                    "id": users_authverificationotp_data["id"],
                                    "email": users_authverificationotp_data["email"],
                                    "mobile": users_authverificationotp_data["mobile"]
                                }
                    else:
                        response_body["message"] = f"Wait for {90 - last_otp_send_seconds} seconds to resend OTP"
            else:
                response_body["message"] = "User not found"
                status_code = 404
        else:
            response_body["message"] = f'Unsupported HTTP method: {http_method}'
            status_code = 405

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        response_body['status'] = False
        response_body['message'] = f"Error: {exc_value}, Line: {exc_traceback.tb_lineno}"

    return {
        'statusCode': status_code,
        'body': json.dumps(response_body, default=json_serializer),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }


def userGetAccessTokebByRefereshToken(event, context):
    status_code = 200
    response_body = {"status": False, "message": ""}
    http_method = event['httpMethod']
    remote_ip = event['headers'].get('X-Forwarded-For', '').split(',')[0].strip()
   
    try:
        if http_method == 'POST':
            headers = event.get('headers', {})
            referesh_token = headers.get('Authorization') or headers.get('authorization')
            
            if not referesh_token:
                raise ValueError("Referesh token missing")
                
            # Split the token
            token_parts = referesh_token.split()

            if len(token_parts) != 2 or token_parts[0].lower() != "bearer":
                raise ValueError("Invalid token format")

            referesh_token = token_parts[1].strip()
            referesh_token_data = jwt.decode(referesh_token, JWT_SECRET, algorithms=["HS256"])

            request_body_data = convert_empty_strings_to_none(json.loads(event['body']))
            request_body = decrypt_data(request_body_data.get("data"))
            user_id = request_body.get("user_id", None)
            hotel_id = referesh_token_data.get("hotel_id", None)
            
            if user_id:
                user_data = gxp_db.get_query("users_user", ["id"], condition="id=%s AND jti=%s AND is_active=True", 
                                             params=(user_id, referesh_token_data["jti"])).get("data")
                
                if user_data:
                    response_body = get_user_access_token_by_login(user_data["id"], remote_ip, is_last_login_update=False, hotel_id=hotel_id)
                    
                    if hotel_id:
                        hotel_detail = gxp_db.get_query("hotel_hotel", "*", condition="id=%s AND is_active=True", params=(hotel_id,)).get("data", {})
                        if not hotel_detail:
                            raise ValueError("Invalid token or not access")
                        
                        response_body["data"]["hotel"] = hotel_detail
                else:
                    response_body["message"] = "User not found"
                    status_code = 404
            else:
                response_body["message"] = f"Unsupported HTTP method: {http_method}"
           
        else:
            response_body["message"] = f"required field is empty or not found"
            status_code = 405

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        response_body['status'] = False
        response_body['message'] = f"Error: {exc_value}, Line: {exc_traceback.tb_lineno}"

    return {
        'statusCode': status_code,
        'body': json.dumps(response_body, default=json_serializer),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }



def userAccessHotelListDetail(event, context):
    status_code = 200
    query_result = {"status": False, "message": "", "data": {}}
    http_method = event['httpMethod']
    remote_ip = event['headers'].get('X-Forwarded-For', '').split(',')[0].strip()
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["hotel_name"])[0]
            get_columns = multi_value_qp.pop('column', ["id", "hotel_name", "property_code", "email", "favicon_icon", "logo",
                                                        "address", "city", "state", "country", "zip_code", "is_active"])
            
            condition = "1=1"
            
            if not user_data['is_gxp_staff']:
                users_userhotel = gxp_db.select_query("users_userhotel", columns=["hotel_id"], condition="user_id=%s", params=(user_data['user_id'],)).get("data")
                users_userhotel_id_list = [user_hotel['hotel_id'] for user_hotel in users_userhotel]
                condition += f" AND id IN {set(users_userhotel_id_list)}"
            
            if 'hotel_name_start_with' in multi_value_qp:
                starts_with_value = multi_value_qp.pop('hotel_name_start_with')[0]
                condition += f" AND hotel_name LIKE '{starts_with_value}%'"
            
            if 'email_with' in multi_value_qp:
                starts_with_value = multi_value_qp.pop('email_start_with')[0]
                condition += f" AND email LIKE '{starts_with_value}%'"
            
            if 'property_code_start_with' in multi_value_qp:
                starts_with_value = multi_value_qp.pop('property_code_start_with')[0]
                condition += f" AND property_code LIKE '{starts_with_value}%'"
            
            # Assuming multi_value_qp might still have additional filters
            for k, v in multi_value_qp.items():
                for value in v:
                    condition += f" AND LOWER({k}) = '{value.lower()}'"

            query_result = gxp_db.select_query("hotel_hotel", get_columns, condition=condition, order_by=order_by,
                                               page_size=page_size, page_number=page_number)
        
        elif http_method == 'POST':
            hotel_id = event['pathParameters']['hotel_id']
            user_hotel_id = hotel_detail = None
            if not user_data['is_gxp_staff']:
                user_hotel_id = gxp_db.get_query("users_userhotel", ["hotel_id"], condition="user_id=%s AND hotel_id=%s",
                                                 params=(user_data["user_id"], hotel_id)).get("data").get("hotel_id", None)
            else:
                user_hotel_id = hotel_id
            
            if user_hotel_id:
                hotel_detail = gxp_db.get_query("hotel_hotel", "*", condition="id=%s AND is_active=True", params=(user_hotel_id,)).get("data")
            
            if hotel_detail:
                query_result = get_user_access_token_by_login(user_data["user_id"], remote_ip, is_last_login_update=False, hotel_id=hotel_detail['id'])
                query_result["data"]["hotel"] = hotel_detail

        else:
            query_result["message"] = f'Unsupported HTTP method: {http_method}'
            status_code = 405

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        query_result['status'] = False
        query_result['message'] = f"Error: {exc_value}, Line: {exc_traceback.tb_lineno}"

    return {
        'statusCode': status_code,
        'body': json.dumps(query_result, default=json_serializer),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }
