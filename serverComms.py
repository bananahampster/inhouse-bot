#!/usr/bin/python3

import asyncio
import json

async def start_udp_listener():
    loop = asyncio.get_event_loop()
    return await loop.create_datagram_endpoint(lambda: InhouseServerProtocol(), local_addr=('0.0.0.0', 16353))

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

def main():
    main_watcher()

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
        data = ("BOT_MSG@%s@%s" % (msg_type, message)).encode()
        self.transport.sendto(data, (addr[0], 16354))  # bot only listens on this port

if __name__ == "__main__":
    main()