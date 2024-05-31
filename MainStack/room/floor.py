import json
import uuid
import sys

from utils.db_operations import DBOperations
from utils.common_functions import json_serializer, convert_empty_strings_to_none
from utils.authentication import IsSuperAdmin
from utils.generate_presigned_url import generate_presigned_url,remove_query_params

gxp_db = DBOperations("gxp-dev")

def floorListCreate(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            get_columns = multi_value_qp.pop('column', "*")

            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                query_result = gxp_db.get_query("room_floor", get_columns, condition="id=%s", params=(id,))
            else:
                query_result = gxp_db.select_query(
                            "room_floor",
                            ['*'],
                            page_size=page_size,
                            page_number=page_number,
                        )
                if query_result.get('data'):
                    for result in query_result['data']:
                        images = json.dumps(result.get('images', '[]'))
                        presigned_urls = []
                        if images:
                            for image_url in images.strip('[]').strip('"').split('","'):  
                                object_name = '/'.join(image_url.split('/')[-5:]) # image_url.split('/')[-1]
                                print(object_name)
                                presigned_url = generate_presigned_url('backopsmedia', object_name, expiration=120,operation='get_object',)
                                presigned_urls.append(presigned_url)
                        result['images'] = presigned_urls
                            
        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            building_id = request_body.get("building_id")
            images = request_body.get('images', [])

            building_exists_result = gxp_db.get_query("room_building", ["*"], condition="id=%s", params=(building_id,))
            if not building_exists_result.get("data"):
                query_result["message"] = "building not found"
            else:
                request_body["id"] = str(uuid.uuid4())
                request_body["hotel_id"] = user_data["hotel_id"]
                request_body["created_by"] = user_data["email"]
                
                s3_bucket = 'backopsmedia'
                object_name = f'test-kishan/room_floor/{user_data["hotel_id"]}/images/{images[0]}'
                content_type = 'image/png'
                presigned_url = generate_presigned_url(s3_bucket, object_name, content_type, operation ='put_object')
                request_body["images"] = json.dumps(remove_query_params(presigned_url))

                query_result = gxp_db.insert_query("room_floor", request_body)
                if query_result['status']:
                    query_result = gxp_db.get_query("room_floor", "*", condition="id=%s", params=(request_body["id"],))
                if presigned_url:
                    query_result["presigned_url"] = presigned_url
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

def floorUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    try:
        room_floor_id = event['pathParameters']['id']
        if http_method == 'PATCH':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))

            request_body["updated_by"] = user_data["email"]

            query_result = gxp_db.update_query("room_floor", request_body, condition="id=%s", params=(room_floor_id,))
            if query_result['status']:
                query_result = gxp_db.get_query("room_floor", "*", condition="id=%s", params=(room_floor_id,))

        elif http_method == 'DELETE':
                query_result = gxp_db.delete_query("room_floor", condition="id=%s", params=(room_floor_id,))  
        
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


        