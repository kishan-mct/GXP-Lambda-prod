import json

from utils.db_operations import DBOperations
pbx_db = DBOperations("pbx-prod")


def IsSuperAdmin(handler):
    def wrapper(event, context):
        user_data = json.loads(event['requestContext']['authorizer']['user_data'])
        user_type = user_data["user_type"]

        if user_type in ["super_admin", "gxp_admin"]:
            return handler(event, context)

        response_body = {
            "status": False,
            "message": "Sorry, you do not have access or authorization to perform this action."
        }
        response = {
            'statusCode': 401,
            'body': json.dumps(response_body),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        return response

    return wrapper

