import base64
import requests


class EmqxApiOpration:
    def __init__(self):
        self.base_url = f"https://ge8ced57.emqx.cloud:8443/api"        
        credentials = "ya01cb32:s11d18a291ee1b5c"
        credentials_base64 = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        self.headers = {"Authorization": f"basic {credentials_base64}"}


    def execute_api(self, method, endpoint, payload={}, query_param={}):
        api_endpoint = f"{self.base_url}/{endpoint}"

        try:
            # Define the HTTP methods and their corresponding requests functions
            http_methods = {
                "GET": requests.get,
                "POST": requests.post,
                "PATCH": requests.patch,
                "DELETE": requests.delete
            }

            # Check if the method is valid
            if method not in http_methods:
                return {"status": False, "error_message": "Invalid HTTP method"}

            # Make the request using the appropriate method
            # print("api_endpoint", api_endpoint)
            # print("query_param", query_param)
            # print("payload", payload)
            
            response = http_methods[method](api_endpoint, params=query_param, json=payload, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return {"status": True, "response_data": response.json()}
            else:
                error_message = response.json()
                print("error_message", error_message)
                return {"status": False, "response_data": error_message["error"]}
        except Exception as e:
            return {"status": False, "response_data": str(e)}


    def get_active_cliets(self, query_param={}):
        endpoint = f"clients"
        print("query_param", query_param)
        return self.execute_api("GET", endpoint, query_param)


    def create_user(self, username, password):
        endpoint = "auth_username"
        payload = {
            "username": username,
            "password": password,
        }
        return self.execute_api("POST", endpoint, payload)
    
    
    def delete_user(self, username):
        endpoint = f"auth_username/{username}"
        return self.execute_api("DELETE", endpoint)
    
    
    def publish_message(self, payload):
        endpoint = f"mqtt/publish/"
        return self.execute_api("POST", endpoint, payload)
