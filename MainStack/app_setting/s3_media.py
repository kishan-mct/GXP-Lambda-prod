import json
import uuid
from utils.s3_operations import S3Operations
from utils.common_functions import json_serializer, convert_empty_strings_to_none

def s3MediaHandler(event, context):
    # Initialize response structure
    response_body = {"status": False, "message": ""}
    http_method = event['httpMethod']
    user_data = json.loads(event['requestContext']['authorizer']['user_data'])
    hotel_id = user_data.get("hotel_id", None)

    try:
        if http_method == 'POST':
            s3_operations = S3Operations()
            access_level = 'public'
            
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            media_type = request_body.get('media_type')
            file_type = request_body.get('file_type')

            if not media_type or not file_type:
                raise ValueError("Media type and file type are required")

            file_key = ""
            if media_type == "user_profile":
                access_level = 'private'
                file_key = f"user-profile/{user_data['user_id']}.{file_type}"
            elif media_type == "brand_logo":
                file_key = f"brand/logo/{uuid.uuid4()}.{file_type}"
            elif media_type == "brand_favicon":
                file_key = f"brand/favicon/{uuid.uuid4()}.{file_type}"
            elif media_type == "hotel_logo":
                file_key = f"hotel/logo/{uuid.uuid4()}.{file_type}"
            elif media_type == "hotel_favicon":
                file_key = f"hotel/favicon/{uuid.uuid4()}.{file_type}"
            elif media_type in ["hotel_info", "building", "floor", "room_type", "local_event", "nearby_place", "tv_channel", "guest_doc", "guest_selfie",
                                "guest_face", "booking_excel", "addon_item"]:
                if not hotel_id:
                    raise ValueError("Hotel ID is required for hotel-related media types")
                media_paths = {
                    "hotel_info": "info-place",
                    "building": "building",
                    "floor": "floor",
                    "room_type": "room-type",
                    "local_event": "local-event",
                    "nearby_place": "nearby-place",
                    "tv_channel": "tv-channel",
                    "guest_doc": "guest-doc",
                    "guest_selfie": "guest-selfie",
                    "guest_face": "guest-face",
                    "booking_excel": "booking-excl",
                    "addon_item": "addon-item"
                }
                file_key = f"hotel/{hotel_id}/{media_paths[media_type]}/{uuid.uuid4()}.{file_type}"

            presign_url = s3_operations.upload_file(file_key, access_level)
            
            if presign_url:
                # Remove the query parameters part
                url_without_query = presign_url.split('?')[0]

                # Split the URL by '/'
                parts = url_without_query.split('/')

                # Join the relevant parts to form the desired string
                database_url = '/'.join(parts[4:])

                response_body["status"] = True
                response_body["data"] = {"presign_url": presign_url, "database_url": database_url}
            else:
                response_body["message"] = "Failed to generate presign URL"

        elif http_method == 'DELETE':
            s3_operations = S3Operations()
            request_body = convert_empty_strings_to_none(json.loads(event['body']))
            file_keys = request_body.get('file_keys', [])
            if not file_keys:
                raise ValueError("File keys are required for deletion")

            s3_response = s3_operations.delete_files(file_keys)
            if s3_response:
                response_body["status"] = True
                response_body["message"] = "Files deleted successfully"
            else:
                response_body["message"] = "Failed to delete files"
            
    except Exception as e:
        print("ERROR:", str(e))
        response_body["message"] = str(e)
    finally:
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, default=json_serializer),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }   
