import requests, os
import json
import pandas as pd
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sqlite3


"""
    당신의 퇴근요정

    나라장터 api 활용 엑셀 시트 저장
"""



# API 변수 정의 
basicUrl = "http://apis.data.go.kr/1230000/"
serivceKey = "D83pd0SOWqYWJX2N3uy5jJ4fmpcbCPFOZOQk2Yd7AncIEcHlvTph7S8SHUlhmLM9v1u1CcZGlZPnozhaAhyvuw%3D%3D"
indstrytyCd = "1468" # 업종코드

class Util:
    def SetqueryUrl(params:dict = dict()):
        queryUrl = ""
        for i in params:
            if params[i] != '':
                queryUrl += f"{i}={params[i]}&"
        # print (queryUrl)
        return queryUrl
    
class Sqlite:
    def clearDB():
        connection = sqlite3.connect(rf"{os.getcwd()}\Database\입찰공고.db")
        cursor = connection.cursor()
        sql_command = """
                DELETE FROM BidPblancListInfoServcPPSSrch
            """
        cursor.execute(sql_command)
        cursor.fetchall()
        connection.commit()

        connection.close()

    def selectDB(savePath):
        connection = sqlite3.connect(rf"{os.getcwd()}\Database\입찰공고.db")
        cursor = connection.cursor()
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
        data = cursor.execute(sql_command)
        
        # 컬럼명 포함 데이터프레임 생성
        col_names = [desc[0] for desc in cursor.description]  # SQL 쿼리 결과의 컬럼명 가져오기
        df = pd.DataFrame(data, columns=col_names)
        # df = pd.DataFrame(data)

        # 데이터프레임 출력
        print("DataFrame 출력:")
        print(df)

        # Excel 파일로 저장 (openpyxl 엔진 사용)
        filename = "나라장터-입찰공고용역조회_{}.xlsx".format(time.strftime("%Y%m%d"))
        df.to_excel(rf"{savePath}\{filename}", index=False, engine='openpyxl')
        print("데이터가 'output.xlsx' 파일로 저장되었습니다.")

        connection.close()

    def Upsert(parmas):
        try:
            connection = sqlite3.connect(rf"{os.getcwd()}\Database\입찰공고.db")
            cursor = connection.cursor()
            for i in range(len(parmas)):
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
                # sql_command = f'''
                #     INSERT INTO BidPblancListInfoServcPPSSrch (bidNtceNo,bidNtceOrd,bidNtceNm,ntceInsttNm,dminsttNm,bidNtceDt,bidClseDt,asignBdgtAmt,srvceDivNm)
                #         VALUES ("{parmas[i][0]}", "{parmas[i][1]}", "{parmas[i][2]}", "{parmas[i][3]}",
                #         "{parmas[i][4]}", "{parmas[i][5]}", "{parmas[i][6]}","{parmas[i][7]}", "{parmas[i][8]}")
                #         ON CONFLICT(bidNtceNo) 
                #         DO UPDATE SET 
                #             bidNtceNm = EXCLUDED.bidNtceNm,
                #             ntceInsttNm = EXCLUDED.ntceInsttNm,
                #             dminsttNm = EXCLUDED.dminsttNm,
                #             bidNtceDt = EXCLUDED.bidNtceDt ,
                #             bidClseDt = EXCLUDED.bidClseDt,
                #             asignBdgtAmt = EXCLUDED.asignBdgtAmt,
                #             srvceDivNm = EXCLUDED.srvceDivNm
                # '''
                # bidNtceNo = EXCLUDED.bidNtceNo,
                # bidNtceOrd = EXCLUDED.bidNtceOrd,
                # print (sql_command)

                cursor.execute(sql_command)
                cursor.fetchall()
                connection.commit()

            connection.close()
        except Exception as e:
            print (str(e))


class HrcspSsstndrdInfoService:
    '''	조달청_나라장터 사전규격정보서비스 '''
    global classNm
    classNm = "HrcspSsstndrdInfoService"
        
    def getPublicPrcureThngInfoServcPPSSrch(inqryDiv="1",inqryBgnDt="",inqryEndDt=""):
        '''	
            나라장터 검색조건에 의한 사전규격 용역 목록 조회

            -검색유형: 사전규격공개
            -진행일자: 최근 일주일(ex: 4.8~4.15)
            -업무구분: 일반용역, 기술용역
            - 사업명: 구축, 유지관리, 유지보수
        
        '''

        selectApi="getPublicPrcureThngInfoServcPPSSrch"

        url = f"{basicUrl}ao/{classNm}/{selectApi}?inqryDiv={inqryDiv}&inqryBgnDt={inqryBgnDt}&inqryEndDt={inqryEndDt}&pageNo=1&numOfRows=100&ServiceKey={serivceKey}"
        req = requests.get(url)

        if req.status_code == 200:
            try:
                # XML 파싱
                root = ET.fromstring(req.text)

                # body -> items 태그로 이동
                items = root.find('.//body/items')
                if items is not None:
                    data = []
                    for item in items.findall('item'):
                        # 각 item 태그에서 추출할 데이터 (필요한 태그 추가)
                        ref_no = item.find('refNo').text if item.find('refNo') is not None else "N/A"
                        order_instt_nm = item.find('orderInsttNm').text if item.find('orderInsttNm') is not None else "N/A"
                        prdct_Clsfc_No_Nm = item.find('prdctClsfcNoNm').text if item.find('prdctClsfcNoNm') is not None else "N/A"
                        asign_bdgt_amt = item.find('asignBdgtAmt').text if item.find('asignBdgtAmt') is not None else "N/A"

                        data.append({"참조번호": ref_no,"품명":prdct_Clsfc_No_Nm, "발주기관명": order_instt_nm, "배정예산금액(원화)":  f"{int(asign_bdgt_amt):,}"})

                    # pandas 데이터프레임으로 변환
                    df = pd.DataFrame(data)

                    # 데이터프레임 출력
                    print("DataFrame 출력:")
                    print(df)

                    # Excel 파일로 저장 (openpyxl 엔진 사용)
                    filename = "나라장터_{}.xlsx".format(time.strftime("%Y%m%d%H%M%S"))
                    df.to_excel(rf"D:\iway\2025\기타\나라장터\{filename}", index=False, engine='openpyxl')
                    print("데이터가 'output.xlsx' 파일로 저장되었습니다.")

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



# 나라장터 입찰공고정보서비스 - BidPublicInfoService
# 나라장터검색조건에 의한 입찰공고공사조회
class BidPublicInfoService:
    '''
    나라장터 입찰공고정보서비스
    
    --- 검색조건 ---
    -공고/개찰일자: 개찰일자, 현재 날짜로부터 3주 후부터~현재 날짜로부터 2개월 후 날짜까지
    -업무구분: 일반용역, 기술용역, 기타, 민간
    -업종: 1468 소프트웨어사업자
    -공고명: 구축 / 유지관리 / 유지보수 (각각 검색)   
    
    '''

    
    global classNm
    classNm = "BidPublicInfoService"

    # region [나라장터검색조건에 의한 입찰공고공사조회]
    def getBidPblancListInfoCnstwkPPSSrch(inqryDiv="1",inqryBgnDt="",inqryEndDt="",bidNtceNm=""):
        '''나라장터검색조건에 의한 입찰공고공사조회'''
        selectApi="getBidPblancListInfoCnstwkPPSSrch"
        '''
        inqryDiv
        1:공고게시일시, 2:개찰일시
            1. 공고게시일시 : 공고일자(pblancDate)
            2. 개찰일시 : 개찰일시(opengDt)

        inqryBgnDt, inqryEndDt (조회시작일시, 조회종료일시) ==> YYYYMMDDHHMM
            조회구분이 '1'인 경우 공고게시일시 필수, '2'인 경우 개찰일시 필수
        indstrytyCd 업종코드
        indstrytyNm 업종명
        '''
        dict1 = {"inqryDiv":inqryDiv,"inqryBgnDt":inqryBgnDt,"inqryEndDt":inqryEndDt,"bidNtceNm":bidNtceNm,"indstrytyCd":indstrytyCd}
        queryUrl = Util.SetqueryUrl(dict1)
        # queryUrl = f"inqryDiv={inqryDiv}&inqryBgnDt={inqryBgnDt}&inqryEndDt={inqryEndDt}&bidNtceNm={bidNtceNm}"
        url = f"{basicUrl}ad/{classNm}/{selectApi}?pageNo=1&numOfRows=1000&ServiceKey={serivceKey}&{queryUrl}type=xml"
        req = requests.get(url)

        if req.status_code == 200:
            try:
                # XML 파싱
                root = ET.fromstring(req.text)

                # body -> items 태그로 이동
                items = root.find('.//body/items')
                if items is not None:
                    data = []
                    for item in items.findall('item'):
                        # 각 item 태그에서 추출할 데이터 (필요한 태그 추가)
                        ref_no = item.find('refNo').text if item.find('refNo') is not None else "N/A"
                        bidNtceNm = item.find('bidNtceNm').text if item.find('bidNtceNm') is not None else "N/A"
                        ntceInsttNm = item.find('ntceInsttNm').text if item.find('ntceInsttNm') is not None else "N/A"
                        bdgtAmt = item.find('bdgtAmt').text if item.find('bdgtAmt') is not None else "N/A"

                        data.append({"참조번호": ref_no,
                                     "입찰공고명":bidNtceNm, 
                                     "공고기관명": ntceInsttNm, 
                                     "예산금액":   f"{int(bdgtAmt):,}"})

                    # pandas 데이터프레임으로 변환
                    df = pd.DataFrame(data)

                    # 데이터프레임 출력
                    print("DataFrame 출력:")
                    print(df)

                    # Excel 파일로 저장 (openpyxl 엔진 사용)
                    filename = "나라장터-입찰공고공사조회_{}.xlsx".format(time.strftime("%Y%m%d%H%M%S"))
                    df.to_excel(rf"D:\iway\2025\기타\나라장터\{filename}", index=False, engine='openpyxl')
                    print("데이터가 'output.xlsx' 파일로 저장되었습니다.")

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
        print (url)
        req = requests.get(url)

        if req.status_code == 200:
            try:
                # XML 파싱
                root = ET.fromstring(req.text)

                totalCount =  (root.find('.//body').find('totalCount').text)
                print (totalCount)

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
                    Sqlite.Upsert(datas)
                    
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


inputDate = datetime.now()
startDate = (inputDate+ relativedelta(weeks=3)).strftime('%Y%m%d')+"0000"
endDate = (inputDate + relativedelta(months=2)).strftime('%Y%m%d')+"2359"

print (inputDate)
print (rf"{os.getcwd()}\Database\입찰공고.db")

Sqlite.clearDB()
print ("DB 초기화")


from datetime import datetime
from dateutil.relativedelta import relativedelta


# 기준 날짜 설정
inputDate = datetime.now()
startDate = (inputDate + relativedelta(weeks=3)).strftime('%Y%m%d') + "0000"
endDate = (inputDate + relativedelta(months=2)).strftime('%Y%m%d') + "2359"

# 문자열로 된 날짜를 datetime 객체로 변환
start = datetime.strptime(startDate[:8], '%Y%m%d')
end = datetime.strptime(endDate[:8], '%Y%m%d')

# 한 달 단위로 날짜를 나누기
current = start
bidNtceNms = ["구축", "유지보수", "유지관리"]
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

savePath = input("저장 경로 입력 : ")
Sqlite.selectDB(savePath)
input("수행 완료, any key press....")


# print (rf"{os.getcwd()}\Database\입찰공고.db")