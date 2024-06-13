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
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'svg': 'image/svg+xml',
            'heic': 'image/heic',
            'pdf': 'application/pdf',
            'csv': 'text/csv',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'mp3': 'audio/mpeg',
            'mp4': 'video/mp4',
            'wav': 'audio/x-wav',
            'ogg': 'audio/ogg'
        }
        
        # Retrieve the content type based on the file extension
        content_type = mime_types.get(file_extension.lower())
        if not content_type:
            print(f"Unknown file extension: {file_extension} for file key: {file_key}")
        
        return content_type
    
    
    def upload_s3_file(self, file_key, expires_in=None):
        file_key_parts = file_key.split("/")
        access_level = "public-read" if file_key_parts[0] not in ['user-profile', 'hotel'] else "private"
        
        file_key = self.generate_file_key(file_key)
        expires_in = expires_in or self.default_expires_in
        
        content_type = self.generate_content_type(file_key)
        if not content_type:
            # Default content type if file extension is unknown
            content_type = 'application/octet-stream'
        
        # Generate the pre-signed URL for uploading
        put_presign_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': self.bucket, 'Key': file_key, 'ContentType': content_type, 'ACL': 'private' if access_level == 'private' else 'public-read'},
            ExpiresIn=expires_in
        )
        
        if access_level == 'private':
            get_presign_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_key},
                ExpiresIn=expires_in
            )
        else:
            get_presign_url = f"https://{self.bucket}.s3.us-east-1.amazonaws.com/{self.location}/{file_key}"
        
        return {"put_presign_url": put_presign_url, "get_presign_url": get_presign_url}
    
    def get_s3_url(self, file_key, expires_in=None):
        file_key_parts = file_key.split("/")
        access_level = "public-read" if file_key_parts[0] not in ['user-profile', 'hotel'] else "private"
        
        file_key = self.generate_file_key(file_key)
        expires_in = expires_in or self.default_expires_in
        
        # Generate the pre-signed URL for downloading
        if access_level == 'private':
            get_presign_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_key},
                ExpiresIn=expires_in
            )
        else:
            get_presign_url = f"https://{self.bucket}.s3.us-east-1.amazonaws.com/{self.location}/{file_key}"
            
        return get_presign_url

    def get_s3_urls(self, file_keys, expires_in=None):
        expires_in = expires_in or self.default_expires_in
        
        urls = []
        for key in file_keys:   
            file_key_parts = file_key.split("/")
            access_level = "public-read" if file_key_parts[0] not in ['user-profile', 'hotel'] else "private"
        
            file_key = self.generate_file_key(key)
            
            if access_level == 'private':
                get_presign_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': file_key},
                    ExpiresIn=expires_in
                )
                urls.append(get_presign_url)
            
            else:
                get_presign_url = f"https://{self.bucket}.s3.us-east-1.amazonaws.com/{self.location}/{file_key}"
                urls.append(get_presign_url)
        
        return urls
    
    def delete_s3_file(self, file_key):
        file_key = self.generate_file_key(file_key)
        response = s3_client.delete_objects(Bucket=self.bucket, Delete={'Objects': [{'Key': file_key}]})
        return response
    
    def delete_s3_files(self, file_keys):
        objects = [{'Key': self.generate_file_key(key)} for key in file_keys]
        response = s3_client.delete_objects(Bucket=self.bucket, Delete={'Objects': objects})
        return response

    def list_s3_files(self, folder):
        prefix_path = f"{self.location}/{folder}"
        response = s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix_path)
        keys = [item['Key'] for item in response.get('Contents', [])]
        return keys
