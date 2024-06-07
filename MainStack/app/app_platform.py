import json
import sys
import uuid

from utils.db_operations import DBOperations
from utils.common_functions import convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def appPlatformListCreateUpdate(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["name"])[0]
            
            condition = "1=1"
            parameter = ()
            
            if multi_value_qp:
                parameter = parameter + tuple(
                    [[elm.lower() for elm in inner_list] for inner_list in multi_value_qp.values()])
                filter_field = 'AND '.join([f"LOWER({k})" + ' IN %s ' for k in multi_value_qp.keys()])
                condition = f"{condition} AND {filter_field}"
                
            query_result = gxp_db.select_query("app_platform", "*", condition=condition, page_size=page_size, page_number=page_number, order_by=order_by)

        elif http_method == 'POST' and user_data["user_type"] == "super_admin":
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            name = request_body.get('name')
            platform_id = request_body.get('id')
            
            if platform_id:
                existing_record = gxp_db.get_query("app_platform", ["name"], condition="LOWER(name)=LOWER(%s) AND id!=%s", 
                                                params=(name, platform_id)).get("data")
                if existing_record:
                    query_result["message"] = f"platform {name} already exists."
                else:
                    query_result = gxp_db.update_query("app_platform", request_body, condition="id=%s", params=(platform_id,))
                    if query_result['status']:
                        query_result = gxp_db.get_query("app_platform", "*", "id=%s", params=(platform_id,))
            else:
                existing_record = gxp_db.get_query("app_platform", ["name"], condition="LOWER(name)=LOWER(%s)", 
                                                params=(name, )).get("data")
                if existing_record:
                    query_result["message"] = f"platform {name} already exists."
                else:
                    request_body["id"] = str(uuid.uuid4())
                    query_result = gxp_db.insert_query("app_platform", request_body)
                    if query_result['status']:
                        query_result = gxp_db.get_query("app_platform", "*", "id=%s", params=(request_body["id"],))
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
