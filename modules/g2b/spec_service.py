 # 사전규격 조회
import logging
from datetime import datetime

class SpecService:
    SERVICE_PATH = "ao/HrcspSsstndrdInfoService"
    OPERATION = "getPublicPrcureThngInfoServcPPSSrch"
    NUM_OF_ROWS = 100

    def __init__(self, api_client):
        self.api_client = api_client

    def search(
        self,
        inqryBgnDt,
        inqryEndDt,
        bidNtceNm="",
        swBizObjYn="",
        status_callback=None
    ):
        """
        사전규격 조회

        Args:
            inqryBgnDt: 조회 시작일 (YYYYMMDDHHMM)
            inqryEndDt: 조회 종료일 (YYYYMMDDHHMM)
            bidNtceNm: 품명 또는 검색어
            swBizObjYn: 소프트웨어 사업 여부
            status_callback: 진행 상태 콜백

        Returns:
            list: 사전규격 조회 결과
        """

        start_date = datetime.strptime(inqryBgnDt, "%Y%m%d%H%M")
        end_date = datetime.strptime(inqryEndDt, "%Y%m%d%H%M")

        if start_date > end_date:
            raise ValueError("조회 시작일이 종료일보다 늦습니다.")

        logging.info(
            "사전규격 조회 시작: %s ~ %s / 검색어: %s",
            inqryBgnDt,
            inqryEndDt,
            bidNtceNm
        )

        results = []
        page_no = 1
        total_count = 0

        while True:
            self._update_status(
                f"사전규격 조회 중... {page_no}페이지",
                status_callback
            )

            params = {
                "pageNo": page_no,
                "numOfRows": self.NUM_OF_ROWS,
                "inqryDiv": "1",
                "inqryBgnDt": inqryBgnDt,
                "inqryEndDt": inqryEndDt,
                "prdctClsfcNoNm": bidNtceNm,
                "swBizObjYn": swBizObjYn
            }

            root = self.api_client.request_xml(
                service_path=self.SERVICE_PATH,
                operation=self.OPERATION,
                params=params
            )

            body = root.find(".//body")

            if body is None:
                logging.warning(
                    "사전규격 API 응답에 body가 없습니다. page=%s",
                    page_no
                )
                break

            try:
                total_count = int(body.findtext("totalCount", "0"))
            except (TypeError, ValueError):
                total_count = 0

            items = body.find("items")

            if items is None:
                break

            page_results = []

            for item in items.findall("item"):
                bsnsDivNm = item.findtext("bsnsDivNm", "")
                prdctClsfcNoNm = item.findtext("prdctClsfcNoNm", "")
                rlDminsttNm = item.findtext("rlDminsttNm", "")
                orderInsttNm = item.findtext("orderInsttNm", "")
                ofclNm = item.findtext("ofclNm", "")
                rcptDt = item.findtext("rcptDt", "")

                opninRgstClseDt = item.findtext(
                    "opninRgstClseDt",
                    ""
                )

                asignBdgtAmt = item.findtext(
                    "asignBdgtAmt",
                    "0"
                )

                status = self._compare_with_time(opninRgstClseDt)

                try:
                    asignBdgtAmt = int(
                        float(asignBdgtAmt.replace(",", ""))
                    )
                except (ValueError, AttributeError):
                    asignBdgtAmt = 0

                row = [
                    bsnsDivNm,
                    prdctClsfcNoNm,
                    rlDminsttNm,
                    orderInsttNm,
                    ofclNm,
                    rcptDt,
                    status,
                    asignBdgtAmt
                ]

                page_results.append(row)

            results.extend(page_results)

            logging.info(
                "사전규격 조회 진행: page=%s / total=%s / 누적=%s",
                page_no,
                total_count,
                len(results)
            )

            if page_no * self.NUM_OF_ROWS >= total_count:
                break

            if not page_results:
                break

            page_no += 1

        logging.info(
            "사전규격 조회 완료: 총 %s건",
            len(results)
        )

        return results

    @staticmethod
    def _compare_with_time(compare_time):
        """
        기존 Util.compare_with_time()과 동일한 기준
        """

        if not compare_time:
            return ""

        try:
            end_time = datetime.strptime(
                compare_time,
                "%Y-%m-%d %H:%M:%S"
            )

            if datetime.now() < end_time:
                return "게시중"

            return "마감"

        except ValueError:
            logging.warning(
                "사전규격 마감일 형식 오류: %s",
                compare_time
            )
            return ""

    @staticmethod
    def _update_status(msg, callback=None):
        if callback:
            callback(msg)
        else:
            logging.info(msg)