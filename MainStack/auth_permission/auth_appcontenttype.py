import json
import uuid
import sys

from utils.db_operations import DBOperations
from utils.common_functions import json_serializer, convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def authAppContentTypeListCreateUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["model", "app_label"])[0]
            
            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                query_result = gxp_db.get_query("auth_appcontenttype", "*", condition="id=%s", params=(id,))
            else:
                query_result = gxp_db.select_query("auth_appcontenttype", "*", order_by=order_by, page_size=page_size, page_number=page_number)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            app_label = request_body.get('app_label')
            model = request_body.get('model')
            
            existing_record = gxp_db.get_query("auth_appcontenttype", ["app_label", "model"], condition="LOWER(app_label)=LOWER(%s) AND LOWER(model)=LOWER(%s)", 
                                               params=(app_label, model)).get("data")
            if existing_record:
                query_result["message"] = f"app_label {app_label} in {model} model already exists."
            else:
                request_body['id'] = str(uuid.uuid4())
                query_result = gxp_db.insert_query("auth_appcontenttype", request_body)

                if query_result['status']:
                    query_result = gxp_db.get_query("auth_appcontenttype", "*", "id=%s", params=(id,))
                    
        elif http_method == 'PATCH':
            auth_appcontenttype_id = event['pathParameters']['auth_appcontenttype_id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            app_label = request_body.get('app_label')
            model = request_body.get('model')
            
            existing_record = gxp_db.get_query("auth_appcontenttype", ["app_label", "model"], condition="LOWER(app_label)=LOWER(%s) AND LOWER(model)=LOWER(%s) AND id!=%s", 
                                               params=(app_label, model, auth_appcontenttype_id)).get("data")
            if existing_record:
                query_result["message"] = f"app_label {app_label} in {model} model already exists."
            else:
                query_result = gxp_db.update_query("auth_appcontenttype", request_body, condition="id=%s", params=(auth_appcontenttype_id,))
                if query_result['status']:
                    query_result = gxp_db.get_query("auth_appcontenttype", "*", condition="id=%s", params=(auth_appcontenttype_id,))

        elif http_method == 'DELETE':
            auth_appcontenttype_id = event['pathParameters']['auth_appcontenttype_id']
            query_result = gxp_db.delete_query("auth_appcontenttype", condition="id=%s", params=(auth_appcontenttype_id,))  

        else:
            status_code = 405
            query_result["message"] = f'Unsupported HTTP method: {http_method}'



    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        query_result['status'] = False
        query_result['message'] = f"Error: {exc_value}, Line: {exc_traceback.tb_lineno}"
    
    finally:
        return {
            'statusCode': status_code,
            'body': json.dumps(query_result, default=json_serializer),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
