import os
from datetime import datetime, timedelta, timezone
from threading import Timer
from typing import Dict, List

import dotenv
import discord
import dateparser
import pytz
from discord.ext import commands

from . import utils

MAX_DURATION = 7776000
# load environment variables from .env file
dotenv.load_dotenv('.env')

TOKEN = os.getenv('DISCORD_TOKEN')

# initialize discord bot
bot = commands.Bot(command_prefix='.')

# dictionary mapping event names to their timers
timers: Dict[str, utils.BotTimer] = {}


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    activity = discord.Game(name='.help')
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.command(name='schedule')
async def schedule(ctx: commands.Context, event_name: str,  start_time: str, *participants: discord.User):
    """
    Add event to queue, mentioning the participants once the given date and time is reached
    Note: participants is passed in as an argument list so mention the users who will participate at the end
    """
    if not participants:
        await ctx.send("Please have at least one participant")
        return
    if event_name in timers:
        await ctx.send(f'There is already an event scheduled with the name "{event_name}". '
                       + 'please use another name or cancel the other timer with '
                       + '.cancel event_name and then add this one again')

    eastern = pytz.timezone('US/Eastern')

    parsed_datetime = dateparser.parse(start_time, settings={'DATE_ORDER': 'MDY'})

    # parse returns None if it failed to parse the date
    if not parsed_datetime:
        await ctx.send(f"Invalid datetime: {start_time}. Try again idiot")
        return

    # get timer duration using localized time
    local_time = parsed_datetime.astimezone(eastern)

    utc_time = local_time.astimezone(pytz.utc)

    timer_duration = (utc_time - pytz.utc.localize(datetime.utcnow())).total_seconds()

    # make sure time is in the future
    if timer_duration <= 0:
        await ctx.send("Please input a time in the future, ~~idiot~~")
        return

    # make sure time isnt 2 months in the future
    if timer_duration > MAX_DURATION:
        await ctx.send("Wow! That is a long ways away. Please schedule the event for closer in the future")
        return

    # create timer that starts the event when finished
    timers[event_name] = utils.BotTimer(timer_duration, callback=start_event, args=[ctx.channel.id, event_name, participants])

    await ctx.send(f'{event_name} has been scheduled for {local_time.strftime("%-m/%-d/%Y at %-I:%M %p EST")}')


@bot.command(name='cancel')
async def cancel(ctx: commands.Context, event_name: str = None):
    """
    Cancel an event with the given event_name
    """
    if not event_name:
        await ctx.send("Please provide an event name")
        return
    if event_name not in timers:
        await ctx.send(f'There is no event scheduled with the name "{event_name}", please try again.')
        return

    timers[event_name].cancel()
    del timers[event_name]
    await ctx.send(f'{event_name} was canceled')


@bot.command(name='remaining')
async def remaining(ctx: commands.Context, event_name: str):
    """
    Gets the time remaining until event with given event_name
    """
    if event_name not in timers:
        await ctx.send(f'There is no event scheduled with the name "{event_name}", please try again.')
        return

    seconds = timers[event_name].remaining

    # calculate days, hours, and minutes remaining
    days, remainder = divmod(seconds, 86400)

    hours, remainder = divmod(remainder, 3600)

    minutes, seconds = divmod(remainder, 60)

    await ctx.send(f'{event_name} will happen in {int(days)} days, {int(hours)} hours, '
                   + f'{int(minutes)} minutes, and {int(seconds)} seconds')


async def start_event(channel_id: int, event_name: str, *participants):
    channel = await bot.fetch_channel(channel_id)
    participants = participants[0]
    await channel.send(f'{" ".join(x.mention for x in participants)}, {event_name} is starting now!!')


bot.run(TOKEN)
