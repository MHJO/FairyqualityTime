# SQLite 조회 및 저장
# modules/g2b/database.py

import os
import sys
import sqlite3
import logging


# ==================================================
# DB 경로 설정
# ==================================================

if getattr(sys, "frozen", False):
    APP_PATH = os.path.dirname(sys.executable)
else:
    APP_PATH = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )

DB_PATH = os.path.join(APP_PATH, "Database", "나라장터.db")


class Sqlite:

    # ==================================================
    # DB 연결
    # ==================================================

    @staticmethod
    def get_connection():
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        return sqlite3.connect(DB_PATH)

    # ==================================================
    # 데이터 전체 삭제
    # ==================================================

    @staticmethod
    def clearDB(type):
        if type == "1":
            table_name = "BidPblancListInfoServcPPSSrch"

        elif type == "2":
            table_name = "HrcspSsstndrdInfoService"

        else:
            raise ValueError(f"잘못된 DB 타입입니다: {type}")

        sql = f"DELETE FROM {table_name}"

        with Sqlite.get_connection() as connection:
            connection.execute(sql)

        logging.info("DB 데이터 삭제 완료: type=%s", type)

    # ==================================================
    # 데이터 저장
    # ==================================================

    @staticmethod
    def Upsert(params, type, check_duplicate=True):

        try:
            if type == "1":

                table_name = "BidPblancListInfoServcPPSSrch"

                columns = """
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
                """

                placeholders = ",".join(["?"] * 11)

                values = """
                    SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                """

                if check_duplicate:
                    values += """
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM BidPblancListInfoServcPPSSrch
                            WHERE srvceDivNm = ?
                            AND bidNtceNo = ?
                            AND bidNtceOrd = ?
                            AND ntceKindNm = ?
                            AND bidNtceDt = ?
                        )
                    """

            elif type == "2":

                table_name = "HrcspSsstndrdInfoService"

                columns = """
                    bsnsDivNm,
                    prdctClsfcNoNm,
                    rlDminsttNm,
                    orderInsttNm,
                    ofclNm,
                    rcptDt,
                    Status,
                    asignBdgtAmt
                """

                placeholders = ",".join(["?"] * 8)

                values = """
                    SELECT ?, ?, ?, ?, ?, ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM HrcspSsstndrdInfoService
                        WHERE bsnsDivNm = ?
                        AND prdctClsfcNoNm = ?
                        AND rlDminsttNm = ?
                        AND orderInsttNm = ?
                        AND rcptDt = ?
                    )
                """

            else:
                raise ValueError(f"잘못된 DB 타입입니다: {type}")

            sql = f"""
                INSERT INTO {table_name} ({columns})
                {values}
            """

            inserted_count = 0

            with Sqlite.get_connection() as connection:

                cursor = connection.cursor()

                for row in params:

                    row = tuple(row)

                    if type == "1" and not check_duplicate:
                        sql_command = f"""
                            INSERT INTO {table_name} ({columns})
                            VALUES ({placeholders})
                        """
                        cursor.execute(sql_command, row)

                    elif type == "1":
                        duplicate_params = (
                            row
                            + (
                                row[0],
                                row[1],
                                row[2],
                                row[3],
                                row[8]
                            )
                        )
                        cursor.execute(sql, duplicate_params)

                    else:
                        duplicate_params = (
                            row
                            + (
                                row[0],
                                row[1],
                                row[2],
                                row[3],
                                row[5]
                            )
                        )
                        cursor.execute(sql, duplicate_params)

                    inserted_count += cursor.rowcount

            logging.info(
                "DB 저장 완료: type=%s / 입력=%s건 / 저장=%s건",
                type,
                len(params),
                inserted_count
            )

            return True

        except Exception:
            logging.exception("DB 저장 실패: type=%s", type)
            return False

    # ==================================================
    # 엑셀 출력용 데이터 조회
    # ==================================================

    @staticmethod
    def selectDB(type="", statusType=""):

        if type == "1":

            sql = """
                SELECT
                    srvceDivNm as 업무구분,
                    ntceKindNm as 구분,
                    (bidNtceNo || '-' || bidNtceOrd) as 입찰공고번호,
                    bidNtceNm as 공고명,
                    ntceInsttNm as 공고기관,
                    dminsttNm as 수요기관,
                    (bidNtceDt || '(' || bidClseDt || ')')
                        as '게시일시(입찰마감일시)',
                    printf('%,d', CAST(asignBdgtAmt AS INTEGER))
                        || '원' AS 사업금액
                FROM BidPblancListInfoServcPPSSrch
            """

        elif type == "2":

            sql = """
                SELECT
                    bsnsDivNm as 업무구분,
                    prdctClsfcNoNm as 사업명,
                    rlDminsttNm as 수요기관,
                    orderInsttNm as 공고기관,
                    ofclNm as 담당자,
                    rcptDt as 진행일자,
                    Status as 진행상태,
                    printf('%,d', CAST(asignBdgtAmt AS INTEGER))
                        || '원' AS '배정예산금액(원화)'
                FROM HrcspSsstndrdInfoService
            """

            if statusType == "Y":
                sql += " WHERE Status != '마감'"

            elif statusType != "A":
                raise ValueError(
                    f"잘못된 사전규격 조회 상태입니다: {statusType}"
                )

        else:
            raise ValueError(f"잘못된 DB 타입입니다: {type}")

        with Sqlite.get_connection() as connection:

            cursor = connection.execute(sql)

            columns = [
                desc[0]
                for desc in cursor.description
            ]

            rows = cursor.fetchall()

        return columns, rows