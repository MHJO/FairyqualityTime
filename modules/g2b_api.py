import requests, os, sys
import json
import pandas as pd
import xml.etree.ElementTree as ET
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sqlite3
import configparser

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog,QApplication, QMessageBox
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QIcon

"""
    당신의 퇴근요정!

    나라장터 api 활용 엑셀 시트 저장
"""

properies = configparser.ConfigParser(interpolation=None)
configPath =rf"{os.getcwd()}\config.ini"
print (configPath)
properies.read(configPath, encoding='utf-8')

datagov = properies['datagov']



# API 변수 정의 
basicUrl = "http://apis.data.go.kr/1230000/"
# serivceKey = "D83pd0SOWqYWJX2N3uy5jJ4fmpcbCPFOZOQk2Yd7AncIEcHlvTph7S8SHUlhmLM9v1u1CcZGlZPnozhaAhyvuw%3D%3D"
serivceKey = datagov["apikey"]
# indstrytyCd = "1468" # 업종코드
indstrytyCd = datagov["indstrytyCd"]
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
        connection = sqlite3.connect(rf"{os.getcwd()}\Database\나라장터.db")
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

    def selectDB(savePath, type="", statusType=""):
        try:
            connection = sqlite3.connect(rf"{os.getcwd()}\Database\나라장터.db")
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

            # 데이터프레임 출력
            file_path=rf"{savePath}\{filename}"
            try:
                # 기존 엑셀 파일에서 sheet_name 읽기
                existing_df = pd.read_excel(file_path, sheet_name=sheet_name)
            except FileNotFoundError:
                # 파일이 없을 경우 빈 데이터프레임 생성 및 파일 저장
                print(f"'{file_path}' 파일이 존재하지 않아 새로 생성합니다.")
                existing_df = pd.DataFrame()
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    existing_df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"새 파일 생성 후 '{sheet_name}' 시트를 추가했습니다.")
            except ValueError:
                # 지정된 시트가 없을 경우 빈 데이터프레임 생성
                print(f"'{sheet_name}' 시트가 존재하지 않아 새로 생성합니다.")
                existing_df = pd.DataFrame()
                
            # Concatenate the existing and new DataFrames
            updated_df = pd.concat([existing_df, df_new], ignore_index=True)
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                updated_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print("데이터가 'output.xlsx' 파일로 저장되었습니다.")

            connection.close()
            return True
        except Exception as e:
            print (e.__str__)
            return False

    def Upsert(parmas, type):
        try:
            connection = sqlite3.connect(rf"{os.getcwd()}\Database\나라장터.db")
            # if type =="1":
            #     connection = sqlite3.connect(rf"{os.getcwd()}\Database\입찰공고.db")
            # elif type =="2":
            #     connection = sqlite3.connect(rf"{os.getcwd()}\Database\사전규격.db")
            cursor = connection.cursor()
            for i in range(len(parmas)):
                if type =="1":
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
            # "swBizObjYn": swBizObjYn  # SW대상여부 - 
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
    global classNm
    classNm = "BidPublicInfoService"

    # region[나라장터검색조건에 의한 입찰공고용역조회]
    def getBidPblancListInfoServcPPSSrch(inqryBgnDt="",inqryEndDt="",bidNtceNm="" ):
        
        print (f"나라장터검색조건에 의한 입찰공고용역조회 => {bidNtceNm}")
        selectApi="getBidPblancListInfoServcPPSSrch"

        dict1 = {
            "inqryDiv":"2", # 조회구분 - 개찰일시
            # "opengDt":inqryEndDt, # 개찰일시
            "inqryBgnDt":inqryBgnDt, # 조회시작일시
            "inqryEndDt":inqryEndDt, #조회종료일시
            "bidNtceNm":bidNtceNm, # 입찰공고명
            "indstrytyCd":indstrytyCd, # 업종코드            
        }

        queryUrl = Util.SetqueryUrl(dict1)

        url = f"{basicUrl}ad/{classNm}/{selectApi}?pageNo=1&numOfRows=100&ServiceKey={serivceKey}&{queryUrl}type=xml"
        # print (url)
        req = requests.get(url)

        if req.status_code == 200:
            try:
                # XML 파싱
                root = ET.fromstring(req.text)

                totalCount =  (root.find('.//body').find('totalCount').text)
                print ("용역 => ", totalCount)

                # body -> items 태그로 이동
                items = root.find('.//body/items')
                datas =[]
                if items is not None:
                    count = 1
                    
                    for item in items.findall('item'):
                        data = []
                        # 각 item 태그에서 추출할 데이터 (필요한 태그 추가)
                        ref_no = item.find('refNo').text if item.find('refNo') is not None else "N/A"
                        srvceDivNm = item.find('srvceDivNm').text if item.find('srvceDivNm') is not None else "N/A" # 용역구분명
                        bidNtceNo =item.find('bidNtceNo').text if item.find('bidNtceNo') is not None else "N/A" # 입찰공고번호 
                        bidNtceOrd =item.find('bidNtceOrd').text if item.find('bidNtceOrd') is not None else "N/A" # 입찰공고차수
                        bidNNoOrd = f"{bidNtceNo}-{bidNtceOrd}"
                        ntceKindNm =item.find('ntceKindNm').text if item.find('ntceKindNm') is not None else "N/A" # 구분
                        bidNtceNm = item.find('bidNtceNm').text if item.find('bidNtceNm') is not None else "N/A" # 입찰공고명
                        # print (bidNtceNo, bidNtceOrd, bidNtceNm)
                        ntceInsttNm = item.find('ntceInsttNm').text if item.find('ntceInsttNm') is not None else "N/A" # 공고기관명
                        dminsttNm = item.find('dminsttNm').text if item.find('dminsttNm') is not None else "N/A" # 수요기관
                        
                        bidBeginDt = item.find('bidBeginDt').text if item.find('bidBeginDt') is not None else "N/A"  # 입찰개시일시
                        bidNtceDt = item.find('bidNtceDt').text if item.find('bidNtceDt') is not None else "-"# 입찰공고일시
                        bidClseDt = item.find('bidClseDt').text if item.find('bidClseDt') is not None else "-" # 게시일시 -> 입찰마감일시
                        opengDt = item.find('opengDt').text if item.find('opengDt') is not None else "-" # 개찰일시

                        presmptPrce = item.find('presmptPrce').text if item.find('presmptPrce') is not None else "N/A" #추정가격 
                        vat = item.find('VAT').text if item.find('VAT')is not None else "N/A" # 부가가치세
                        asignBdgtAmt = int(presmptPrce) + int(vat)
                        # bdgtAmt = item.find('bdgtAmt').text if item.find('bdgtAmt') is not None else "N/A"
                        data.append(srvceDivNm) # 용역구분
                        data.append(bidNtceNo)
                        data.append(bidNtceOrd) # 차수
                        data.append(ntceKindNm)
                        data.append(bidNtceNm)
                        data.append(ntceInsttNm)
                        data.append(dminsttNm)
                        data.append(opengDt) # 개찰일시
                        # data.append(bidBeginDt) # 입찰개시일시
                        data.append(bidNtceDt) # 입찰공고일시
                        data.append(bidClseDt) # 입찰마감일시
                        data.append(asignBdgtAmt)
                        
                        datas.append(data)
                    Sqlite.Upsert(datas,type="1")
                    
                else:
                        print("items 태그를 찾을 수 없습니다.")
                
            except ET.ParseError as e:
                print(f"XML 파싱 에러: {e}")
            except ValueError as e:
                print(f"데이터 변환 에러: {e}")
            except Exception as e:
                print(f"다른 에러 발생: {e}")

        else:
            print(f"요청 실패, 상태 코드: {req.status_code}")

    # endregion
# endregion


inputDate = datetime.now()
startDate = (inputDate+ relativedelta(weeks=3)).strftime('%Y%m%d')+"0000"
endDate = (inputDate + relativedelta(months=2)).strftime('%Y%m%d')+"2359"

print (inputDate)
# print (rf"{os.getcwd()}\Database\입찰공고.db")


class g2b_api(QDialog):
    def __init__(self, parent =None):
        super().__init__()
        uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '.ui'), self)
        
        self.init()
        self.initUi()
        self.listener()
    
    def init(self):
        Sqlite.clearDB(type="1")
        Sqlite.clearDB(type="2")
        # print ("DB 초기화")

    def initUi(self):
        self.setWindowTitle("5분 단축 - 당신의 퇴근요정!")
        self.setWindowIcon(QIcon('fairy.ico'))

        self.date_1.setDate(inputDate+ relativedelta(weeks=3))
        self.date_2.setDate(inputDate + relativedelta(months=2))
        self.date_3.setDate(inputDate+ relativedelta(days=-7))
        self.date_4.setDate(inputDate)
        # self.rdo_N.setChecked(True)
        self.rdo_StatusY.setChecked(True)
        self.txt_savePath.setText(datagov["savePath"])

    def listener(self):
        self.btnOk.clicked.connect(self.run)
    
    def run(self):
        properies["datagov"]["savePath"] = self.txt_savePath.text()
        with open(configPath, 'w', encoding='utf-8') as configfile:
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

        bidNtceNms = ["구축", "유지보수", "유지관리"]
        # 문자열로 된 날짜를 datetime 객체로 변환
        start = datetime.strptime(startDate[:8], '%Y%m%d')
        end = datetime.strptime(endDate[:8], '%Y%m%d')

        # 한 달 단위로 날짜를 나누기
        current = start
        self.progressBar.setValue(10)
        while current < end:
            next_month = current + relativedelta(months=1)
            if next_month > end:
                next_month = end  # endDate를 초과하지 않도록 조정
            
            startDate1 =current.strftime('%Y%m%d')+ "0000"
            endDate1 =(next_month-relativedelta(days=1)).strftime('%Y%m%d')+ "2359"
            print(f"기간: {startDate1} ~ {endDate1}")
            for bidNtceNm in bidNtceNms:
                BidPublicInfoService.getBidPblancListInfoServcPPSSrch(startDate1,endDate1,bidNtceNm=bidNtceNm)
            current = next_month

        # savePath = input("저장 경로 입력 : ")
        
        if os.path.exists(savePath+"\\"+filename):
            os.remove(savePath+"\\"+filename)
        selectDB1 = Sqlite.selectDB(savePath, type="1")
        if selectDB1 == True:
            print ("입찰용역 완료 -----> 사전규격 진행")
            self.progressBar.setValue(50)

            startDate2 = (inputDate+ relativedelta(days=-7)).strftime('%Y%m%d') + "0000"
            endDate2 = (inputDate).strftime('%Y%m%d') + "2359"
            # statusType = input("사전규격 진행상태 표기 방법 선택 ( A : 게시중, 마감 모두 표기, Y : 게시중만 표기) => ").upper()
            if self.rdo_StatusAll.isChecked() :
                statusType = 'A'
            elif self.rdo_StatusY.isChecked():
                statusType = 'Y'

            for bidNtceNm in bidNtceNms:
                HrcspSsstndrdInfoService.getPublicPrcureThngInfoServcPPSSrch(inqryDiv='1',inqryBgnDt=startDate2,inqryEndDt=endDate2,bidNtceNm=bidNtceNm, statusType=statusType)

            selectDB2 = Sqlite.selectDB(savePath, type="2",statusType=statusType)
            if selectDB2 == True:
                # input("수행 완료, any key press....")
                self.progressBar.setValue(100)



    



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = g2b_api()
    window.show()
    sys.exit(app.exec_())









