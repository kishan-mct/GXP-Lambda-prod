import json


def IsSuperAdmin(handler):
    def wrapper(event, context):
        user_data = json.loads(event['requestContext']['authorizer']['user_data'])
        user_type = user_data["user_type"]

        if user_type == "super_admin":
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
