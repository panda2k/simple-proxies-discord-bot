import discord
from discord.ext import commands
import logging
import os
import requests
import json

TOKEN = os.getenv('SIMPLE_PROXIES_BOT_TOKEN')
bot = commands.Bot(command_prefix='.')
api_url = '127.0.0.1:8000/api/v1/'

@bot.command(name='setbillingemail')
async def on_message(ctx, billing_email: str):
    author_id = ctx.message.author.id
    update_email_response = requests.put(
        f'{api_url}users/{author_id}/billing_email', 
        data = json.dumps({'billing_email': billing_email})
    )
    if update_email_response.status_code == 404:
        create_user_response = requests.post(
            api_url + 'users/',
            data = json.dumps({
                'discord_id': author_id,
                'billing_email': billing_email
            })
        )
        if create_user_response.status_code != 201:
            await ctx.message.author.send('Error when creating user. Error code ' + create_user_response.status_code + '. Please contact admins about this error')
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
    update_ip_response = requests.post(
        f'{api_url}users/{author_id}/billing_email',
        data = json.dumps({'ip_address': ip_address})
    )
    if update_ip_response.status_code == 404:
        ctx.message.author.send("You haven't registered in our database yet. Please register by setting a billing email with the command `.setbillingemail`")
        return
    elif update_ip_response.status_code == 400:
        ctx.message.author.send('Please input a valid IP address. Make sure this is an IPV4 address. Retry the `.bindip` command')
        return

    ctx.message.author.send('Successfully bound IP')



bot.run(TOKEN)
