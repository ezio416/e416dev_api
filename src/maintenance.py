# c 2024-08-25
# m 2024-08-25

import json
import sqlite3 as sql

import app
import util


def add_campaign_index_to_other_warriors() -> None:
    # ret: dict = {}

    with sql.connect(app.db_file) as con:
    #     con.row_factory = sql.Row
        cur: sql.Cursor = con.cursor()

    #     cur.execute('BEGIN')
    #     for val in cur.execute('SELECT * FROM OtherWarriors').fetchall():
    #         ret[val['uid']] = dict(val)

    #     index: int = 0
    #     last_campaign: str = ''
    #     for uid, val in ret.items():
    #         map: dict = ret[uid]

    #         if last_campaign != map['campaign']:
    #             last_campaign = map['campaign']
    #             index = 0

    #         map['index'] = index
    #         index += 1

    #     with open('OtherWarriors.json', 'a', newline='\n') as f:
    #         json.dump(ret, f, indent=4)

        cur.execute('DROP TABLE OtherWarriors')

    with open('OtherWarriors.json') as f:
        ret: dict = json.loads(f.read())

    app.write_other_warriors(ret)

    pass


def main() -> None:
    pass


if __name__ == '__main__':
    main()
