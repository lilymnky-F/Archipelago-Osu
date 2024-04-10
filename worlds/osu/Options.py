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


class MinimumDifficulty(Range):
    """Atleast 1 difficulty of each included song will have a Star Rating between this and the Maximum.
    Star Ratings are multipled by 100, ie: a Star Rating of 1.23 will be 123
    """
    range_start = 0
    range_end = 1000
    default = 0
    display_name = "Minimum Star Rating"


class MaximumDifficulty(Range):
    """Atleast 1 difficulty of each included song will have a Star Rating between this and the Minimum.
    Star Ratings are multipled by 100, ie: a Star Rating of 1.23 will be 123
    """
    range_start = 0
    range_end = 1000
    default = 1000
    display_name = "Maximum Star Rating"


class MaximumLength(Range):
    """Maximum Length a Song can be, in seconds.
    """
    range_start = 0
    range_end = 2200
    default = 300
    display_name = "Maximum Length"


class DisableDifficultyReduction(Toggle):
    """Prevents plays using difficulty reduction mods from sending checks. Doesn't currently Work."""
    display_name = "Disable Difficulty Reduction"


class DisableStandard(Toggle):
    """Ignores Standard Difficultys when Generating"""
    display_name = "Exclude Standard"


class DisableCatch(Toggle):
    """Ignores Catch The Beat Difficultys when Generating"""
    display_name = "Exclude Catch The Beat"


class DisableTaiko(Toggle):
    """Ignores Taiko Difficultys when Generating"""
    display_name = "Exclude Taiko"


class DisableMania(Toggle):
    """Ignores Mania Difficultys when Generating"""
    display_name = "Exclude Mania"


@dataclass
class OsuOptions(PerGameCommonOptions):
    starting_songs: StartingSongs
    additional_songs: AdditionalSongs
    disable_difficulty_reduction: DisableDifficultyReduction
    maximum_difficulty: MaximumDifficulty
    minimum_difficulty: MinimumDifficulty
    maximum_length: MaximumLength
    exclude_standard: DisableStandard
    exclude_catch: DisableCatch
    exclude_taiko: DisableTaiko
    exclude_mania: DisableMania
