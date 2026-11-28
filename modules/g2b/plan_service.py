# 발주계획 조회
# modules/g2b/plan_service.py

import os
import sqlite3
from modules import logger
import requests
import xml.etree.ElementTree as ET

from typing import Optional


class PlanService:
    SERVICE_PATH = "ao/OrderPlanSttusService"
    OPERATION = "getOrderPlanSttusListServcPPSSrch"
    NUM_OF_ROWS = 100

    """
    나라장터 발주계획 조회 서비스

    API 조회 → XML 파싱 → SQLite 저장

    Args:
        inqryBgnDt: 조회 시작일 (YYYYMMDDHHMM)
        inqryEndDt: 조회 종료일 (YYYYMMDDHHMM) * 최대 1개월
        orderBgnYm:	발주시작년월 (YYYYMM)
        orderEndYm:	발주종료년월 (YYYYMM) * 최대 1달

        status_callback: 진행 상태 콜백


    """

    
    TABLE_NAME = "OrderPlanSttusListServcPPSSrch"

    def __init__(self, api_client):
        self.api_client = api_client

    # --------------------------------------------------
    # 로그
    # --------------------------------------------------

    def _log(self, message):
        if self.logger:
            self.logger.info(message)

    # --------------------------------------------------
    # DB 저장
    # --------------------------------------------------

    def _save_to_db(self, datas):
        """
        발주계획 데이터 DB 저장
        기존 데이터와 중복되는 항목은 저장하지 않음.

        중복 기준:
        bizNm + orderInsttNm + nticeDt
        """

        if not datas:
            return 0

        connection = sqlite3.connect(self.db_path)

        try:
            cursor = connection.cursor()

            sql = f"""
                INSERT INTO {self.TABLE_NAME} (
                    bizNm,
                    orderInsttNm,
                    nticeDt,
                    sumOrderAmt
                )
                SELECT ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM {self.TABLE_NAME}
                    WHERE bizNm = ?
                    AND orderInsttNm = ?
                    AND nticeDt = ?
                )
            """

            before_count = connection.total_changes

            for data in datas:
                bizNm, orderInsttNm, nticeDt, sumOrderAmt = data

                cursor.execute(
                    sql,
                    (
                        bizNm,
                        orderInsttNm,
                        nticeDt,
                        sumOrderAmt,
                        bizNm,
                        orderInsttNm,
                        nticeDt
                    )
                )

            inserted_count = connection.total_changes - before_count

            connection.commit()

            return inserted_count

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    # --------------------------------------------------
    # XML 파싱
    # --------------------------------------------------

    def _parse_response(self, response_text):

        root = ET.fromstring(response_text)

        body = root.find(".//body")

        if body is None:
            header = root.find(".//header")

            result_code = (
                header.findtext("resultCode", "")
                if header is not None else ""
            )

            result_msg = (
                header.findtext("resultMsg", "")
                if header is not None else ""
            )

            raise ValueError(
                f"API 응답에 body가 없습니다. "
                f"({result_code}: {result_msg})"
            )

        total_count = int(body.findtext("totalCount", "0"))

        items = body.find("items")

        datas = []

        if items is not None:

            for item in items.findall("item"):

                biz_nm = item.findtext("bizNm", "N/A")
                order_instt_nm = item.findtext(
                    "orderInsttNm", "N/A"
                )
                ntice_dt = item.findtext("nticeDt", "N/A")
                sum_order_amt = item.findtext(
                    "sumOrderAmt", "0"
                )

                datas.append([
                    biz_nm,
                    order_instt_nm,
                    ntice_dt,
                    sum_order_amt
                ])

        return total_count, datas

    # --------------------------------------------------
    # 발주계획 API 조회
    # --------------------------------------------------

    def get_order_plan(
        self,
        order_bgn_ym="",
        order_end_ym="",
        inqry_bgn_dt="",
        inqry_end_dt="",
        bid_ntce_nm=""
    ):
        """
        나라장터 발주계획 조회

        Parameters
        ----------
        order_bgn_ym : str
            발주시작년월 (YYYYMM)

        order_end_ym : str
            발주종료년월 (YYYYMM)

        inqry_bgn_dt : str
            조회시작일시 (YYYYMMDDHHMM)

        inqry_end_dt : str
            조회종료일시 (YYYYMMDDHHMM)

        bid_ntce_nm : str
            사업명 검색어

        Returns
        -------
        dict
            total_count : API 전체 조회 건수
            fetched_count : 실제 수집 건수
            inserted_count : DB 신규 저장 건수
        """

        params = {
            "ServiceKey": self.service_key,
            "pageNo": 1,
            "numOfRows": 100,
            "type": "xml",
            "orderBgnYm": order_bgn_ym,
            "orderEndYm": order_end_ym,
            "inqryBgnDt": inqry_bgn_dt,
            "inqryEndDt": inqry_end_dt,
            "bizNm": bid_ntce_nm
        }

        total_count = 0
        fetched_count = 0
        inserted_count = 0

        page_no = 1

        self._log(
            f"발주계획 조회 시작: {bid_ntce_nm} "
            f"({inqry_bgn_dt} ~ {inqry_end_dt})"
        )

        while True:

            params["pageNo"] = page_no

            try:
                response = self.session.get(
                    self.API_URL,
                    params=params,
                    timeout=self.timeout
                )

                response.raise_for_status()

                api_total_count, datas = self._parse_response(
                    response.text
                )

                total_count = api_total_count

                if not datas:
                    break

                fetched_count += len(datas)

                # DB 저장
                inserted = self._save_to_db(datas)

                inserted_count += inserted

                self._log(
                    f"발주계획 {page_no}페이지 조회 완료 "
                    f"({len(datas)}건 / 신규 저장 {inserted}건)"
                )

                # 마지막 페이지 확인
                if page_no * params["numOfRows"] >= total_count:
                    break

                page_no += 1

            except requests.RequestException as e:

                self._log(f"발주계획 API 요청 오류: {e}")
                raise

            except ET.ParseError as e:

                self._log(f"발주계획 XML 파싱 오류: {e}")
                raise

            except Exception as e:

                self._log(f"발주계획 조회 오류: {e}")
                raise

        self._log(
            f"발주계획 조회 완료: "
            f"전체 {total_count}건 / "
            f"수집 {fetched_count}건 / "
            f"신규 저장 {inserted_count}건"
        )

        return {
            "total_count": total_count,
            "fetched_count": fetched_count,
            "inserted_count": inserted_count
        }

    # --------------------------------------------------
    # 리소스 정리
    # --------------------------------------------------

    def close(self):
        self.session.close()