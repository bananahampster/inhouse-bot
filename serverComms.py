#!/usr/bin/python3

import asyncio
import json

class InhouseServerProtocol:
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        print('received %r from %s' % (message, addr))

        message_parts = message.split("@")
        if message_parts[0] != "BOT_MSG":
            return

        if message_parts[1] == "IRC":
            print("message inhouse! {}" % message)

        if message_parts[1] == "MAP":
            with open('prevmaps.json', 'r') as f:
                prevmaps = json.load(f)
                curmap = prevmaps[-1]

                self.send_message("MAP", curmap, addr)

        if message_parts[1] == "RS":
            with open('prevmaps.json', 'r') as f:
                prevmaps = json.load(f)
                curmap = prevmaps[-1]

                self.send_message("RS", curmap, addr)

        if message_parts[1] == "TEAMS":
            with open('prevteams.json', 'r') as f:
                prevteams = json.load(f)

                self.send_message("TEAMS", ', '.join(prevteams[:4]), addr)
                self.send_message("TEAMS", ', '.join(prevteams[4:]), addr)


    def send_message(self, msg_type, message, addr):
        data = f"BOT_MSG@{msg_type}@{message}".encode()
        self.transport.sendto(data, (addr[0], 16354))  # bot only listens on this port
