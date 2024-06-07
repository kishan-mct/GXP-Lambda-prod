import json

from utils.db_operations import DBOperations

def lambdaHealthCheck(event, context):
    status_code = 200
    query_result = {"status": True, "message": ""}
    http_method = event['httpMethod']

    if http_method == "GET":
        query_result["message"] = "function runing"
        
        pms_read_db = DBOperations("gxp-dev")
        query_result = pms_read_db.select_query("users_user", ["email", "user_type"])
        print("query_result", query_result)
        
    else:
        query_result["message"] = f'Unsupported HTTP method: {http_method}'
        status_code = 405

    return {
        'statusCode': status_code,
        'body': json.dumps(query_result),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }