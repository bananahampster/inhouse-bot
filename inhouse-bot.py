#!/usr/bin/python3

import asyncio
import datetime
import discord
import json
import os
import random
import re
import socket
import urllib.request

from collections import deque
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext import tasks

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix = ["!", "+", "-", "nice "], help_command=None, case_insensitive=True, intents=intents)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_NAME = os.getenv('DISCORD_CHANNEL')

SERVER_IP = os.getenv('SERVER_IP')
SERVER_PORT = os.getenv('SERVER_PORT') # port to communicate with server plugin
SERVER_PASSWORD = os.getenv('SERVER_PASSWORD')

NEW_SERVER_IP = os.getenv('NEW_SERVER_IP')
NEW_SERVER_PORT = os.getenv('NEW_SERVER_PORT') # port to communicate with server plugin
NEW_SERVER_PASSWORD = os.getenv('NEW_SERVER_PASSWORD')

CLIENT_PORT = os.getenv('CLIENT_PORT') # port to communicate with client plugin listener (serverComms.py)

# on load, load previous teams + map from the prev* files
if os.path.exists('prevmaps.json'):
    with open('prevmaps.json', 'r') as f:
        previousMaps = deque(json.load(f), maxlen=5)
else:
    previousMaps = []

if os.path.exists('prevteams.json'):
    with open('prevteams.json', 'r') as f:
        previousTeam = json.load(f)
else:
    previousTeam = []

emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
mapList = []

playerList = {}
pickupStarted = False
pickupActive = False
playerNumber = 8
lastAdd = datetime.datetime.utcnow()
lastAddCtx = None

mapChoices = []

recentlyPlayedMapsMsg = None
mapVote = False
mapVoteMessage = None
mapVoteMessageView = None
nextCancelConfirms = False

useNewServer = False

## lock commands that matter for being out of order
commandLock = asyncio.Lock()

class MapChoice:
    def __init__(self, mapName, decoration=None):
        self.mapName = mapName
        self.decoration = decoration
        self.votes = []

    ## maybe other voting methods here?

async def HandleMapButtonCallback(self, interaction: discord.Interaction, button: discord.ui.Button):
    global mapVoteMessage
    if self is mapVoteMessageView:
        processVote(interaction.user, int(button.custom_id))
        await interaction.response.edit_message(embed=GenerateMapVoteEmbed())

class MapChoiceView(discord.ui.View):
    def __init__(self, mapChoices):
        super().__init__()
        self.addButtons()

    def addButtons(self):
        global emoji
        for idx, mapChoice in enumerate(mapChoices):
            self.add_item(self.createButton(label=f"{emoji[idx]} {mapChoice.mapName}", custom_id=f"{idx + 1}"))

    def createButton(self, label, custom_id):
        button = discord.ui.Button(label=label, custom_id=custom_id)

        async def mapButtonCallback(interaction: discord.Interaction):
            await HandleMapButtonCallback(self, interaction, button)

        button.callback = mapButtonCallback
        return button



# @debounce(2)
async def printPlayerList(ctx):
    global playerList
    global playerNumber

    msg =  ", ".join([s for s in playerList.values()])
    counter = str(len(playerList)) + "/" + str(playerNumber)

    await ctx.send("```\nPlayers (" + counter + ")\n" + msg + "```")
    await updateNick(ctx, counter)

async def DePopulatePickup(ctx):
    global pickupStarted
    global pickupActive
    global playerNumber
    global mapVote
    global playerList

    mapVote = False
    pickupStarted = False
    pickupActive = False
    playerNumber = 8
    playerList = {}

    if idlecancel.is_running():
        idlecancel.stop()

    if ctx:
        await updateNick(ctx)


def PickMaps(initial=False):
    global mapList
    global mapChoices

    # it is possible that no tier1 maps are left if the number of tier1 maps is less than 8
    firstTier = mapList["tier1"]
    if len(firstTier) == 0:
        firstTier = mapList["tier2"]

    mapChoices = []
    if initial:
        for i in range(3):
            if i == 0:
                mapname = random.choice(firstTier)
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname, "⭐"))
            elif i == 1:
                mapname = random.choice(firstTier + mapList["tier2"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname))
            elif i == 2:
                mapname = random.choice(mapList["tier2"] + mapList["tier3"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname))
    else:
        for i in range(3):
            if i == 0:
                mapname = random.choice(firstTier)
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname, "✨"))
            elif i == 1:
                mapname = random.choice(firstTier + mapList["tier2"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname, "⭐"))
            elif i == 2:
                mapname = random.choice(mapList["tier2"])
                RemoveMap(mapname)
                mapChoices.append(MapChoice(mapname))

def RemoveMap(givenMap):
    global mapList

    if givenMap in mapList['tier1']:
        mapList['tier1'].remove(givenMap)
    elif givenMap in mapList['tier2']:
        mapList['tier2'].remove(givenMap)
    elif givenMap in mapList['tier3']:
        mapList['tier3'].remove(givenMap)

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

async def updateNick(ctx, status=None):
    if status == "" or status is None:
        status = None
    else:
        status = "inhouse-bot (" + status + ")"

    await ctx.message.guild.me.edit(nick=status)

def resetMaps(): 
    global mapList
    global previousMaps

    with open('maplist.json') as f:
        mapList = json.load(f)
        for prevMap in previousMaps:
            for tier in mapList.values():
                if prevMap in tier:
                    tier.remove(prevMap)

async def sendMapEmbed(ctx):
    global mapChoices
    global mapVoteMessage
    global mapVoteMessageView

    embed = GenerateMapVoteEmbed()
    mapVoteMessageView = MapChoiceView(mapChoices)
    mapVoteMessage = await ctx.send(embed=embed, view=mapVoteMessageView)

    return mapVoteMessageView

async def setActiveServer(ctx, isNew=False):
    global useNewServer

    useNewServer = isNew

    with open('activeServer.json', 'w') as f:
        activeServer = { 'useNewServer': useNewServer }
        json.dump(activeServer, f)

    if isNew:
        await ctx.send('Using new server!')
    else:
        await ctx.send('Using old server.')

def getActiveServer():
    global useNewServer
    return NEW_SERVER_IP if useNewServer else SERVER_IP

def getActiveServerPort():
    global useNewServer
    return NEW_SERVER_PORT if useNewServer else SERVER_PORT

def getActiveServerPassword():
    global useNewServer
    return NEW_SERVER_PASSWORD if useNewServer else SERVER_PASSWORD

@client.command(pass_context=True)
@commands.has_role('admin')
async def useNew(ctx):
    await setActiveServer(ctx, True)

@client.command(pass_context=True)
@commands.has_role('admin')
async def useOld(ctx):
    await setActiveServer(ctx, False)

@client.command(pass_context=True)
async def pickup(ctx):
    global pickupStarted
    global pickupActive
    global mapVote
    global mapList
    global playerNumber
    global previousMaps
    global recentlyPlayedMapsMsg
    global nextCancelConfirms
    global useNewServer

    async with commandLock: 
        if ctx.prefix == "nice ":
            await add(ctx)
            return

        if pickupStarted == False and pickupActive == False and mapVote == False and ctx.channel.name == CHANNEL_NAME:
            resetMaps()
            await DePopulatePickup(ctx)

            pickupStarted = True
            nextCancelConfirms = False
            recentlyPlayedMapsMsg = "Maps %s were recently played and are removed from voting." % ", ".join(previousMaps)

            await ctx.send("Pickup started on %s server. !add in 10 seconds" % ("new Vultur" if useNewServer else "old NFO"))
            await updateNick(ctx, "starting...")
            await asyncio.sleep(5)
            await ctx.send("!add in 5 seconds")
            await asyncio.sleep(5)

            if pickupStarted == True:
                pickupActive = True
                await ctx.send("!add enabled")
                await printPlayerList(ctx)
            else:
                await ctx.send("Pickup was canceled before countdown finished 🤨")

@client.command(pass_context=True)
async def cancel(ctx):
    global pickupStarted
    global pickupActive
    global mapVote
    global mapVoteMessage
    global nextCancelConfirms

    async with commandLock: 
        if mapVote != False and not nextCancelConfirms:
            await ctx.send("You're still picking maps, still wanna cancel?")
            nextCancelConfirms = True
            return
        if pickupStarted == True or pickupActive == True:
            pickupStarted = False
            pickupActive = False
            if mapVoteMessage is not None:
                await mapVoteMessage.edit(view=None)
                mapVoteMessage = None
            await ctx.send("Pickup canceled.")
            await DePopulatePickup(ctx)
        else:
            await ctx.send("No pickup active.")

@client.command(pass_context=True)
async def playernumber(ctx, numPlayers: int):
    global playerNumber

    if ctx.channel.name != CHANNEL_NAME:
        return

    try:
        players = int(numPlayers)
    except:
        await ctx.send("Given value isn't a number you doofus.")
        return

    if players % 2 == 0 and players <= 20 and players >= 2:
        playerNumber = players
        await ctx.send("Set pickup to fill at %d players" % playerNumber)
        await updateNick(ctx, str(len(playerList)) + "/" + str(playerNumber))
    else:
        await ctx.send("Can't set pickup to an odd number, too few, or too many players")

def GenerateMapVoteEmbed():
    global emoji
    global mapChoices
    global recentlyPlayedMapsMsg

    embed = discord.Embed(
        title="Vote for your map!",
        description=f"When vote is stable, !lockmap",
        color=0x00FFFF
    )

    for i in range(len(mapChoices)):
        mapChoice = mapChoices[i]
        mapName = mapChoice.mapName
        decoration = mapChoice.decoration or ""

        votes = mapChoice.votes
        numVotes = len(votes)
        whoVoted = ", ".join([playerList[playerId] for playerId in votes])
        whoVotedString = whoVoted
        if len(whoVoted) > 0:
            whoVotedString = "_" + whoVotedString + "_"

        if numVotes == 1:
            voteCountString = "1 vote"
        else:
            voteCountString = "%d votes" % (numVotes)

        embed.add_field(name="", value=emoji[i] + " `" + mapName + " " + decoration + (" " * (25 - len(mapName) - 2 * len(decoration))) + voteCountString + "`\n\u200B" + whoVotedString, inline=False)

    if recentlyPlayedMapsMsg != None:
        embed.add_field(name="", value=recentlyPlayedMapsMsg, inline=False)

    playersVoted = [playerId for mapChoice in mapChoices for playerId in mapChoice.votes]
    playersAbstained = [playerList[playerId] for playerId in playerList.keys() if playerId not in playersVoted]
    if len(playersAbstained) != 0 and len(playersAbstained) != len(playerList):
        embed.add_field(name="", value="```💩 " + ", ".join(playersAbstained) +  " need" + ("s" if len(playersAbstained) == 1 else "") + " to vote 💩```", inline=False)

    return embed

@client.command(pass_context=True, name="+")
async def plusPlus(ctx):
    if ctx.prefix == "+":
        await add(ctx)

@client.command(pass_context=True, name="-")
async def minusMinus(ctx):
    if ctx.prefix == "-":
        await remove(ctx)

@client.command(pass_context=True)
async def add(ctx):
    global playerNumber
    global playerList
    global pickupActive
    global mapVote
    global lastAdd
    global lastAddCtx
    global mapChoices

    player = ctx.author
    
    async with commandLock: 
        if pickupActive == True and ctx.channel.name == CHANNEL_NAME:
            playerId = player.id
            playerName = player.display_name
            if playerId not in playerList:
                playerList[playerId] = playerName
                lastAdd = datetime.datetime.utcnow()

                if not idlecancel.is_running():
                    idlecancel.start()
                    lastAddCtx = ctx

                if len(playerList) < playerNumber:
                    await printPlayerList(ctx)
                else:
                    pickupActive = False
                    if idlecancel.is_running():
                        idlecancel.stop()

                    await printPlayerList(ctx)
                    await updateNick(ctx, "voting...")

                    # ensure that playerlist is first n people added
                    playerList = dict(list(playerList.items())[:playerNumber])

                    PickMaps(True)
                    mapChoices.append(MapChoice("New Maps"))

                    mapVote = True
                    await sendMapEmbed(ctx)

                    mentionString = ""
                    for playerId in playerList.keys():
                        mentionString = mentionString + ("<@%s> " % playerId)
                    await ctx.send(mentionString)

@tasks.loop(minutes=30)
async def idlecancel():
    global lastAdd
    global lastAddCtx
    global pickupActive
    global mapVote

    if pickupActive == True and pickupStarted == True and mapVote == False:
        # check if 3 hours since last add
        lastAddDiff = (datetime.datetime.utcnow() - lastAdd).total_seconds()
        print("last add was %d minutes ago" % (lastAddDiff / 60))

        if lastAddDiff > (3 * 60 * 60):
            print("stopping pickup")

            await lastAddCtx.send("Pickup idle for more than three hours, canceling.")
            await DePopulatePickup(lastAddCtx)

@client.command(pass_context=True)
async def remove(ctx):
    global playerList
    global pickupActive

    async with commandLock: 
        if pickupActive == True and ctx.channel.name == CHANNEL_NAME:
            if ctx.author.id in playerList:
                del playerList[ctx.author.id]
                await printPlayerList(ctx)

@client.command(pass_context=True)
@commands.has_role('admin')
async def kick(ctx, player: discord.User):
    global playerList

    async with commandLock: 
        if player is not None and player.id in playerList:
            del playerList[player.id]
            await ctx.send("Kicked %s from the pickup." % player.mention)
            await printPlayerList(ctx)

@client.command(pass_context=True)
async def teams(ctx):
    if ctx.channel.name != CHANNEL_NAME:
        return

    if pickupStarted == False:
        await ctx.send("No pickup active.")
    else:
        await printPlayerList(ctx)


def processVote(player: discord.Member=None, vote=None):
    global mapVote
    global playerList

    global mapChoices

    if player.id in playerList:
        # remove any existing votes
        for mapChoice in mapChoices:
            if(player.id in mapChoice.votes):
                mapChoice.votes.remove(player.id)

        mapChoices[vote - 1].votes.append(player.id)

@client.command(pass_context=True, aliases=["fv"])
async def lockmap(ctx):
    global mapVote
    global mapVoteMessage
    global mapVoteMessageView

    global mapChoices

    global mapList
    global previousMaps
    global recentlyPlayedMapsMsg
    global nextCancelConfirms

    if ctx.channel.name != CHANNEL_NAME:
        return

    async with commandLock: 
        rankedVotes = []
        highestVote = 0
        winningMap = " "

        if(mapVote == True):
            nextCancelConfirms = False

            # get top maps
            mapTally = [(mapChoice.mapName, len(mapChoice.votes)) for mapChoice in mapChoices]
            rankedVotes = sorted(mapTally, key=lambda e: e[1], reverse=True)

            print(rankedVotes)

            if len(rankedVotes) == 0:
                await ctx.send("Failed to determine votes correctly, resetting...")

                resetMaps()
                PickMaps(True)
                mapChoices.append(MapChoice("New Maps"))

                await sendMapEmbed(ctx)
                return

            highestVote = rankedVotes[0][1]

            # don't allow lockmap if no votes were cast
            if highestVote == 0:
                await ctx.send("!lockmap denied; no votes were cast.")
                return

            # Hide voting buttons now that the vote is complete.
            mapVoteMessageView = None
            await mapVoteMessage.edit(view=None)

            winningMaps = [pickedMap for (pickedMap, votes) in rankedVotes if votes == highestVote]

            # don't allow "New Maps" to win
            if len(winningMaps) > 1 and "New Maps" in winningMaps:
                winningMap = "New Maps"
            else:
                winningMap = random.choice(winningMaps)

            if(winningMap == "New Maps"):
                PickMaps()
                carryOverMap = random.choice([pickedMap for (pickedMap, votes) in rankedVotes if votes == rankedVotes[1][1] and pickedMap != "New Maps"])
                mapChoices.append(MapChoice(carryOverMap, "🔁"))

                recentlyPlayedMapsMsg = None
                await sendMapEmbed(ctx)
            else:
                mapVoteMessage = None
                mapVoteMessageView = None

                mapVote = False
                RecordMapAndTeams(winningMap)

                await ctx.send("The winning map is: " + winningMap)
                await ctx.send("🎉🎉 JOIN INHOUSE YA HOSERS 🎉🎉")
                await ctx.send("steam://connect/%s:27015/%s" % (getActiveServer(), getActiveServerPassword()))
                await DePopulatePickup(ctx)

@client.command(pass_context=True)
async def vote(ctx):
    global mapVote
    global playerList
    global mapChoices

    if mapVote == True and ctx.channel.name == CHANNEL_NAME:
        playersVoted = [playerId for mapChoice in mapChoices for playerId in mapChoice.votes]
        playersAbstained = [playerId for playerId in playerList.keys() if playerId not in playersVoted]

        mentionString = "🗳️🗳️ vote maps or kick: "
        for playerId in playersAbstained:
            mentionString = mentionString + ("<@%s> " % playerId)
        await ctx.send(mentionString + " 🗳️🗳️")

@client.command(pass_context=True)
async def lockset(ctx, mapToLockset):
    global previousMaps
    global pickupActive
    global mapVote

    if ctx.channel.name != CHANNEL_NAME:
        return

    async with commandLock: 
        if pickupActive != False and mapVote != False:
            await ctx.send("Error: can only !lockset during map voting or if no pickup is active (changes the map for the last pickup)")
            return

        previousMaps.pop()
        previousMaps.append(mapToLockset)

        with open('prevmaps.json', 'w') as f:
            json.dump(list(previousMaps), f)

        await ctx.send("Set pickup map to %s" % mapToLockset)

@client.command(pass_context=True)
async def timeleft(ctx):
    global useNewServer

    if ctx.channel.name != CHANNEL_NAME:
        return

    # construct a UDP packet and send it to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto("BOT_MSG@TIMELEFT@".encode(), (getActiveServer(), int(getActiveServerPort())))

    await asyncio.sleep(3)
    if os.path.exists('timeleft.json'):
        with open('timeleft.json', 'r') as f:
            try:
                timeleft = json.load(f)
                if timeleft is not None and timeleft['timeleft']:
                    await ctx.send("Timeleft (%s server): %s" % ("new" if useNewServer else "old", timeleft['timeleft']))
                    return
            except:
                await ctx.send("Server did not respond.")
    else:
        await ctx.send("Server did not respond")

@client.command(pass_context=True)
async def stats(ctx):
    with open('prevlog.json', 'r') as f:
        prevlog = json.load(f)
        await ctx.send('Stats: %s' % prevlog['site'])

@client.command(pass_context=True)
@commands.has_role('admin')
async def forcestats(ctx):
    print("forcestats -- channel name" + ctx.channel.name)
    if ctx.channel.name == 'moderator-only':
        await ctx.send("force-parsing stats; wait 7 sec...")

        with open('prevlog.json', 'w') as f:
            f.write(r"{}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto("BOT_MSG@END".encode(), ('0.0.0.0', int(CLIENT_PORT)))

        # try at least 5 times before aborting
        for i in range(5):
            await asyncio.sleep(7)

            with open('prevlog.json', 'r') as f:
                prevlog = json.load(f)

                if 'site' in prevlog:
                    await ctx.send('Stats: %s' % prevlog['site'])
                    return
                
                await ctx.send('...still parsing')

        await ctx.send('Failed to parse latest log.  Check inhouse-comms logs')

@client.command(pass_context=True)
@commands.has_role('admin')
async def forceFill(ctx):    
    global pickupStarted
    global pickupActive

    global playerList
    global playerNumber

    global nextCancelConfirms
    global recentlyPlayedMapsMsg

    print('force-starting pickup')
    if ctx.channel.name != CHANNEL_NAME:
        return
    
    if len(playerList) != 0:
        await ctx.send("Can't test filling pickup with players added.")
        return
    
    resetMaps()
    await DePopulatePickup(ctx)

    pickupStarted = True
    pickupActive = True    
    playerList = {}
    playerNumber = 2
    
    pickupStarted = True
    nextCancelConfirms = False
    recentlyPlayedMapsMsg = "Maps %s were recently played and are removed from voting." % ", ".join(previousMaps)

    playerList['144036876842434561'] = "azooo"
    await add(ctx)

@client.command(pass_context=True)
async def hltv(ctx):
    await ctx.send("HLTV: http://inhouse.site.nfoservers.com/HLTV/akw/")

@client.command(pass_context=True)
async def logs(ctx):
    await ctx.send("Logs: http://inhouse.site.nfoservers.com/akw/")

@client.command(pass_context=True)
async def tfcmap(ctx, map):
    map = map.lower()
    with urllib.request.urlopen(r"http://mrclan.com/tfcmaps/") as mapIndex:
        response = mapIndex.read().decode("utf-8")
        matches = re.findall('<a href="/tfcmaps/%s.zip' % (map), response, re.I)
        if len(matches) != 0:
            await ctx.send("Found map: http://mrclan.com/tfcmaps/%s.zip" % (map))
        else:
            await ctx.send("Didn't find specified map. [All known maps are here](http://mrclan.com/tfcmaps/).")

@client.command(pass_context=True)
async def server(ctx):
    await ctx.send("steam://connect/%s:27015/%s" % (getActiveServer(), getActiveServerPassword()))

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

@client.command(pass_context=True)
async def nuki(ctx):
    await ctx.send("https://clips.twitch.tv/PoorRefinedTurnipFreakinStinkin")

@client.command(pass_context=True)
async def repair(ctx):
    await ctx.send("https://www.twitch.tv/davjs/clip/ViscousPuzzledKoupreySmoocherZ")

@client.command(pass_context=True)
async def country(ctx):
    await ctx.send("http://hampalyzer.com/country-trolls-hump2.mp4")

@client.command(pass_context=True)
async def neon(ctx):
    await ctx.send("https://clips.twitch.tv/VenomousCrepuscularJuicePeanutButterJellyTime")

@client.command(pass_context=True)
async def proonz(ctx):
    await ctx.send("https://streamable.com/xugb7r")

@client.command(pass_context=True)
async def masz(ctx):
    await ctx.send("https://www.twitch.tv/neonlight_tfc/clip/BoldEnthusiasticFerretKevinTurtle-Wz33i-BA34JDjxVp")

@client.command(pass_context=True)
async def swk(ctx):
    await ctx.send("https://streamable.com/ut068u")

@client.command(pass_context=True)
async def seagals(ctx):
    clips = [
        "https://streamable.com/mt9hjy",
        "https://streamable.com/7ko1hh",
        "https://streamable.com/m0cmzf",
        "https://clips.twitch.tv/VictoriousConsiderateMosquitoHeyGirl-L8XUHMzJWHPWgTnY"
    ]

    await ctx.send(random.choice(clips))

@client.command(pass_context=True)
async def angel(ctx):
    await ctx.send("https://www.twitch.tv/nugki/clip/BlindingPatientPotPeteZaroll")

@client.command(pass_context=True)
async def ja(ctx):
    await ctx.send("https://www.twitch.tv/bananahampster/clip/DependableSpineyTruffleBIRB")

@client.command(pass_context=True)
async def kix(ctx):
    await ctx.send("https://www.twitch.tv/r0flz/clip/UglyGrotesqueCattlePraiseIt")

@client.command(pass_context=True)
async def help(ctx):
    await ctx.send("pickup: !pickup !add !remove !teams !lockmap !cancel !playernumber")
    await ctx.send("info: !stats !timeleft !hltv !logs !tfcmap !server")
    await ctx.send("admin: !kick !lockset !forcestats !vote !forcefill !useNew !useOld")
    await ctx.send("fun: !hamp !teamz !packup !doug !akw !nuki !neon !swk !ja")
    await ctx.send("fun: !repair !country !proonz !angel !masz !seagals (1/4) !kix")

@client.event
async def on_ready():
    global useNewServer

    print(f'{client.user} is aliiiiiive!')

    # figure out if we should be using new server
    if os.path.exists('activeServer.json'):
        with open('activeServer.json', 'r') as f:
            activeServer = json.load(f)
            if activeServer['useNewServer']:
                useNewServer = True

client.run(TOKEN)
