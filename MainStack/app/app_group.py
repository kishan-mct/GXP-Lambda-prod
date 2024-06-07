import json
import sys
import uuid

from utils.db_operations import DBOperations
from utils.common_functions import convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def appGroupListCreateUpdateDestroy(event, context):
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
            
            condition = "1=1"
            parameter = ()
            
            if multi_value_qp:
                parameter = parameter + tuple(
                    [[elm.lower() for elm in inner_list] for inner_list in multi_value_qp.values()])
                filter_field = 'AND '.join([f"LOWER({k})" + ' IN %s ' for k in multi_value_qp.keys()])
                condition = f"{condition} AND {filter_field}"
            
            if 'id' in multi_value_qp:
                ag_id = multi_value_qp.pop('id')[0]
                table = "app_group ag " \
                        "LEFT JOIN app_grouppermission agp ON ag.id = agp.group_id " \
                        "LEFT JOIN app_permission ap ON agp.permission_id = ap.id " 
                columns = [
                    "ag.*",
                    "COALESCE(json_agg(json_build_object('id', ap.id,  'module_id', ap.module_id, 'name', ap.name, "
                                                "'codename', ap.codename, 'is_super', ap.is_super, 'is_delete', ap.is_delete)), '[]') AS app_permission "
                ]
                condition = "ag.id=%s AND ag.hotel_id IS NULL GROUP BY ag.id"
                params = (ag_id,)
                if hotel_id:
                    condition = "ag.id=%s AND ag.hotel_id=%s GROUP BY ag.id"
                    params = (ag_id, hotel_id)
                
                query_result = gxp_db.get_query(table, columns, condition=condition, params=params)
                
            else:
                condition = "hotel_id IS NULL"
                params = ()
                if hotel_id:
                    condition = f"{condition} AND hotel_id='{hotel_id}'"
                    parameter = parameter + (hotel_id, )
                
                query_result = gxp_db.select_query("app_group", "*", condition=condition, params=parameter, order_by=order_by,
                                                   page_size=page_size, page_number=page_number)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            name = request_body.get('name')
            app_grouppermission = request_body.pop('app_grouppermission', [])
            
            condition = "LOWER(name)=LOWER(%s) AND hotel_id IS NULL"
            params = (name, )
            if hotel_id:
                condition = "LOWER(name)=LOWER(%s) AND hotel_id=%s"
                params = (name, hotel_id)
                
            existing_record = gxp_db.get_query("app_group", ["name"], condition=condition, params=params).get("data")
            if existing_record:
                query_result["message"] = f"{name} group name already exists."
            else:
                request_body["id"] = str(uuid.uuid4())
                if hotel_id:
                    request_body["hotel_id"] = hotel_id
                    
                query_result = gxp_db.insert_query("app_group", request_body)

                if query_result['status']:
                    if app_grouppermission:
                        app_grouppermission_data = [
                            {
                                "id": str(uuid.uuid4()), 
                                "group_id": request_body["id"], 
                                "permission_id": app_permission_id
                            } 
                            for app_permission_id in app_grouppermission
                        ]
                        gxp_db.bulk_insert_query("app_grouppermission", app_grouppermission_data)
                        
                    query_result = gxp_db.get_query("app_group", "*", "id=%s", params=(request_body["id"],))
                        
        elif http_method == 'PATCH':
            app_group_id = event['pathParameters']['app_group_id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            name = request_body.get('name')
            app_grouppermission = request_body.pop('app_grouppermission', [])
            existing_record = False
            
            if name or hotel_id:
                condition = "LOWER(name)=LOWER(%s) AND hotel_id IS NULL AND id!=%s"
                params = (name, app_group_id)
                if hotel_id:
                    condition = "LOWER(name)=LOWER(%s) AND hotel_id=%s AND id!=%s"
                    params = (name, hotel_id, app_group_id)
                    
                existing_record = gxp_db.get_query("app_group", ["name"], condition=condition, params=params).get("data")
                
            if existing_record:
                query_result["message"] = f"{name} group name already exists."
            else:
                if app_grouppermission:
                    gxp_db.delete_query("app_grouppermission", condition="group_id=%s", params=(app_group_id, ))
                    app_grouppermission_data = [
                        {
                            "id": str(uuid.uuid4()), 
                            "group_id": app_group_id, 
                            "permission_id": app_permission_id
                        } 
                        for app_permission_id in app_grouppermission
                    ]
                    gxp_db.bulk_insert_query("app_grouppermission", app_grouppermission_data)
                
                query_result = gxp_db.update_query("app_group", request_body, condition="id=%s", params=(app_group_id,))
                if query_result['status']:
                    query_result = gxp_db.get_query("app_group", "*", condition="id=%s", params=(app_group_id,))

        elif http_method == 'DELETE':
            app_group_id = event['pathParameters']['app_group_id']
            gxp_db.delete_query("users_usergroups", condition="group_id=%s", params=(app_group_id,))
            gxp_db.delete_query("app_grouppermission", condition="group_id=%s", params=(app_group_id,))
            query_result = gxp_db.delete_query("app_group", condition="id=%s", params=(app_group_id,))
            
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
