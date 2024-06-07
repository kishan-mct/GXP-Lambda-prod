import base64
import logging
import random
import requests
import re
import json
import jinja2
import string
import xml.dom.minidom
import os

from datetime import date, datetime, time
from decimal import Decimal


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_random_number(length):
    return ''.join(random.choice(string.digits) for _ in range(length))

def decrypt_data(encoded_data):
    try:
        return json.loads(base64.b64decode(encoded_data).decode('utf-8'))
    
    except (ValueError, TypeError, Exception) as e:
        # Handle specific decryption errors
        logging.error("Error decrypting data: %s", e)
        raise Exception("Error decrypting data: " + str(e))

    
def json_serializer(obj):
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')  # Assuming utf-8 encoding for bytes
    raise TypeError(f"Type {type(obj)} is not serializable")


# Recursive JSON serializer that handles circular references
def recursive_json_serializer(obj):
    serialized = set()

    def serializer(obj):
        if id(obj) in serialized:
            raise ValueError("Circular reference detected")

        serialized.add(id(obj))

        return json_serializer(obj)

    return json.dumps(obj, default=serializer)


def convert_empty_strings_to_none(data):
    if isinstance(data, list):
        return [convert_empty_strings_to_none(item) for item in data]
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and value.strip() == "":
                data[key] = None
            elif isinstance(value, dict) or isinstance(value, list):
                convert_empty_strings_to_none(value)
    else:
        if data == "null":
            data = None
    return data


def string_convert_to_list(value):
    # Check if the string is empty
    if value == "{}":
        return []
    # Remove the curly braces and split by comma
    return value.strip('{}').split(',')


def read_template_file(template_path):
    with open(template_path, 'r', encoding='utf-8') as file:
        return file.read()

# Tempalte render
def render_jinja_template(template_name, context):
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    template_path = os.path.join(template_dir, template_name)
    
    template_content = read_template_file(template_path)
    # Render template with context
    template = jinja2.Template(template_content)
    rendered_email_msg = template.render(context)
    
    return rendered_email_msg



# Send the email wia Smtp2go service APIs
def send_mail_wia_smtp2go(to_mail_address_lst, reply_to, mail_subject, mail_html):
    smtp_send_mail_dict = {
        "api_key": "api-F17A02F4102911EE8098F23C91C88F4E",
        "to": to_mail_address_lst,
        "sender": reply_to,
        "subject": mail_subject,
        "html_body": mail_html,
        "custom_headers": [
            {
                "header": "Reply-To",
                "value": reply_to
            }
        ]
    }

    send_mail = requests.post("https://api.smtp2go.com/v3/email/send", json=smtp_send_mail_dict)
    return send_mail.json()


# Kaushik Testing SMS Chat - 16505824777 - Off
# Kaushik Patel - 16506007010
# Vinay Jivani - 16506803180
# Hotel Golden Crown - 16506007873
# OwnAI Test SMS Number - 16504147461
# Vipul Patel - 16503342969

# Send the sms wia BULK SOLUTION (BVS) service APIs
def send_msg_wia_bulk_vs_sms(from_number, to_number, message_text, message_media_urls=[]):
    msg_body = {"From": from_number, "To": to_number}

    if message_text:
        msg_body['Message'] = message_text

    if message_media_urls:
        msg_body['MediaURLs'] = message_media_urls

    auth_headers = {"Authorization": "Basic dnBhdGVsQG1hY3JvdGVjaC5uZXQ6MGUzMTMxZWM2NjU0NTA1YjEzOTAzNzkzNjYwYjI0MWQ="}
    _sms_request = requests.post("https://portal.bulkvs.com/api/v1.0/messageSend", json=msg_body, headers=auth_headers)
    if _sms_request.status_code == 200:
        return {"status": True, "bulk_vs_sms": _sms_request.json()}

    return {"status": False, "bulk_vs_sms": _sms_request.text}
