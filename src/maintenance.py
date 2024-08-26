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


def recalculate_totd_warriors() -> None:
    maps: dict = {}

    with sql.connect(app.db_file) as con:
        con.row_factory = sql.Row
        cur: sql.Cursor = con.cursor()

        cur.execute('BEGIN')
        for val in cur.execute('SELECT * FROM TotdWarriors').fetchall():
            maps[val['uid']] = dict(val)

    with open('totd_warrior_changes.txt', 'a', newline='\n') as f:
        i: int = 0

        for uid, map in maps.items():
            new_warrior: int = app.get_warrior_time(map['authorTime'], map['worldRecord'], True)

            if map['warriorTime'] != new_warrior:
                # line: str = f'{map['date']}: {util.format_race_time(map['warriorTime'])} -> {util.format_race_time(new_warrior)}'
                # print(line)
                # f.write(f'{line}\n')
                map['warriorTime'] = new_warrior
                i += 1

        print(f'found {i}/{len(maps)} incorrect warrior times')

    with sql.connect(app.db_file) as con:
        cur: sql.Cursor = con.cursor()

        cur.execute('BEGIN')

        for uid, map in maps.items():
            cur.execute(f'''
                REPLACE INTO TotdWarriors (
                    authorTime,
                    custom,
                    date,
                    name,
                    reason,
                    uid,
                    warriorTime,
                    worldRecord
                ) VALUES (
                    "{map['authorTime']}",
                    "{map['custom']}",
                    "{map['date']}",
                    "{map['name']}",
                    "{map['reason']}",
                    "{uid}",
                    "{map['warriorTime']}",
                    "{map['worldRecord']}"
                )
            ''')

    pass


def main() -> None:
    # recalculate_totd_warriors()
    pass


if __name__ == '__main__':
    main()
