import json
import sys
from passlib.hash import pbkdf2_sha256

from utils.db_operations import DBOperations
from utils.s3_operations import S3Operations
from utils.common_functions import json_serializer, convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")
s3_operations = S3Operations()
user_detail_column = ["id", "first_name", "last_name", "email", "mobile", "mobile_iso", "is_active", "date_joined", "gender",
                    "profile_picture", "device_data", "date_of_birth", "address_line_first", "address_line_second", "zip_code",
                    "city", "state", "country", "special_notes", "is_email_verify", "last_login", "ip_address",
                    "created_at", "updated_at", "created_by", "updated_by", "user_type", "is_gxp_staff"]

def userProfileGetUpdate(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        user_id = user_data['user_id']
        if http_method == 'GET':
            query_result = gxp_db.get_query("users_user", user_detail_column, condition="id=%s", params=(user_id, ))
            
            permissions_query = f"""
                SELECT 
                    json_agg(json_build_object(
                        'name', p.name,
                        'codename', p.codename
                    )) AS access_permissions
                FROM 
                    users_user u
                LEFT JOIN 
                    users_usergroups ug ON u.id = ug.user_id
                LEFT JOIN 
                    app_group g ON ug.group_id = g.id
                LEFT JOIN 
                    app_grouppermission gp ON g.id = gp.group_id
                LEFT JOIN 
                    app_permission p ON gp.permission_id = p.id
                WHERE 
                    u.id = '{user_id}'
            """
            
            user_userpermission = gxp_db.raw_query_fetchone(permissions_query)
            user_profile = query_result["data"]

            if query_result["status"]:
                query_result["data"]["access_permissions"] = user_userpermission["data"]["access_permissions"]
                 
            user_profile["profile_picture"] = s3_operations.get_files(user_profile["profile_picture"]) if user_profile.get("profile_picture") else None

        elif http_method == 'PATCH':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            # Check if the email already exists
            email_exists_result = None
            email = request_body.get("email", None)
            
            if email:
                email_exists_result = gxp_db.get_query("users_user", ["email"], condition="LOWER(email)=LOWER(%s) AND id!='%s'", 
                                                       params=(email, user_id)).get("data", {}).get("email", None)

            if email_exists_result:
                query_result["message"] = f"{email} user email already exists"
            else:
                password = request_body.get("password", None)
                if password:
                    request_body["password"] = pbkdf2_sha256.hash(password)
                    
                query_result = gxp_db.update_query("users_user", request_body, condition="id=%s", params=(user_id,))
                if query_result["status"]:
                    query_result = gxp_db.get_query("users_user u", user_detail_column, condition="id=%s", params=(user_id,))
                
        else:
            query_result["message"] = f"Unsupported HTTP method: {http_method}"
            status_code = 405

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        query_result['status'] = False
        query_result['message'] = f"message: {exc_value}, error_line: {exc_traceback.tb_lineno}"
    finally:
        return {
            'statusCode': status_code,
            'body': json.dumps(query_result, default=json_serializer),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
