import json
import re
import time
import requests

cas_url = 'https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Ftis.sustech.edu.cn%2Fcas'
ele_url = 'https://tis.sustech.edu.cn/Xsxk/addGouwuche'

session = requests.Session()
tis = session.get(cas_url)
headers = {
    'username': '',
    'password': '',
    'execution': re.findall('on" value="(.+?)"', tis.text)[0],
    '_eventId': 'submit',
    'geolocation': ''
}

ele_head = {
    "p_pylx": "1",
    "mxpylx": "1",
    "p_sfgldjr": "0",
    "p_sfredis": "0",
    "p_sfsyxkgwc": "0",
    "p_xktjz": "rwtjzyx"
}


def login():
    tis = session.post(cas_url, headers)
    if str(tis.content, 'utf-8').startswith('<!DOCTYPE html><html>'):
        raise Exception('Username or password incorrect')
    print('Successfully logged in')


def qk(course: dict):
    ele_head.update(course)

    tis = session.post(ele_url, ele_head)
    trial_cnt = 1
    try:
        while tis.json()['jg'] == '-1' and trial_cnt <= 600:
            tis = session.post(ele_url, ele_head)
            print(trial_cnt, tis.json()['message'], sep='\t')
            trial_cnt += 1
            time.sleep(0.2)
    except:
        print(tis.content)
    
    try:
        print(
            f'\033[0;33;40m{course.get("course_name")} finished, please check manually in tis\033[0m\n', )
    except:
        print(
            f'\033[0;33;40m{course} finished, please check manually in tis\033[0m\n')


if __name__ == '__main__':
    with open('user.json') as f:
        info = json.load(f)
        headers.update({'username': info.get('sid'),
                        'password': info.get('pwd')})
        ele_head.update(info.get('ele_head'))
        courses = info.get('courses')

    login()
    for course in courses:
        qk(course)

    print(f'\nAll done, have fun!')
    session.close()
