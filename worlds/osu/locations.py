from typing import NamedTuple

from BaseClasses import Location, MultiWorld

from .items import osu_song_max


class OsuLocation(Location):
    game: str = "osu!"


class OsuLocationData(NamedTuple):
    address: int | None = None
    locked_item: str | None = None


location_data_table: dict[str, OsuLocationData] = {
}

for i in range(osu_song_max):
    location_data_table[f"Song {i+1} (Item 1)"] = OsuLocationData(
        address=727000000 + (2 * i),
    )
    location_data_table[f"Song {i + 1} (Item 2)"] = OsuLocationData(
        address=727000000 + (2 * i) + 1,
    )

location_table = {name: data.address for name, data in location_data_table.items() if data.address is not None}