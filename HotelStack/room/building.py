import json
import uuid
import sys

from utils.db_operations import DBOperations
from utils.sql_query_filter import get_condition_and_params
from utils.common_functions import json_serializer, convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")

def buildingListCreate(event, context):
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
            get_columns = multi_value_qp.pop('column', "*")
            order_by = multi_value_qp.pop('order_by', [None])[0]

            filters = {k: v[0] for k, v in multi_value_qp.items()}

            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                query_result = gxp_db.get_query("room_building", get_columns, condition="id=%s", params=(id,))
            else:
                condition, params = get_condition_and_params(filters)
                query_result = gxp_db.select_query("room_building", get_columns, condition=condition, params=params,
                                                   order_by=order_by, page_size=page_size, page_number=page_number)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            building_name = request_body.get('building_name',None)
            short_name = request_body.get('short_name',None)
            
            exists_result = gxp_db.get_query("room_building","*",
                condition="hotel_id = %s AND (LOWER(building_name) = LOWER(%s) OR LOWER(short_name) = LOWER(%s))",
                params=(hotel_id, building_name, short_name)).get("data")
            
            if exists_result:
                if exists_result['building_name'].lower() == building_name.lower():
                    query_result["message"] = f"Building {building_name} name already exists"
                elif exists_result['short_name'].lower() == short_name.lower():
                    query_result["message"] = f"Building short {short_name} name already exists"
                return query_result
                            
            request_body["id"] = str(uuid.uuid4())
            request_body["hotel_id"] = user_data["hotel_id"]
            request_body["created_by"] = user_data["email"]
            
            query_result = gxp_db.insert_query("room_building", request_body)
            if query_result['status']:
                query_result = gxp_db.get_query("room_building", "*", condition="id=%s", params=(request_body["id"],))
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

def buildingUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    hotel_id = user_data.get("hotel_id")
    
    try:
        if http_method == 'PATCH':
            room_building_id = event['pathParameters']['id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            building_name = request_body.get('building_name',None)
            short_name = request_body.get('short_name',None)
            proceed_with_execution = True
            
            if  building_name :
                exists_result = gxp_db.get_query("room_building","*",condition="hotel_id = %s AND LOWER(building_name) = LOWER(%s) AND id != %s",
                    params=(hotel_id, building_name, room_building_id))
                if exists_result.get("data",{}):
                    query_result["status"] = False
                    query_result["message"] = f"Building {building_name} name already exists"
                    proceed_with_execution = False
            
            if  short_name :
                exists_result = gxp_db.get_query("room_building","*",condition="hotel_id = %s AND LOWER(short_name) = LOWER(%s) AND id != %s",
                    params=(hotel_id, short_name, room_building_id))
                if exists_result.get("data",{}):
                    query_result["status"] = False
                    query_result["message"] = f"short {short_name} name already exists"
                    proceed_with_execution = False

            if proceed_with_execution:
                request_body["updated_by"] = user_data["email"]
                query_result = gxp_db.update_query("room_building", request_body, condition="id=%s", params=(room_building_id,))
                if query_result['status']:
                    query_result = gxp_db.get_query("room_building", "*", condition="id=%s", params=(room_building_id,))

        elif http_method == 'DELETE':
                query_result = gxp_db.delete_query("room_building", condition="id=%s", params=(room_building_id,))  
        
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