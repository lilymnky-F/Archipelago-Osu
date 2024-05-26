from Options import Toggle, Option, Range, Choice, DeathLink, ItemSet, OptionSet, PerGameCommonOptions
from dataclasses import dataclass
from .Items import get_song_data


class StartingSongs(Range):
    """The number of songs that will be automatically unlocked at the start of a run."""
    range_start = 3
    range_end = 10
    default = 5
    display_name = "Starting Song Count"


class AdditionalSongs(Range):
    """The total number of songs that will be placed in the randomization pool.
    - This does not count any starting songs or the goal song.
    Not all gamemodes have enough songs for the maximum amount on their own.
    """
    range_start = 15
    range_end = 400
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
    """Prevents plays using difficulty reduction mods from sending checks."""
    display_name = "Disable Difficulty Reduction"


class EnableExplicitLyrics(Toggle):
    """Allows Songs with 18+ Lyrics to generate.
    While this can be played on the main Archipelago Server, Streaming them there is not reccomended."""
    display_name = "Include Explicit Lyrics"


class EnableLoved(Toggle):
    """Allows Loved Beatmaps to Appear when Generating. Not Reccomended with 'Disable Difficulty Reduction' Enabled."""
    display_name = "Enable Loved Beatmaps"


class DisableStandard(Toggle):
    """Ignores Standard Difficultys when Generating"""
    display_name = "Exclude Standard"


class DisableCatch(Toggle):
    """Ignores Catch The Beat Difficultys when Generating"""
    display_name = "Exclude Catch The Beat"


class DisableTaiko(Toggle):
    """Ignores Taiko Difficultys when Generating"""
    display_name = "Exclude Taiko"


class Disable4k(Toggle):
    """Ignores 4-Key Mania Difficultys when Generating"""
    display_name = "Exclude 4k"


class Disable7k(Toggle):
    """Ignores 7-Key Mania Difficultys when Generating"""
    display_name = "Exclude 7k"


class DisableMiscKeymodes(Toggle):
    """Ignores Mania Difficultys of Key Counts other than 4 and 7 when Generating"""
    display_name = "Exclude Miscellaneous Key Counts"


# next few taken pretty much or entirely from Muse Dash
class AdditionalItemPercentage(Range):
    """The percentage of songs that will have 2 items instead of 1 when completing them.
    Starting Songs will always have 2 items.
    Locations will be filled with duplicate songs if there are not enough items.
    """
    display_name = "Additional Item %"
    range_start = 50
    default = 80
    range_end = 100


class PerformancePointsPercentage(Range):
    """Collecting enough 'Performace Points' will unlock the goal song needed for completion.
    This option controls how many are in the item pool, based on the total number of songs.
    The 'Performance Points' in this multiworld are unrelated to your accounts PP Score"""
    range_start = 10
    range_end = 40
    default = 20
    display_name = "Performance Points Percentage"


class PerformancePointsWinCountPercentage(Range):
    """The percentage of Performance Points in the item pool required to unlock the winning song."""
    range_start = 50
    range_end = 100
    default = 80
    display_name = "Percentage of Performace Points Needed"


class IncludeSongs(OptionSet):
    """List of Beatmapset IDs to include. Will add songs in ascending order by ID after the starting songs.
    IE: If you have 5 starting songs, the first ID will be song 6
    """
    display_name = "Include Songs"
    valid_keys = {str(beatmapset['id']) for beatmapset in get_song_data()}


class ExcludeSongs(OptionSet):
    """List of Beatmapset IDs to exclude. Listed Beatmapset IDs cannot appear in the Rando
    """
    display_name = "Exclude Songs"
    valid_keys = {str(beatmapset['id']) for beatmapset in get_song_data()}


@dataclass
class OsuOptions(PerGameCommonOptions):
    starting_songs: StartingSongs
    additional_songs: AdditionalSongs
    additional_item_percentage: AdditionalItemPercentage
    disable_difficulty_reduction: DisableDifficultyReduction
    maximum_difficulty: MaximumDifficulty
    minimum_difficulty: MinimumDifficulty
    maximum_length: MaximumLength
    exclude_standard: DisableStandard
    exclude_catch: DisableCatch
    exclude_taiko: DisableTaiko
    exclude_4k: Disable4k
    exclude_7k: Disable7k
    exclude_other_keys: DisableMiscKeymodes
    performance_points_count_percentage: PerformancePointsPercentage
    performance_points_win_count_percentage: PerformancePointsWinCountPercentage
    explicit_lyrics: EnableExplicitLyrics
    enable_loved: EnableLoved
    include_songs: IncludeSongs
    exclude_songs: ExcludeSongs
