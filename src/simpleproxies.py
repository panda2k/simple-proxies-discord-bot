import requests 
import time
import random
import string
from hashlib import sha256
import hmac
import json

BASE_API_URL = 'http://127.0.0.1:8000/api/v1'
API_KEY = None

def create_user(discord_id: str, billing_email: str):
    data = {
        'discord_id': discord_id,
        'billing_email': billing_email
    }
    
    headers = generate_headers(API_KEY, request_body = data)


    create_user_response = requests.post(
        BASE_API_URL + '/users/',
        json = data,
        headers = headers
    )        

    return create_user_response

def set_billing_email(discord_id: str, billing_email: str):
    data = {
        'billing_email': billing_email
    }

    headers = generate_headers(API_KEY, request_body = data)

    update_billing_address_response = requests.put(
        f'{BASE_API_URL}/users/{discord_id}/billingemail/',
        json = data,
        headers = headers
    )

    return update_billing_address_response

def bind_ip(discord_id: str, ip_address: str):
    data = {
        'ip_address': ip_address
    }

    headers = generate_headers(API_KEY, request_body = data)

    bind_ip_response = requests.post(
        f'{BASE_API_URL}/users/{discord_id}/ip/',
        json = data,
        headers = headers
    )
    
    return bind_ip_response

def unbind_ip(discord_id: str, ip_address: str):
    data = {
        'ip_address': ip_address
    }

    headers = generate_headers(API_KEY, request_body = data)

    bind_ip_response = requests.delete(
        f'{BASE_API_URL}/users/{discord_id}/ip/',
        json = data,
        headers = headers
    )
    
    return bind_ip_response    

def get_user_overview(discord_id: str):
    headers = generate_headers(API_KEY)

    user_info_response = requests.get(
        f'{BASE_API_URL}/users/{discord_id}/',
        headers = headers
    )
    
    return user_info_response

def email_invoice(discord_id: str, data_amount: int, plan_name: str):
    data = {
        'data_amount': data_amount,
        'delivery_method': 'mail',
        'plan_name': plan_name
    }

    headers = generate_headers(API_KEY, request_body = data)


    send_invoice_response = requests.post(
        f'{BASE_API_URL}/users/{discord_id}/invoice/',
        json = data,
        headers = headers
    )

    return send_invoice_response        

def generate_stripe_session(discord_id: str, data_amount: int, plan_name: str):
    data = {
        'data_amount': data_amount,
        'delivery_method': 'web',
        'plan_name': plan_name
    }

    headers = generate_headers(API_KEY, request_body = data)

    generate_session_response = requests.post(
        f'{BASE_API_URL}/users/{discord_id}/invoice/',
        json = data,
        headers = headers
    )

    return generate_session_response

def generate_proxies(discord_id: str, proxy_pool: str, proxy_type: str, proxy_region: str, proxy_count: int):
    data = {
        'region': proxy_region.lower(),
        'type': proxy_type.lower(),
        'proxy_count': proxy_count,
        'proxy_pool': proxy_pool,
        'discord_id': discord_id
    }

    headers = generate_headers(API_KEY, request_body = data)

    create_proxies_response = requests.post(
        f'{BASE_API_URL}/proxies/generate/',
        json = data,
        headers = headers
    )
    
    return create_proxies_response
def delete_user(discord_id: str):
    headers = generate_headers(API_KEY)


    delete_user_response = requests.delete(
        f'{BASE_API_URL}/users/{discord_id}/', 
        headers = headers
    )

    return delete_user_response

def get_all_users(key = None):
    headers = generate_headers(API_KEY)

    get_users_response = requests.get(
        f'{BASE_API_URL}/users/',
        headers = headers
    )
    return get_users_response

def get_total_data(key = None):
    headers = generate_headers(API_KEY)
    
    data_response = requests.get(
        f'{BASE_API_URL}/users/data/',
        headers = headers
    )

    return data_response

def generate_headers(api_token, request_body = None):
    timestamp = int(time.time())
    if request_body == None:
        signature = hmac.new(
            api_token.encode('utf-8'), 
            msg = str(timestamp).encode('utf-8'), 
            digestmod = sha256
        ).hexdigest()
    else:     
        signature = hmac.new(
            api_token.encode('utf-8'), 
            msg = ("{}.{}".format(timestamp, json.dumps(request_body))).encode('utf-8'), 
            digestmod = sha256
        ).hexdigest()
    return {'timestamp': str(timestamp), 'signature': signature, 'Content-Type': 'application/json',}
