import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from botocore.exceptions import ClientError
from urllib.parse import urlparse, urlunparse

def generate_presigned_url(bucket_name, object_name, content_type=None, expiration=180, operation=None):
    s3_client = boto3.client('s3')
    try:
        if operation == 'put_object':
            response = s3_client.generate_presigned_url('put_object',
                                                        Params={'Bucket': bucket_name,
                                                            'Key': object_name,
                                                            'ContentType': content_type},
                                                        ExpiresIn=expiration)
        elif operation == 'get_object':
            response = s3_client.generate_presigned_url('get_object',
                                                        Params={'Bucket': bucket_name,
                                                                'Key': object_name
                                                                },
                                                        ExpiresIn=expiration)
        else:
            raise ValueError("Invalid operation. Use 'put_object' or 'get_object'.")
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        print(f"Error generating presigned URL: {str(e)}")
        return None

    return response


def remove_query_params(url):
    parsed_url = urlparse(url)
    url_without_params = urlunparse(parsed_url._replace(query=""))
    return url_without_params
