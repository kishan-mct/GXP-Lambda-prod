import json
import uuid
import sys

from utils.db_operations import DBOperations
from utils.s3_operations import S3Operations
from utils.common_functions import json_serializer, convert_empty_strings_to_none
from utils.authentication import IsSuperAdmin
from utils.filter import filter_execute_query

gxp_db = DBOperations("gxp-dev")
s3_operations = S3Operations()

@IsSuperAdmin
def hotelBrandCreateUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        if http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            name = request_body.get('name', None)

            name_exists_result = gxp_db.get_query("hotel_brand", "*", condition="LOWER(name) = LOWER(%s)", params=(name,))
            if name_exists_result.get("data", {}):
                query_result["status"] = False
                query_result["message"] = f"{name} hotel brand name already exists"
                return query_result

            request_body["id"] = str(uuid.uuid4())

            query_result = gxp_db.insert_query("hotel_brand", request_body)
            if query_result['status']:
                query_result = gxp_db.get_query("hotel_brand", "*", condition="id=%s", params=(request_body["id"],))

            
        elif http_method == 'PATCH':
            user_id = event['pathParameters']['id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            name = request_body.get('name', None)

            name_exists_result = gxp_db.get_query("hotel_brand", "*", condition="LOWER(name) = LOWER(%s)", params=(name,))
            if name_exists_result.get("data", {}):
                query_result["status"] = False
                query_result["message"] = f"{name} hotel brand name already exists"
                return query_result
            
            query_result = gxp_db.update_query("hotel_brand", request_body, condition="id=%s", params=(user_id,))
            if query_result['status']:
                query_result = gxp_db.get_query("hotel_brand", "*", condition="id=%s", params=(user_id,))

        elif http_method == 'DELETE':
                query_result = gxp_db.delete_query("hotel_brand", condition="id=%s", params=(user_id,))  
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

def hotelBrandlist(event, context):
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
            get_columns = multi_value_qp.pop('column', "*")
            filters = {k: v[0] for k, v in multi_value_qp.items() if k not in ('page_size', 'page_number', 'column')}

            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                query_result = gxp_db.get_query("hotel_brand", get_columns, condition="id=%s", params=(id,))
            
            else:
                query_result = filter_execute_query("hotel_brand", get_columns, filters, page_size, page_number,order_by)
                
                logos = query_result["data"]
                [logo.update({"logo": s3_operations.public_access_level_urls(logo["logo"])}) for logo in logos if logo.get("logo")]

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