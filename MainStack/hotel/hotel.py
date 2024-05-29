import json
import uuid
import sys

from utils.db_operations import DBOperations
from utils.common_functions import json_serializer, convert_empty_strings_to_none
from utils.authentication import IsSuperAdmin

gxp_db = DBOperations("gxp-dev")

@IsSuperAdmin
def hotelListCreate(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["hotel_name"])[0]
            get_columns = multi_value_qp.pop('column','*')

            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                query_result = gxp_db.get_query("hotel_hotel",get_columns,condition="id=%s",params=(id,))
            else:
                query_result = gxp_db.select_query("hotel_hotel",['*'],
                                page_size=page_size,
                                page_number=page_number,
                                order_by=order_by
                            )

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
    
            request_body["id"] = str(uuid.uuid4())
            request_body["created_by"] = user_data["email"]
            
            query_result = gxp_db.insert_query("hotel_hotel", request_body)
            if query_result['status']:
                query_result = gxp_db.get_query("hotel_hotel", "*", condition="id=%s", params=(request_body["id"],))

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


@IsSuperAdmin
def hotelUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']

    try:
        hotel_id = event['pathParameters']['id']
        if http_method == 'PATCH':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))

            query_result = gxp_db.update_query("hotel_hotel", request_body, condition="id=%s", params=(hotel_id,))
            if query_result['status']:
                query_result = gxp_db.get_query("hotel_hotel", "*", condition="id=%s", params=(hotel_id,))

        elif http_method == 'DELETE':
                query_result = gxp_db.delete_query("hotel_hotel", condition="id=%s", params=(hotel_id,))  
        
        else:
            status_code = 405
            query_result["message"] = f'Unsupported HTTP method: {http_method}'

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