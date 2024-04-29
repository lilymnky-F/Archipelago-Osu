from __future__ import annotations
import os
import sys
import asyncio
import shutil
import requests
import aiohttp
import webbrowser

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

    def _cmd_resync(self):
        """Manually trigger a resync. Usually Shouldn't be needed"""
        self.output(f"Syncing items.")
        self.ctx.syncing = True

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

    def _cmd_songs(self):
        """Display all songs in logic."""
        indexes = self.get_available_ids()
        self.output(f"You Have {count_item(self.ctx, 726999999)} Performance Points, you need {self.ctx.preformance_points_needed} to unlock your goal.")
        self.output(f"You currently have {len(indexes)} songs in Logic")
        for i in indexes:
            song = list(self.ctx.pairs.keys())[i]
            beatmapset = self.ctx.pairs[song]
            self.output(f"{song}: {beatmapset['title']} (ID: {beatmapset['id']})")

    def _cmd_all_songs(self):
        """Displays all songs included in current generation."""
        played_songs = self.get_played_songs()
        self.output(f"You have played {len(played_songs)}/{len(self.ctx.pairs)-1} songs")
        for song in self.ctx.pairs:
            beatmapset = self.ctx.pairs[song]
            self.output(f"{song}: {beatmapset['title']} (ID: {beatmapset['id']}) {'(passed)' if song in played_songs else ''}")

    def _cmd_update(self, mode=''):
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
            request = f"https://osu.ppy.sh/api/v2/users/{os.environ['PLAYER_ID']}/scores/recent?include_fails=1&limit=100"
        except KeyError:
            self.output("Please set a Player ID.")
            return
        # Add Mode to request, otherwise it will use the user's default
        if mode and mode.lower() in self.mode_names.keys():
            request += f"&mode={self.mode_names[mode.lower()]}"
        scores = requests.get(request, headers={"Accept": "application/json", "Content-Type": "application/json",
                                                "Authorization": f"Bearer {token}"})
        # Get Scores with Token
        try:
            score_list = scores.json()
        except (KeyError, IndexError):
            self.output("Error Retrieving plays, Check your API Key.")
            return
        if not score_list:
            self.output("No Plays Found. Check the Gamemode")
            return
        found = False
        for score in score_list:
            if score['created_at'] in self.ctx.last_scores:
                if not found:
                    self.output("No New Plays Found.")
                return
            found = True
            self.ctx.last_scores.append(score['created_at'])
            if len(self.ctx.last_scores) > 20:
                self.ctx.last_scores.pop(0)
            self.check_location(score)

    def _cmd_download(self, number=''):
        """Downloads the given song number in '/show_songs', or 'victory' for the goal song."""
        if number.lower() == 'next':
            if len(self.get_available_ids()) > 0:
                number = self.get_available_ids()[0]+1
            else:
                self.output("You have no songs to download")
                return
        try:
            song_number = int(number)-1
        except ValueError:
            if not (number.lower().capitalize() == 'Victory'):
                self.output("Please Give a Number or 'Victory'")
                return
            song_number = -1
        try:
            song = list(self.ctx.pairs.keys())[song_number]
        except IndexError:
            self.output("Use the Song Numbers in '/show_songs' (Not the IDs)")
            return
        beatmapset = self.ctx.pairs[song]
        self.output(f"Downloading {song}: {beatmapset['title']} (ID: {beatmapset['id']}) as '{beatmapset['id']} {beatmapset['artist']} - {beatmapset['title']}.osz'")
        asyncio.create_task(self.download_beatmapset(beatmapset))

    def _cmd_auto_track(self, mode=''):
        """Toggles Auto Tracking for the Given Mode"""
        if mode.lower() in self.mode_names.keys():
            if self.mode_names[mode.lower()] not in self.ctx.auto_modes:
                self.ctx.auto_modes.append(self.mode_names[mode.lower()])
                return
            self.ctx.auto_modes.remove(self.mode_names[mode.lower()])
            return
        self.output('Please Supply a Valid Mode')

    def _cmd_test(self, number=''):
        message = [{"cmd": 'LocationChecks', "locations": [int(number)]}]
        asyncio.create_task(self.ctx.send_msgs(message))

    def get_available_ids(self):
        # Gets the Index of each Song the player has but has not played
        incomplete_items = []
        for item in self.ctx.items_received:
            song_index = item.item-727000000
            location_id = (song_index*2)+727000000
            if (location_id in self.ctx.missing_locations or location_id+1 in self.ctx.missing_locations) and song_index not in incomplete_items:
                incomplete_items.append(song_index)
        if count_item(self.ctx, 726999999) >= self.ctx.preformance_points_needed:
            incomplete_items.append(-1)
        incomplete_items.sort()
        return incomplete_items

    def get_played_ids(self):
        # Gets the Index of each Song the player has played
        played_items = []
        for item in self.ctx.items_received:
            song_index = item.item-727000000
            location_id = (song_index*2)+727000000
            if location_id not in self.ctx.missing_locations and location_id+1 not in self.ctx.missing_locations:
                played_items.append(song_index)
        played_items.sort()
        return played_items
    
    def get_played_songs(self):
        # Gets the Song value of each Song the player has played
        played_ids = self.get_played_ids()
        if -1 in played_ids:
            played_ids.remove(-1) # Remove victory song from played songs as it was somehow showing up
        played_songs = []
        for played in played_ids:
            played_songs.append(list(self.ctx.pairs.keys())[played])
        return played_songs

    def check_location(self, score):
        self.output(score['beatmapset']['title'] + " " + score['beatmap']['version'] + f' Passed: {score["passed"]}')
        # Check if the score is a pass, then check if it's in the AP
        if not score['passed']:
            # self.output("You cannot check a location without passing the song")
            return
        if self.ctx.disable_difficulty_reduction and any(x in score['mods'] for x in ['NF', 'EZ', 'HT']):
            self.output("Your current settings do not allow difficulty reduction mods.")
            return
        for song in self.ctx.pairs:
            if self.ctx.pairs[song]['id'] == score['beatmapset']['id']:
                self.output(f'Play Matches {song}')
                if song == "Victory":
                    if count_item(self.ctx, 726999999) >= self.ctx.preformance_points_needed:
                        with open(os.path.join(self.ctx.game_communication_path, 'victory'), 'w') as f:
                            f.close()
                        return
                    self.output("You don't have enough preformance points")
                    return
                if not count_item(self.ctx, 727000000 + list(self.ctx.pairs.keys()).index(song)):
                    self.output("You don't have this song unlocked")
                    return
                for i in range(2):
                    location_id = 727000000 + (2 * list(self.ctx.pairs.keys()).index(song)) + i
                    if location_id in self.ctx.missing_locations:
                        filename = f"send{location_id}"
                        with open(os.path.join(self.ctx.game_communication_path, filename), 'w') as f:
                            f.close()

    async def download_beatmapset(self, beatmapset):
        print(f'Downloading {beatmapset["artist"]} - {beatmapset["title"]} ({beatmapset["id"]})')
        async with aiohttp.request("GET", f"https://beatconnect.io/b/{beatmapset['id']}") as req:
            content = await req.read()
        if len(content) < 400:
            self.output(f'Error Downloading {beatmapset["id"]} {beatmapset["artist"]} - {beatmapset["title"]}.osz')
            self.output('Please Manually Add the Map or Try Again Later.')
            return
        f = f'{beatmapset["id"]} {beatmapset["artist"]} - {beatmapset["title"]}.osz'
        filename = "".join(i for i in f if i not in "\/:*?<>|\"")
        path = self.ctx.game_communication_path + ' config'
        with open(os.path.join(path, filename), 'wb') as f:
            f.write(content)
        webbrowser.open(os.path.join(path, filename))


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
        self.last_scores: list = []
        self.auto_modes: list[str] = []
        self.token: str = ''
        self.disable_difficulty_reduction: bool = False
        self.all_locations: list[int] = []
        self.preformance_points_needed = 9999  # High Enough to never accidently trigger if the slot data fails
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
                self.disable_difficulty_reduction = slot_data.get('DisableDifficultyReduction', False)
            if not os.path.exists(self.game_communication_path):
                os.makedirs(self.game_communication_path)
            for ss in self.checked_locations:
                filename = f"send{ss}"
                with open(os.path.join(self.game_communication_path, filename), 'w') as f:
                    f.close()

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


def count_item(ctx, code) -> int:
    current = 0
    for item in ctx.items_received:
        if item.item == code:
            current += 1
    return current


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


async def auto_get_last_scores(ctx, mode=''):
    # Make URl for the request
    try:
        request = f"https://osu.ppy.sh/api/v2/users/{os.environ['PLAYER_ID']}/scores/recent?include_fails=1&limit=100"
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
            print(score_list, "a")
            print(scores)
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
        if len(ctx.last_scores) > 100:
            ctx.last_scores.pop(0)
        check_location(ctx, score)


def check_location(ctx, score):
    if not score['passed']:
        return
    if ctx.disable_difficulty_reduction and any(x in score['mods'] for x in ['NF', 'EZ', 'HT']):
        return
    for song in ctx.pairs:
        if ctx.pairs[song]['id'] == score['beatmapset']['id']:
            print(f'Play Matches {song}')
            if song == "Victory":
                if count_item(ctx, 726999999) >= ctx.preformance_points_needed:
                    with open(os.path.join(ctx.game_communication_path, 'victory'), 'w') as f:
                        f.close()
                    return
                print("You don't have enough preformance points")
                return
            if not count_item(ctx, 727000000 + list(ctx.pairs.keys()).index(song)):
                print("You don't have this song unlocked")
                return
            for i in range(2):
                location_id = 727000000 + (2 * list(ctx.pairs.keys()).index(song)) + i
                if location_id in ctx.missing_locations:
                    filename = f"send{location_id}"
                    with open(os.path.join(ctx.game_communication_path, filename), 'w') as f:
                        f.close()


async def game_watcher(ctx: APosuContext):
    count = 0
    while not ctx.exit_event.is_set():
        if ctx.syncing:
            sync_msg = [{'cmd': 'Sync'}]
            if ctx.locations_checked:
                sync_msg.append({"cmd": "LocationChecks", "locations": list(ctx.locations_checked)})
            await ctx.send_msgs(sync_msg)
            ctx.syncing = False
        if count >= 30:
            for mode in ctx.auto_modes:
                await auto_get_last_scores(ctx, mode)
                await asyncio.sleep(0.2)
            count = 0
        count += 1
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