import json
import uuid
import sys

from utils.db_operations import DBOperations
from utils.filter import filter_execute_query
from utils.common_functions import json_serializer, convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")

def roomTypeListCreate(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    print(user_data)

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            get_columns = multi_value_qp.pop('column', "*")
            order_by = multi_value_qp.pop('order_by', ["roomtype_name"])[0]


            filters = {k: v[0] for k, v in multi_value_qp.items() if k not in ('page_size', 'page_number', 'column')}
            print("filters",filters)

            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                query_result = gxp_db.get_query("room_roomtype", get_columns, condition="id=%s", params=(id,))
            else:
                 query_result = filter_execute_query("room_roomtype", get_columns, filters, page_size, page_number,order_by)
                 print("query_result",query_result)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))

            request_body["id"] = str(uuid.uuid4())
            request_body["hotel_id"] = user_data["hotel_id"]
            request_body["created_by"] = user_data["email"]

            query_result = gxp_db.insert_query("room_roomtype", request_body)
            if query_result['status']:
                query_result = gxp_db.get_query("room_roomtype", "*", condition="id=%s", params=(request_body["id"],))
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

def roomTypeUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        room_type_id = event['pathParameters']['id']
        if http_method == 'PATCH':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))

            request_body["updated_by"] = user_data["email"]

            query_result = gxp_db.update_query("room_roomtype", request_body, condition="id=%s", params=(room_type_id,))
            if query_result['status']:
                query_result = gxp_db.get_query("room_roomtype", "*", condition="id=%s", params=(room_type_id,))

        elif http_method == 'DELETE':
                query_result = gxp_db.delete_query("room_roomtype", condition="id=%s", params=(room_type_id,))  
        
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
    


#  if '__' in field:
#             table_alias, field = field.split('__', 1)
#             if table_alias not in joined_tables:
#                 if table_alias == 'hotel_hotel':
#                     joins.append("JOIN hotel_hotel ON room_roomtype.hotel_id = hotel_hotel.id")
#                 else:
#                     joins.append(f"JOIN {table_alias} ON room_roomtype.{table_alias}_id = {table_alias}.id")
#                 joined_tables.add(table_alias)
#             sql_field = f"{table_alias}.{field}"
#         else:
#             sql_field = field