# c 2024-03-25
# m 2024-03-26

from base64 import b64encode
from json import loads
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


def write_zones(zones: dict) -> None:
    log('writing zones to database')

    con: sql.Connection = sql.connect(db_file)
    cur: sql.Cursor     = con.cursor()

    zoneColumns: str = ''' (
        name   TEXT,
        parent CHAR(36),
        id     CHAR(36) PRIMARY KEY
    ); '''

    cur.execute('DROP TABLE IF EXISTS Zones')
    cur.execute(f'CREATE TABLE IF NOT EXISTS Zones {zoneColumns}')

    for zone_id in zones:
        cur.execute(f'''
            REPLACE INTO ZONES (
                name,
                parent,
                id
            ) VALUES (
                "{zones[zone_id]['name']}","{zones[zone_id]['parent']}","{zone_id}"
            )
        ''')

        con.commit()

    con.close()

    log('wrote zones to database')


def main() -> None:
    tokens: dict = get_tokens()

    zones: dict = get_zones(tokens)

    write_zones(zones)

    print('hi')


if __name__ == '__main__':
    main()
