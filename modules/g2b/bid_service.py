# 입찰공고 조회
import logging

from datetime import datetime, timedelta


class BidService:
    """
    나라장터 입찰공고정보서비스

    담당 기능
    - 입찰공고 용역 조회
    - 조회 기간 분할
    - 페이지별 데이터 조회
    - XML 응답 데이터 추출

    DB 저장 및 엑셀 생성은 담당하지 않음.
    """

    SERVICE_PATH = "ad/BidPublicInfoService02"
    OPERATION = "getBidPblancListInfoServcPPSSrch02"

    NUM_OF_ROWS = 100

    def __init__(self, api_client, industry_code=""):
        self.api_client = api_client
        self.industry_code = industry_code

    def search(
        self,
        inqryBgnDt,
        inqryEndDt,
        bidNtceNm="",
        status_callback=None
    ):
        """
        나라장터 입찰공고 용역 조회

        Args:
            inqryBgnDt (str): 조회 시작일시 YYYYMMDDHHMM
            inqryEndDt (str): 조회 종료일시 YYYYMMDDHHMM
            bidNtceNm (str): 입찰공고명 검색어
            status_callback (callable): 진행 상태 콜백

        Returns:
            list: 조회 결과
        """

        start_date = datetime.strptime(
            inqryBgnDt, "%Y%m%d%H%M"
        )

        end_date = datetime.strptime(
            inqryEndDt, "%Y%m%d%H%M"
        )

        if start_date > end_date:
            raise ValueError("조회 시작일이 종료일보다 늦습니다.")

        results = []

        current_start = start_date

        logging.info(
            f"입찰공고 조회 시작: {inqryBgnDt} ~ {inqryEndDt}, "
            f"검색어: {bidNtceNm}"
        )

        # 전체 조회 기간을 최대 7일 단위로 분할
        while current_start <= end_date:

            max_end = (
                current_start + timedelta(days=6)
            ).replace(hour=23, minute=59, second=0)

            current_end = min(max_end, end_date)

            search_bgn_dt = current_start.strftime("%Y%m%d%H%M")
            search_end_dt = current_end.strftime("%Y%m%d%H%M")

            msg = (
                f"입찰공고용역 조회중.. "
                f"- 조회 기간: {search_bgn_dt} ~ {search_end_dt}"
            )

            self._update_status(msg, status_callback)

            # 기간별 조회 결과
            period_results = self._search_period(
                search_bgn_dt,
                search_end_dt,
                bidNtceNm
            )

            results.extend(period_results)

            # 다음 조회는 현재 종료일 다음 날 00:00부터
            current_start = (
                current_end + timedelta(days=1)
            ).replace(hour=0, minute=0)

        logging.info(
            f"입찰공고 조회 완료: 검색어={bidNtceNm}, "
            f"조회 건수={len(results)}"
        )

        return results

    def _search_period(
        self,
        start_date,
        end_date,
        bidNtceNm
    ):
        """
        지정된 기간의 페이지별 조회
        """

        results = []

        page_no = 1
        total_count = 0

        while True:

            params = {
                "pageNo": page_no,
                "numOfRows": self.NUM_OF_ROWS,
                "inqryDiv": "2",
                "inqryBgnDt": start_date,
                "inqryEndDt": end_date,
                "bidNtceNm": bidNtceNm,
                "indstrytyCd": self.industry_code,
            }

            try:
                root = self.api_client.request_xml(
                    service_path=self.SERVICE_PATH,
                    operation=self.OPERATION,
                    params=params
                )

                body = root.find(".//body")

                if body is None:
                    logging.error(
                        f"API 응답에 body가 없습니다. "
                        f"기간: {start_date} ~ {end_date}"
                    )
                    break

                total_count_text = body.findtext(
                    "totalCount", "0"
                )

                try:
                    total_count = int(total_count_text)
                except (ValueError, TypeError):
                    total_count = 0

                items = body.find("items")

                page_results = []

                if items is not None:

                    for item in items.findall("item"):

                        srvceDivNm = item.findtext(
                            "srvceDivNm", "N/A"
                        )

                        bidNtceNo = item.findtext(
                            "bidNtceNo", "N/A"
                        )

                        bidNtceOrd = item.findtext(
                            "bidNtceOrd", "N/A"
                        )

                        ntceKindNm = item.findtext(
                            "ntceKindNm", "N/A"
                        )

                        bidNtceNmValue = item.findtext(
                            "bidNtceNm", "N/A"
                        )

                        ntceInsttNm = item.findtext(
                            "ntceInsttNm", "N/A"
                        )

                        dminsttNm = item.findtext(
                            "dminsttNm", "N/A"
                        )

                        bidNtceDt = item.findtext(
                            "bidNtceDt", "-"
                        )

                        bidClseDt = item.findtext(
                            "bidClseDt", "-"
                        )

                        opengDt = item.findtext(
                            "opengDt", "-"
                        )

                        presmptPrce = item.findtext(
                            "presmptPrce", "0"
                        )

                        vat = item.findtext(
                            "VAT", "0"
                        )

                        try:
                            asignBdgtAmt = (
                                int(presmptPrce)
                                + int(vat)
                            )
                        except (ValueError, TypeError):
                            asignBdgtAmt = 0

                        page_results.append([
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

                results.extend(page_results)

                logging.info(
                    f"입찰공고 조회: "
                    f"{start_date} ~ {end_date}, "
                    f"페이지={page_no}, "
                    f"조회={len(page_results)}건, "
                    f"전체={total_count}건"
                )

                # 마지막 페이지 확인
                if page_no * self.NUM_OF_ROWS >= total_count:
                    break

                # 데이터가 없는 경우 반복 방지
                if not page_results:
                    break

                page_no += 1

            except Exception as e:
                print((
                    f"입찰공고 API 조회 오류: "
                    f"{start_date} ~ {end_date}, "
                    f"페이지={page_no}, 오류={e}"
                ))
                logging.error(
                    f"입찰공고 API 조회 오류: "
                    f"{start_date} ~ {end_date}, "
                    f"페이지={page_no}, 오류={e}"
                )

                raise RuntimeError(
                    f"입찰공고 조회에 실패했습니다.\n"
                    f"조회 기간: {start_date} ~ {end_date}\n"
                    f"페이지: {page_no}\n"
                    f"원인: {e}"
                ) from e

        return results

    @staticmethod
    def _update_status(msg, callback=None):

        if callback:
            callback(msg)
        else:
            logging.info(msg)