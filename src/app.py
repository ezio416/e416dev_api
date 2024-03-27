# c 2024-03-25
# m 2024-03-26

from base64 import b64encode
from dateutil.parser import parse
from json import loads
from math import ceil
import os
import sqlite3 as sql
from time import sleep

from discord_webhook import DiscordEmbed, DiscordWebhook
from requests import get, post

from util import log, strip_format_codes


db_file:       str   = f'{__file__}/../../tm.db'
tm2020_app_id: str   = '86263886-327a-4328-ac69-527f0d20a237'
url_core:      str   = 'https://prod.trackmania.core.nadeo.online'
url_live:      str   = 'https://live-services.trackmania.nadeo.live'
wait_time:     float = 0.5


def get_account_name(id: str, tokens: dict) -> str:
    log(f'getting account name for {id}')

    sleep(wait_time)

    req = get(
        f'https://api.trackmania.com/api/display-names?accountId[]={id}',
        headers={'Authorization': tokens['oauth']}
    )

    loaded: dict = loads(req.text)
    name:   str  = loaded[id]

    log(f'got account name for {id} ({name})')

    return name


def get_campaign_maps(tokens: dict) -> dict:
    log('getting campaign maps')

    uid_groups: list = []
    uid_limit:  int  = 270
    uids:       list = []

    sleep(wait_time)

    req = get(
        url=f'{url_live}/api/token/campaign/official?length=99&offset=0',
        headers={'Authorization': tokens['live']}
    )

    loaded = loads(req.text)
    campList = loaded['campaignList']

    for campaign in reversed(campList):
        for map in campaign['playlist']:
            uids.append(map['mapUid'])

    maps_by_uid: dict = {uid: {} for uid in uids}

    while True:
        if len(uids) > uid_limit:
            uid_groups.append(','.join(uids[:uid_limit]))
            uids = uids[uid_limit:]
        else:
            uid_groups.append(','.join(uids))
            break

    for i, group in enumerate(uid_groups):
        log(f'getting campaign map info ({i + 1}/{len(uid_groups)} groups)')

        sleep(wait_time)

        req = get(
            url=f'{url_core}/maps?mapUidList={group}',
            headers={'Authorization': tokens['core']}
        )

        for map in loads(req.text):
            uid: str = map['mapUid']
            maps_by_uid[uid]['author']        = map['author']
            maps_by_uid[uid]['authorTime']    = map['authorScore']
            maps_by_uid[uid]['bronzeTime']    = map['bronzeScore']
            maps_by_uid[uid]['downloadUrl']   = map['fileUrl']
            maps_by_uid[uid]['goldTime']      = map['goldScore']
            maps_by_uid[uid]['id']            = map['mapId']
            maps_by_uid[uid]['name']          = str(map['name']).strip()
            maps_by_uid[uid]['silverTime']    = map['silverScore']
            maps_by_uid[uid]['submitter']     = map['submitter']
            maps_by_uid[uid]['thumbnailUrl']  = map['thumbnailUrl']
            maps_by_uid[uid]['timestampIso']  = map['timestamp']
            maps_by_uid[uid]['timestampUnix'] = int(parse(map['timestamp']).timestamp())
            maps_by_uid[uid]['uid']           = uid

        j: int = 0

        for uid in maps_by_uid:
            maps_by_uid[uid]['campaign'] = ceil((j + 1) / 25) - 1
            maps_by_uid[uid]['index']    = j

            j += 1

    log('got campaign maps')

    return maps_by_uid


def get_token(audience: str) -> str:
    log(f'getting token for {audience}')

    sleep(wait_time)

    if audience == 'OAuth':
        req = post(
            'https://api.trackmania.com/api/access_token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': os.environ['TM_OAUTH_IDENTIFIER'],
                'client_secret': os.environ['TM_OAUTH_SECRET']
            }
        )

        loaded: dict = loads(req.text)
        token:  str  = loaded['access_token']

    else:
        req = post(
            f'{url_core}/v2/authentication/token/basic',
            headers={
                'Authorization': f'Basic {b64encode(f'{os.environ['TM_E416DEV_SERVER_USERNAME']}:{os.environ['TM_E416DEV_SERVER_PASSWORD']}'.encode('utf-8')).decode('ascii')}',
                'Content-Type': 'application/json',
                'Ubi-AppId': tm2020_app_id,
                'User-Agent': os.environ['TM_E416DEV_AGENT'],
            },
            json={'audience': audience}
        )

        loaded: dict = loads(req.text)
        token:  str  = f'nadeo_v1 t={loaded['accessToken']}'

    log(f'got token for {audience}')

    return token


def get_tokens() -> dict:
    return {
        'core':  get_token('NadeoServices'),
        'live':  get_token('NadeoLiveServices'),
        'oauth': get_token('OAuth')
    }


def get_zones(tokens: dict) -> dict:
    log('getting zones')

    zones: dict = {}

    sleep(wait_time)

    req = get(
        url=f'{url_core}/zones',
        headers={'Authorization': tokens['core']},
    )

    for key in loads(req.text.encode('utf-8').decode()):
        zones[key['zoneId']] = {
            'name':   key['name'],
            'parent': key['parentId'],
        }

    log('got zones')

    return zones


def write_campaign_maps(campaign_maps: dict) -> None:
    log('writing campaign maps to database')

    with sql.connect(db_file) as con:
        cur: sql.Cursor = con.cursor()

        cur.execute('BEGIN')
        cur.execute('DROP TABLE IF EXISTS CampaignMaps')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS CampaignMaps (
                author        CHAR(36),
                authorTime    INT,
                bronzeTime    INT,
                campaign      INT,
                downloadUrl   CHAR(86),
                goldTime      INT,
                id            CHAR(36),
                mapIndex      INT,
                name          VARCHAR(16),
                silverTime    INT,
                submitter     CHAR(36),
                thumbnailUrl  CHAR(90),
                timestampIso  CHAR(25),
                timestampUnix INT,
                uid           VARCHAR(27) PRIMARY KEY
            );
        ''')

        for uid in campaign_maps:
            cur.execute(f'''
                INSERT INTO CampaignMaps (
                    author,
                    authorTime,
                    bronzeTime,
                    campaign,
                    downloadUrl,
                    goldTime,
                    id,
                    mapIndex,
                    name,
                    silverTime,
                    submitter,
                    thumbnailUrl,
                    timestampIso,
                    timestampUnix,
                    uid
                ) VALUES (
                    "{campaign_maps[uid]['author']}",
                    "{campaign_maps[uid]['authorTime']}",
                    "{campaign_maps[uid]['bronzeTime']}",
                    "{campaign_maps[uid]['campaign']}",
                    "{campaign_maps[uid]['downloadUrl']}",
                    "{campaign_maps[uid]['goldTime']}",
                    "{campaign_maps[uid]['id']}",
                    "{campaign_maps[uid]['index']}",
                    "{campaign_maps[uid]['name']}",
                    "{campaign_maps[uid]['silverTime']}",
                    "{campaign_maps[uid]['submitter']}",
                    "{campaign_maps[uid]['thumbnailUrl']}",
                    "{campaign_maps[uid]['timestampIso']}",
                    "{campaign_maps[uid]['timestampUnix']}",
                    "{campaign_maps[uid]['uid']}"
                )
            ''')

    log('wrote campaign maps to database')


def write_zones(zones: dict) -> None:
    log('writing zones to database')

    with sql.connect(db_file) as con:
        cur: sql.Cursor = con.cursor()

        cur.execute('BEGIN')
        cur.execute('DROP TABLE IF EXISTS Zones')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS Zones (
                id     CHAR(36) PRIMARY KEY,
                name   TEXT,
                parent CHAR(36)
            );
        ''')

        for id in zones:
            cur.execute(f'''
                INSERT INTO ZONES (
                    id
                    name,
                    parent,
                ) VALUES (
                    "{id}",
                    "{zones[id]['name']}",
                    "{zones[id]['parent']}"
                )
            ''')

    log('wrote zones to database')


def main() -> None:
    tokens: dict = get_tokens()

    campaign_maps: dict = get_campaign_maps(tokens)
    write_campaign_maps(campaign_maps)

    zones: dict = get_zones(tokens)
    write_zones(zones)

    print('hi')


if __name__ == '__main__':
    main()
