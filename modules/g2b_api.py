import requests, os, sys
import json
import pandas as pd
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import sqlite3
import configparser
import logging

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog,QApplication, QMessageBox
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QIcon

"""
    당신의 퇴근요정!

    나라장터 api 활용 엑셀 시트 저장
"""

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

APP_PATH = get_app_path()

# 로그 저장 경로
LOG_DIR = os.path.join(APP_PATH, "Log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"g2b_api_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

def resource_path(relative_path):
    """
    개발 환경과 PyInstaller 환경 모두에서
    UI, 이미지 등 번들 리소스 파일을 찾는다.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

properies = configparser.ConfigParser(interpolation=None)
configPath = os.path.join(APP_PATH, "config.ini")
print(f"config.ini 경로: {configPath}")
if not os.path.exists(configPath):
    raise FileNotFoundError(
        f"config.ini 파일을 찾을 수 없습니다.\n\n"
        f"확인 경로: {configPath}"
    )

properies.read(configPath, encoding="utf-8")

if "datagov" not in properies:
    raise KeyError(
        f"config.ini에 [datagov] 섹션이 없습니다.\n\n"
        f"확인 경로: {configPath}"
    )

datagov = properies["datagov"]

# API 변수 정의 
basicUrl = datagov.get("basicUrl", "http://apis.data.go.kr/1230000/")
serivceKey = datagov["apikey"]
indstrytyCd = datagov.get("indstrytyCd", "")  # 업종코드

DB_PATH = os.path.join(APP_PATH, "Database", "나라장터.db")


# Excel 파일로 저장
filename = "나라장터_{}.xlsx".format(time.strftime("%Y%m%d"))


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
    
class Sqlite:
    def clearDB(type):
        connection = sqlite3.connect(DB_PATH)
        if type =="1":
            sql_command = """
                DELETE FROM BidPblancListInfoServcPPSSrch
            """
        elif (type =="2"):
            sql_command = """
                DELETE FROM HrcspSsstndrdInfoService
            """
        cursor = connection.cursor()
        
        cursor.execute(sql_command)
        cursor.fetchall()
        connection.commit()

        connection.close()

    def selectDB(savePath, type="", statusType="", alert="N"):
        try:
            connection = sqlite3.connect(DB_PATH)
            if type == "1":
                sql_command = """
                    SELECT srvceDivNm as 업무구분,
                        ntceKindNm as 구분, 
                        (bidNtceNo||'-'||bidNtceOrd) as 입찰공고번호, 
                        bidNtceNm as 공고명,
                        ntceInsttNm as 공고기관,
                        dminsttNm as 수요기관, 
                        (bidNtceDt ||'('||bidClseDt||')') as '게시일시(입찰마감일시)', 
                        printf('%,d', CAST(asignBdgtAmt AS INTEGER)) || '원' AS 사업금액
                        from BidPblancListInfoServcPPSSrch
                """
                sheet_name="입찰공고용역"

            elif (type == "2"):
                if statusType =="A":
                    sql_command = """
                        SELECT bsnsDivNm as 업무구분,
                            prdctClsfcNoNm as 사업명, 
                            rlDminsttNm as 수요기관, 
                            orderInsttNm as 공고기관, 
                            ofclNm as 담당자, 
                            rcptDt as 진행일자, 
                            Status as 진행상태, 
                            printf('%,d', CAST(asignBdgtAmt AS INTEGER)) || '원' AS '배정예산금액(원화)'
                            from HrcspSsstndrdInfoService
                    """
                elif statusType == "Y":
                    sql_command = """
                        SELECT bsnsDivNm as 업무구분,
                            prdctClsfcNoNm as 사업명, 
                            rlDminsttNm as 수요기관, 
                            orderInsttNm as 공고기관, 
                            ofclNm as 담당자, 
                            rcptDt as 진행일자, 
                            Status as 진행상태, 
                            printf('%,d', CAST(asignBdgtAmt AS INTEGER)) || '원' AS '배정예산금액(원화)'
                        from HrcspSsstndrdInfoService
                        where Status != '마감'
                    """
                sheet_name="사전규격"

            cursor = connection.cursor()
            print (sheet_name)
            data = cursor.execute(sql_command)
            
            # 컬럼명 포함 데이터프레임 생성
            col_names = [desc[0] for desc in cursor.description]  # SQL 쿼리 결과의 컬럼명 가져오기

            # pandas 데이터프레임으로 변환
            df_new = pd.DataFrame(data,columns=col_names)

            file_path = os.path.join(savePath, filename)

            if not os.path.exists(savePath):
                os.makedirs(savePath, exist_ok=True)

            # 파일이 이미 있으면 기존 시트는 유지하고
            # 현재 저장하는 시트만 교체
            if os.path.exists(file_path):
                with pd.ExcelWriter(
                    file_path,
                    engine="openpyxl",
                    mode="a",
                    if_sheet_exists="replace"
                ) as writer:
                    df_new.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )

            # 파일이 없으면 새로 생성
            else:
                with pd.ExcelWriter(
                    file_path,
                    engine="openpyxl",
                    mode="w"
                ) as writer:
                    df_new.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )
            
            print("데이터가 'output.xlsx' 파일로 저장되었습니다.")

            connection.close()
            if alert == "Y":
                telegram_alert(
                    file_path,
                    caption=f"나라장터 데이터 전달드립니다. ({len(df_new)}건)"
                )

            return True
        except Exception as e:
            print (e.__str__)
            return False

    def Upsert(parmas, type,check_duplicate=True):
        try:
            connection = sqlite3.connect(DB_PATH)
            cursor = connection.cursor()
            for i in range(len(parmas)):
                if type =="1":
                    if check_duplicate == False:
                        sql_command = f'''
                            INSERT INTO BidPblancListInfoServcPPSSrch (
                                srvceDivNm,
                                bidNtceNo,
                                bidNtceOrd,
                                ntceKindNm,
                                bidNtceNm,
                                ntceInsttNm,
                                dminsttNm,
                                opengDt,
                                bidNtceDt,
                                bidClseDt,
                                asignBdgtAmt
                            )
                            VALUES (
                                "{parmas[i][0]}",
                                "{parmas[i][1]}",
                                "{parmas[i][2]}",
                                "{parmas[i][3]}",
                                "{parmas[i][4]}",
                                "{parmas[i][5]}",
                                "{parmas[i][6]}",
                                "{parmas[i][7]}",
                                "{parmas[i][8]}",
                                "{parmas[i][9]}",
                                "{parmas[i][10]}"
                            )
                        '''
                    else:
                        sql_command = f'''
                            INSERT INTO BidPblancListInfoServcPPSSrch (
                                srvceDivNm, bidNtceNo, bidNtceOrd, ntceKindNm, bidNtceNm, ntceInsttNm, dminsttNm, opengDt, bidNtceDt, bidClseDt, asignBdgtAmt
                                )
                                SELECT "{parmas[i][0]}", "{parmas[i][1]}", "{parmas[i][2]}", "{parmas[i][3]}", "{parmas[i][4]}", "{parmas[i][5]}", "{parmas[i][6]}", "{parmas[i][7]}", "{parmas[i][8]}", "{parmas[i][9]}", "{parmas[i][10]}"
                                WHERE NOT EXISTS (
                                    SELECT 1 FROM BidPblancListInfoServcPPSSrch
                                WHERE srvceDivNm="{parmas[i][0]}" AND bidNtceNo = "{parmas[i][1]}" AND bidNtceOrd = "{parmas[i][2]}" 
                                AND ntceKindNm="{parmas[i][3]}" AND bidNtceDt="{parmas[i][8]}"
                                )
                        '''
                elif type == "2":
                    sql_command = f''' 
                        INSERT INTO HrcspSsstndrdInfoService (
                            bsnsDivNm, prdctClsfcNoNm, rlDminsttNm, orderInsttNm, ofclNm, rcptDt, Status, asignBdgtAmt
                        )
                        SELECT "{parmas[i][0]}", "{parmas[i][1]}", "{parmas[i][2]}", "{parmas[i][3]}", "{parmas[i][4]}", "{parmas[i][5]}", "{parmas[i][6]}", "{parmas[i][7]}"
                        WHERE NOT EXISTS (
                            SELECT 1 FROM HrcspSsstndrdInfoService
                        WHERE bsnsDivNm="{parmas[i][0]}" AND prdctClsfcNoNm = "{parmas[i][1]}" AND rlDminsttNm = "{parmas[i][2]}" 
                        AND orderInsttNm="{parmas[i][3]}" AND rcptDt="{parmas[i][5]}"
                        )
                    '''
                cursor.execute(sql_command)
                cursor.fetchall()
                connection.commit()

            connection.close()
        except Exception as e:
            print (str(e))


# region [사전규격정보서비스]
class HrcspSsstndrdInfoService:
    '''	조달청_나라장터 사전규격정보서비스 '''

    def getPublicPrcureThngInfoServcPPSSrch(inqryDiv="1", inqryBgnDt="", inqryEndDt="", bidNtceNm="", swBizObjYn="Y", statusType = ""):
        '''
            나라장터 검색조건에 의한 사전규격 용역 목록 조회
        '''
        selectApi = "getPublicPrcureThngInfoServcPPSSrch"
        dict1 = {
            "inqryDiv": inqryDiv,  # 조회구분
            "inqryBgnDt": inqryBgnDt,  # 조회시작일시
            "inqryEndDt": inqryEndDt,  # 조회종료일시
            "prdctClsfcNoNm": bidNtceNm,  # 입찰공고명
            "swBizObjYn": swBizObjYn  # SW대상여부 - 
        }

        queryUrl = Util.SetqueryUrl(dict1)
        pageNo = 1  # 초기 페이지 번호 설정
        totalCounts = 100
        
        
        while True:

            url = f"{basicUrl}ao/HrcspSsstndrdInfoService/{selectApi}?pageNo={pageNo}&numOfRows=100&ServiceKey={serivceKey}&{queryUrl}type=xml"
            print(url)
            req = requests.get(url)

            if req.status_code == 200:
                try:
                    # XML 파싱
                    root = ET.fromstring(req.text)
                    
                    totalCount = int(root.find('.//body').find('totalCount').text)  # API 응답에서 totalCount 사용
                    print(f"사전규격 용역 목록 조회 => {bidNtceNm}, totalCount = {totalCount}")
                    datas = []
                    print (len(datas))
                    items = root.find('.//body/items')
                    if items is not None:
                        
                        for item in items.findall('item'):
                            data = []
                            # 각 item 태그에서 추출할 데이터
                            bsnsDivNm = item.find('bsnsDivNm').text if item.find('bsnsDivNm') is not None else "N/A"  # 업무구분명
                            prdctClsfcNoNm = item.find('prdctClsfcNoNm').text if item.find('prdctClsfcNoNm') is not None else "N/A"  # 사업명
                            orderInsttNm = item.find('orderInsttNm').text if item.find('orderInsttNm') is not None else "N/A"  # 공고기관명
                            rlDminsttNm = item.find('rlDminsttNm').text if item.find('rlDminsttNm') is not None else "N/A"  # 수요기관명
                            opninRgstClseDt = item.find('opninRgstClseDt').text if item.find('opninRgstClseDt') is not None else "N/A"  # 의견마감등록일시
                            ofclNm = item.find('ofclNm').text if item.find('ofclNm') is not None else "N/A"  # 담당자명
                            swBizObjYn = item.find('swBizObjYn').text if item.find('swBizObjYn') is not None else "N/A"  # SW 사업 대상 여부
                            rcptDt = item.find('rcptDt').text if item.find('rcptDt') is not None else "N/A"  # 접수일자 -> 진행일자
                            asignBdgtAmt = item.find('asignBdgtAmt').text if item.find('asignBdgtAmt') is not None else "N/A"  # 배정 예산액
                            Status = Util.compare_with_time(opninRgstClseDt)
                            data.append(bsnsDivNm)
                            data.append(prdctClsfcNoNm)
                            data.append(rlDminsttNm)
                            data.append(orderInsttNm)
                            data.append(ofclNm)
                            data.append(rcptDt)
                            data.append(Status)
                            data.append(asignBdgtAmt)
                            datas.append(data)
                    Sqlite.Upsert(datas,type="2")
                            

                    pageNo += 1  # 페이지 번호 증가
                    # totalCount가 100 이하라면 반복 종료
                    if totalCount > totalCounts:
                        totalCounts = 100 * pageNo
                    else:
                        # telegram_alert(f"사전규격 용역 목록 조회 : {bidNtceNm}, totalCount : {totalCount}")
                        break
                    

                except ET.ParseError as e:
                    print(f"XML 파싱 에러: {e}")
                except Exception as e:
                    print(f"다른 에러 발생: {e}")
            else:
                print(f"요청 실패, 상태 코드: {req.status_code}")

          
        
# endregion


# region [나라장터 입찰공고정보서비스 - BidPublicInfoService]
class BidPublicInfoService:
    '''
    나라장터 입찰공고정보서비스
       
    '''
    classNm = "BidPublicInfoService02"

    # region[나라장터검색조건에 의한 입찰공고용역조회]
    @staticmethod
    def getBidPblancListInfoServcPPSSrch(inqryBgnDt="",
                                         inqryEndDt="",
                                         bidNtceNm="",
                                         status_callback=None ):
        
        print (f"나라장터검색조건에 의한 입찰공고용역조회 => {bidNtceNm}")
        selectApi="getBidPblancListInfoServcPPSSrch02"

        start_date = datetime.strptime(inqryBgnDt, "%Y%m%d%H%M")
        end_date = datetime.strptime(inqryEndDt, "%Y%m%d%H%M")

        current_start = start_date

        # 전체 조회 기간을 최대 7일 단위로 분할
        while current_start <= end_date:

            max_end = (current_start + timedelta(days=6)).replace(hour=23,minute=59)
            current_end = min(max_end, end_date)
            search_bgn_dt = current_start.strftime("%Y%m%d%H%M")
            search_end_dt = current_end.strftime("%Y%m%d%H%M")

            msg = (
                f"입찰공고용역 조회중.. "
                f"- 조회 기간: {search_bgn_dt} ~ {search_end_dt}"
            )

            print(msg)

            if status_callback:
                status_callback(msg)
            else:
                logging.info(msg)

            # -------------------------------------------------
            # API 조회 조건
            # -------------------------------------------------

            params = {
                "inqryDiv": "2",
                "inqryBgnDt": search_bgn_dt,
                "inqryEndDt": search_end_dt,
                "bidNtceNm": bidNtceNm,
                "indstrytyCd": indstrytyCd,
            }

            queryUrl = Util.SetqueryUrl(params)

            # -------------------------------------------------
            # 페이지별 조회
            # -------------------------------------------------

            pageNo = 1
            numOfRows = 100
            totalCount = 0

            while True:

                url = (
                    f"{basicUrl}ad/"
                    f"{BidPublicInfoService.classNm}/"
                    f"{selectApi}"
                    f"?pageNo={pageNo}"
                    f"&numOfRows={numOfRows}"
                    f"&ServiceKey={serivceKey}"
                    f"&{queryUrl}type=xml"
                )

                print (url)
                try:
                    req = requests.get(url,timeout=30)
                    req.raise_for_status()
                    root = ET.fromstring(req.text)
                    body = root.find(".//body")
                    if body is None:
                        logging.error(
                            f"API 응답에 body가 없습니다.\n"
                            f"URL: {url}\n"
                            f"응답: {req.text[:1000]}"
                        )
                        break

  
                    total_count_text = body.findtext("totalCount","0")

                    try:
                        totalCount = int(total_count_text)
                    except ValueError:
                        totalCount = 0

                    items = body.find("items")
                    datas = []

                    if items is not None:
                        for item in items.findall("item"):
                            srvceDivNm = item.findtext("srvceDivNm", "N/A")
                            bidNtceNo = item.findtext("bidNtceNo","N/A")
                            bidNtceOrd = item.findtext("bidNtceOrd","N/A")
                            ntceKindNm = item.findtext("ntceKindNm","N/A")
                            bidNtceNmValue = item.findtext("bidNtceNm","N/A")
                            ntceInsttNm = item.findtext("ntceInsttNm","N/A")
                            dminsttNm = item.findtext("dminsttNm","N/A")
                            bidNtceDt = item.findtext("bidNtceDt","-")
                            bidClseDt = item.findtext("bidClseDt","-")
                            opengDt = item.findtext("opengDt","-")
                            presmptPrce = item.findtext("presmptPrce","0")
                            vat = item.findtext("VAT","0")

                            try:
                                asignBdgtAmt = (
                                    int(presmptPrce)
                                    + int(vat)
                                )
                            except (ValueError, TypeError):
                                asignBdgtAmt = 0

                            datas.append([
                                srvceDivNm,
                                bidNtceNo,
                                bidNtceOrd,
                                ntceKindNm,
                                bidNtceNmValue,
                                ntceInsttNm,
                                dminsttNm,
                                opengDt,
                                bidNtceDt,
                                bidClseDt,
                                asignBdgtAmt,
                            ])

                    if datas:
                        Sqlite.Upsert(datas,type="1")

                    # 마지막 페이지인지 확인
                    if pageNo * numOfRows >= totalCount:
                        break

                    pageNo += 1

                except requests.RequestException as e:
                    logging.error(f"API 요청 오류 "f"({search_bgn_dt} ~ {search_end_dt}): {e}")
                    break

                except ET.ParseError as e:
                    logging.error(f"XML 파싱 오류 "f"({search_bgn_dt} ~ {search_end_dt}): {e}")
                    break

                except Exception as e:
                    logging.error(f"조회 중 오류 "f"({search_bgn_dt} ~ {search_end_dt}): {e}")
                    break

            # 다음 조회는 현재 종료일 다음 날 00:00부터 시작
            current_start = (current_end + timedelta(days=1)).replace(hour=0, minute=0)

    # endregion
# endregion


inputDate = datetime.now()
# startDate = (inputDate+ relativedelta(weeks=3)).strftime('%Y%m%d')+"0000"
# endDate = (inputDate + relativedelta(months=2)).strftime('%Y%m%d')+"2359"
# region [telegram 알림]
def telegram_alert(file_path, caption=""):
    token = "7312357814:AAHu04_PCkjMg2A-lQA2pAFxlsuCHp8fS6k"
    chat_id = "-1002614264482"  # 채널 ID
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    
    data = {
        "chat_id": chat_id,
        "caption": caption  # 파일과 함께 첨부할 텍스트 (캡션)
    }
    
    with open(file_path, "rb") as file:
        files = {"document": file}
        response = requests.post(url, data=data, files=files)
    
    # print(response.json())
# endregion


# region [g2b_api]
class g2b_api(QDialog):
    def __init__(self, parent =None):
        super().__init__()
        ui_file = resource_path(
            f"ui/{os.path.splitext(os.path.basename(__file__))[0]}.ui"
        )
        uic.loadUi(ui_file, self)
        
        
        self.init()
        self.initUi()
        self.listener()

    def update_status(self, msg):
        self.lb_status.setText(f"상태: {msg}")
        logging.info(msg)
        QApplication.processEvents()
    
    def init(self):
        Sqlite.clearDB(type="1")
        Sqlite.clearDB(type="2")
        # print ("DB 초기화")

    def initUi(self):
        self.setWindowTitle("5분 단축 - 당신의 퇴근요정!")
        icon_path = resource_path("image/fairy.ico")
        self.setWindowIcon(QIcon(icon_path))

        self.date_1.setDate(inputDate+ relativedelta(weeks=3))
        self.date_2.setDate(inputDate + relativedelta(months=2))
        self.date_3.setDate(inputDate+ relativedelta(days=-7))
        self.date_4.setDate(inputDate)
        # self.rdo_N.setChecked(True)
        self.rdo_StatusY.setChecked(True)
        self.txt_savePath.setText(datagov["savePath"])
        self.txt_code.setText(indstrytyCd)
        self.txt_keyword.setText(datagov["keywords"])

    def listener(self):
        self.btnOk.clicked.connect(self.run)
        
    def run(self):
        global indstrytyCd

        indstrytyCd = self.txt_code.text().strip()

        properies["datagov"]["savePath"] = self.txt_savePath.text()
        properies["datagov"]["indstrytyCd"] = indstrytyCd
        properies["datagov"]["keywords"] = self.txt_keyword.text()

        with open(configPath, "w", encoding="utf-8") as configfile:
            properies.write(configfile)
        
        savePath = self.txt_savePath.text()
        if savePath =="":
            QMessageBox.information(self, "알림","저장경로를 입력해주세요.")
            return
        else:
            # 유효 경로인지 체크
            if os.path.isdir(savePath) == True:
                pass
            else:
                QMessageBox.warning(self, "알림", "경로가 존재하지 않습니다.\n경로를 확인해주세요.")
                return

        # bidNtceNms = ["구축", "유지보수", "유지관리"]

        bidNtceNms = self.txt_keyword.text().split(',')

        startDate1 = (datetime.strptime(self.date_1.text(),'%Y-%m-%d').strftime('%Y%m%d') + "0000")
        endDate1 = (datetime.strptime(self.date_2.text(),'%Y-%m-%d').strftime('%Y%m%d') + "2359")

        print(f"전체 조회 기간: {startDate1} ~ {endDate1}")
        logging.info(f"전체 조회 기간: {startDate1} ~ {endDate1}")

        for bidNtceNm in bidNtceNms:
            BidPublicInfoService.getBidPblancListInfoServcPPSSrch(
                startDate1,
                endDate1,
                bidNtceNm=bidNtceNm.strip(),
                status_callback=self.update_status
            )
        
        # if os.path.exists(savePath+"\\"+filename):
        #     os.remove(savePath+"\\"+filename)

        try:
            selectDB1 = Sqlite.selectDB(savePath, type="1", alert="N")
            if selectDB1 == True:
                logging.info("나라장터 데이터 조회 완료")
                QMessageBox.information(self, "알림", "조회 완료")
        except Exception as e:
            QMessageBox.warning(self, "알림", e.__str__)
            return
               

        try:
            inputDate2 = datetime.strptime(self.date_3.text(),'%Y-%m-%d')
            inputDate3 = datetime.strptime(self.date_4.text(),'%Y-%m-%d')
            # startDate2 = (inputDate+ relativedelta(days=-7)).strftime('%Y%m%d') + "0000"
            startDate2 = (inputDate2).strftime('%Y%m%d') + "0000"
            endDate2 = (inputDate3).strftime('%Y%m%d') + "2359"
            # statusType = input("사전규격 진행상태 표기 방법 선택 ( A : 게시중, 마감 모두 표기, Y : 게시중만 표기) => ").upper()
            if self.rdo_StatusAll.isChecked() :
                statusType = 'A'
            elif self.rdo_StatusY.isChecked():
                statusType = 'Y'

            for bidNtceNm in bidNtceNms:
                HrcspSsstndrdInfoService.getPublicPrcureThngInfoServcPPSSrch(
                    inqryDiv='1',inqryBgnDt=startDate2,inqryEndDt=endDate2,bidNtceNm=bidNtceNm,
                    swBizObjYn='Y',statusType=statusType)

            if self.chk_alert.isChecked():
                alertType = "Y"
            else:
                alertType = "N"
            selectDB2 = Sqlite.selectDB(savePath, type="2",statusType=statusType, alert=alertType)
            if selectDB2 == True:
                logging.info("나라장터 데이터 조회 완료")
                
        except Exception as e:
            QMessageBox.warning(self, "알림", e.__str__)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = g2b_api()
    window.show()
    sys.exit(app.exec_())








