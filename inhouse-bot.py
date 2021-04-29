#!/usr/bin/python3

import asyncio
import discord
import json
import os
import random

from dotenv import load_dotenv
from discord.ext import commands
from discord.utils import get

client = commands.Bot(command_prefix = "!", case_insensitive=True)
client.remove_command('help')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

msgList = []
playerList = {}
msg = " "
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

def PopulateTable():
    global msgList
    global playerList
    global msg
    # msgList = []
    # for i in range(len(playerList)):
    #     msgList.append(playerList[i])

    # msg = ''.join(msgList)
    # return msg

    msg =  ", ".join([s for s in playerList.values()])
    return msg

def DePopulatePickup():
    global pickupActive
    global mapsPicked
    global mapVote
    global msgList
    global eList
    global msg
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
    eList = []
    blueTeam = []
    redTeam = []
    playerList = {}
    msg = None
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

@client.command(pass_context=True)
async def pickup(ctx):
    global pickupActive
    global mapChoice1
    global mapChoice2
    global mapChoice3
    global mapChoice4
    global mapList

    if pickupActive == 0 and mapVote == 0 and mapsPicked == 0 and pickNum == 1:

        with open('maplist.json') as f:
            mapList = json.load(f)

        DePopulatePickup
        await ctx.send("Pickup started, you can add in 10 seconds")
        await asyncio.sleep(5)
        await ctx.send("Pickup started, you can add in 5 seconds")
        await asyncio.sleep(5)
        await ctx.send("Type !add")

        pickupActive = 1

        PopulateTable()
        await ctx.send("```\n Players\n" + msg + "```")

@client.command(pass_context=True)
async def cancel(ctx):
    await ctx.send("pickup cancelled..")
    DePopulatePickup()

@client.command(pass_context=True)
async def add(ctx):
    global playerList
    global pickupActive
    global vMsg
    global mapChoice1
    global mapChoice2
    global mapChoice3
    global mapChoice4
    global mapVotes
    global mapVote
    if(pickupActive == 1):

        playerId = ctx.author.id
        playerName = ctx.author.display_name
        if playerId not in playerList:
            playerList[playerId] = playerName

        PopulateTable()
        await ctx.send("```\n Players\n" + msg + "```")

    if(len(playerList) >= 8):
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
    sameVotes = []
    ordered = []
    highestVote = 0
    winningMap = " "
    # mapVotes[mapChoice1] = len(mapVotes[mapChoice1])
    # mapVotes[mapChoice2] = len(mapVotes[mapChoice2])
    # mapVotes[mapChoice3] = len(mapVotes[mapChoice3])
    # mapVotes[mapChoice4] = len(mapVotes[mapChoice4])
    # print(mapVotes)
    if(mapVote == 1):
    #     for i in list(mapVotes):
    #         if(mapVotes[i] > highestVote):
    #             sameVotes.clear()
    #             sameVotes.append(i)
    #             highestVote = mapVotes[i]
    #         elif(mapVotes[i] == highestVote):
    #             highestVote = mapVotes[i]
    #             sameVotes.append(i)
    #     ordered = sorted(mapVotes, key=mapVotes.get, reverse=True)
    #     print(ordered)

        # get top maps
        mapTally = [(pickedMap, len(votes)) for (pickedMap, votes) in mapVotes.items()]
        sameVotes = sorted(mapTally, key=lambda e: e[0], reverse=True)

        highestVote = sameVotes[0][1]
        sameVotes = [pickedMap for (pickedMap, votes) in sameVotes if votes == highestVote ]
        winningMap = random.choice(sameVotes)

        if(winningMap == "New Maps"):
            mapVotes = {}
            PickMaps()
            mapChoice4 = ordered[1]
            mapVotes[mapChoice4] = []

            vMsg = await ctx.send("```Vote for your map!  Be quick, you only have 60 seconds to vote..\n\n"
                                    + "1️⃣ " + mapChoice1 + " " * (30 - len(mapChoice1)) + str(len(mapVotes[mapChoice1])) + " Votes\n"
                                    + "2️⃣ " + mapChoice2 + " " * (30 - len(mapChoice2)) + str(len(mapVotes[mapChoice2])) + " Votes\n"
                                    + "3️⃣ " + mapChoice3 + " " * (30 - len(mapChoice3)) + str(len(mapVotes[mapChoice3])) + " Votes\n"
                                    + "4️⃣ " + mapChoice4 + " " * (30 - len(mapChoice4)) + str(len(mapVotes[mapChoice4])) + " Votes```")

            await vMsg.add_reaction("1️⃣")
            await vMsg.add_reaction("2️⃣")
            await vMsg.add_reaction("3️⃣")
            await vMsg.add_reaction("4️⃣")
        else:
            await ctx.send("The winning map is " + winningMap)
            await ctx.send("Assign captains to begin the team picking process with !cap @cap1 @cap2")
            mapVote = 0
            mapsPicked = 1

@client.command(pass_context=True)
async def cap(ctx, cap1: discord.Member, cap2: discord.Member):
    global tMsg
    global mapsPicked
    global captains
    if(mapsPicked == 1):
        if(cap1.display_name in playerList.values()):
            blueTeam.append(cap1.display_name)
            captains.append(cap1.display_name)
            del playerList[cap1.id]
        if(cap2.display_name in playerList.values()):
            redTeam.append(cap2.display_name)
            captains.append(cap2.display_name)
            del playerList[cap2.id]

        pMsgList = ["Player List: "]
        bTeamMsgList = ["Blue Team: "]
        rTeamMsgList = ["Red Team: "]

        for i in playerList.values():
            pMsgList.append(i + "\n")

        for i in blueTeam:
            bTeamMsgList.append(i + "\n")

        for i in redTeam:
            rTeamMsgList.append(i + "\n")

        pMsg = ' '.join(pMsgList)
        bMsg = ' '.join(bTeamMsgList)
        rMsg = ' '.join(rTeamMsgList)

        tMsg = await ctx.send("```\n" + pMsg + "\n\n" + bMsg + "\n\n" + rMsg + "```")



@client.command(pass_context=True)
async def remove(ctx):
    global playerList
    global pickupActive
    global msg

    if(pickupActive == 1):
        if ctx.author.id in playerList:
            del playerList[ctx.author.id]

            PopulateTable()
            await ctx.send("```\n Players\n" + msg + "```")

@client.command(pass_context=True)
async def pick(ctx, name: discord.Member):
    global blueTeam
    global redTeam
    global tMsg
    global playerList
    global pickNum
    playerName = name.display_name
    playerId = name.id
    captain = ctx.author.display_name
    if captain in captains:
        if captain in blueTeam:
            if((pickNum == 1) or (pickNum == 3) or (pickNum == 6)):
                del playerList[playerId]
                blueTeam.append(playerName)
                pickNum += 1

        if captain in redTeam:
            if((pickNum == 2) or (pickNum == 4) or (pickNum == 5) or (pickNum == 7)):
                del playerList[playerId]
                redTeam.append(playerName)
                pickNum += 1

        if(len(playerList) == 1):
            blueTeam.append(playerList[0])
            playerList = {}

            bTeamMsgList = ["Blue Team: "]
            rTeamMsgList = ["Red Team: "]

            for i in blueTeam:
                bTeamMsgList.append(i + " ")

            for i in redTeam:
                rTeamMsgList.append(i + " ")

            bMsg = ' '.join(bTeamMsgList)
            rMsg = ' '.join(rTeamMsgList)
            await ctx.send("Here are the teams...")
            await ctx.send("```\n" + bMsg + "\n\n" + rMsg + "```")

            DePopulatePickup()


        if(len(playerList) > 1):
            pMsgList = ["Player List: "]
            bTeamMsgList = ["Blue Team: "]
            rTeamMsgList = ["Red Team: "]

            for i in playerList:
                pMsgList.append(i + " ")

            for i in blueTeam:
                bTeamMsgList.append(i + " ")

            for i in redTeam:
                rTeamMsgList.append(i + " ")

            pMsg = ' '.join(pMsgList)
            bMsg = ' '.join(bTeamMsgList)
            rMsg = ' '.join(rTeamMsgList)

            await tMsg.edit(content= "```\n" + pMsg + "\n\n" + bMsg + "\n\n" + rMsg + "```")

@client.event
async def on_reaction_add(reaction, user):
    global mapVote
    global playerList
    global alreadyVoted
    global mapVotes
    #print(reaction.author.display_name)
    if((reaction.message.channel.name == "inhouse") and (mapVote == 1) and (user.display_name != "inhouse-bot")):
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
                await vMsg.edit(content="```Vote for your map!  Be quick, you only have 30 seconds to vote..\n\n"
                                + "1️⃣ " + mapChoice1 + " " * (30 - len(mapChoice1)) + str(len(mapVotes[mapChoice1])) + " Votes\n"
                                + "2️⃣ " + mapChoice2 + " " * (30 - len(mapChoice2)) + str(len(mapVotes[mapChoice2])) + " Votes\n"
                                + "3️⃣ " + mapChoice3 + " " * (30 - len(mapChoice3)) + str(len(mapVotes[mapChoice3])) + " Votes\n"
                                + "4️⃣ " + mapChoice4 + " " * (30 - len(mapChoice4)) + str(len(mapVotes[mapChoice4])) + " Votes```")
            # else:
            #     await reaction.message.channel.send("Youre not in the pickup sir.")

@client.event
async def on_ready():
    print(f'{client.user} is aliiiiiive!')


client.run(TOKEN)