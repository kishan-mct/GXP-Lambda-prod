import json
import uuid
from utils.s3_operations import S3Operations
from utils.common_functions import json_serializer, convert_empty_strings_to_none


def s3MediaHandler(event, context):
    response_body = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    hotel_id = user_data.get("hotel_id")

    try:
        s3_operations = S3Operations()

        if http_method == 'POST':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            media_type = request_body.get('media_type')
            file_type = request_body.get('file_type')

            if not media_type or not file_type:
                raise ValueError("Media type and file type are required")

            media_type_list = ["user-profile", "brand-logo", "brand-favicon", "hotel-logo", "hotel-favicon",
                               "hotel-info", "building", "floor", "room-type", "local-event", "nearby-place",
                               "tv-channel", "guest-doc", "guest-selfie", "guest-face", "booking-excl", "addon-item"]
 

            if media_type not in media_type_list:
                raise ValueError("Invalid media type")


            if media_type in ["user-profile", "brand-logo", "brand-favicon", "hotel-logo", "hotel-favicon"]:
                file_key = f"{media_type}/{uuid.uuid4()}.{file_type}"
            else:
                if not hotel_id:
                    raise ValueError("Hotel ID is required for hotel-related media types")
                file_key = f"hotel/{hotel_id}/{media_type}/{uuid.uuid4()}.{file_type}"

            s3_urls = s3_operations.upload_s3_file(file_key)

            if s3_urls['put_presign_url']:
                response_body["status"] = True
                database_url = '/'.join(s3_urls['put_presign_url'].split('?')[0].split('/')[4:])
                response_body["data"] = {"put_presign_url": s3_urls['put_presign_url'], "get_presign_url": s3_urls['get_presign_url'], "database_url": database_url}
            else:
                response_body["message"] = "Failed to generate presign URL"

        elif http_method == 'DELETE':
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            file_keys = request_body.get('file_keys')

            if not file_keys:
                raise ValueError("File keys are required for deletion")

            s3_response = s3_operations.delete_s3_files(file_keys)

            if s3_response:
                response_body["status"] = True
                response_body["message"] = "Files deleted successfully"
            else:
                response_body["message"] = "Failed to delete files"

    except ValueError as e:
        response_body["message"] = str(e)
    except Exception as e:
        print("ERROR:", str(e))
        response_body["message"] = "An error occurred"
    finally:
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, default=json_serializer),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
