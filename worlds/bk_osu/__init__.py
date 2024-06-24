from BaseClasses import Tutorial
from worlds.AutoWorld import WebWorld, World
from multiprocessing import Process
from ..LauncherComponents import Component, components, Type


def run_client():
    from worlds.bk_osu.Client import main
    p = Process(target=main)
    p.start()


components.append(Component("osu! BK Client", func=run_client, component_type=Type.CLIENT))


class BkOsuWebWorld(WebWorld):
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


class BkOsuWorld(World):
    """
    osu! is a free to play rhythm game featuring 4 modes, an online ranking system/statistics,
    and songs downloadable from its website.
    """

    # This init is from apsudoku
    game = "bk osu!"
    web = BkOsuWebWorld()

    item_name_to_id = {}
    location_name_to_id = {}

    @classmethod
    def stage_assert_generate(cls, multiworld):
        raise Exception(
            "You cannot generate with BK osu! Please use the 'osu!' apworld instead.")
