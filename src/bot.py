import discord
from discord.ext import commands
import logging
import os
import requests
import json
from datetime import datetime
import time
from hashlib import sha256
import hmac
from io import BytesIO

TOKEN = os.getenv('SIMPLE_PROXIES_BOT_TOKEN')
PROXY_API_TOKEN = os.getenv('SIMPLE_PROXIES_API_KEY')
bot = commands.Bot(command_prefix='.')
api_url = 'http://127.0.0.1:8000/api/v1/'

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

@bot.command(name='setbillingemail')
async def on_message(ctx, billing_email: str):
    author_id = ctx.message.author.id
    update_email_response = requests.put(
        f'{api_url}users/{author_id}/billing_email/', 
        data = json.dumps({'billing_email': billing_email})
    )
    if update_email_response.status_code == 404:
        data = json.dumps({
                'discord_id': author_id,
                'billing_email': billing_email
            })
        create_user_response = requests.post(
            api_url + 'users/',
            data = data,
            headers = generate_headers(data)
        )
        if create_user_response.status_code != 201:
            await ctx.message.author.send('Error when creating user. Error code ' + str(create_user_response.status_code) + '. Please contact admins about this error')
            return
    elif update_email_response.status_code == 400:
        await ctx.message.author.send('Please input a valid email. Retry the `.setbillingemail` command')
        return
    elif update_email_response == 500:
        await ctx.message.author.send('Error when updating email. Contact admins about this')
        return
    
    await ctx.message.author.send('Successfully updated billing email')


@bot.command(name='bindip')
async def on_message(ctx, ip_address: str):
    author_id = ctx.message.author.id
    data = json.dumps({'ip_address': ip_address})
    update_ip_response = requests.post(
        f'{api_url}users/{author_id}/ip/',
        data = data,
        headers = generate_headers(data)
    )
    if update_ip_response.status_code == 404:
        await ctx.message.author.send("You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`")
        return
    elif update_ip_response.status_code == 400:
        await ctx.message.author.send('Please input a valid IP address. Make sure this is an IPV4 address. Retry the `.bindip` command')
        return

    await ctx.message.author.send('Successfully bound IP')

@bot.command(name='overview')
async def on_message(ctx):
    author_id = ctx.message.author.id
    user_info_response = requests.get(f'{api_url}users/{author_id}/', headers=generate_headers())
    if user_info_response.status_code == 404:
        await ctx.message.author.send("You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`")
        return
    elif user_info_response.status_code == 500:
        await ctx.message.author.send('Error fetching user. Please contact admins about this issue')
        return
    
    user_info = json.loads(user_info_response.text)
    user_info_string = "```User Overview:\n" \
                        f"Billing Email: {user_info['billing_email']}\n" \
                        f"Bound IPs: {', '.join(user_info['binds'])}\n" \
                        f"Remaining Data: {user_info['data_string']}\n" 
    if user_info['data_expiry'] == "N/A":
        user_info_string += "Data Expiration: N/A ```"
    else:
        user_info_string += f'Data Expiration: {datetime.fromtimestamp(int(user_info["data_expiry"])).strftime("%Y-%m-%d")}```'

    await ctx.message.author.send(user_info_string)

@bot.command(name='purchase')
async def on_message(ctx, data_amount: int):
    author_id = ctx.message.author.id
    data = json.dumps({'data_amount': data_amount})
    send_invoice_response = requests.post(
        f'{api_url}users/{author_id}/sendinvoice/',
        data = data,
        headers = generate_headers(data)
    )
    if send_invoice_response.status_code == 404:
        await ctx.message.author.send("You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`")
        return
    elif send_invoice_response.status_code == 400:
        await ctx.message.author.send("Input a valid amount of data. Must be an integer and above 0. Redo the `.purchase` command")
        return
    elif send_invoice_response.status_code == 500:
        await ctx.message.author.send("Error when generating stripe invoice. Contact admins")
        return
    
    await ctx.message.author.send("Check your billing email for a stripe invoice. Once the invoice is paid the data will be added to your account.")

@bot.command(name='generate')
async def on_message(ctx, proxy_type: str, region: str, proxy_count: int):
    author_id = ctx.message.author.id
    data = json.dumps({
        'region': region.lower(),
        'type': proxy_type.lower(),
        'proxy_count': proxy_count
    })
    create_proxies_response = requests.post(
        f'{api_url}proxies/generate/',
        data = data,
        headers = generate_headers(data)
    )
    if create_proxies_response.status_code == 400:
        if create_proxies_response.text != '':
            await ctx.message.author.send(create_proxies_response.text.replace('"', ''))
        else:
            await ctx.message.author.send('Authentication error. Contact admins')
        return
    
    proxies = json.loads(create_proxies_response.text).strip('[]').replace(' ', '').replace('"', '').replace(',', '\n')
    proxy_file = BytesIO(proxies.encode())

    await ctx.message.author.send(file = discord.File(proxy_file, filename='Proxies.txt'))

bot.run(TOKEN)
