import json
import sys
import jwt
import os

from utils.db_operations import DBOperations
from utils.common_functions import json_serializer


def JwtAuthorizer(event, context):
    try:
        access_token = event.get('authorizationToken') or event.get('authorizationtoken')

        if not access_token:
            raise ValueError("Access token missing")
            
        # Split the token
        token_parts = access_token.split()

        if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
            raise ValueError("Invalid token format")

        access_token = token_parts[1].strip()

        # Decode the JWT token
        user_data = jwt.decode(access_token, os.environ.get('JWT_SECRET'), algorithms=['HS256'])
        user_data_json = json.dumps(user_data, default=json_serializer)
        
        print("user_data_json", user_data_json)
        return allowPolicy(event['methodArn'], user_data_json)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print("JWT Exception", f"message: {exc_value}, error_line: {exc_traceback.tb_lineno}")

    return denyAllPolicy()


def denyAllPolicy():
    return {
        "principalId": "*",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "*",
                    "Effect": "Deny",
                    "Resource": "*"
                }
            ]
        },
    }


def allowPolicy(methodArn, user_data):
    return {
        "principalId": "apigateway.amazonaws.com",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": methodArn,
                }
            ]
        },
        "context": {
            "user_data": user_data  # Add the custom user data here
        }
    }
