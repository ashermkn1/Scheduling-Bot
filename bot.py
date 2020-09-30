import os
from datetime import datetime
from typing import Dict, Optional

import dateparser
import discord
import dotenv
import pytz
from discord.ext import commands

from utils import BotTimer

MAX_DURATION = 7776000
# load environment variables from .env file
dotenv.load_dotenv('.env')
TOKEN = os.getenv('DISCORD_TOKEN')

# initialize discord bot
bot = commands.Bot(command_prefix='.')

# dictionary mapping event names to their timers
timers: Dict[str, BotTimer] = {}


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    activity = discord.Game(name='.help')
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.command()
async def schedule(ctx: commands.Context, event_name: str, start_time: str, *participants: discord.User):
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
        return

    local_time = await parse_datetime(ctx, start_time)

    if not local_time:
        return

    utc_time = local_time.astimezone(pytz.utc)

    timer_duration = (utc_time - pytz.utc.localize(datetime.utcnow())).total_seconds()
    # create timer that starts the event when finished
    timers[event_name] = BotTimer(timer_duration, callback=start_event,
                                  args=[ctx.channel.id, event_name, *participants])

    await ctx.send(f'{event_name} has been scheduled for {local_time.strftime("%m/%d/%Y at %I:%M%p EST")}')


async def parse_datetime(ctx: commands.Context, timestamp: str) -> Optional[datetime]:
    eastern = pytz.timezone('US/Eastern')

    parsed_datetime = dateparser.parse(timestamp, settings={'DATE_ORDER': 'MDY'})

    # parse returns None if it failed to parse the date
    if not parsed_datetime:
        await ctx.send(f"Invalid datetime: {timestamp}")
        return None

    # get timer duration using localized time
    local_time = parsed_datetime.astimezone(eastern)

    utc_time = local_time.astimezone(pytz.utc)

    timer_duration = (utc_time - pytz.utc.localize(datetime.utcnow())).total_seconds()

    # make sure time is in the future
    if timer_duration <= 0:
        await ctx.send("Please input a time in the future, ~~idiot~~")
        return None

    # make sure time isnt 2 months in the future
    if timer_duration > MAX_DURATION:
        await ctx.send("Wow! That is a long ways away. Please schedule the event for closer in the future")
        return None

    return local_time


@bot.command()
async def reschedule(ctx: commands.Context, event_name: str, new_time: str):
    """
    Reschedule an event with the given name to given time
    """
    if event_name not in timers:
        await ctx.send(f'There is no event scheduled with the name "{event_name}", please try again.')
        return

    old_timer: BotTimer = timers[event_name]
    args = old_timer.args
    print(args)
    local_time = await parse_datetime(ctx, new_time)

    if not local_time:
        return

    utc_time = local_time.astimezone(pytz.utc)

    timer_duration = (utc_time - pytz.utc.localize(datetime.utcnow())).total_seconds()

    timers[event_name].cancel()

    timers[event_name] = BotTimer(timer_duration, callback=start_event, args=args)

    await ctx.send(f'{event_name} has been rescheduled to {local_time.strftime("%m/%d/%Y at %I:%M%p EST")}')


@bot.command()
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


@bot.command()
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


@bot.command(name="listall")
async def list_all(ctx: commands.Context):
    """
    lists all of the events currently schedules, showing their name and time remaining
    """
    if not timers:
        await ctx.send("There are no events currently scheduled")
        return

    for name in timers:
        await ctx.invoke(bot.get_command(name="remaining"), event_name=name)


async def start_event(channel_id: int, event_name: str, *participants):
    channel = await bot.fetch_channel(channel_id)
    await channel.send(f'{" ".join(x.mention for x in participants)}, {event_name} is starting now!!')
    del timers[event_name]


bot.run(TOKEN)
