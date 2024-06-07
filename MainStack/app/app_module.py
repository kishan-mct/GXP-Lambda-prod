import json
import uuid
import sys

from utils.db_operations import DBOperations
from utils.common_functions import json_serializer, convert_empty_strings_to_none

gxp_db = DBOperations("gxp-dev")


def appModuleListCreateUpdateDestroy(event, context):
    status_code = 200
    query_result = {"status": False, "message": ""}
    http_method = event['httpMethod']

    try:
        if http_method == 'GET':
            multi_value_qp = event['multiValueQueryStringParameters'] or {}
            page_size = multi_value_qp.pop('page_size', [None])[0]
            page_number = multi_value_qp.pop('page_number', [1])[0]
            order_by = multi_value_qp.pop('order_by', ["app", "module"])[0]
            get_columns = multi_value_qp.pop('column', "*")
            
            condition = "1=1"
            parameter = ()
            
            if multi_value_qp:
                parameter = parameter + tuple(
                    [[elm.lower() for elm in inner_list] for inner_list in multi_value_qp.values()])
                filter_field = 'AND '.join([f"LOWER({k})" + ' IN %s ' for k in multi_value_qp.keys()])
                condition = f"{condition} AND {filter_field}"

            if 'id' in multi_value_qp:
                id = multi_value_qp.pop('id')[0]
                query_result = gxp_db.get_query("app_module", get_columns, condition="id=%s", params=(id,))
            else:
                query_result = gxp_db.select_query("app_module", get_columns, condition=condition, params=parameter,
                                                   order_by=order_by, page_size=page_size, page_number=page_number)

        elif http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            module = request_body.get('module')
            is_super = request_body.get('is_super', False)
            is_delete = request_body.get('is_delete', False)
            
            existing_record = gxp_db.get_query("app_module", ["app", "module"], 
                                               condition="LOWER(module)=LOWER(%s)",
                                               params=(module, )).get("data")
            if existing_record:
                query_result["message"] = f"app {existing_record['app']} in {existing_record['module']} module already exists."
            else:
                request_body["id"] = str(uuid.uuid4())
                query_result = gxp_db.insert_query("app_module", request_body)

                if query_result['status']:
                    auth_permission_list = [
                        {
                            "id": str(uuid.uuid4()),
                            "module_id": request_body["id"],
                            "name": f"Can add {module}",
                            "codename": f"add_{module}",
                            "is_super": is_super,
                            "is_delete": is_delete
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "module_id": request_body["id"],
                            "name": f"Can change {module}",
                            "codename": f"change_{module}",
                            "is_super": is_super,
                            "is_delete": is_delete
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "module_id": request_body["id"],
                            "name": f"Can delete {module}",
                            "codename": f"delete_{module}",
                            "is_super": is_super,
                            "is_delete": is_delete
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "module_id": request_body["id"],
                            "name": f"Can view {module}",
                            "codename": f"view_{module}",
                            "is_super": is_super,
                            "is_delete": is_delete
                        }
                    ]
                    gxp_db.bulk_insert_query("app_permission", auth_permission_list)
                    query_result = gxp_db.get_query("app_module", "*", "id=%s", params=(request_body["id"],))
                    
        elif http_method == 'PATCH':
            app_module_id = event['pathParameters']['app_module_id']
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            module = request_body.get('module')
            
            existing_record = gxp_db.get_query("app_module", ["app", "module"], condition="LOWER(module)=LOWER(%s) AND id!=%s", 
                                               params=(module, app_module_id)).get("data")
            if existing_record:
                query_result["message"] = f"app {existing_record['app']} in {existing_record['module']} module already exists."
            else:
                query_result = gxp_db.update_query("app_module", request_body, condition="id=%s", params=(app_module_id,))
                if query_result['status']:
                    query_result = gxp_db.get_query("app_module", "*", condition="id=%s", params=(app_module_id,))

        elif http_method == 'DELETE':
            app_module_id = event['pathParameters']['app_module_id']
            app_permission_ids_query = gxp_db.select_query("app_permission", ["id"], condition="module_id=%s", params=(app_module_id,))
            app_permission_ids = [app_permission_id['id'] for app_permission_id in app_permission_ids_query.get('data', [])]

            gxp_db.delete_query("app_grouppermission", condition="permission_id IN %s", params=(tuple(app_permission_ids), ))
            gxp_db.delete_query("app_permission", condition="module_id=%s", params=(app_module_id,))
            query_result = gxp_db.delete_query("app_module", condition="id=%s", params=(app_module_id,))  

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
