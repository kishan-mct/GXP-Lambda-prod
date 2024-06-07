import json
import uuid
import sys

from passlib.hash import pbkdf2_sha256
from utils.authentication import IsSuperAdmin
from utils.db_operations import DBOperations
from utils.common_functions import json_serializer, convert_empty_strings_to_none, string_convert_to_list

gxp_db = DBOperations("gxp-dev")

user_detail_column = ["id", "first_name", "last_name", "email", "mobile", "mobile_iso", "is_active", "date_joined", "gender",
                    "profile_picture", "device_data", "date_of_birth", "address_line_first", "address_line_second", "zip_code",
                    "city", "state", "country", "special_notes", "is_email_verify", "last_login", "ip_address",
                    "created_at", "updated_at", "created_by", "updated_by", "user_type", "is_gxp_staff", "access_app_platform"]


@IsSuperAdmin
def gxpUserListCreateUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        if http_method == 'GET':
            multi_value_qp = event.get('multiValueQueryStringParameters') or {}
            user_id = multi_value_qp.pop('id', [None])[0]
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["last_name", "first_name"])[0]
            column = ["id", "first_name", "last_name", "email", "mobile", "profile_picture", "address_line_first", "address_line_second",
                      "city", "state", "country", "user_type", "last_login", "is_active"]
            get_columns = multi_value_qp.pop('column', column)
            
            condition = "is_gxp_staff=%s"
            parameter = ("true",)
            
            if multi_value_qp:
                parameter = parameter + tuple(
                    [[elm.lower() for elm in inner_list] for inner_list in multi_value_qp.values()])
                filter_field = 'AND '.join([f"LOWER({k})" + ' IN %s ' for k in multi_value_qp.keys()])
                condition = f"{condition} AND {filter_field}"
            
            if user_id:
                user_detail_query = f"""
                    SELECT
                        u.id,
                        u.first_name,
                        u.last_name,
                        u.email,
                        u.mobile,
                        u.mobile_iso,
                        u.is_active,
                        u.date_joined,
                        u.gender,
                        u.profile_picture,
                        u.device_data,
                        u.date_of_birth,
                        u.address_line_first,
                        u.address_line_second,
                        u.zip_code,
                        u.city,
                        u.state,
                        u.country,
                        u.special_notes,
                        u.is_email_verify,
                        u.last_login,
                        u.ip_address,
                        u.created_at,
                        u.updated_at,
                        u.created_by,
                        u.updated_by,
                        u.user_type,
                        u.access_app_platform,
                        array_remove(array_agg(DISTINCT ug.group_id), NULL) AS group_ids
                    FROM
                        users_user u
                    LEFT JOIN
                        users_usergroups ug ON u.id = ug.user_id
                    WHERE
                        u.id = '{user_id}'
                    GROUP BY
                        u.id;
                """
                query_result = gxp_db.raw_query_fetchone(user_detail_query)
                if query_result["status"]:
                    query_result["data"]["user_grouppermission"] = string_convert_to_list(query_result["data"].pop("group_ids"))
            else:
                query_result = gxp_db.select_query("users_user", get_columns, condition=condition, params=parameter, order_by=order_by, 
                                                page_size=page_size, page_number=page_number)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            email = request_body.get('email', None)
            password = request_body.get('password', None)
            user_grouppermission = request_body.pop('user_grouppermission', [])
            
            # Check if the email already exists
            email_exists_result = gxp_db.get_query("users_user", "*", condition="LOWER(email) = LOWER(%s)", params=(email,))
            if email_exists_result.get("data", {}):
                query_result["status"] = False
                query_result["message"] = f"{email} email user already exists"
            else:
                # Continue with user creation
                request_body.update({
                    "id": str(uuid.uuid4()),
                    "is_gxp_staff": "true",
                    "password": pbkdf2_sha256.hash(password),
                    "access_app_platform": json.dumps(request_body.pop("access_app_platform", [])),
                    "created_by": user_data["email"]
                })
                query_result = gxp_db.insert_query("users_user", request_body)
                
                if query_result["status"]:
                    # Bulk insert user group permissions if provided
                    if user_grouppermission:
                        user_grouppermission_data = [
                            {
                                "id": str(uuid.uuid4()),
                                "user_id": request_body["id"],
                                "group_id": grouppermission_id
                            }
                            for grouppermission_id in user_grouppermission
                        ]
                        if user_grouppermission_data:
                            gxp_db.bulk_insert_query("users_usergroups", user_grouppermission_data)

                    # Retrieve the newly created user details
                    query_result = gxp_db.get_query("users_user", user_detail_column, condition="id=%s", params=(request_body["id"],))
        
        elif http_method == 'PATCH':
            user_id = event['pathParameters']['id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            email = request_body.get('email', None)
            user_grouppermission = request_body.pop('user_grouppermission', [])
            access_app_platform = request_body.pop('access_app_platform', [])
            proceed_with_execution = True
            
            # Check if the email already exists
            if email:
                email_exists_result = gxp_db.get_query("users_user", "*", condition="LOWER(email) = LOWER(%s) AND id!=%s", params=(email, user_id))
                if email_exists_result.get("data", {}):
                    query_result["status"] = False
                    query_result["message"] = f"{email} email user already exists"
                    proceed_with_execution = False
            
            # Continue with user update
            if proceed_with_execution:
                if user_grouppermission:
                    gxp_db.delete_query("users_usergroups", condition="user_id=%s", params=(user_id,))
                    auth_group_permission_data = [
                        {
                          "id": str(uuid.uuid4()),
                          "user_id": user_id, 
                          "group_id": group_id
                        }
                        for group_id in user_grouppermission
                    ]
                    gxp_db.bulk_insert_query("users_usergroups", auth_group_permission_data)               
                
                # Update user details
                if "password" in request_body:
                    request_body["password"] = pbkdf2_sha256.hash(request_body["password"])

                if access_app_platform:
                    request_body["access_app_platform"] = json.dumps(access_app_platform)
                
                request_body["updated_by"] = user_data["email"]
                query_result = gxp_db.update_query("users_user", request_body, condition="id=%s", params=(user_id,))
                
                if query_result['status']:
                    query_result = gxp_db.get_query("users_user", user_detail_column, condition="id=%s", params=(user_id,))


        elif http_method == 'DELETE':
            user_id = event['pathParameters']['id']
            user_data = gxp_db.get_query("users_user", ["profile_picture"], condition="id=%s", params=(user_id, )).get("data", {})
            if user_data["profile_picture"]:
                from utils.s3_operations import S3Operations
                s3_operations = S3Operations()
                s3_operations.delete_file(user_data["profile_picture"])
                
            gxp_db.delete_query("users_userhotel", condition="user_id=%s", params=(user_id,))
            gxp_db.delete_query("users_usergroups", condition="user_id=%s", params=(user_id,))
            query_result = gxp_db.delete_query("users_user", condition="id=%s", params=(user_id,))
       
        else:
            query_result["status"] = False
            query_result["message"] = f'Unsupported HTTP method: {http_method}'
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
