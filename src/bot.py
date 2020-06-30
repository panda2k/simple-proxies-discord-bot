import discord
import logging
import os
import requests
import json
from datetime import datetime
import time
from hashlib import sha256
import hmac
from io import BytesIO
import re
import asyncio

TOKEN = os.getenv('SIMPLE_PROXIES_BOT_TOKEN')
PROXY_API_TOKEN = os.getenv('SIMPLE_PROXIES_API_KEY')
client = discord.Client()
api_url = 'https://api.simpleproxies.io/api/v1/'
command_prefix = '.'
bot_status_channel_id = 727293181841899541
member_join_log_id = 726876190882791594
admin_bot_commands_id = 727295549505798234
member_role_id = 723732422830850090
admin_id = 221682464291160067

@client.event
async def on_message(message):
    if message.author == client.user or message.content.startswith(command_prefix) == False:
        return

    response_message = 'Input a valid command'
    author_id = message.author.id
    message_arguments = re.compile('\s+').split(message.content)

    if message_arguments[0] == '.setbillingemail':
        response_message = set_billing_email(author_id, message_arguments[1])
    elif message_arguments[0] == '.bindip':
        response_message = bind_ip(author_id, message_arguments[1])
    elif message_arguments[0] == '.unbindip':
        response_message = unbind_ip(author_id, message_arguments[1])
    elif message_arguments[0] == '.overview':
        response_message = get_overview(author_id)
    elif message_arguments[0] == '.purchase':
        try:
            response_message = purchase_data(author_id, int(message_arguments[1]))
        except ValueError:
            response_message = "Input a valid integer as the data amount"
    elif message_arguments[0] == '.generate':
        try:
            response_message = generate_proxies(author_id, message_arguments[1], message_arguments[2], int(message_arguments[3]))
            await message.author.send(file=response_message)
            return
        except ValueError:
            response_message = "Input a valid integer as the proxy amount"
    elif message.channel.id == admin_bot_commands_id:
        if message_arguments[0] == '.status':
            if message_arguments[1] == 'True':
                status = True
            elif message_arguments[1] == 'False':
                status = False
            else:
                response_message = 'Input a valid status'
                await message.channel.send(response_message)
                return

            await delete_previous_message(bot_status_channel_id)
            await send_bot_status(status)
            await message.channel.send('Successfully changed status')
            return
        elif message_arguments[0] == '.purge':
            try:
                await purge_users(message_arguments[1])
            except KeyError:
                await purge_users()

    await message.author.send(response_message)

@client.event
async def on_member_join(member):
    channel = client.get_channel(member_join_log_id)
    await channel.send(str(member.id) + ' just joined.')

async def delete_previous_message(channel_id):
    channel = client.get_channel(channel_id)
    last_message = await channel.fetch_message(channel.last_message_id)
    await last_message.delete()

async def purge_users(users = None):
    database_members_response = requests.get(api_url + 'users/', headers = generate_headers())

    if users == None:
        discord_server_members = discord.Role(id = 723732422830850090).members # becomes the list of users to be kicked

        bot_command_channel = client.get_channel(admin_bot_commands_id)
        if database_members_response.status_code == 400:
            await bot_command_channel.send('Authentication error')
            return
        elif database_members_response.status_code == 500:
            await bot_command_channel.send('Error fetching users. Traceback: ' + database_members_response.text)
        
        database_members = json.loads(database_members_response.text) 
        for discord_member in discord_server_members:
            if discord_member.id in database_members:
                if database_members[discord_member.id]['data'] != 0:
                    discord_server_members.remove(discord_member)
    else: 
        #write later
        await bot_command_channel.send('Under development')
    
    await bot_command_channel.send(f'Finished processing users.\n{len(discord_server_members)} will be kicked.\n**LIST OF USERS TO BE KICKED**')
    for member in discord_server_members:
        await bot_command_channel.send(member.display_name + ':' + member.id)
    
    confirmation_message = await bot_command_channel.send('React to this message with :white_check_mark: to kick these users and react with :x: to cancel operation')
    await confirmation_message.add_reaction(':white_check_mark:')
    await confirmation_message.add_reaction(':x:')

    def check_reaction(reaction, user):
        if user == admin_id:
            if str(reaction.emoji) == ':white_check_mark:':
                return True
            elif str(reaction.emoji) == ':x:':
                return False
    
    try:
        execute_delete = await client.wait_for('reaction_add', timeout = 60.0, check = check_reaction)
    except asyncio.TimeoutError:
        await bot_command_channel.send('Command timed out. Rerun if needed')
    else:
        if execute_delete:
            await bot_command_channel.send('Executing purge')
        else:
            await bot_command_channel.send('Cancelling purge')

async def send_bot_status(bot_status):
    channel = client.get_channel(bot_status_channel_id)
    status_embed = discord.Embed(
        title = 'Simple Proxies Bot Status',
        description = "View this message to see if the bot is operational. Although the bot is online, it might be undergoing maintenance. If the bot is ever giving errors, check here to make sure the bot isn't under maintenance.", 
    )
    if bot_status == True:
        status_embed.description += "\n\n**BOT STATUS**: :white_check_mark:"
        status_embed.colour = int('5dcf48', 16)
    elif bot_status == False:
        status_embed.description += "\n\n**BOT STATUS**: :x:"
        status_embed.colour = int('cf4d48', 16)
    await channel.send(embed = status_embed)

def generate_proxies(author_id, proxy_type: str, region: str, proxy_count: int):
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
            return create_proxies_response.text.replace('"', '')
        else:
            return 'Authentication error. Contact admins'
    
    proxies = json.loads(create_proxies_response.text).strip('[]').replace(' ', '').replace('"', '').replace(',', '\n')
    proxy_file = BytesIO(proxies.encode())

    return discord.File(proxy_file, filename='Proxies.txt')

def purchase_data(author_id, data_amount: int):
    data = json.dumps({'data_amount': data_amount})
    send_invoice_response = requests.post(
        f'{api_url}users/{author_id}/sendinvoice/',
        data = data,
        headers = generate_headers(data)
    )
    if send_invoice_response.status_code == 404:
        return "You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`"
    elif send_invoice_response.status_code == 400:
        return "Input a valid amount of data. Must be an integer and above 0. Redo the `.purchase` command"
    elif send_invoice_response.status_code == 500:
        return "Error when generating stripe invoice. Contact admins"
    
    return "Check your billing email for a stripe invoice. Once the invoice is paid the data will be added to your account."


def set_billing_email(author_id, billing_email):
    data = json.dumps({'billing_email': billing_email})
    update_email_response = requests.put(
        f'{api_url}users/{author_id}/billingemail/', 
        data = data,
        headers = generate_headers(request_body = data)
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
            return'Error when creating user. Error code ' + str(create_user_response.status_code) + '. Please contact admins about this error'
    elif update_email_response.status_code == 400:
        return 'Please input a valid email. Retry the `.setbillingemail` command'
    elif update_email_response == 500:
        return 'Error when updating email. Contact admins about this'
    
    return 'Successfully updated billing email'

def unbind_ip(author_id, ip_address):
    data = json.dumps({'ip_address': ip_address})
    remove_ip_response = requests.delete(
        f'{api_url}users/{author_id}/ip/',
        data = data,
        headers = generate_headers(data)
    )
    if remove_ip_response.status_code == 404:
        return "You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`"
    elif remove_ip_response.status_code == 400:
        return "That IP address was not bound. No changes made"
    
    return 'Successfully unbound IP'

def bind_ip(author_id, ip_address):
    data = json.dumps({'ip_address': ip_address})
    update_ip_response = requests.post(
        f'{api_url}users/{author_id}/ip/',
        data = data,
        headers = generate_headers(data)
    )
    if update_ip_response.status_code == 404:
        return "You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`"
    elif update_ip_response.status_code == 400:
        return 'Please input a valid IP address. Make sure this is an IPV4 address. Retry the `.bindip` command'

    return 'Successfully bound IP'

def get_overview(author_id):
    user_info_response = requests.get(f'{api_url}users/{author_id}/', headers=generate_headers())
    if user_info_response.status_code == 404:
        return "You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`"
    elif user_info_response.status_code == 500:
        return 'Error fetching user. Please contact admins about this issue'
    
    user_info = json.loads(user_info_response.text)
    user_info_string = "```User Overview:\n" \
                        f"Billing Email: {user_info['billing_email']}\n" \
                        f"Bound IPs: {', '.join(user_info['binds'])}\n" \
                        f"Remaining Data: {user_info['data_string']}\n" 
    if user_info['data_expiry'] == "N/A":
        user_info_string += "Data Expiration: N/A ```"
    else:
        user_info_string += f'Data Expiration: {datetime.fromtimestamp(int(user_info["data_expiry"])).strftime("%Y-%m-%d")}```'

    return user_info_string

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

client.run(TOKEN)
