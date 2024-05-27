import json
import sys
import uuid

from utils.db_operations import DBOperations
from utils.common_functions import convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def authPermissionListCreateUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    hotel_id = user_data.get("hotel_id")

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["app_content_type_id", "codename"])[0]
            
            table = "auth_permission ap " \
                    "JOIN auth_appcontenttype apc on apc.id = ap.app_content_type_id "
                    
            columns = [
                "ap.*",
                "json_build_object('id', apc.id, 'app_label', apc.app_label, 'model', apc.model) AS auth_appcontenttype "
            ]
            
            condition = "1=1"
            if 'ap.id' in multi_value_qp:
                id = multi_value_qp.pop('ap.id')[0]
                condition += f" AND ap.id='{id}'"
                if hotel_id:
                    condition += " AND ap.is_super=False"
                
                query_result = gxp_db.get_query(table, columns, condition=condition)
            else:
                if hotel_id:
                    condition += " AND ap.is_super=False"
                
                query_result = gxp_db.select_query(table, columns, condition=condition, page_size=page_size, page_number=page_number, order_by=order_by)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            app_content_type_id = request_body.get('app_content_type_id')
            codename = request_body.get('codename')
            
            existing_record = gxp_db.get_query("auth_appcontenttype", ["app_label", "model"], condition="app_content_type_id=%s AND LOWER(codename)=LOWER(%s)", 
                                               params=(app_content_type_id, codename)).get("data")
            if existing_record:
                query_result["message"] = f"{codename} codename already exists in app_content_type."
            else:
                request_body["id"] = str(uuid.uuid4())
                query_result = gxp_db.insert_query("auth_permission", request_body)

                if query_result['status']:
                    query_result = gxp_db.get_query("auth_permission", "*", "id=%s", params=(request_body["id"],))
             
        elif http_method == 'PATCH':
            auth_permission_id = event['pathParameters']['auth_permission_id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            content_type_id = request_body.get('content_type_id')
            codename = request_body.get('codename')
            existing_record = False
            
            if content_type_id and codename:
                existing_record = gxp_db.get_query("auth_appcontenttype", ["app_label", "model"], condition="app_content_type_id=%s AND LOWER(codename)=LOWER(%s) AND id!=%s", 
                                                params=(app_content_type_id, codename, auth_permission_id)).get("data")
            if existing_record:
                query_result["message"] = f"{codename} codename already exists in app_content_type."
            else:
                query_result = gxp_db.update_query("auth_permission", request_body, condition="id=%s", params=(auth_permission_id,))
                if query_result['status']:
                    query_result = gxp_db.get_query("auth_permission", "*", condition="id=%s", params=(auth_permission_id,))

        elif http_method == 'DELETE':
            auth_permission_id = event['pathParameters']['auth_permission_id']
            query_result = gxp_db.delete_query("auth_permission", condition="id=%s", params=(auth_permission_id,))
            
        else:
            query_result["message"] = f'Unsupported HTTP method: {http_method}'
            status_code = 405

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        query_result['status'] = False
        query_result['message'] = f"Error: {exc_value}, Line: {exc_traceback.tb_lineno}"

    return {
        'statusCode': status_code,
        'body': json.dumps(query_result),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }
