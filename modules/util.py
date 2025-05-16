from datetime import datetime

import os
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
        
