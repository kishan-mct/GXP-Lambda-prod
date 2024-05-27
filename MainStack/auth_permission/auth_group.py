import json
import sys
import uuid

from utils.db_operations import DBOperations
from utils.common_functions import convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def authGroupListCreateUpdateDestroy(event, context):
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
            order_by = multi_value_qp.pop('order_by', ["name"])[0]
            
            ag_id = multi_value_qp.pop('ag.id', [None])[0]
            if ag_id:
                table = "auth_group ag " \
                        "LEFT JOIN auth_grouppermission agp ON ag.id = agp.group_id " \
                        "LEFT JOIN auth_permission ap ON agp.permission_id = ap.id " 
                columns = [
                    "ag.*",
                    "COALESCE(json_agg(json_build_object('id', ap.id, 'name', ap.name, 'app_content_type_id', ap.app_content_type_id, "
                                                "'codename', ap.codename, 'is_super', ap.is_super)), '[]') AS permissions "
                ]
                condition = "ag.id=%s AND ag.hotel_id IS NULL GROUP BY ag.id"
                params = (ag_id,)
                if hotel_id:
                    condition = "ag.id=%s AND ag.hotel_id=%s GROUP BY ag.id"
                    params = (ag_id, hotel_id)
                
                query_result = gxp_db.get_query(table, columns, condition=condition, params=params)
                
            else:
                condition = "hotel_id IS NOT NULL" # add not Null #
                params = ()
                if hotel_id:
                    condition = f"hotel_id='{hotel_id}'"
                    params = (hotel_id, )
                
                query_result = gxp_db.select_query("auth_group", "*", condition=condition, params=params, order_by=order_by, page_size=page_size, page_number=page_number)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            name = request_body.get('name')
            auth_grouppermission = request_body.pop('auth_grouppermission', {})
            
            condition = "LOWER(name)=LOWER(%s) AND hotel_id IS NULL"
            params = (name, )
            if hotel_id:
                condition = "LOWER(name)=LOWER(%s) AND hotel_id=%s"
                params = (name, hotel_id)
                
            existing_record = gxp_db.get_query("auth_group", ["name"], condition=condition, params=params).get("data")
            if existing_record:
                query_result["message"] = f"{name} group name already exists."
            else:
                request_body["id"] = str(uuid.uuid4())
                if hotel_id:
                    request_body["hotel_id"] = hotel_id
                    
                query_result = gxp_db.insert_query("auth_group", request_body)

                if query_result['status']:
                    add_permission = auth_grouppermission.pop('add_permission', {})
                    if add_permission:
                        auth_grouppermission_data = [
                            {
                                "id": str(uuid.uuid4()), 
                                "group_id": request_body["id"], 
                                "permission_id": permission_id
                            } 
                            for permission_id in add_permission
                        ]
                        gxp_db.bulk_insert_query("auth_grouppermission", auth_grouppermission_data)
                        
                    query_result = gxp_db.get_query("auth_group", "*", "id=%s", params=(request_body["id"],))
                        
        elif http_method == 'PATCH':
            auth_group_id = event['pathParameters']['auth_group_id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            name = request_body.get('name')
            auth_grouppermission = request_body.pop('auth_grouppermission', [])
            existing_record = False
            
            if name or hotel_id:
                condition = "LOWER(name)=LOWER(%s) AND hotel_id IS NULL AND id!=%s"
                params = (name, auth_group_id)
                if hotel_id:
                    condition = "LOWER(name)=LOWER(%s) AND hotel_id=%s AND id!=%s"
                    params = (name, hotel_id, auth_group_id)
                    
                existing_record = gxp_db.get_query("auth_group", ["name"], condition=condition, params=params).get("data")
                
            if existing_record:
                query_result["message"] = f"{name} group name already exists."
            else:
                add_permission = auth_grouppermission.pop('add_permission', [])
                if add_permission:
                    auth_grouppermission_data = [
                        {
                            "id": str(uuid.uuid4()), 
                            "group_id": auth_group_id, 
                            "permission_id": permission_id
                        } 
                        for permission_id in add_permission
                    ]
                    gxp_db.bulk_insert_query("auth_grouppermission", auth_grouppermission_data)
                
                remove_permission = auth_grouppermission.pop('remove_permission', [])
                if remove_permission:
                    gxp_db.delete_query("auth_grouppermission", condition="group_id=%s AND permission_id IN %s", params=(auth_group_id, remove_permission))
                        
                query_result = gxp_db.update_query("auth_group", request_body, condition="id=%s", params=(auth_group_id,))
                if query_result['status']:
                    query_result = gxp_db.get_query("auth_group", "*", condition="id=%s", params=(auth_group_id,))

        elif http_method == 'DELETE':
            auth_group_id = event['pathParameters']['auth_group_id']
            gxp_db.delete_query("auth_grouppermission", condition="group_id=%s", params=(auth_group_id,))
            query_result = gxp_db.delete_query("auth_group", condition="id=%s", params=(auth_group_id,))
            
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
