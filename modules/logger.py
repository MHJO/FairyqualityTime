import os
import sys

import inspect
import traceback
import typing
from datetime import datetime

log_file: str = ''

def init(path: str, app_name: str):
    global log_file

    log_name = f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"

    log_dir = path + r'\log'

    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    # 로그 파일 준비
    log_file = os.path.join(log_dir, log_name)

    f = open(log_file, 'a', encoding='utf-8')
    f.close()


def log(data: typing.Union[str, list[str]]):
    global log_file

    prefix = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            try:
                if isinstance(data, list):
                    for line in data:
                        print(inspect.stack()[1][0])
                        print(inspect.getmodule(inspect.stack()[1][0]))
                        print(f'{prefix} [{inspect.getmodule(inspect.stack()[1][0]).__file__.split("/")[-1]}:'
                              f'{inspect.currentframe().f_back.f_code.co_name}('
                              f'line:{inspect.currentframe().f_back.f_lineno})] : '
                              f'{data}\n')
                        f.write(f'{prefix} [{inspect.getmodule(inspect.stack()[1][0]).__file__.split("/")[-1]}:'
                                f'{inspect.currentframe().f_back.f_code.co_name}('
                                f'line:{inspect.currentframe().f_back.f_lineno})] : '
                                f'{line}\n')
                    f.close()
                else:
                    print(f'{prefix} [{inspect.getmodule(inspect.stack()[1][0]).__file__.split("/")[-1]}:'
                            f'{inspect.currentframe().f_back.f_code.co_name}('
                            f'line:{inspect.currentframe().f_back.f_lineno})] : '
                            f'{data}\n')
                    f.write(f'{prefix} [{inspect.getmodule(inspect.stack()[1][0]).__file__.split("/")[-1]}:'
                            f'{inspect.currentframe().f_back.f_code.co_name}('
                            f'line:{inspect.currentframe().f_back.f_lineno})] : '
                            f'{data}\n')
                f.close()
            except Exception as e:
                traceback.print_exc()
                f.write(f'{prefix} {data}\n')
    except Exception as e:
        traceback.print_exc()
