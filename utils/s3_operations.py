import boto3

s3_client = boto3.client('s3')

class S3Operations:
    def __init__(self, bucket="devgxp", location="dev", default_expires_in=3600):
        self.bucket = bucket
        self.location = location
        self.default_expires_in = default_expires_in

    def generate_file_key(self, file_key):
        return f"{self.location}/{file_key}"

    def generate_content_type(self, file_key):
        # Extract the file extension from the file key
        file_extension = file_key.split('.')[-1]
        
        # Dictionary mapping file extensions to MIME types
        mime_types = {
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "png": "image/png",
            # Add more mappings as needed
        }
        
        # Retrieve the content type based on the file extension
        content_type = mime_types.get(file_extension.lower())
        if not content_type:
            print(f"Unknown file extension: {file_extension} for file key: {file_key}")
        
        return content_type
    
    
    def upload_file(self, file_key, access_level='private', expires_in=None):
        file_key = self.generate_file_key(file_key)
        expires_in = expires_in or self.default_expires_in
        
        content_type = self.generate_content_type(file_key)
        if not content_type:
            # Default content type if file extension is unknown
            content_type = 'application/octet-stream'
        
        # Generate the pre-signed URL for uploading
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': self.bucket, 'Key': file_key, 'ContentType': content_type},
            ExpiresIn=expires_in
        )
        
        # If access level is public, make the object public
        if access_level == 'public':
            s3_client.put_object_acl(Bucket=self.bucket, Key=file_key, ACL='public-read')
        
        return upload_url

    def get_files(self, file_key, expires_in=None):
        file_key = self.generate_file_key(file_key)
        expires_in = expires_in or self.default_expires_in
        
        # Generate the pre-signed URL for downloading
        get_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': file_key},
            ExpiresIn=expires_in
        )
        
        return get_url

    def get_presigned_urls(self, keys, expires_in=None):
        expires_in = expires_in or self.default_expires_in
        
        urls = []
        for key in keys:
            file_key = self.generate_file_key(key)
            get_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_key},
                ExpiresIn=expires_in
            )
            urls.append(get_url)
        
        return urls
    
    def public_access_level_urls(self,file_key):
        base_url = "https://devgxp.s3.amazonaws.com/dev/"
        if file_key and not file_key.startswith("http"):
            return f"{base_url}{file_key}"
        return None
    
    def list_files(self):
        response = s3_client.list_objects_v2(Bucket=self.bucket, Prefix=self.location)
        keys = [item['Key'] for item in response.get('Contents', [])]
        return keys

    def delete_files(self, keys):
        objects = [{'Key': self.generate_file_key(key)} for key in keys]
        response = s3_client.delete_objects(Bucket=self.bucket, Delete={'Objects': objects})
        return response

    def delete_file(self, key):
        response = s3_client.delete_objects(Bucket=self.bucket, Delete={'Objects': [{'Key': key}]})
        return response
