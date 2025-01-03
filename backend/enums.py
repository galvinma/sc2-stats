from enum import Enum


# TODO Enable support for CN region. Think this would require hitting a separate API.
class RegionId(Enum):
    US = 1
    EU = 2
    KR = 3
    # CN = 5


class RealmId(Enum):
    US = 1
    LatAm = 2
    Europe = 1
    RUssia = 2
    Korea = 1
    # Taiwan = 2
    # China = 1


# TODO Enable support for other queues
class QueueId(Enum):
    # WoL_1v1 = 1
    # WoL_2v2 = 2
    # WoL_3v3 = 3
    # WoL_4v4 = 4
    # HotS_1v1 = 101
    # HotS_2v2 = 102
    # HotS_3v3 = 103
    # HotS_4v4 = 104
    LotV_1v1 = 201
    # LotV_2v2 = 202
    # LotV_3v3 = 203
    # LotV_4v4 = 204
    # LotV_Archon = 206


# TODO Enable support for random team types
class TeamType(Enum):
    ARRANGED = 0
    # RANDOM = 1


class LeagueId(Enum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2
    PLATINUM = 3
    DIAMOND = 4
    MASTER = 5
    GRANDMASTER = 6
