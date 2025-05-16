import os
import configparser


properies = configparser.ConfigParser(interpolation=None)
configPath =rf"{os.getcwd()}\config.ini"
print (configPath)
properies.read(configPath, encoding='utf-8')
datagov = properies['datagov']


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

        queryUrl = util.SetqueryUrl(dict1)

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