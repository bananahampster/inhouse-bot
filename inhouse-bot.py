#!/usr/bin/python3

import asyncio
import threading
import discord
import json
import os
import random
import socket

from collections import deque
from discord import player
from discord.flags import PublicUserFlags
from dotenv import load_dotenv
from discord.ext import commands
from discord.utils import get

from debounce import debounce
from serverComms import InhouseServerProtocol

client = commands.Bot(command_prefix = "!", case_insensitive=True)
client.remove_command('help')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# on load, load previous teams + map from the prev* files
with open('prevmaps.json', 'r') as f:
    previousMaps = deque(json.load(f), maxlen=4)

with open('prevteams.json', 'r') as f:
    previousTeam = json.load(f)

mapList = []

msgList = []
playerList = {}
pickupActive = 0
mapchoice1 = None
mapChoice2 = None
mapChoice3 = None
mapChoice4 = None
mapSelected = []
mapVotes = {}
blueTeam = []
redTeam = []
alreadyVoted = []
vMsg = None
mapVote = 0
tmsg = None
ordered = []
mapsPicked = 0
captains = []
pickNum = 1


## deal with socket stuffz
# def background_loop(loop):
#     listen = loop.create_datagram_endpoint(InhouseServerProtocol, local_addr=('127.0.0.1', 16353))
#     transport, protocol = loop.run_until_complete(listen)

#     try:
#         loop.run_forever()
#     except KeyboardInterrupt:
#         pass

#     transport.close()
#     loop.close()

# loop = asyncio.new_event_loop()
# t = threading.Thread(target=background_loop, args=(loop, ))
# t.start()

# async def main_watcher():
#     loop = asyncio.get_running_loop()
#     transport, protocol = await loop.create_datagram_endpoint(lambda: InhouseServerProtocol(), local_addr=('127.0.0.1', 16353))

#     try:
#         await loop.run_forever()
#     except KeyboardInterrupt:
#         pass
#     finally:
#         transport.close()


# asyncio.run(main_watcher())


async def start_udp_listener():
    loop = asyncio.get_event_loop()
    return await loop.create_datagram_endpoint(lambda: InhouseServerProtocol(), local_addr=('127.0.0.1', 16353))

def main_watcher():
    loop = asyncio.get_event_loop()
    coro = start_udp_listener()
    transport, _ = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
        loop.close()

main_watcher()

# @debounce(2)
async def printPlayerList(ctx):
    global playerList

    msg =  ", ".join([s for s in playerList.values()])
    await ctx.send("```\nPlayers (" + str(len(playerList)) + "/8)\n" + msg + "```")

def DePopulatePickup():
    global pickupActive
    global mapsPicked
    global mapVote
    global msgList
    global playerList
    global blueTeam
    global redTeam
    global mapSelected
    global ordered
    global mapVotes
    global captains
    global pickNum

    ordered = []
    pickNum = 1
    captains = []
    mapVote = 0
    mapsPicked = 0
    pickupActive = 0
    msgList = []
    blueTeam = []
    redTeam = []
    playerList = {}
    mapSelected = []
    mapVotes = {}

def PickMaps():
    global mapChoice1
    global mapChoice2
    global mapChoice3
    global mapSelected
    global mapVotes
    global mapList

    mapname = random.choice(mapList)
    mapChoice1 = mapname
    mapList.remove(mapname)
    mapVotes[mapChoice1] = []

    mapname = random.choice(mapList)
    mapChoice2 = mapname
    mapList.remove(mapname)
    mapVotes[mapChoice2] = []

    mapname = random.choice(mapList)
    mapChoice3 = mapname
    mapList.remove(mapname)
    mapVotes[mapChoice3] = []

def RecordMapAndTeams(winningMap):
    global previousMaps
    global playerList
    global previousTeam

    previousMaps.append(winningMap)
    with open('prevmaps.json', 'w') as f:
        json.dump(list(previousMaps), f)

    previousTeam = list(playerList.values())
    with open('prevteams.json', 'w') as f:
        json.dump(previousTeam, f)

@client.command(pass_context=True)
async def pickup(ctx):
    global pickupActive
    global mapVote
    global mapsPicked
    global mapList
    global previousMaps

    if pickupActive == 0 and mapVote == 0 and mapsPicked == 0 and pickNum == 1:
        pickupActive = 1

        with open('maplist.json') as f:
            mapList = json.load(f)
            for prevMap in previousMaps:
                mapList.remove(prevMap)

        DePopulatePickup
        await ctx.send("Pickup started. !add in 10 seconds")
        await asyncio.sleep(5)
        await ctx.send("!add in 5 seconds")
        await asyncio.sleep(5)

        if pickupActive == 1:
            await ctx.send("!add enabled")
            await printPlayerList(ctx)
        else:
            await ctx.send("Pickup was canceled before countdown finished 🤨")

@client.command(pass_context=True)
async def cancel(ctx):
    if pickupActive == 1:
        await ctx.send("Pickup canceled.")
        DePopulatePickup()
    elif mapVote != 0:
        await ctx.send("You're still picking maps, still wanna cancel?")
        mapVote = 0
    else:
        await ctx.send("No pickup active.")

@client.command(pass_context=True)
async def add(ctx, player: discord.Member=None):
    global playerList
    global pickupActive
    global vMsg
    global mapChoice1
    global mapChoice2
    global mapChoice3
    global mapChoice4
    global mapVotes
    global mapVote

    # if player is None:
    player = ctx.author

    if pickupActive == 1:
        playerId = player.id
        playerName = player.display_name
        if playerId not in playerList:
            playerList[playerId] = playerName

            await printPlayerList(ctx)

    if len(playerList) >= 1:
        # ensure that playerlist is first 8 people added
        playerList = dict(list(playerList.items())[:8])

        pickupActive = 0
        PickMaps()
        mapChoice4 = "New Maps"
        mapVotes[mapChoice4] = []

        vMsg = await ctx.send("```Vote for your map!  When vote is stable, !lockmap\n\n"
                                + "1️⃣ " + mapChoice1 + " " * (30 - len(mapChoice1)) + str(len(mapVotes[mapChoice1])) + " Votes\n"
                                + "2️⃣ " + mapChoice2 + " " * (30 - len(mapChoice2)) + str(len(mapVotes[mapChoice2])) + " Votes\n"
                                + "3️⃣ " + mapChoice3 + " " * (30 - len(mapChoice3)) + str(len(mapVotes[mapChoice3])) + " Votes\n"
                                + "4️⃣ " + mapChoice4 + " " * (30 - len(mapChoice4)) + str(len(mapVotes[mapChoice4])) + " Votes```")

        await vMsg.add_reaction("1️⃣")
        await vMsg.add_reaction("2️⃣")
        await vMsg.add_reaction("3️⃣")
        await vMsg.add_reaction("4️⃣")

        mapVote = 1

@client.command(pass_context=True)
async def remove(ctx):
    global playerList
    global pickupActive

    if(pickupActive == 1):
        if ctx.author.id in playerList:
            del playerList[ctx.author.id]
            await printPlayerList(ctx)

@client.command(pass_context=True)
async def teams(ctx):
    await printPlayerList(ctx)

@client.event
async def on_reaction_add(reaction, user):
    global mapVote
    global playerList
    global alreadyVoted
    global mapVotes
    #print(reaction.author.display_name)
    if((reaction.message.channel.name == "inhouse-bot-test") and (mapVote == 1) and (user.display_name != "inhouse-bot")):
        if((reaction.emoji == '1️⃣') or (reaction.emoji == '2️⃣') or (reaction.emoji == '3️⃣') or (reaction.emoji == '4️⃣')):
            if(user.id in playerList):
                for i in list(mapVotes):
                    if(user.id in mapVotes[i]):
                        mapVotes[i].remove(user.id)
                if(reaction.emoji == '1️⃣'):
                    mapVotes[mapChoice1].append(user.id)
                if(reaction.emoji == '2️⃣'):
                    mapVotes[mapChoice2].append(user.id)
                if(reaction.emoji == '3️⃣'):
                    mapVotes[mapChoice3].append(user.id)
                if(reaction.emoji == '4️⃣'):
                    mapVotes[mapChoice4].append(user.id)
                await vMsg.edit(content="```Vote for your map!  When vote is stable, !lockmap\n\n"
                                + "1️⃣ " + mapChoice1 + " " * (30 - len(mapChoice1)) + str(len(mapVotes[mapChoice1])) + " Votes\n"
                                + "2️⃣ " + mapChoice2 + " " * (30 - len(mapChoice2)) + str(len(mapVotes[mapChoice2])) + " Votes\n"
                                + "3️⃣ " + mapChoice3 + " " * (30 - len(mapChoice3)) + str(len(mapVotes[mapChoice3])) + " Votes\n"
                                + "4️⃣ " + mapChoice4 + " " * (30 - len(mapChoice4)) + str(len(mapVotes[mapChoice4])) + " Votes```")


@client.command(pass_context=True)
async def lockmap(ctx):
    global mapsPicked
    global mapChoice1
    global mapChoice2
    global mapChoice3
    global mapChoice4
    global mapVotes
    global mapVote
    global vMsg
    global mapList
    global tMsg
    global blueTeam
    global redTeam
    global previousMaps

    rankedVotes = []
    highestVote = 0
    winningMap = " "

    if(mapVote == 1):
        # get top maps
        mapTally = [(pickedMap, len(votes)) for (pickedMap, votes) in mapVotes.items()]
        rankedVotes = sorted(mapTally, key=lambda e: e[1], reverse=True)

        highestVote = rankedVotes[0][1]
        winningMaps = [pickedMap for (pickedMap, votes) in rankedVotes if votes == highestVote ]
        winningMap = random.choice(winningMaps)

        if(winningMap == "New Maps"):
            mapVotes = {}
            PickMaps()
            mapChoice4 = random.choice([pickedMap for (pickedMap, votes) in rankedVotes if votes == rankedVotes[1][1]])
            mapVotes[mapChoice4] = []

            vMsg = await ctx.send("```Vote for your map!  When vote is stable, !lockmap\n\n"
                                    + "1️⃣ " + mapChoice1 + " " * (30 - len(mapChoice1)) + str(len(mapVotes[mapChoice1])) + " Votes\n"
                                    + "2️⃣ " + mapChoice2 + " " * (30 - len(mapChoice2)) + str(len(mapVotes[mapChoice2])) + " Votes\n"
                                    + "3️⃣ " + mapChoice3 + " " * (30 - len(mapChoice3)) + str(len(mapVotes[mapChoice3])) + " Votes\n"
                                    + "4️⃣ " + mapChoice4 + " " * (30 - len(mapChoice4)) + str(len(mapVotes[mapChoice4])) + " Votes```")

            await vMsg.add_reaction("1️⃣")
            await vMsg.add_reaction("2️⃣")
            await vMsg.add_reaction("3️⃣")
            await vMsg.add_reaction("4️⃣")
        else:
            await ctx.send("The winning map is: " + winningMap)
            await ctx.send("🎉🎉 JOIN INHOUSE YA HOSERS 🎉🎉")
            await ctx.send("steam://connect/104.153.105.235:27015/kawk")
            RecordMapAndTeams(winningMap)
            DePopulatePickup()


@client.command(pass_context=True)
async def teamz(ctx):
    await ctx.send("```\nPlayers (8/8)\nnuki, nuki, nuki, nuki, nuki, nuki, nuki, nuki```")

@client.command(pass_context=True)
async def packup(ctx):
    await ctx.send("Where's that fucking Hampster?  I swear I'm gonna pack that rodent up... 🐹")

@client.command(pass_context=True)
async def doug(ctx):
    await ctx.send("Doug was a semi-professional Team Fortress Classic Player between 2000 and 2007 achieving co-leading The Cereal Killers to holding all three major league titles at the same time. Doug left gaming for almost a decade and now he's back, streaming old Team Fortress Classic and Fortnite games.")

@client.command(pass_context=True)
async def akw(ctx):
    await ctx.send("akw likes butts 🍑")

@client.event
async def on_ready():
    print(f'{client.user} is aliiiiiive!')


client.run(TOKEN)