# c 2024-03-25
# m 2024-03-27

from base64 import b64encode
from datetime import datetime as dt
from json import loads
from math import ceil
import os
import sqlite3 as sql
from time import sleep

from dateutil.parser import parse
from discord_webhook import DiscordEmbed, DiscordWebhook
from pytz import timezone as tz
from requests import get, post

from util import format_race_time, log, now, strip_format_codes


db_file:       str   = f'{os.path.dirname(__file__)}/../tm.db'
tm2020_app_id: str   = '86263886-327a-4328-ac69-527f0d20a237'
uid_file:      str   = f'{os.path.dirname(__file__)}/../latest_totd.txt'
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

    name: str = loads(req.text)[id]

    log(f'got account name for {id} ({name})')

    return name


def get_campaign_maps(tokens: dict) -> dict:
    log('getting campaign maps')

    uid_groups: list = []
    uid_limit:  int  = 270
    uids:       list = []

    sleep(wait_time)

    req = get(
        f'{url_live}/api/token/campaign/official?length=99&offset=0',
        headers={'Authorization': tokens['live']}
    )

    for campaign in reversed(loads(req.text)['campaignList']):
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
            f'{url_core}/maps?mapUidList={group}',
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
                'grant_type':    'client_credentials',
                'client_id':     os.environ['TM_OAUTH_IDENTIFIER'],
                'client_secret': os.environ['TM_OAUTH_SECRET']
            }
        )

        token: str = loads(req.text)['access_token']

    else:
        req = post(
            f'{url_core}/v2/authentication/token/basic',
            headers={
                'Authorization': f'Basic {b64encode(f'{os.environ['TM_E416DEV_SERVER_USERNAME']}:{os.environ['TM_E416DEV_SERVER_PASSWORD']}'.encode('utf-8')).decode('ascii')}',
                'Content-Type':  'application/json',
                'Ubi-AppId':     tm2020_app_id,
                'User-Agent':    os.environ['TM_E416DEV_AGENT'],
            },
            json={'audience': audience}
        )

        token: str = f'nadeo_v1 t={loads(req.text)['accessToken']}'

    log(f'got token for {audience}')

    return token


def get_tokens() -> dict:
    return {
        'core':  get_token('NadeoServices'),
        'live':  get_token('NadeoLiveServices'),
        'oauth': get_token('OAuth')
    }


def get_totd_maps(tokens: dict) -> dict:
    log('getting TOTD maps')

    uid_groups: list = []
    uid_limit:  int  = 270
    uids:       list = []

    sleep(wait_time)

    req = get(
        f'{url_live}/api/token/campaign/month?length=99&offset=0',
        headers={'Authorization': tokens['live']}
    )

    maps_by_uid: dict = {}

    loaded = loads(req.text)
    monthList = loaded['monthList']

    for month in reversed(monthList):
        for day in month['days']:
            uid: str = day['mapUid']
            if uid == '' or uid in uids:
                continue

            uids.append(uid)
            maps_by_uid[uid] = {
                'date': f'{month['year']}-{str(month['month']).zfill(2)}-{str(day['monthDay']).zfill(2)}',
                'season': day['seasonUid']
            }

    while True:
        if len(uids) > uid_limit:
            uid_groups.append(','.join(uids[:uid_limit]))
            uids = uids[uid_limit:]
        else:
            uid_groups.append(','.join(uids))
            break

    for i, group in enumerate(uid_groups):
        log(f'getting TOTD map info ({i + 1}/{len(uid_groups)} groups)')

        sleep(wait_time)

        req = get(
            f'{url_core}/maps?mapUidList={group}',
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
            maps_by_uid[uid]['nameClean']     = strip_format_codes(str(map['name']).strip())
            maps_by_uid[uid]['nameRaw']       = str(map['name']).strip()
            maps_by_uid[uid]['silverTime']    = map['silverScore']
            maps_by_uid[uid]['submitter']     = map['submitter']
            maps_by_uid[uid]['thumbnailUrl']  = map['thumbnailUrl']
            maps_by_uid[uid]['timestampIso']  = map['timestamp']
            maps_by_uid[uid]['timestampUnix'] = int(parse(map['timestamp']).timestamp())
            maps_by_uid[uid]['uid']           = uid

    j: int = 0

    for uid in maps_by_uid:
        maps_by_uid[uid]['index'] = j

        j += 1

    log('got TOTD maps')

    return maps_by_uid


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


def map_is_new(uid: str) -> bool:
    if os.path.isfile(uid_file):
        with open(uid_file, 'r') as f:
            last_uid: str = f.read().strip('\n')

        if uid == last_uid:
            return False

    else:
        with open(uid_file, 'w', newline='\n') as f:
            f.write(f'{uid}\n')

    return True


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


def write_totd_maps(totd_maps: dict) -> None:
    log('writing TOTD maps to database')

    with sql.connect(db_file) as con:
        cur: sql.Cursor = con.cursor()

        cur.execute('BEGIN')
        cur.execute('DROP TABLE IF EXISTS TotdMaps')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS TotdMaps (
                author        CHAR(36),
                authorTime    INT,
                bronzeTime    INT,
                date          CHAR(10),
                downloadUrl   CHAR(86),
                goldTime      INT,
                id            CHAR(36),
                mapIndex      INT,
                nameClean     TEXT,
                nameRaw       TEXT,
                season        CHAR(36),
                silverTime    INT,
                submitter     CHAR(36),
                thumbnailUrl  CHAR(90),
                timestampIso  CHAR(25),
                timestampUnix INT,
                uid           VARCHAR(27) PRIMARY KEY
            );
        ''')

        for uid in totd_maps:
            cur.execute(f'''
                INSERT INTO TotdMaps (
                    author,
                    authorTime,
                    bronzeTime,
                    date,
                    downloadUrl,
                    goldTime,
                    id,
                    mapIndex,
                    nameClean,
                    nameRaw,
                    season,
                    silverTime,
                    submitter,
                    thumbnailUrl,
                    timestampIso,
                    timestampUnix,
                    uid
                ) VALUES (
                    "{totd_maps[uid]['author']}",
                    "{totd_maps[uid]['authorTime']}",
                    "{totd_maps[uid]['bronzeTime']}",
                    "{totd_maps[uid]['date']}",
                    "{totd_maps[uid]['downloadUrl']}",
                    "{totd_maps[uid]['goldTime']}",
                    "{totd_maps[uid]['id']}",
                    "{totd_maps[uid]['index']}",
                    "{totd_maps[uid]['nameClean']}",
                    "{totd_maps[uid]['nameRaw']}",
                    "{totd_maps[uid]['season']}",
                    "{totd_maps[uid]['silverTime']}",
                    "{totd_maps[uid]['submitter']}",
                    "{totd_maps[uid]['thumbnailUrl']}",
                    "{totd_maps[uid]['timestampIso']}",
                    "{totd_maps[uid]['timestampUnix']}",
                    "{totd_maps[uid]['uid']}"
                )
            ''')

    log('wrote TOTD maps to database')


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
                    id,
                    name,
                    parent
                ) VALUES (
                    "{id}",
                    "{zones[id]['name']}",
                    "{zones[id]['parent']}"
                )
            ''')

    log('wrote zones to database')


def run() -> None:
    tokens: dict = get_tokens()

    totd_maps: dict = get_totd_maps(tokens)

    latest_totd: dict = totd_maps[list(totd_maps)[-1]]

    if (map_is_new(latest_totd['uid'])):
        webhook = DiscordWebhook(
            os.environ['TM_TOTD_NOTIF_DISCORD_WEBHOOK_URL'],
            content='<@&1205378175601745970>'
        )

        embed = DiscordEmbed(
            f'Track of the Day for {latest_totd['date']}',
            color='00a719'
        )

        embed.add_embed_field('Map', f'[{latest_totd['nameClean']}](https://trackmania.io/#/totd/leaderboard/{latest_totd['season']}/{latest_totd['uid']})', False)
        embed.add_embed_field('Author', f'[{get_account_name(latest_totd['author'], tokens)}](https://trackmania.io/#/player/{latest_totd['author']})', False)
        embed.add_embed_field('Author Medal', format_race_time(latest_totd['authorTime']), False)
        embed.set_thumbnail(latest_totd['thumbnailUrl'])
        webhook.add_embed(embed)
        webhook.execute()

    else:
        log(f'ERROR: latest map is old ({latest_totd['date']} - {latest_totd['nameClean']})')

    write_totd_maps(totd_maps)

    write_campaign_maps(get_campaign_maps(tokens))
    write_zones(get_zones(tokens))


def main() -> None:
    attempts:              int = 10
    wait_between_attempts: int = 10

    while True:
        now_paris = dt.now(tz('Europe/Paris'))

        if now_paris.hour == 19 and now_paris.minute == 0:
            for i in range(attempts):
                try:
                    run()
                    break
                except Exception as e:
                    log(f'ERROR: {e} | attempt {i + 1}/{attempts} failed, waiting {wait_between_attempts} seconds')
                    sleep(wait_between_attempts)

                if i == attempts - 1:
                    log('ERROR: max attempts reached')

                    DiscordWebhook(
                        os.environ['TM_TOTD_NOTIF_DISCORD_WEBHOOK_URL'],
                        content='<@174350279158792192> ERROR: CHECK SERVER LOGS'
                    ).execute()

            # print('waiting 60 seconds')
            sleep(60)
        else:
            # print(f'{now()} waiting')
            sleep(1)


if __name__ == '__main__':
    main()
