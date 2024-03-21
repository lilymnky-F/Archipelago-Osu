from __future__ import annotations
import os
import sys
import asyncio
import shutil
import requests

import ModuleUpdate

ModuleUpdate.update()

import Utils

if __name__ == "__main__":
    Utils.init_logging("osu!Client", exception_logger="Client")

from NetUtils import NetworkItem, ClientStatus
from CommonClient import gui_enabled, logger, get_base_parser, ClientCommandProcessor, \
    CommonContext, server_loop


class APosuClientCommandProcessor(ClientCommandProcessor):
    def __init__(self, ctx: APosuContext):
        self.ctx = ctx

    def _cmd_slot_data(self)   :
        """Show Slot Data, For Debug Purposes. Probably don't run this"""
        # self.output(f"Data: {str(self.ctx.pairs)}")
        self.output(self.ctx.items_received)
        pass

    def _cmd_resync(self)   :
        """Manually trigger a resync."""
        self.output(f"Syncing items.")
        self.ctx.syncing = True

    def _cmd_set_api_key(self, key=""):
        """Sets the Client Secret, generated in the "OAuth" Section of Account Settings"""
        os.environ['API_KEY'] = key
        self.output(f"Set to {key}")

    def _cmd_set_client_id(self, id=""):
        """Sets the Client ID, generated in the "OAuth" Section of Account Settings"""
        os.environ['CLIENT_ID'] = id
        self.output(f"Set to {id}")

    def _cmd_set_player_id(self, id=""):
        """Sets the player's user ID, found in the URL of their profile"""
        os.environ['PLAYER_ID'] = id
        self.output(f"Set to {id}")

    def _cmd_get_last_scores(self, mode=''):
        """Gets the player's last score, in a given gamemode or their set default"""

        # Requests a token using the user's Client ID and Secret
        try:
            authreq = requests.post("https://osu.ppy.sh/oauth/token",
                                    headers={"Accept": "application/json",
                                             "Content-Type": "application/x-www-form-urlencoded"},
                                    data=f"client_id={os.environ['CLIENT_ID']}&client_secret={os.environ['API_KEY']}&grant_type=client_credentials&scope=public")
            token = authreq.json()["access_token"]
        except KeyError:
            self.output("Please set an API Key and Client ID.")
            return
        # Make URl for the request
        try:
            request = f"https://osu.ppy.sh/api/v2/users/{os.environ['PLAYER_ID']}/scores/recent?include_fails=1&limit=15"
        except KeyError:
            self.output("Please set a Player ID.")
            return
        # Add Mode to request, otherwise it will use the user's default
        if mode and mode.lower() in ['fruits', 'mania', 'osu', 'taiko']:
            request += f"&mode={mode}"
        scores = requests.get(request, headers={"Accept": "application/json", "Content-Type": "application/json",
                                                "Authorization": f"Bearer {token}"})
        # Get Scores with Token
        try:
            score = scores.json()[0]
        except KeyError:
            if scores.ok:
                self.output("No plays found.")
                return
            self.output("Error Retrieving plays, Check your API Key.")
            return
        self.output(score['beatmapset']['title'] + " " + score['beatmap']['version'] + f' Passed: {score["passed"]}')
        # Check if the score is a pass, then check if it's in the AP
        if score['passed']:
            for song in self.ctx.pairs:
                if self.ctx.pairs[song]['id'] == score['beatmapset']['id']:
                    self.output(f'Play Matches {song}')
                    for i in range(2):
                        location_id = 727000000 + (2 * list(self.ctx.pairs.keys()).index(song))+i
                        self.output(location_id)
                        self.output(self.ctx.all_locations)
                        if location_id in self.ctx.all_locations:
                            filename = f"send{location_id}"
                            with open(os.path.join(self.ctx.game_communication_path, filename), 'w') as f:
                                f.close()



class APosuContext(CommonContext):
    command_processor: int = APosuClientCommandProcessor
    game = "osu!"
    items_handling = 0b111  # full remote
    want_slot_data = True

    def __init__(self, server_address, password):
        super(APosuContext, self).__init__(server_address, password)
        self.send_index: int = 0
        self.syncing = False
        self.awaiting_bridge = False
        self.pairs: dict = {}
        self.all_locations: list[int] = []
        self.preformance_points_needed = 9999 # High Enough to never accidently trigger if the slot data fails
        # self.game_communication_path: files go in this path to pass data between us and the actual game
        if "localappdata" in os.environ:
            self.game_communication_path = os.path.expandvars(r"%localappdata%/APosu")
        else:
            # not windows. game is an exe so let's see if wine might be around to run it
            if "WINEPREFIX" in os.environ:
                wineprefix = os.environ["WINEPREFIX"]
            elif shutil.which("wine") or shutil.which("wine-stable"):
                wineprefix = os.path.expanduser(
                    "~/.wine")  # default root of wine system data, deep in which is app data
            else:
                msg = "APosuClient couldn't detect system type. Unable to infer required game_communication_path"
                logger.error("Error: " + msg)
                Utils.messagebox("Error", msg, error=True)
                sys.exit(1)
            self.game_communication_path = os.path.join(
                wineprefix,
                "drive_c",
                os.path.expandvars("users/$USER/Local Settings/Application Data/APosu"))

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(APosuContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    async def connection_closed(self):
        await super(APosuContext, self).connection_closed()
        for root, dirs, files in os.walk(self.game_communication_path):
            for file in files:
                if file.find("obtain") <= -1:
                    os.remove(root + "/" + file)

    @property
    def endpoints(self):
        if self.server:
            return [self.server]
        else:
            return []

    async def shutdown(self):
        await super(APosuContext, self).shutdown()
        for root, dirs, files in os.walk(self.game_communication_path):
            for file in files:
                if file.find("obtain") <= -1:
                    os.remove(root + "/" + file)

    def on_package(self, cmd: str, args: dict):
        if cmd in {"Connected"}:
            print(args)
            slot_data = args.get('slot_data', None)
            if slot_data:
                self.pairs = slot_data.get('Pairs', {})
                self.preformance_points_needed = slot_data.get('PreformancePointsNeeded', 0)
            if not os.path.exists(self.game_communication_path):
                os.makedirs(self.game_communication_path)
            for ss in self.checked_locations:
                filename = f"send{ss}"
                with open(os.path.join(self.game_communication_path, filename), 'w') as f:
                    f.close()
            checked_locations = args.get('checked_locations', [])

            missing_locations = args.get('missing_locations', [])
            self.all_locations = missing_locations+checked_locations

        if cmd in {"ReceivedItems"}:
            start_index = args["index"]
            if start_index != len(self.items_received):
                for item in args['items']:
                    filename = f"AP_{str(NetworkItem(*item).location)}PLR{str(NetworkItem(*item).player)}.item"
                    with open(os.path.join(self.game_communication_path, filename), 'w') as f:
                        f.write(str(NetworkItem(*item).item))
                        f.close()

        if cmd in {"RoomUpdate"}:
            if "checked_locations" in args:
                for ss in self.checked_locations:
                    filename = f"send{ss}"
                    with open(os.path.join(self.game_communication_path, filename), 'w') as f:
                        f.close()

    def run_gui(self):
        """Import kivy UI system and start running it as self.ui_task."""
        from kvui import GameManager

        class ChecksFinderManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago")
            ]
            base_title = "Archipelago osu! Client"

        self.ui = ChecksFinderManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")


async def game_watcher(ctx: APosuContext):
    while not ctx.exit_event.is_set():
        if ctx.syncing:
            sync_msg = [{'cmd': 'Sync'}]
            if ctx.locations_checked:
                sync_msg.append({"cmd": "LocationChecks", "locations": list(ctx.locations_checked)})
            await ctx.send_msgs(sync_msg)
            ctx.syncing = False
        sending = []
        victory = False
        for root, dirs, files in os.walk(ctx.game_communication_path):
            for file in files:
                if file.find("send") > -1:
                    st = file.split("send", -1)[1]
                    sending = sending + [(int(st))]
                if file.find("victory") > -1:
                    victory = True
        ctx.locations_checked = sending
        message = [{"cmd": 'LocationChecks', "locations": sending}]
        await ctx.send_msgs(message)
        if not ctx.finished_game and victory:
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            ctx.finished_game = True
        await asyncio.sleep(0.1)


if __name__ == '__main__':
    async def main(args):
        ctx = APosuContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        progression_watcher = asyncio.create_task(
            game_watcher(ctx), name="ChecksFinderProgressionWatcher")

        await ctx.exit_event.wait()
        ctx.server_address = None

        await progression_watcher

        await ctx.shutdown()


    import colorama

    parser = get_base_parser(description="ChecksFinder Client, for text interfacing.")

    args, rest = parser.parse_known_args()
    colorama.init()
    asyncio.run(main(args))
    colorama.deinit()
