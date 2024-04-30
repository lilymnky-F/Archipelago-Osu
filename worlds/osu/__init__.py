from BaseClasses import Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from .Items import OsuItem, item_data_table, item_table, osu_song_data, osu_song_pool
from .Locations import OsuLocation, location_table, location_data_table
from Options import PerGameCommonOptions  # Muse Dash uses this for a type (where I don't) but I'm having an error
from typing import ClassVar               # where the "Type" Import below breaks if I remove this, so I'm ignoring it!
from .Options import OsuOptions
from .Regions import region_data_table
from math import floor
from multiprocessing import Process
from ..LauncherComponents import Component, components, Type


def run_client():
    from worlds.osu.Client import main
    p = Process(target=main)
    p.start()


components.append(Component("osu!Client", func=run_client, component_type=Type.CLIENT))


class OsuWebWorld(WebWorld):
    theme = "partyTime"
    tutorials = [
        Tutorial(
            tutorial_name="WIP",
            description="A guide to playing osu!ap.",
            language="English",
            file_name="guide_en.md",
            link="guide/en",
            authors=["Kanave"]
        )
    ]


class OsuWorld(World):
    """
    osu! is a free to play rhythm game featuring 4 modes, an online ranking system/statistics,
    and songs downloadable from its website.
    """

    # Lots of code is taken from Mushdash, Clique, and various other APworlds
    game = "osu!"
    options_dataclass = OsuOptions
    options: OsuOptions
    data_version = 3
    web = OsuWebWorld()

    location_name_to_id = location_table
    item_name_to_id = item_table

    song_pool: list
    song_data: list
    pairs = dict
    starting_songs: list
    included_songs: list
    location_count: int
    disallowed_modes: list
    disable_difficulty_reduction: bool

    def generate_early(self):
        self.pairs = {}
        self.song_pool = osu_song_pool.copy()
        self.song_data = osu_song_data.copy()
        self.disallowed_modes = []
        self.starting_songs = []
        self.included_songs = []
        self.disable_difficulty_reduction = bool(self.options.disable_difficulty_reduction.value)
        for i in zip(['osu', 'fruits', 'taiko', '4k', '7k'], [self.options.exclude_standard, self.options.exclude_catch, self.options.exclude_taiko, self.options.exclude_4k, self.options.exclude_7k]):
            if i[1]:
                self.disallowed_modes.append(i[0])
        if self.options.exclude_other_keys:
            self.disallowed_modes.extend([f'{x}k' for x in range(1, 19) if x not in [4, 7]])
        starting_song_count = self.options.starting_songs
        additional_song_count = self.options.additional_songs
        for song in self.song_pool[:starting_song_count]:
            self.starting_songs.append(song)
        for song in self.song_pool[starting_song_count:additional_song_count+starting_song_count]:
            self.included_songs.append(song)

        # Pair the Generic Songs to their proper Songs
        self.get_eligible_songs()
        if len(self.song_data) < len(self.starting_songs + self.included_songs + ["Victory"]):
            raise Exception(f"Player {self.player}'s settings cannot generate enough songs")
        self.random.shuffle(self.song_data)
        for generic_song, osu_song in zip((self.starting_songs + self.included_songs + ["Victory"]), self.song_data):
            self.pairs[generic_song] = osu_song

        for song in self.starting_songs:
            self.multiworld.push_precollected(self.create_item(song))

        self.location_count = len(self.starting_songs) + len(self.included_songs)
        location_multiplier = 1 + (self.get_additional_item_percentage() / 100.0)
        self.location_count = floor(self.location_count * location_multiplier)

        minimum_location_count = len(self.included_songs) + self.get_music_sheet_count()
        if self.location_count < minimum_location_count:
            self.location_count = minimum_location_count

    def get_eligible_songs(self) -> None:
        marked_for_removal = []
        for beatmapset in self.song_data:
            if not self.check_eligibility(beatmapset):
                marked_for_removal.append(beatmapset)

        for beatmapset in marked_for_removal:
            self.song_data.remove(beatmapset)

    def check_eligibility(self, beatmapset):
        if beatmapset["nsfw"] or beatmapset["length"] > self.options.maximum_length:
            return False
        for difficulty in beatmapset["beatmaps"]:
            if difficulty['mode'] not in self.disallowed_modes and self.options.minimum_difficulty <= difficulty['sr']*100 <= self.options.maximum_difficulty:
                return True
        return False

    def create_item(self, name: str) -> OsuItem:
        return OsuItem(name, item_data_table[name].type, item_data_table[name].code, self.player)

    def create_items(self) -> None:
        song_keys_in_pool = self.included_songs.copy()

        # Note: Item count will be off if plando is involved.
        item_count = self.get_music_sheet_count()

        # First add all goal song tokens
        for _ in range(0, item_count):
            self.multiworld.itempool.append(self.create_item("Performance Points"))

        # Next fill all remaining slots with song items
        needed_item_count = self.location_count
        while item_count < needed_item_count:
            # If we have more items needed than keys, just iterate the list and add them all
            if len(song_keys_in_pool) <= needed_item_count - item_count:
                for key in song_keys_in_pool:
                    self.multiworld.itempool.append(self.create_item(key))

                item_count += len(song_keys_in_pool)
                continue

            # Otherwise add a random assortment of songs
            self.random.shuffle(song_keys_in_pool)
            for i in range(0, needed_item_count - item_count):
                self.multiworld.itempool.append(self.create_item(song_keys_in_pool[i]))

            item_count = needed_item_count

    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
        song_select_region = Region("Song Select", self.player, self.multiworld)
        self.multiworld.regions += [menu_region, song_select_region]
        menu_region.connect(song_select_region)

        all_selected_locations = self.starting_songs.copy()
        included_song_copy = self.included_songs.copy()

        self.random.shuffle(included_song_copy)
        all_selected_locations.extend(included_song_copy)

        two_item_location_count = self.location_count - len(all_selected_locations)

        # Make a region per song/album, then adds 1-2 item locations to them
        for i in range(0, len(all_selected_locations)):
            name = all_selected_locations[i]
            region = Region(name, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            song_select_region.connect(region, name, lambda state, place=name: state.has(place, self.player))

            # Up to 2 Locations are defined per song
            region.add_locations({name + " (Item 1)": location_data_table[name + " (Item 1)"].address}, OsuLocation)
            if i < two_item_location_count:
                region.add_locations({name + " (Item 2)": location_data_table[name + " (Item 2)"].address}, OsuLocation)

    def get_filler_item_name(self) -> str:
        return "Circle"

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: \
            state.has("Performance Points", self.player, self.get_music_sheet_win_count())

    def get_music_sheet_count(self) -> int:
        multiplier = self.options.performance_points_count_percentage / 100.0
        song_count = (len(self.starting_songs) * 2) + len(self.included_songs)
        return max(1, floor(song_count * multiplier))

    def get_music_sheet_win_count(self) -> int:
        multiplier = self.options.performance_points_win_count_percentage.value / 100.0
        sheet_count = self.get_music_sheet_count()
        return max(1, floor(sheet_count * multiplier))

    def get_additional_item_percentage(self) -> int:
        return 80

    def fill_slot_data(self):
        return {
            "Pairs": self.pairs,
            "PreformancePointsNeeded": self.get_music_sheet_win_count(),
            "DisableDifficultyReduction": self.disable_difficulty_reduction
        }