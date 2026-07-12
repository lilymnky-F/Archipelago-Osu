from typing import Dict, NamedTuple, Optional

from BaseClasses import Item, ItemClassification

import functools
import orjson

def load_text_file(name: str) -> str:
    import pkgutil
    return pkgutil.get_data(__name__, name).decode()

class OsuItem(Item):
    game = "osu!"


class OsuItemData(NamedTuple):
    code: Optional[int] = None
    type: ItemClassification = ItemClassification.filler


@functools.cache
def get_song_data() -> list[dict]:
    OsuSongData = load_text_file("OsuSongData.json")
    return orjson.loads(OsuSongData)


def find_beatmapset(id) -> dict:
    for beatmapset in osu_song_data:
        if beatmapset["id"] == id:
            return beatmapset
    raise ValueError("Beatmap not in Song Data")

osu_song_data = get_song_data()
osu_song_max = 520
osu_song_pool = []

item_data_table: Dict[str, OsuItemData] = {
    "Performance Points": OsuItemData(
        code=726999999,
        type=ItemClassification.progression_skip_balancing,
    ),
    "Circle": OsuItemData(
        code=726999998,
    ),
}

for i in range(osu_song_max):
    item_data_table[f"Song {i+1}"] = OsuItemData(
        code=727000000+i,
        type=ItemClassification.progression,
    )
    osu_song_pool.append(f"Song {i+1}")

item_table = {name: data.code for name, data in item_data_table.items() if data.code is not None}
