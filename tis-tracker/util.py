import json
import logging
import re
import requests
import pandas as pd
import os
import time


cas_url = 'https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Ftis.sustech.edu.cn%2Fcas'
session = requests.Session()

logger = logging.getLogger('tis.info')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s ~ \033[96m%(funcName)s\033[0m: %(message)s',
                    datefmt='%H:%M:%S')


tis = session.get(cas_url)
headers = {
    'username': '',
    'password': '',
    'execution': re.findall('on" value="(.+?)"', tis.text)[0],
    '_eventId': 'submit',
    'geolocation': ''
}

with open('user.json') as f:
    info = json.load(f)
    headers.update({'username': info.get('sid'),
                    'password': info.get('pwd')})
    receiver = f'https://api.day.app/{info.get("bark")}'

    sel_header = {
        'p_xn': info.get('year'),
        'p_xq': info.get('sem'),
        'pageSize': '50'
    }

name = {}
capacity = {}
now = {}
prev = {}
warning = []


def login():
    tis = session.post(cas_url, headers)
    if str(tis.content, 'utf-8').startswith('<!DOCTYPE html><html>'):
        logger.critical('Username or password incorrect')
        exit(1)
    logger.info('successfully logged in')


def init():
    global name, capacity
    msg = f'{receiver}/Start%20tracking%20your%20tis/Summarizing%20courses%20with%20no%20remaining%20capacity' \
        + '?isArchive=0&icon=https://i.imgur.com/a61hBq8.png'
    requests.get(msg)
    selected = session.post(
        'https://tis.sustech.edu.cn/Xsxk/queryYxkc', sel_header)

    inf = selected.json()['yxkcList']
    name = {x['id']: x['kcmc'] for x in inf}
    capacity = {x['id']: int(x['zrl']) for x in inf}
    if os.path.exists('./timeline.json'):
        logger.warning('timeline.json already exists')
        return
    inf = selected.json()['yxkcList']
    df = pd.DataFrame()
    df['id'] = [x['id'] for x in inf]
    df['name'] = [x['kcmc'] for x in inf]
    df['capacity'] = [int(x['zrl']) for x in inf]
    df['selected'] = [{int(time.time()): int(x['yxzrs'])}
                      for x in inf]
    # df['paid'] = [int(x['xkxs']) for x in inf]
    with open('timeline.json', 'w') as f:
        df.to_json(f, orient='records', force_ascii=False)
    logger.info(f'timeline initialized: {os.getcwd()}/timeline.json')


def warn():
    global warning
    warning.clear()

    for k, v in now.items():
        try:
            if v > prev[k]:
                logger.warning(f'{name[k]} has {v - prev[k]} new students')
            if v != prev[k] and v >= capacity[k] - 5:
                warning.append(k)
        except KeyError:
            prev[k] = 0
            if v >= capacity[k]:
                warning.append(k)
    if len(warning) == 0:
        logger.info('no changes since the last check')
        return

    for w in warning:
        msg = f'{receiver}/{name[w]}/选课{"新增%20" if now[w] > prev[w] else "减少%20"}{abs(now[w] - prev[w])}%20人%20-%20{now[w]}%20%2F%20{capacity[w]}' \
            + '?isArchive=0&icon=https://i.imgur.com/a61hBq8.png'
            # + '?isArchive=0&group='+name[w]+'&icon=https://i.imgur.com/a61hBq8.png'
        requests.get(msg)


def update():
    global prev, now
    prev = now
    timestamp = str(int(time.time()))
    selected = session.post(
        'https://tis.sustech.edu.cn/Xsxk/queryYxkc', sel_header)
    if str(selected.content, 'utf-8').startswith('<!DOCTYPE html><html>'):
        login()
    selected = session.post(
        'https://tis.sustech.edu.cn/Xsxk/queryYxkc', sel_header)
    nd = selected.json()['yxkcList']
    now = {x['id']: int(x['yxzrs']) for x in nd}

    df = pd.read_json('timeline.json', orient='records')
    for k, v in now.items():
        mp = df.loc[df['id'] == k, 'selected']
        mp.values[0][timestamp] = v
    df.to_json('timeline.json', orient='records', force_ascii=False)
    logger.info('timeline updated')


if __name__ == '__main__':
    try:
        login()
        init()
        while True:
            print()
            update()
            warn()
            time.sleep(60)

    except KeyboardInterrupt:
        session.close()
