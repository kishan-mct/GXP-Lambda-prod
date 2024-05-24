import json
import uuid
import sys
from passlib.hash import pbkdf2_sha256

from utils.db_operations import DBOperations
from utils.common_functions import json_serializer, convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def userListCreate(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    hotel_id = user_data.get("hotel_id")

    try:
        hotel_id = user_data.get("hotel_id")
        if http_method == 'GET':
            multi_value_qp = event.get('multiValueQueryStringParameters') or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["last_name", "first_name"])[0]
            
            table = "public.users_user"
                    
            columns = [
                "id",
                "first_name",
                "last_name",
                "email",
                "mobile",
                "mobile_iso",
                "is_active",
                "date_joined",
                "gender",
                "profile_picture",
                "device_data",
                "date_of_birth",
                "address_line_first",
                "address_line_second",
                "zip_code",
                "city",
                "state",
                "country",
                "special_notes",
                "is_email_verify",
                "password",
                "last_login",
                "ip_address",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
                "user_type",
                "jti",
                "is_gxp_staff"
            ]
            
            condition = "1=1"
            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                condition += f" AND id='{id}'"
            
            if hotel_id:
                condition += f" AND id IN (SELECT user_id FROM users_userhotel WHERE hotel_id='{hotel_id}')"
            else :
                condition += " AND is_gxp_staff=true OR is_gxp_staff=false"

            query_result = gxp_db.select_query(
                table,
                columns,
                condition=condition,
                page_size=page_size,
                page_number=page_number,
                order_by=order_by
            )

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            email = request_body.get('email', None)
            mobile_number = request_body.get('mobile_number', None)
            user_type = request_body.get('user_type', None)
            password = request_body.get('password', None)
            first_name = request_body.get('first_name', None)
            last_name = request_body.get('last_name', None)
            user_permission = request_body.pop('user_permission', {})
            user_grouppermission = request_body.pop('user_grouppermission', {})
            
            if not email or not user_type or not password or not first_name or not last_name:
                query_result["message"] = "Required field is empty"
            else:
                # Check if the email already exists
                email_exists_result = gxp_db.get_query("users_user", "*", condition="LOWER(email) = LOWER(%s)", params=(email,))
                if email_exists_result.get("data", {}):
                    query_result["status"] = False
                    query_result["message"] = f"{email} user email already exists"
                else:
                    # Continue with user creation
                    add_permission = user_permission.pop('add_permission', {})
                    add_grouppermission = user_grouppermission.pop('add_grouppermission', {})
                    request_body["password"] = pbkdf2_sha256.hash(password)
                    request_body["id"] = str(uuid.uuid4())
                    request_body["created_by"] = user_data["email"]

                    # Only check mobile number if provided
                    if mobile_number:
                        # Check if the mobile number already exists
                        mobile_exists_result = gxp_db.get_query("users_user", "*", condition="mobile_number = %s", params=(mobile_number,))
                        if mobile_exists_result.get("result", {}):
                            query_result["status"] = False
                            query_result["message"] = f"{mobile_number} user mobile number already exists"
                        else:
                            # Continue with user creation
                            query_result = gxp_db.insert_query("users_user", request_body)
                            query_result = gxp_db.get_query("users_user", "*", condition="id=%s", params=(request_body["id"],))

                    else:
                        # Continue with user creation since mobile number is not provided
                        query_result = gxp_db.insert_query("users_user", request_body)
                        if query_result["status"]:
                            
                            if add_permission:
                                user_permission_data = [
                                    {
                                        "id": str(uuid.uuid4()),
                                        "user_id": request_body["id"],
                                        "permission_id": permission_ids
                                    }
                                    for permission_ids in add_permission
                                ]
                                if user_permission_data:
                                    gxp_db.bulk_insert_query("users_userpermissions", user_permission_data)

                            if add_grouppermission:
                                user_grouppermission_data = [
                                {
                                    "id": str(uuid.uuid4()),
                                    "user_id": request_body["id"],
                                    "group_id": grouppermission_id
                                }
                                for grouppermission_id in add_grouppermission
                            ]
                            if user_grouppermission_data:
                                 gxp_db.bulk_insert_query("users_usergroups", user_grouppermission_data)
                            query_result = gxp_db.get_query("users_user", "*", condition="id=%s", params=(request_body["id"],))
                        
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

def userRetrieveUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        user_id = event['pathParameters']['id']
        if http_method == 'GET':
            query_result  = gxp_db.get_query("users_user", "*", condition="id=%s", params=(user_id,))
        
        elif http_method == 'PATCH':
            proceed_with_execution = True
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            email = request_body.get('email', None)
            user_permission = request_body.pop('user_permission', {})
            user_grouppermission = request_body.pop('user_grouppermission', {})
            
                # Check if the email already exists
            if email:
                email_exists_result = gxp_db.get_query("users_user", "*", condition="LOWER(email) = LOWER(%s) AND id!=%s", params=(email, user_id))
                if email_exists_result.get("result", {}):
                    query_result["status"] = False
                    query_result["message"] = f"{email} user email already exists"
                    proceed_with_execution = False
                print("proceed_with_execution",proceed_with_execution)
            
            else :
             if proceed_with_execution:
                # Continue with user creation
                add_permission = user_permission.pop('add_permission', [])
                add_group_permission = user_grouppermission.pop('add_grouppermission',[])

                if add_permission:
                    auth_permission_data = [
                        {
                            "id": str(uuid.uuid4()), 
                            "user_id": user_id, 
                            "permission_id": permission_id
                        } 
                        for permission_id in add_permission
                    ]
                    gxp_db.bulk_insert_query("users_userpermissions", auth_permission_data)
                remove_permission = user_permission.pop('remove_permission', [])
                if remove_permission:
                    gxp_db.delete_query("users_userpermissions", condition="user_id=%s AND permission_id IN %s", params=(user_id, remove_permission))
                        
                if add_group_permission :
                    auth__group_permission_data = [
                        {
                            "id": str(uuid.uuid4()), 
                            "user_id": user_id, 
                            "group_id": group_id
                        } 
                        for group_id in add_group_permission
                    ]
                    gxp_db.bulk_insert_query("users_usergroups", auth__group_permission_data)
                
                remove_group_permission = user_grouppermission.pop('remove_group_permission', [])
                if remove_group_permission :
                    gxp_db.delete_query("users_usergroups", condition="user_id=%s AND group_id IN %s", params=(user_id, remove_group_permission))
                
                query_result = gxp_db.update_query("users_user", request_body, condition="id=%s", params=(user_id,))

                if query_result['status']:
                    query_result = gxp_db.get_query("users_user", "*", condition="id=%s", params=(user_id,))

        elif http_method == 'DELETE':
            gxp_db.delete_query("users_usergroups", condition="user_id=%s", params=(user_id,))
            gxp_db.delete_query("users_userpermissions", condition="user_id=%s", params=(user_id,))

            query_result = gxp_db.delete_query("users_user", condition="id=%s", params=(user_id,))
            
        else:
            query_result["message"] = f'Unsupported HTTP method: {http_method}'
            status_code = 405

    except Exception as e:
        query_result['status'] = False
        query_result['message'] = repr(e)
    finally:
        return {
            'statusCode': status_code,
            'body': json.dumps(query_result, default=json_serializer),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }



def userProfileGetUpdate(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    
    columns = ['id', 'first_name', 'last_name', 'email', 'mobile', 'mobile_iso', 'is_gxp_staff', 'is_active', 'date_joined',
                'gender', 'profile_picture', 'date_of_birth', 'address_line_first', 'address_line_second', 'city', 'state', 'country', 'zip_code',
                'special_notes', 'is_email_verify', 'user_type']

    try:
        user_id = user_data['user_id']
        if http_method == 'GET':
            query_result = gxp_db.get_query("users_user", columns, condition="id=%s", params=(user_id, ))
            
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
                    query_result = gxp_db.get_query("users_user", columns, condition="id=%s", params=(user_id,))
                            
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
    
def userRetrievepermission(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        user_id = event['pathParameters']['id']
        if http_method == 'GET':
            user_exists_result = gxp_db.get_query("users_user", ["id"], condition="id=%s", params=(user_id,))
            
            if not user_exists_result.get("data"):
                query_result["message"] = f"User not found"
            
            else:
                user_data = gxp_db.get_query("users_user", ['*'], condition="id=%s", params=(user_id,))
                
                permissions_query_result = gxp_db.select_query(
                    "users_userpermissions up JOIN auth_permission ap ON up.permission_id = ap.id",
                    ["ap.*"],
                    condition="up.user_id=%s",
                    params=(user_id,)
                )
                permissions_data = permissions_query_result.get("data", [])
                permissions = [perm["id"] for perm in permissions_data]

                # Fetch user group permissions
                permission_group_results = gxp_db.select_query(
                    "users_usergroups up JOIN auth_group agp ON up.group_id = agp.id",
                    ["agp.*"],
                    condition="up.user_id=%s",
                    params=(user_id,)
                )
                group_permissions_data = permission_group_results.get("data", [])
                group_permissions = [perm["id"] for perm in group_permissions_data]

                query_result = {
                    "status":True,
                    "id": user_id,
                    "permissions": permissions,
                    "group_permissions": group_permissions
                }
        else:
            query_result["message"] = f'Unsupported HTTP method: {http_method}'
            status_code = 405

    except Exception as e:
        query_result['status'] = False
        query_result['message'] = repr(e)
    finally:
        return {
            'statusCode': status_code,
            'body': json.dumps(query_result, default=json_serializer),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }