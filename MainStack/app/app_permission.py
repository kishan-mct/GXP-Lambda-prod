import json
import sys
import uuid

from utils.db_operations import DBOperations
from utils.common_functions import convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def appPermissionListCreateUpdateDestroy(event, context):
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
            order_by = multi_value_qp.pop('order_by', ["module_id", "codename"])[0]
            
            table = "app_permission ap " \
                    "JOIN app_module am on am.id = ap.module_id "
                    
            columns = [
                "ap.*",
                "json_build_object('id', am.id, 'app', am.app, 'module', am.module, 'is_super', am.is_super, 'is_delete', am.is_delete) AS app_module "
            ]
            
            condition = "1=1"
            parameter = ()
            
            if 'ap.id' in multi_value_qp:
                id = multi_value_qp.pop('ap.id')[0]
                condition += f" AND ap.id='{id}'"
                if hotel_id:
                    condition += " AND ap.is_super=False"
                
                query_result = gxp_db.get_query(table, columns, condition=condition)
            else:
                if multi_value_qp:
                    parameter = parameter + tuple(
                        [[elm.lower() for elm in inner_list] for inner_list in multi_value_qp.values()])
                    filter_field = 'AND '.join([f"LOWER({k})" + ' IN %s ' for k in multi_value_qp.keys()])
                    condition = f"{condition} AND {filter_field}"
                
                if hotel_id:
                    condition = f"{condition} AND ap.is_super=False"
                
                query_result = gxp_db.select_query(table, columns, condition=condition, page_size=page_size, page_number=page_number, order_by=order_by)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            codename = request_body.get('codename')
            
            existing_record = gxp_db.get_query("app_permission", ["name", "codename"], condition="LOWER(codename)=LOWER(%s)", 
                                               params=(codename, )).get("data")
            if existing_record:
                query_result["message"] = f"codename {codename} already exists."
            else:
                request_body["id"] = str(uuid.uuid4())
                query_result = gxp_db.insert_query("app_permission", request_body)

                if query_result['status']:
                    query_result = gxp_db.get_query("app_permission", "*", "id=%s", params=(request_body["id"],))
             
        elif http_method == 'PATCH':
            app_permission_id = event['pathParameters']['app_permission_id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            content_type_id = request_body.get('content_type_id')
            codename = request_body.get('codename')
            existing_record = False
            
            if content_type_id and codename:
                existing_record = gxp_db.get_query("app_permission", ["name", "model"], condition="LOWER(codename)=LOWER(%s) AND id!=%s", 
                                                params=(codename, app_permission_id)).get("data")
            if existing_record:
                query_result["message"] = f"codename {codename} already exists."
            else:
                query_result = gxp_db.update_query("app_permission", request_body, condition="id=%s", params=(app_permission_id,))
                if query_result['status']:
                    query_result = gxp_db.get_query("app_permission", "*", condition="id=%s", params=(app_permission_id,))

        elif http_method == 'DELETE':
            app_permission_id = event['pathParameters']['app_permission_id']
            gxp_db.delete_query("app_grouppermission", condition="permission_id=%s", params=(app_permission_id,))
            query_result = gxp_db.delete_query("app_permission", condition="id=%s", params=(app_permission_id,))
            
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
