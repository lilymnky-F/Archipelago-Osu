from __future__ import annotations
import os
import sys
import asyncio
import shutil
import aiohttp
import random

import ModuleUpdate

ModuleUpdate.update()

import Utils

if __name__ == "__main__":
    Utils.init_logging("osu! bk Client", exception_logger="Client")

from NetUtils import NetworkItem, ClientStatus
from CommonClient import gui_enabled, logger, get_base_parser, ClientCommandProcessor, \
    CommonContext, server_loop


class APosuClientCommandProcessor(ClientCommandProcessor):
    def __init__(self, ctx: APosuContext):
        self.ctx = ctx
        self.mode_names = {'fruits': 'fruits',
                           'catch': 'fruits',
                           'ctb': 'fruits',
                           '4k': 'mania',
                           '7k': 'mania',
                           'o!m': 'mania',
                           'mania': 'mania',
                           'osu': 'osu',
                           'std': 'osu',
                           'standard': 'osu',
                           'taiko': 'taiko',
                           '': ''}

    # def _cmd_slot_data(self):
    #    """Show Slot Data, For Debug Purposes. Probably don't run this"""
    #    self.output(f"Data: {str(self.ctx.pairs)}")
    #    pass


    def _cmd_set_api_key(self, key=""):
        """Sets the Client Secret, generated in the "OAuth" Section of Account Settings"""
        os.environ['API_KEY'] = key
        self.output(f"Set to ##################")

    def _cmd_set_client_id(self, id=""):
        """Sets the Client ID, generated in the "OAuth" Section of Account Settings"""
        os.environ['CLIENT_ID'] = id
        self.output(f"Set to {id}")

    def _cmd_set_player_id(self, id=""):
        """Sets the player's user ID, found in the URL of their profile"""
        os.environ['PLAYER_ID'] = id
        self.output(f"Set to {id}")

    def _cmd_save_keys(self):
        """Saves the player's current IDs"""
        filename = "config"
        path = self.ctx.game_communication_path+' config'
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, filename), 'w') as f:
            for info in [os.environ['API_KEY'], os.environ['CLIENT_ID'], os.environ['PLAYER_ID']]:
                f.write(info)
                f.write(" ")
        self.output("Saved Current Data")

    def _cmd_load_keys(self):
        """loads the player's previously saved IDs"""
        filename = "config"
        path = self.ctx.game_communication_path+' config'
        with open(os.path.join(path, filename), 'r') as f:
            data = f.read()
            d = data.split(" ")
            os.environ['API_KEY'], os.environ['CLIENT_ID'], os.environ['PLAYER_ID'] = d[0], d[1], d[2],
            self.output("Loaded Previous Data")

    def _cmd_start_hinting(self, mode=''):
        """Toggles Hint Tracking for the Given Mode (or "All"). Set/Load Keys First"""
        try:
            [os.environ['API_KEY'], os.environ['CLIENT_ID'], os.environ['PLAYER_ID']]
        except KeyError:
            self.output('Please set your Client ID, Client Secret, and Player ID')
            return
        modes = []
        if mode.lower() == 'all':
            modes = ['osu', 'fruits', 'taiko', 'mania']
        if mode.lower() in self.mode_names.keys():
            if self.mode_names[mode.lower()] in self.ctx.auto_modes:
                self.output(f'Auto Tracking Disabled{f" for {mode}" if mode else " for your default mode"}')
                self.ctx.auto_modes.remove(self.mode_names[mode.lower()])
                return
            modes = [self.mode_names[mode.lower()]]
            self.output(f'Auto Tracking Enabled{f" for {mode}" if mode else " for your default mode"}')
        if not modes:
            self.output('Please Supply a Valid Mode')
            return
        asyncio.create_task(self.prepare_hints(modes))

    def _cmd_check(self):
        """Checks how close you are to your next Hint"""
        self.output(f'You need {240-self.ctx.length_tally} more seconds, '
                    f'or {4-self.ctx.panic_tally} more songs to earn a hint.')

    async def prepare_hints(self, modes: list):
        """Marks all currently played songs to prep for hints"""
        self.output("Preparing to generate hints, do not play songs yet.")
        for mode in modes:
            await auto_get_last_scores(self.ctx, mode, check=False)
            print(mode)
            await asyncio.sleep(0.1)
        self.ctx.auto_modes += modes
        self.output('Hinting is ready, enjoy!')
        return


class APosuContext(CommonContext):
    command_processor: int = APosuClientCommandProcessor
    tags = CommonContext.tags | {"TextOnly", "HintGame"}
    game = None
    items_handling = 0b111  # receive all items for /received
    want_slot_data = True  # Can't use game specific slot_data

    def __init__(self, server_address, password):
        super(APosuContext, self).__init__(server_address, password)
        self.send_index: int = 0
        self.syncing = False
        self.awaiting_bridge = False
        self.seen: list[int] = []
        self.count: dict = {}
        self.last_scores: list = []
        self.auto_modes: list[str] = []
        self.auto_download: bool = False
        self.token: str = ''
        self.length_tally: int = 0
        self.panic_tally: int = 0
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
            if not os.path.exists(self.game_communication_path):
                os.makedirs(self.game_communication_path)

    def run_gui(self):
        """Import kivy UI system and start running it as self.ui_task."""
        from kvui import GameManager

        class OsuManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago")
            ]
            base_title = "Archipelago osu! Client"

        self.ui = OsuManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")


async def get_token(ctx):
    try:
        async with aiohttp.request("POST", "https://osu.ppy.sh/oauth/token",
                                    headers={"Accept": "application/json",
                                    "Content-Type": "application/x-www-form-urlencoded"},
                                    data=f"client_id={os.environ['CLIENT_ID']}&client_secret={os.environ['API_KEY']}"
                                         f"&grant_type=client_credentials&scope=public") as authreq:
            tokenjson = await authreq.json()
            print(tokenjson)
            ctx.token = tokenjson['access_token']
    except KeyError:
        print('nokey')
        return


async def auto_get_last_scores(ctx, mode='', check=True):
    # Make URl for the request
    try:
        request = f"https://osu.ppy.sh/api/v2/users/{os.environ['PLAYER_ID']}/scores/recent?include_fails=1&limit=10"
    except KeyError:
        print('No Player ID')
        return
    # Add Mode to request, otherwise it will use the user's default
    if mode:
        request += f"&mode={mode}"
    if not ctx.token:
        await get_token(ctx)
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {ctx.token}"}
    async with aiohttp.request("GET", request, headers=headers) as scores:
        try:
            score_list = await scores.json()
        except (KeyError, IndexError):
            await get_token(ctx)
            print("Error Retrieving plays, Check your API Key.")
            return
    if not score_list:
        print("No Plays Found. Check the Gamemode")
        return
    found = False
    for score in score_list:
        if score['created_at'] in ctx.last_scores:
            if not found:
                print("No New Plays Found.")
            return
        found = True
        ctx.last_scores.append(score['created_at'])
        if len(ctx.last_scores) > 400:
            ctx.last_scores.pop(0)
        if check:
            await check_location(ctx, score)


async def check_location(ctx, score):
    if not score['passed']:
        return
    if score['beatmap']['id'] in ctx.seen:
        return
    print("seen")
    ctx.seen.append(score['beatmap']['id'])
    ctx.length_tally += score['beatmap']['total_length']
    ctx.panic_tally += 1
    while ctx.length_tally > 240:
        ctx.length_tally -= 240
        ctx.panic_tally = 0
        location = random.choice(list(ctx.missing_locations))
        message = [{"cmd": 'LocationScouts', "locations": [location], 'create_as_hint': 1}]
        await ctx.send_msgs(message)
    if ctx.panic_tally > 3:
        ctx.panic_tally = 0
        ctx.length_tally = 0
        location = random.choice(list(ctx.missing_locations))
        message = [{"cmd": 'LocationScouts', "locations": [location], 'create_as_hint': 1}]
        await ctx.send_msgs(message)


async def game_watcher(ctx: APosuContext):
    count = 0
    while not ctx.exit_event.is_set():
        if count >= 30:
            for mode in ctx.auto_modes:
                await auto_get_last_scores(ctx, mode, check=True)
                await asyncio.sleep(1)
            count = 0
        count += 1
        await asyncio.sleep(0.1)


def main():
    async def _main(args):
        ctx = APosuContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        progression_watcher = asyncio.create_task(
            game_watcher(ctx), name="osu!ProgressionWatcher")

        await ctx.exit_event.wait()
        ctx.server_address = None

        await progression_watcher

        await ctx.shutdown()

    import colorama

    parser = get_base_parser(description="osu! Client, for text interfacing.")

    args, rest = parser.parse_known_args()
    colorama.init()
    asyncio.run(_main(args))
    colorama.deinit()


if __name__ == '__main__':
    main()