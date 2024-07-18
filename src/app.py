# c 2024-03-25
# m 2024-07-18

from datetime import datetime as dt, timezone
from math import ceil
import os
import sqlite3 as sql
from time import sleep

from discord_webhook import DiscordEmbed, DiscordWebhook
from nadeo_api import auth, core, live, oauth
from pytz import timezone as tz

from util import format_race_time, log, strip_format_codes


db_file:   str   = f'{os.path.dirname(__file__)}/../tm.db'
uid_file:  str   = f'{os.path.dirname(__file__)}/../latest_totd.txt'
url_core:  str   = 'https://prod.trackmania.core.nadeo.online'
url_live:  str   = 'https://live-services.trackmania.nadeo.live'
wait_time: float = 0.5


def get_account_name(tokens: dict, account_id: str) -> str:
    log(f'getting account name for {account_id}')

    sleep(wait_time)
    req = oauth.account_names_from_ids(tokens['oauth'], account_id)

    account_name: str = req[account_id]

    log(f'account name: {account_name}')

    return account_name


def get_campaign_maps(tokens: dict) -> dict:
    log('getting campaign maps')

    uid_groups: list = []
    uid_limit:  int  = 270
    uids:       list = []

    sleep(wait_time)
    maps: dict = live.maps_campaign(tokens['live'], 99)

    campaignList: list[dict] = maps['campaignList']

    for campaign in reversed(campaignList):
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
        map_info: dict = core.get(
            tokens['core'],
            'maps',
            {'mapUidList': group}
        )

        for map in map_info:
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
            maps_by_uid[uid]['timestampUnix'] = int(dt.fromisoformat(map['timestamp']).timestamp())
            maps_by_uid[uid]['uid']           = uid

    j: int = 0

    for uid in maps_by_uid:
        maps_by_uid[uid]['campaign'] = ceil((j + 1) / 25) - 1
        maps_by_uid[uid]['index']    = j

        j += 1

    log('got campaign maps')

    return maps_by_uid


def get_tokens() -> dict:
    log('getting core token')
    token_core: auth.Token = auth.get_token(
        auth.audience_core,
        os.environ['TM_E416DEV_SERVER_USERNAME'],
        os.environ['TM_E416DEV_SERVER_PASSWORD'],
        os.environ['TM_E416DEV_AGENT'],
        True
    )

    log('getting live token')
    token_live: auth.Token = auth.get_token(
        auth.audience_live,
        os.environ['TM_E416DEV_SERVER_USERNAME'],
        os.environ['TM_E416DEV_SERVER_PASSWORD'],
        os.environ['TM_E416DEV_AGENT'],
        True
    )

    log('getting oauth token')
    token_oauth: auth.Token = auth.get_token(
        auth.audience_oauth,
        os.environ['TM_OAUTH_IDENTIFIER'],
        os.environ['TM_OAUTH_SECRET']
    )

    return {
        'core': token_core,
        'live': token_live,
        'oauth': token_oauth
    }


def get_totd_maps(tokens: dict) -> dict:
    log('getting TOTD maps')

    uid_groups: list = []
    uid_limit:  int  = 270
    uids:       list = []

    sleep(wait_time)
    maps: dict = live.maps_totd(tokens['live'], 99)

    maps_by_uid: dict = {}

    monthList: list[dict] = maps['monthList']

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
        map_info: dict = core.get(
            tokens['core'],
            'maps',
            {'mapUidList': group}
        )

        for map in map_info:
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
            maps_by_uid[uid]['timestampUnix'] = int(dt.fromisoformat(map['timestamp']).timestamp())
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
    req = core.zones(tokens['core'])

    for key in req:
        zones[key['zoneId']] = {
            'name':   key['name'],
            'parent': key['parentId'],
        }

    sep: str = '|'

    for id in zones:
        name: str = zones[id]['name']

        if (parent_id := zones[id]['parent']):
            name += f'{sep}{zones[parent_id]['name']}'
            if (g0parent_id := zones[parent_id]['parent']):
                name += f'{sep}{zones[g0parent_id]['name']}'
                if (g1parent_id := zones[g0parent_id]['parent']):
                    name += f'{sep}{zones[g1parent_id]['name']}'
                    if (g2parent_id := zones[g1parent_id]['parent']):
                        name += f'{sep}{zones[g2parent_id]['name']}'

        zones[id]['nameFull'] = name.split(f'{sep}World')[0]

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
                id       CHAR(36) PRIMARY KEY,
                name     TEXT,
                nameFull TEXT,
                parent   CHAR(36)
            );
        ''')

        for id in zones:
            cur.execute(f'''
                INSERT INTO ZONES (
                    id,
                    name,
                    nameFull,
                    parent
                ) VALUES (
                    "{id}",
                    "{zones[id]['name']}",
                    "{zones[id]['nameFull']}",
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
