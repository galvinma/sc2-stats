from enum import Enum


class RegionId(Enum):
    US = 1
    EU = 2
    KO = 3
    CN = 5


class QueueId(Enum):
    WoL_1v1 = 1
    WoL_2v2 = 2
    WoL_3v3 = 3
    WoL_4v4 = 4
    HotS_1v1 = 101
    HotS_2v2 = 102
    HotS_3v3 = 103
    HotS_4v4 = 104
    LotV_1v1 = 201
    LotV_2v2 = 202
    LotV_3v3 = 203
    LotV_4v4 = 204
    LotV_Archon = 206


class TeamType(Enum):
    ARRANGED = 1
    RANDOM = 2


class LeagueId(Enum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2
    PLATINUM = 3
    DIAMOND = 4
    MASTER = 5
    GRANDMASTER = 6
