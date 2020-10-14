# base packages
import os
import json
from io import BytesIO
import re
import asyncio

# installed packages
import discord
import requests

# custom packages
import simpleproxies

# configure packages
DISCORD_TOKEN = os.getenv('SIMPLE_PROXIES_BOT_TOKEN')
simpleproxies.API_KEY = os.getenv('SIMPLE_PROXIES_API_KEY')
simpleproxies.BASE_API_URL = 'https://api.simpleproxies.io/api/v1'

# static variables
COMMAND_PREFIX = '.'
BOT_STATUS_CHANNEL_ID = 727293181841899541
MEMBER_JOIN_LOG_ID = 726876190882791594
ADMIN_BOT_COMMANDS_ID = 727295549505798234
MEMBER_ROLE_ID = 723732422830850090
ADMIN_ID = 221682464291160067
SERVER_ID = 723013366037348412

client = discord.Client()

@client.event
async def on_message(message):
    if message.author == client.user or not message.content.startswith(COMMAND_PREFIX):
        return

    response_message = 'Input a valid command'
    author_id = message.author.id
    message_arguments = re.compile('\s+').split(message.content.strip()) # split by all white space

    if message_arguments[0] == '.setbillingemail':
        response_message = set_billing_email(author_id, billing_email = message_arguments[1])
    elif message_arguments[0] == '.overview':
        response_message = get_overview(author_id)
    elif message_arguments[0] == '.purchase':
        try:
            response_message = purchase_data(author_id, plan_name = message_arguments[1], data_amount = int(message_arguments[2]))
        except IndexError:
            response_message = 'You are missing some message arguments. The proper format is `.purchase proxy_plan data_amount`'
        except ValueError:
            response_message = "Input a valid integer as the data amount"
    elif message_arguments[0] == '.generate':
        try:
            response_message = generate_proxies(
                author_id = author_id, 
                proxy_pool = message_arguments[1], 
                proxy_type = message_arguments[2], 
                region = message_arguments[3], 
                proxy_count = int(message_arguments[4])
            )
            try:
                await message.author.send(file=response_message)
            except discord.errors.InvalidArgument:
                await message.author.send(response_message)
            finally:
                return
        except IndexError:
            response_message = 'You are missing some message arguments. The proper format is `.generate proxy_pool proxy_type, region, proxy_count`'
        except ValueError:
            response_message = "Input a valid integer as the proxy amount. The proper format is `.generate proxy_pool proxy_type, region, proxy_count`"
    elif message.channel.id == ADMIN_BOT_COMMANDS_ID:
        if message_arguments[0] == '.purge':
            try:
                await purge_users(users = message_arguments[1])
            except IndexError:
                await purge_users()
            return

    await message.author.send(response_message)

# USER COMMANDS
def generate_proxies(author_id: int, proxy_pool: str, proxy_type: str, region: str, proxy_count: int):
    create_proxies_response = simpleproxies.generate_proxies(author_id, proxy_pool, proxy_type, region, proxy_count)
    
    if create_proxies_response.status_code != 200:
        return process_bad_response(create_proxies_response)

    proxies = '\n'.join(json.loads(create_proxies_response.text)['proxies'])
    proxy_file = BytesIO(proxies.encode())

    return discord.File(proxy_file, filename='Proxies.txt')

def purchase_data(author_id: int, plan_name: str, data_amount: int):
    send_invoice_response = simpleproxies.email_invoice(author_id, data_amount, plan_name)
    if send_invoice_response.status_code != 200:
        return process_bad_response(send_invoice_response)
    
    return "Check your billing email for a stripe invoice. Once the invoice is paid the data will be added to your account."


def set_billing_email(author_id: int, billing_email: str):
    update_email_response = simpleproxies.set_billing_email(author_id, billing_email)
    if update_email_response.status_code == 404:
        create_user_response = simpleproxies.create_user(author_id, billing_email)

        if create_user_response.status_code != 200:
            return process_bad_response(create_user_response)
    elif update_email_response.status_code == 502:
        return '502 bad gateway. This normally means the billing email you inputted is invalid. If this issue persists, contact admins'
    elif update_email_response.status_code != 200:
        return process_bad_response(update_email_response)
    
    return 'Successfully updated billing email'

def get_overview(author_id: int):
    user_info_response = simpleproxies.get_user_overview(author_id)
    if user_info_response.status_code != 200:
        return process_bad_response(user_info_response)
    
    user_info = json.loads(user_info_response.text)
    user_info_string = "```User Overview:\n" \
                        f"Billing Email: {user_info['billing_email']}\n\n" \
                        f"Star Plan Info\n" \
                        f"Data Remaining: {user_info['oxylabs_data_string']}\n" \
                        "Expiry Date: STAR_EXPIRY```"

    if user_info['oxylabs_data_expiry']:
        user_info_string = user_info_string.replace('STAR_EXPIRY', user_info['oxylabs_data_expiry'])
    else:
        user_info_string.replace('STAR_EXPIRY', 'N/A')

    return user_info_string

# ADMIN METHODS TODO FIX PURGE USERS
@client.event
async def on_ready():
    print('Bot started')

@client.event
async def on_member_join(member):
    channel = client.get_channel(MEMBER_JOIN_LOG_ID)
    await channel.send(str(member.id) + ' just joined.')

async def purge_users(users = None): # TODO fix
    inactive_members = []
    bot_command_channel = client.get_channel(ADMIN_BOT_COMMANDS_ID)

    database_members_response = requests.get(api_url + 'users/', headers = generate_headers())
    if database_members_response.status_code == 401:
        await bot_command_channel.send('Authentication error')
        return
    elif database_members_response.status_code == 500:
        await bot_command_channel.send('Error fetching users. Traceback: ' + database_members_response.text)
        return
    elif database_members_response.status_code != 200:
        await bot_command_channel.send('Unknown error. ' + database_members_response.text)
        return

    database_members = json.loads(database_members_response.text) 

    if users == None:
        discord_server_members = client.get_guild(id = SERVER_ID).get_role(role_id = MEMBER_ROLE_ID).members 
    else:
        discord_server_members = []
        users_list = users.split(',') 
        for user in users_list:
            server_member = client.get_user(user)
            if server_member != None:
                discord_server_members.append(client.get_user(user))
    
    # process users
    for discord_member in discord_server_members:
        if str(discord_member.id) in database_members:
            if database_members[str(discord_member.id)]['data'] == "0":
                inactive_members.append(discord_member)
        else:
            inactive_members.append(discord_member)
    for discord_id in database_members['error_users']:
        await bot_command_channel.send(f'Failed to fetch {discord_id}')
    await bot_command_channel.send(f'Finished processing users.\n{len(inactive_members)} will be kicked.\n**LIST OF USERS TO BE KICKED**')
    for member in inactive_members:
        await bot_command_channel.send(member.display_name + ':' + str(member.id))
    
    confirmation_message = await bot_command_channel.send('React to this message with :white_check_mark: to kick these users and react with :x: to cancel operation')
    await confirmation_message.add_reaction('\U00002705')
    await confirmation_message.add_reaction('\U0000274C')

    try:
        reaction, user = await client.wait_for('reaction_add', 
                                                timeout = 60.0, 
                                                check = lambda reaction, user: (str(reaction.emoji) == '\U00002705' or str(reaction.emoji) == '\U0000274C') and user.id != client.user.id)
    except asyncio.TimeoutError:
        await bot_command_channel.send('Command timed out. Rerun if needed')
    else:
        confirmation_message = await bot_command_channel.fetch_message(id = confirmation_message.id)
        for reaction in confirmation_message.reactions:
            if reaction.count > 1:
                if str(reaction.emoji) == '\U00002705':
                    await bot_command_channel.send('Executing purge')
                    for member in inactive_members:
                        delete_member_response = requests.delete(f'{api_url}users/{str(member.id)}/', headers= generate_headers())
                        if delete_member_response.status_code == 401:
                            await bot_command_channel.send('Failed to authenticate to delete ' + str(member.id))
                        elif delete_member_response.status_code == 500:
                            await bot_command_channel.send('Failed to delete ' + str(member.id) + f'\n{delete_member_response.text}')
                        elif delete_member_response.status_code == 200 or delete_member_response.status_code == 404:
                            await member.send("You are being kicked from the Simple Proxies Discord server because you don't have an active plan. If you think this was done incorrectly, DM panda2k#5856. The purge isn't super strict so if you forgot to buy a plan, DM panda2k#5856")  
                            await member.kick()
                            await bot_command_channel.send('Finished kicking and removing ' + str(member.id) + ' from the server and database.')   
                        else:
                            await bot_command_channel.send('Unknown response. Code: ' + str(delete_member_response.status_code))                       
                elif str(reaction.emoji) == '\U0000274C':
                    await bot_command_channel.send('Cancelling purge')

# HELPER FUNCTIONS
def process_bad_response(response):
    print(response.status_code)
    if response.status_code == 400:
        return 'Error code 400. {}'.format(response.text)
    elif response.status_code == 401:
        return 'Authentication error. Contact admins'
    elif response.status_code == 404:
        return 'No user account found. Please set your billing email with .setbillingemail'
    elif response.status_code == 500:
        return 'Fatal error. Contact admins'
    elif response.status_code == 502:
        return 'Bad gateway. Try again. If issue persists, contact admins'

client.run(DISCORD_TOKEN)
