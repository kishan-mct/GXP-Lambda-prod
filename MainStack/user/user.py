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

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["email"])[0]
            get_columns = multi_value_qp.pop('column', ["id", "user_type", "property_user_type", "mobile_number", "email", "first_name",
                                                        "last_name", "profile_picture", "is_active", "is_notification_enable", "last_login_at", 
                                                        "last_login_ip"])
            
            condition = "1=1"
            
            if 'domain_uuid' in multi_value_qp:
                domain_uuid = multi_value_qp.pop('domain_uuid')[0]
                condition += f""" AND JSON_CONTAINS(access_domain, '"{domain_uuid}"')"""
            
            if 'email_start_with' in multi_value_qp:
                starts_with_value = multi_value_qp.pop('email_start_with')[0]
                condition += f" AND email LIKE '{starts_with_value}%'"
            
            if 'first_name_start_with' in multi_value_qp:
                starts_with_value = multi_value_qp.pop('first_name_start_with')[0]
                condition += f" AND first_name LIKE '{starts_with_value}%'"
            
            if 'last_name_start_with' in multi_value_qp:
                starts_with_value = multi_value_qp.pop('last_name_start_with')[0]
                condition += f" AND last_name LIKE '{starts_with_value}%'"
            
            # Assuming multi_value_qp might still have additional filters
            for k, v in multi_value_qp.items():
                for value in v:
                    condition += f" AND LOWER({k}) = '{value.lower()}'"

            query_result = gxp_db.select_query("users_user", get_columns, condition=condition, order_by=order_by,
                                               page_size=page_size, page_number=page_number)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            email = request_body.get('email', None)
            mobile_number = request_body.get('mobile_number', None)
            user_type = request_body.get('user_type', None)
            password = request_body.get('password', None)
            first_name = request_body.get('first_name', None)
            last_name = request_body.get('last_name', None)
            access_domain = request_body.get('access_domain', [])
            user_permission = request_body.get('user_permission', {})
            
            if not email or not user_type or not password or not first_name or not last_name:
                query_result["message"] = "Required field is empty"
            else:
                # Check if the email already exists
                email_exists_result = gxp_db.get_query("users_user", "*", condition="LOWER(email) = LOWER(%s)", params=(email,))

                if email_exists_result.get("result", {}):
                    query_result["status"] = False
                    query_result["message"] = f"{email} user email already exists"
                else:
                    # Continue with user creation
                    request_body["user_permission"] = json.dumps(user_permission)
                    request_body["access_domain"] = json.dumps(access_domain)
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
                    else:
                        # Continue with user creation since mobile number is not provided
                        query_result = gxp_db.insert_query("users_user", request_body)

                    if query_result["status"]:
                        # Fetch the created user for response
                        query_result = gxp_db.get_query("users_user", "*", condition="id=%s", params=(request_body["id"],))
                        access_domain_uuid_list = json.loads(query_result['result']['access_domain'])
                        get_access_domain = gxp_db.select_query("v_domains",
                                                                ['domain_uuid', 'domain_name', 'pbx', 'ip', 'main_cid', 'domain_timezone'],
                                                                condition="domain_uuid IN %s AND domain_enabled=%s",
                                                                params=(access_domain_uuid_list, 'true')).get("result", {})
                        query_result['result'].update({
                            "access_domain": get_access_domain
                        })

        else:
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
            query_result = gxp_db.get_query("users_user", "*", condition="id=%s", params=(user_id,))
            access_domain_uuid_list = json.loads(query_result['result']['access_domain'])
            get_access_domain = []
            if access_domain_uuid_list:
                get_access_domain = gxp_db.select_query("v_domains",
                                                        ['domain_uuid', 'domain_name', 'pbx', 'ip', 'main_cid', 'domain_timezone'],
                                                        condition="domain_uuid IN %s AND domain_enabled=%s",
                                                        params=(access_domain_uuid_list, 'true')).get("result", {})
            query_result['result'].update({
                "access_domain": get_access_domain,
                "user_permission": json.loads(query_result['result']['user_permission'])
            })

        elif http_method == 'PATCH':
            proceed_with_execution = True
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            email = request_body.get('email', None)
            mobile_number = request_body.get('mobile_number', None)
            password = request_body.get('password', None)
            access_domain = request_body.get('access_domain', [])
            user_permission = request_body.get('user_permission', {})
            
            # Check if the email already exists
            if email:
                email_exists_result = gxp_db.get_query("users_user", "*", condition="LOWER(email) = LOWER(%s) AND id!=%s", params=(email, user_id))
                if email_exists_result.get("result", {}):
                    query_result["status"] = False
                    query_result["message"] = f"{email} user email already exists"
                    proceed_with_execution = False
            
            if mobile_number:
                # Check if the mobile number already exists
                mobile_exists_result = gxp_db.get_query("users_user", "*", condition="mobile_number = %s AND id!=%s", params=(mobile_number, user_id))
                if mobile_exists_result.get("result", {}):
                    query_result["status"] = False
                    query_result["message"] = f"{mobile_number} user mobile number already exists"
                    proceed_with_execution = False
            
            if proceed_with_execution:
                # Continue with user creation
                if access_domain:
                    request_body["access_domain"] = json.dumps(access_domain)
                    
                if user_permission:
                    request_body["user_permission"] = json.dumps(user_permission)
                    
                if password:
                    request_body["password"] = pbkdf2_sha256.hash(password)
                    
                request_body["updated_by"] = user_data["email"]
                # Continue with user creation since mobile number is not provided
                query_result = gxp_db.update_query("users_user", request_body, condition="id=%s", params=(user_id, ))

                if query_result["status"]:
                    # Fetch the created user for response
                    query_result = gxp_db.get_query("users_user", "*", condition="id=%s", params=(user_id,))
                    access_domain_uuid_list = json.loads(query_result['result']['access_domain'])
                    get_access_domain = []
                    if access_domain_uuid_list:
                        get_access_domain = gxp_db.select_query("v_domains",
                                                                ['domain_uuid', 'domain_name', 'pbx', 'ip', 'main_cid', 'domain_timezone'],
                                                                condition="domain_uuid IN %s AND domain_enabled=%s",
                                                                params=(access_domain_uuid_list, 'true')).get("result", {})
                    query_result['result'].update({
                        "access_domain": get_access_domain,
                        "user_permission": json.loads(query_result['result']['user_permission'])
                    })


        elif http_method == 'DELETE':
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