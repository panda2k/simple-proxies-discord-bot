import requests
import os
import json
import hmac
from hashlib import sha256
import time

PROXY_API_TOKEN = os.getenv('SIMPLE_PROXIES_API_KEY')
api_url = 'https://api.simpleproxies.io/api/v1/users/data/'
webhook_url = 'https://discordapp.com/api/webhooks/724819468550930482/Sffa_BlE23ZHtf-I3SqSQ7u-9B44o1bqWHBUAaFNYFgLQ_wpEc-7GN_zc5-zGKlJkeJE'
user_id = '221682464291160067'

def send_to_webhook(message): 
    data = json.dumps({
        'content': message,
        'username': 'Data Alert Bot',
        'avatar_url': 'https://rb.gy/tkh0ob',
    })
    webhook_response = requests.post(webhook_url, data = data, headers={'Content-Type': 'application/json'})

def generate_headers(request_body = None):
    timestamp = int(time.time())
    if request_body == None:
        signature = hmac.new(
            PROXY_API_TOKEN.encode('utf-8'), 
            msg = str(timestamp).encode('utf-8'), 
            digestmod = sha256
        ).hexdigest()
    else:     
        signature = hmac.new(
            PROXY_API_TOKEN.encode('utf-8'), 
            msg = ("%d.%s" % (timestamp, request_body)).encode('utf-8'), 
            digestmod = sha256
        ).hexdigest()
    
    return {'timestamp': str(timestamp), 'signature': signature, 'Content-Type': 'application/json',}

def main():
    data_response = requests.get(api_url, headers = generate_headers())
    if data_response.status_code != 200:
        send_to_webhook(f'Bad response. <@{user_id}>')
        return
    
    data = str(round(json.loads(data_response.text)['total_data'] / 1000000000, 2))
    send_to_webhook(f'Make sure you have {data}GBs of data available. <@{user_id}>')

if __name__ == "__main__":
    while True:
        main()
        time.sleep(21600)

