#!/usr/bin/python3

import asyncio
import discord
import json
import os
import random

from collections import deque
from dotenv import load_dotenv
from discord.ext import commands

client = commands.Bot(command_prefix = "!", case_insensitive=True)
client.remove_command('help')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_NAME = os.getenv('DISCORD_CHANNEL')
SERVER_PASSWORD = os.getenv('SERVER_PASSWORD')

# on load, load previous teams + map from the prev* files
with open('prevmaps.json', 'r') as f:
    previousMaps = deque(json.load(f), maxlen=3)

with open('prevteams.json', 'r') as f:
    previousTeam = json.load(f)

mapList = []

msgList = []
playerList = {}
pickupStarted = 0
pickupActive = 0
playerNumber = 8
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
ordered = []
mapsPicked = 0
captains = []
pickNum = 1

# @debounce(2)
async def printPlayerList(ctx):
    global playerList

    msg =  ", ".join([s for s in playerList.values()])
    await ctx.send("```\nPlayers (" + str(len(playerList)) + "/8)\n" + msg + "```")

def DePopulatePickup():
    global pickupStarted
    global pickupActive
    global playerNumber
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
    pickupStarted = 0
    pickupActive = 0
    playerNumber = 8
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
    global pickupStarted
    global pickupActive
    global mapVote
    global mapsPicked
    global mapList
    global previousMaps

    if pickupStarted == 0 and pickupActive == 0 and mapVote == 0 and mapsPicked == 0 and pickNum == 1:
        with open('maplist.json') as f:
            mapList = json.load(f)
            for prevMap in previousMaps:
                mapList.remove(prevMap)

        DePopulatePickup

        pickupStarted = 1
        await ctx.send("Pickup started. !add in 10 seconds")
        await asyncio.sleep(5)
        await ctx.send("!add in 5 seconds")
        await asyncio.sleep(5)

        if pickupStarted == 1:
            pickupActive = 1
            await ctx.send("!add enabled")
            await printPlayerList(ctx)
        else:
            await ctx.send("Pickup was canceled before countdown finished 🤨")

@client.command(pass_context=True)
async def cancel(ctx):
    global pickupStarted
    global pickupActive
    global mapVote

    if mapVote != 0:
        await ctx.send("You're still picking maps, still wanna cancel?")
        mapVote = 0
        return
    if pickupStarted == 1 or pickupActive == 1:
        pickupStarted = 0
        pickupActive = 0
        await ctx.send("Pickup canceled.")
        DePopulatePickup()
    else:
        await ctx.send("No pickup active.")

@client.command(pass_context=True)
async def playernumber(ctx, numPlayers: int):
    global playerNumber

    try:
        players = int(numPlayers)
    except:
        await ctx.send("Given value isn't a number you doofus.")
        return

    if players % 2 == 0 and players <= 20 and players >= 2:
        playerNumber = players
        await ctx.send("Set pickup to fill at %d players" % playerNumber)
    else:
        await ctx.send("Can't set pickup to an odd number, too few, or too many players")

@client.command(pass_context=True)
async def add(ctx, player: discord.Member=None):
    global playerNumber
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

            if len(playerList) < playerNumber:
                await printPlayerList(ctx)
            else:
                pickupActive = 0
                await printPlayerList(ctx)

                # ensure that playerlist is first 8 people added
                playerList = dict(list(playerList.items())[:8])

                PickMaps()
                mapChoice4 = "New Maps"
                mapVotes[mapChoice4] = []

                vMsg = await ctx.send("```Vote for your map!  When vote is stable, !lockmap\n\n"
                                        + "1️⃣ " + mapChoice1 + " " * (30 - len(mapChoice1)) + "\n"
                                        + "2️⃣ " + mapChoice2 + " " * (30 - len(mapChoice2)) + "\n"
                                        + "3️⃣ " + mapChoice3 + " " * (30 - len(mapChoice3)) + "\n"
                                        + "4️⃣ " + mapChoice4 + " " * (30 - len(mapChoice4)) + "```")

                await vMsg.add_reaction("1️⃣")
                await vMsg.add_reaction("2️⃣")
                await vMsg.add_reaction("3️⃣")
                await vMsg.add_reaction("4️⃣")

                mapVote = 1

                for playerId in playerList.keys():
                    user = await client.get_user(playerId)
                    await user.send('#inhouse pickup filled.')

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
    if((reaction.message.channel.name == CHANNEL_NAME) and (mapVote == 1) and (user.display_name != "inhouse-bot")):
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

                playersVoted = [playerId for mapVote in mapVotes.values() for playerId in mapVote]
                playersAbstained = [playerList[playerId] for playerId in playerList.keys() if playerId not in playersVoted]
                toVoteString = "```"
                if len(playersAbstained) != 0:
                    toVoteString = "\n💩 " + ", ".join(playersAbstained) +  " need to vote 💩```"

                await vMsg.edit(content="```Vote for your map!  When vote is stable, !lockmap\n\n"
                    + "1️⃣ " + mapChoice1 + " " * (30 - len(mapChoice1)) + mapVoteOutput(mapChoice1) + "\n"
                    + "2️⃣ " + mapChoice2 + " " * (30 - len(mapChoice2)) + mapVoteOutput(mapChoice2) + "\n"
                    + "3️⃣ " + mapChoice3 + " " * (30 - len(mapChoice3)) + mapVoteOutput(mapChoice3) + "\n"
                    + "4️⃣ " + mapChoice4 + " " * (30 - len(mapChoice4)) + mapVoteOutput(mapChoice4)
                    + toVoteString)

def mapVoteOutput(mapChoice):
    votes = mapVotes[mapChoice]
    numVotes = len(votes)
    whoVoted = ", ".join([playerList[playerId] for playerId in votes])

    if numVotes == 0:
        return "0 votes"

    return "%d votes (%s)" % (numVotes, whoVoted)

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
            mapVote = 0
            RecordMapAndTeams(winningMap)

            await ctx.send("The winning map is: " + winningMap)
            await ctx.send("🎉🎉 JOIN INHOUSE YA HOSERS 🎉🎉")
            await ctx.send("steam://connect/104.153.105.235:27015/" + SERVER_PASSWORD)
            DePopulatePickup()


@client.command(pass_context=True)
async def lockset(ctx, mapToLockset):
    global previousMaps
    global pickupActive
    global mapVote

    if pickupActive == 0 or mapVote == 1:
        await ctx.send("Error: can only !lockset during map voting or if no pickup is active (changes the map for the last pickup)")
        return

    previousMaps.pop()
    previousMaps.append(mapToLockset)

    with open('prevmaps.json', 'w') as f:
        json.dump(list(previousMaps), f)

    await ctx.send("Set pickup map to %s" % mapToLockset)


@client.command(pass_context=True)
async def stats(ctx):
    with open('prevlog.json', 'r') as f:
        prevlog = json.load(f)
        await ctx.send('Stats: %s' % prevlog['site'])

@client.command(pass_context=True)
async def hltv(ctx):
    await ctx.send("HLTV: http://inhouse.site.nfoservers.com/HLTV/akw/")

@client.command(pass_context=True)
async def logs(ctx):
    await ctx.send("Logs: http://inhouse.site.nfoservers.com/akw/")

@client.command(pass_context=True)
async def sever(ctx):
    await ctx.send("steam://connect/104.153.105.235:27015/kawk")

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

@client.command(pass_context=True)
async def hamp(ctx):
    await ctx.send("https://streamable.com/0328u")

@client.event
async def on_ready():
    print(f'{client.user} is aliiiiiive!')


client.run(TOKEN)