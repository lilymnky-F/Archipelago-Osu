from Options import Toggle, Option, Range, Choice, DeathLink, ItemSet, OptionSet, PerGameCommonOptions
from dataclasses import dataclass


class StartingSongs(Range):
    """The number of songs that will be automatically unlocked at the start of a run."""
    range_start = 3
    range_end = 10
    default = 5
    display_name = "Starting Song Count"


class AdditionalSongs(Range):
    """The total number of songs that will be placed in the randomization pool.
    - This does not count any starting songs or the goal song.
    """
    range_start = 15
    range_end = 80
    default = 40
    display_name = "Additional Song Count"


@dataclass
class OsuOptions(PerGameCommonOptions):
    starting_songs: StartingSongs
    additional_songs: AdditionalSongs
