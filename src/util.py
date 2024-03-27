# c 2024-03-26
# m 2024-03-27

from datetime import datetime as dt

from pytz import timezone as tz


log_file: str = f'{__file__}/../../tm.log'


def format_race_time(input_ms: int) -> str:
    min: int = int(input_ms / 60000)
    sec: int = int((input_ms - (min * 60000)) / 1000)
    ms:  int = input_ms % 1000

    return f'{min}:{str(sec).zfill(2)}.{str(ms).zfill(3)}'


def log(msg: str, print_term: bool = True) -> None:
    text: str = f'{now()} {msg}'

    if print_term:
        print(text)

    with open(log_file, 'a', newline='\n') as f:
        f.write(f'{text}\n')


def now() -> str:
    utc    = dt.now(tz('UTC')).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    denver = f'Denver {dt.now(tz('America/Denver')).strftime('%H:%M')}'
    paris  = f'Paris {dt.now(tz('Europe/Paris')).strftime('%H:%M')}'
    return f'[{utc} ({denver}, {paris})]'


def strip_format_codes(raw: str) -> str:
    clean: str = ''
    flag:  int = 0

    for c in raw:
        if flag and c.lower() in 'gilnostwz$<>':
            flag = 0
            continue
        if flag and c.lower() in '0123456789abcdef':
            flag -= 1
            continue
        if c == '$':
            flag = 3
            continue
        flag = 0
        clean += c

    return clean.strip()
