from datetime import datetime

import os
import sys
import logging


class Util:
    def SetqueryUrl(params:dict = dict()):
        queryUrl = ""
        for i in params:
            if params[i] != '':
                queryUrl += f"{i}={params[i]}&"
        # print (queryUrl)
        return queryUrl
    
    def compare_with_time(compare_time):
        tdata_datetime = datetime.strptime(compare_time, "%Y-%m-%d %H:%M:%S")

        current_datetime = datetime.now()
        if current_datetime < tdata_datetime:
            return "게시중"
        else:
            return "마감"

    def get_app_path():
        """
        config.ini, Database, Log 등 실행 파일과 함께 유지되어야 하는
        외부 파일의 기준 경로를 반환한다.
        """
        if getattr(sys, "frozen", False):
            # PyInstaller exe 실행 시 exe가 있는 폴더
            return os.path.dirname(sys.executable)

        # 개발 환경에서는 프로젝트 최상위 폴더
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
