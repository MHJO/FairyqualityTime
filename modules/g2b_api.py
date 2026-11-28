import os
import sys
import json
import time as ttime
import sqlite3
from contextlib import closing
import configparser
import requests
import pandas as pd
import xml.etree.ElementTree as ET
import schedule

from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon

from modules import logger


# =========================================================
# 경로 및 설정
# =========================================================
def get_app_path():
    """config.ini, Database 등 외부 파일의 기준 경로"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path):
    """개발 환경과 PyInstaller 환경의 번들 리소스 경로"""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


APP_PATH = get_app_path()
CONFIG_PATH = os.path.join(APP_PATH, "config.ini")
DB_PATH = os.path.join(APP_PATH, "Database", "나라장터.db")

properies = configparser.ConfigParser(interpolation=None)
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"config.ini 파일을 찾을 수 없습니다.\n{CONFIG_PATH}")

properies.read(CONFIG_PATH, encoding="utf-8")

for section in ("datagov", "telegram", "kakaoTalk"):
    if section not in properies:
        if section == "datagov":
            raise KeyError(f"config.ini에 [{section}] 섹션이 없습니다.")
        properies[section] = {}

datagov = properies["datagov"]
telegram_config = properies["telegram"]
kakaoTalk_config = properies["kakaoTalk"]

BASIC_URL = datagov.get("basicUrl", "https://apis.data.go.kr/1230000/")
SERVICE_KEY = datagov.get("apikey", "")
indstrytyCd = datagov.get("indstrytyCd", "")
filename = f"나라장터_{ttime.strftime('%Y%m%d')}.xlsx"
inputDate = datetime.now()


def save_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as configfile:
        properies.write(configfile)


# =========================================================
# 공통 유틸
# =========================================================
class Util:
    @staticmethod
    def SetqueryUrl(params=None):
        if params is None:
            params = {}
        return "".join(
            f"{key}={value}&"
            for key, value in params.items()
            if value is not None and value != ""
        )

    @staticmethod
    def compare_with_time(compare_time):
        try:
            target = datetime.strptime(compare_time, "%Y-%m-%d %H:%M:%S")
            return "게시중" if datetime.now() < target else "마감"
        except (TypeError, ValueError):
            return "확인필요"


# =========================================================
# SQLite
# =========================================================
class Sqlite:
    @staticmethod
    def initialize_search_history():
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with closing(sqlite3.connect(DB_PATH)) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS G2BSearchHistory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_type TEXT NOT NULL,
                    search_keywords TEXT NOT NULL,
                    search_start TEXT,
                    search_end TEXT,
                    save_path TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    result_count INTEGER NOT NULL,
                    searched_at TEXT NOT NULL
                )
            """)
            connection.commit()

    @staticmethod
    def record_search_history(
        search_type, keywords, search_start, search_end,
        save_path, file_path, result_count
    ):
        with closing(sqlite3.connect(DB_PATH)) as connection:
            connection.execute("""
                INSERT INTO G2BSearchHistory (
                    search_type, search_keywords, search_start, search_end,
                    save_path, file_path, result_count, searched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                search_type,
                json.dumps(keywords, ensure_ascii=False),
                search_start,
                search_end,
                os.path.abspath(save_path),
                os.path.abspath(file_path),
                result_count,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            connection.commit()

    @staticmethod
    def count_records(type, status_type=""):
        table_names = {
            "1": "BidPblancListInfoServcPPSSrch",
            "2": "HrcspSsstndrdInfoService",
            "3": "OrderPlanSttusListServcPPSSrch",
        }
        if type not in table_names:
            raise ValueError(f"알 수 없는 조회 유형: {type}")
        with closing(sqlite3.connect(DB_PATH)) as connection:
            sql = f"SELECT COUNT(*) FROM {table_names[type]}"
            if type == "2" and status_type == "Y":
                sql += " WHERE Status != '마감'"
            cursor = connection.execute(sql)
            return cursor.fetchone()[0]

    @staticmethod
    def clearDB():
        """기존 프로그램과 동일하게 실행 시작 시 세 조회 테이블을 초기화"""
        if not os.path.exists(DB_PATH):
            return

        result_tables = (
            "BidPblancListInfoServcPPSSrch",
            "HrcspSsstndrdInfoService",
            "OrderPlanSttusListServcPPSSrch",
        )
        with closing(sqlite3.connect(DB_PATH)) as connection:
            cursor = connection.cursor()
            existing_tables = {
                row[0] for row in cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            for table_name in result_tables:
                if table_name in existing_tables:
                    cursor.execute(f"DELETE FROM {table_name}")
            connection.commit()

    @staticmethod
    def Upsert(params, type):
        if not params:
            return

        table_columns = {
            "1": (
                "BidPblancListInfoServcPPSSrch",
                ("srvceDivNm", "bidNtceNo", "bidNtceOrd", "ntceKindNm",
                 "bidNtceNm", "ntceInsttNm", "dminsttNm", "opengDt",
                 "bidNtceDt", "bidClseDt", "asignBdgtAmt"),
                (1, 2, 8),
            ),
            "2": (
                "HrcspSsstndrdInfoService",
                ("bsnsDivNm", "prdctClsfcNoNm", "rlDminsttNm", "orderInsttNm",
                 "ofclNm", "rcptDt", "Status", "asignBdgtAmt"),
                (0, 1, 2, 3, 5),
            ),
            "3": (
                "OrderPlanSttusListServcPPSSrch",
                ("bizNm", "orderInsttNm", "nticeDt", "sumOrderAmt"),
                (0, 1, 2),
            ),
        }

        table, columns, key_indexes = table_columns[type]
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        key_where = " AND ".join(f"{columns[i]} = ?" for i in key_indexes)

        sql = (
            f"INSERT INTO {table} ({column_sql}) "
            f"SELECT {placeholders} "
            f"WHERE NOT EXISTS (SELECT 1 FROM {table} WHERE {key_where})"
        )

        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()
            for row in params:
                values = tuple(row)
                keys = tuple(row[i] for i in key_indexes)
                cursor.execute(sql, values + keys)
            connection.commit()

    @staticmethod
    def selectDB(savePath, type="", statusType="", alert="N"):
        try:
            queries = {
                "1": (
                    """
                    SELECT srvceDivNm as 업무구분,
                        ntceKindNm as 구분,
                        (bidNtceNo||'-'||bidNtceOrd) as 입찰공고번호,
                        bidNtceNm as 공고명,
                        ntceInsttNm as 공고기관,
                        dminsttNm as 수요기관,
                        (bidNtceDt ||'('||bidClseDt||')') as '게시일시(입찰마감일시)',
                        printf('%,d', CAST(asignBdgtAmt AS INTEGER)) || '원' AS 사업금액
                    FROM BidPblancListInfoServcPPSSrch
                    """,
                    "입찰공고용역",
                ),
                "2": (
                    """
                    SELECT bsnsDivNm as 업무구분,
                        prdctClsfcNoNm as 사업명,
                        rlDminsttNm as 수요기관,
                        orderInsttNm as 공고기관,
                        ofclNm as 담당자,
                        rcptDt as 진행일자,
                        Status as 진행상태,
                        printf('%,d', CAST(asignBdgtAmt AS INTEGER)) || '원'
                            AS '배정예산금액(원화)'
                    FROM HrcspSsstndrdInfoService
                    """,
                    "사전규격",
                ),
                "3": (
                    """
                    SELECT bizNm as 사업명,
                        orderInsttNm as 수요기관,
                        nticeDt as 게시일시,
                        printf('%,d', CAST(sumOrderAmt AS INTEGER))
                            as '합계발주금액(원화)'
                    FROM OrderPlanSttusListServcPPSSrch
                    """,
                    "발주계획",
                ),
            }

            if type not in queries:
                raise ValueError(f"알 수 없는 내보내기 유형: {type}")

            sql_command, sheet_name = queries[type]
            if type == "2" and statusType == "Y":
                sql_command += "\nWHERE Status != '마감'"

            with sqlite3.connect(DB_PATH) as connection:
                cursor = connection.cursor()
                cursor.execute(sql_command)
                rows = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]

            df = pd.DataFrame(rows, columns=col_names)
            os.makedirs(savePath, exist_ok=True)
            file_path = os.path.join(savePath, filename)

            if os.path.exists(file_path):
                with pd.ExcelWriter(
                    file_path, engine="openpyxl", mode="a",
                    if_sheet_exists="replace"
                ) as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                with pd.ExcelWriter(file_path, engine="openpyxl", mode="w") as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            logger.log(f"{sheet_name}({len(df)}건) 엑셀 저장 완료")

            if alert == "Y":
                telegram_alert(file_path, caption=f"나라장터 조회 - {sheet_name}({len(df)}건)")
                kakaoTalkTome({sheet_name: len(df)})

            return True

        except Exception as e:
            logger.log(f"엑셀 내보내기 오류({type}): {e}")
            return False


# =========================================================
# API 공통 XML 처리
# =========================================================
def _get_xml_items(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    body = root.find(".//body")
    if body is None:
        raise ValueError(f"API 응답에 body가 없습니다: {response.text[:500]}")
    total_count = int(body.findtext("totalCount", "0") or 0)
    items_node = body.find("items")
    items = items_node.findall("item") if items_node is not None else []
    return total_count, items


# =========================================================
# 나라장터 사전규격 및 발주계획 API
# =========================================================
class HrcspSsstndrdInfoService:
    @staticmethod
    def getPublicPrcureThngInfoServcPPSSrch(
        inqryDiv="1", inqryBgnDt="", inqryEndDt="",
        bidNtceNm="", swBizObjYn="Y", statusType=""
    ):
        api_name = "getPublicPrcureThngInfoServcPPSSrch"
        params = {
            "inqryDiv": inqryDiv,
            "inqryBgnDt": inqryBgnDt,
            "inqryEndDt": inqryEndDt,
            "prdctClsfcNoNm": bidNtceNm,
            "swBizObjYn": swBizObjYn,
        }
        query = Util.SetqueryUrl(params)
        page_no = 1
        num_rows = 100

        while True:
            url = (
                f"{BASIC_URL}ao/HrcspSsstndrdInfoService/{api_name}"
                f"?pageNo={page_no}&numOfRows={num_rows}"
                f"&ServiceKey={SERVICE_KEY}&{query}type=xml"
            )
            try:
                total_count, items = _get_xml_items(url)
                rows = []
                for item in items:
                    close_dt = item.findtext("opninRgstClseDt", "N/A")
                    rows.append([
                        item.findtext("bsnsDivNm", "N/A"),
                        item.findtext("prdctClsfcNoNm", "N/A"),
                        item.findtext("rlDminsttNm", "N/A"),
                        item.findtext("orderInsttNm", "N/A"),
                        item.findtext("ofclNm", "N/A"),
                        item.findtext("rcptDt", "N/A"),
                        Util.compare_with_time(close_dt),
                        item.findtext("asignBdgtAmt", "N/A"),
                    ])

                Sqlite.Upsert(rows, type="2")
                logger.log(
                    f"사전규격 조회: {bidNtceNm}, {page_no}페이지, "
                    f"{len(rows)}건 / 전체 {total_count}건"
                )

                if page_no * num_rows >= total_count:
                    break
                page_no += 1

            except Exception as e:
                logger.log(f"사전규격 API 오류({bidNtceNm}): {e}")
                break

    @staticmethod
    def getOrderPlanSttusListServcPPSSrch(
        orderBgnYm="", orderEndYm="", inqryBgnDt="",
        inqryEndDt="", bidNtceNm=""
    ):
        """나라장터 발주계획 조회"""
        api_name = "getOrderPlanSttusListServcPPSSrch"
        params = {
            "serviceKey": SERVICE_KEY,
            "numOfRows": 100,
            "type": "xml",
            "orderBgnYm": orderBgnYm,
            "orderEndYm": orderEndYm,
            "inqryBgnDt": inqryBgnDt,
            "inqryEndDt": inqryEndDt,
            "bizNm": bidNtceNm,
        }
        query = Util.SetqueryUrl(params)
        page_no = 1
        num_rows = 100

        while True:
            url = (
                f"{BASIC_URL}ao/OrderPlanSttusService/{api_name}"
                f"?{query}pageNo={page_no}"
            )
            try:
                total_count, items = _get_xml_items(url)
                rows = []
                for item in items:
                    rows.append([
                        item.findtext("bizNm", "N/A"),
                        item.findtext("orderInsttNm", "N/A"),
                        item.findtext("nticeDt", "N/A"),
                        item.findtext("sumOrderAmt", "N/A"),
                    ])

                Sqlite.Upsert(rows, type="3")
                logger.log(
                    f"발주계획 조회: {bidNtceNm}, {page_no}페이지, "
                    f"{len(rows)}건 / 전체 {total_count}건"
                )

                if page_no * num_rows >= total_count:
                    break
                page_no += 1

            except Exception as e:
                logger.log(f"발주계획 API 오류({bidNtceNm}): {e}")
                break


# =========================================================
# 나라장터 입찰공고 API - 6일 단위 조회
# =========================================================
class BidPublicInfoService:
    classNm = "BidPublicInfoService02"

    @staticmethod
    def getBidPblancListInfoServcPPSSrch(
        inqryBgnDt="", inqryEndDt="", bidNtceNm="", status_callback=None
    ):
        api_name = "getBidPblancListInfoServcPPSSrch02"

        start_date = datetime.strptime(inqryBgnDt, "%Y%m%d%H%M")
        end_date = datetime.strptime(inqryEndDt, "%Y%m%d%H%M")
        current_start = start_date

        # API 조회 제한에 맞춰 6일씩 나누어 조회
        while current_start <= end_date:
            max_end = (current_start + timedelta(days=6)).replace(
                hour=23, minute=59, second=0, microsecond=0
            )
            current_end = min(max_end, end_date)

            search_start = current_start.strftime("%Y%m%d%H%M")
            search_end = current_end.strftime("%Y%m%d%H%M")
            message = (
                f"입찰공고 조회중 - {bidNtceNm} "
                f"({search_start} ~ {search_end})"
            )

            logger.log(message)
            if status_callback:
                status_callback(message)

            params = {
                "inqryDiv": "2",
                "inqryBgnDt": search_start,
                "inqryEndDt": search_end,
                "bidNtceNm": bidNtceNm,
                "indstrytyCd": indstrytyCd,
            }
            query = Util.SetqueryUrl(params)
            page_no = 1
            num_rows = 100

            while True:
                url = (
                    f"{BASIC_URL}ad/{BidPublicInfoService.classNm}/{api_name}"
                    f"?pageNo={page_no}&numOfRows={num_rows}"
                    f"&ServiceKey={SERVICE_KEY}&{query}type=xml"
                )
                try:
                    total_count, items = _get_xml_items(url)
                    rows = []

                    for item in items:
                        try:
                            estimated_price = int(item.findtext("presmptPrce", "0") or 0)
                            vat = int(item.findtext("VAT", "0") or 0)
                            budget = estimated_price + vat
                        except (TypeError, ValueError):
                            budget = 0

                        rows.append([
                            item.findtext("srvceDivNm", "N/A"),
                            item.findtext("bidNtceNo", "N/A"),
                            item.findtext("bidNtceOrd", "N/A"),
                            item.findtext("ntceKindNm", "N/A"),
                            item.findtext("bidNtceNm", "N/A"),
                            item.findtext("ntceInsttNm", "N/A"),
                            item.findtext("dminsttNm", "N/A"),
                            item.findtext("opengDt", "-"),
                            item.findtext("bidNtceDt", "-"),
                            item.findtext("bidClseDt", "-"),
                            budget,
                        ])

                    Sqlite.Upsert(rows, type="1")
                    logger.log(
                        f"입찰공고 {search_start}~{search_end}, "
                        f"{page_no}페이지: {len(rows)}건 / 전체 {total_count}건"
                    )

                    if page_no * num_rows >= total_count:
                        break
                    page_no += 1

                except Exception as e:
                    logger.log(
                        f"입찰공고 API 오류({search_start}~{search_end}): {e}"
                    )
                    break

            current_start = (current_end + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )


# =========================================================
# 알림
# =========================================================
def telegram_alert(file_path, caption=""):
    try:
        token = telegram_config.get("token", "").strip()
        chat_id = telegram_config.get("chatId", "").strip()
        if not token or not chat_id:
            logger.log("Telegram 설정이 없어 알림을 건너뜁니다.")
            return

        url = f"https://api.telegram.org/bot{token}/sendDocument"
        with open(file_path, "rb") as file:
            response = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"document": file},
                timeout=30,
            )
        response.raise_for_status()
    except Exception as e:
        logger.log(f"Telegram 알림 오류: {e}")


def kakaoTalkTome(text_content):
    try:
        access_token = kakaoTalk_config.get("token", "").strip()
        if not access_token:
            logger.log("KakaoTalk 설정이 없어 알림을 건너뜁니다.")
            return

        message_template = {
            "object_type": "text",
            "text": str(text_content),
            "link": {"web_url": "https://www.g2b.go.kr"},
        }
        response = requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"template_object": json.dumps(message_template)},
            timeout=30,
        )
        response.raise_for_status()
    except Exception as e:
        logger.log(f"KakaoTalk 알림 오류: {e}")


# =========================================================
# 메인 UI
# =========================================================
class g2b_api(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # ui_file = resource_path(
        #     f"ui/{os.path.splitext(os.path.basename(__file__))[0]}.ui"
        # )
        ui_file = resource_path(f"ui/g2b_api.ui")
        uic.loadUi(ui_file, self)
        self.load_style()

        self.new_window = None
        self.timer = None

        self.init()
        self.initUi()
        self.listener()

    def load_style(self):
        try:
            print (os.path.join(APP_PATH, "css", "g2b_api.css"))
            with open(os.path.join(APP_PATH, "css", "g2b_api.css"), "r", encoding="utf-8") as f:
                print("11")
                self.setStyleSheet(f.read())
        except Exception as e:
            print("스타일 로딩 오류:", e)

    def init(self):
        Sqlite.initialize_search_history()
        Sqlite.clearDB()

    def initUi(self):
        self.setWindowTitle("5분 단축 - 당신의 퇴근요정!")
        icon_path = resource_path("image/fairy.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.date_1.setDate(inputDate + relativedelta(weeks=3))
        self.date_2.setDate(inputDate + relativedelta(months=2))
        self.date_3.setDate(inputDate + relativedelta(days=-7))
        self.date_4.setDate(inputDate)

        self.dt_month1.setDate(inputDate + relativedelta(months=-2))
        self.dt_month2.setDate(
            inputDate + relativedelta(years=1) + relativedelta(months=-2)
        )
        self.date_5.setDate(inputDate + relativedelta(months=-1))
        self.date_6.setDate(inputDate)

        self.rdo_1m.setChecked(True)
        self.rdo_StatusY.setChecked(True)
        self.sb_cycle.setValue(2)

        self.txt_savePath.setText(datagov.get("savePath", ""))
        self.txt_code.setText(indstrytyCd)
        self.txt_keyword.setText(datagov.get("keywords", ""))

        # UI 파일의 체크 상태에 의존하되, 체크박스가 checkable인지 확인
        self.change_ui()

    def listener(self):
        self.btnOk.clicked.connect(self.run)
        self.gb_auto.toggled.connect(self.change_ui)
        self.btn_auto.clicked.connect(self.run_schedule)
        self.btn_cancel.clicked.connect(self.cancel_schedule)
        self.rdo_1m.toggled.connect(self.change_date5)
        self.rdo_3m.toggled.connect(self.change_date5)
        self.rdo_6m.toggled.connect(self.change_date5)
        self.rdo_12m.toggled.connect(self.change_date5)
        self.btn_alert.clicked.connect(self.alert_setting)

    def update_status(self, msg):
        if hasattr(self, "lb_status"):
            self.lb_status.setText(f"상태: {msg}")
        logger.log(msg)
        QApplication.processEvents()

    def record_saved_search(
        self, search_type, type_code, keywords, start, end, save_path,
        status_type=""
    ):
        Sqlite.record_search_history(
            search_type,
            keywords,
            start,
            end,
            save_path,
            os.path.join(save_path, filename),
            Sqlite.count_records(type_code, status_type),
        )

    def change_ui(self):
        self.btnOk.setEnabled(not self.gb_auto.isChecked())

    def change_date5(self):
        if self.rdo_1m.isChecked():
            self.date_5.setDate(inputDate + relativedelta(months=-1))
        elif self.rdo_3m.isChecked():
            self.date_5.setDate(inputDate + relativedelta(months=-3))
        elif self.rdo_6m.isChecked():
            self.date_5.setDate(inputDate + relativedelta(months=-6))
        elif self.rdo_12m.isChecked():
            self.date_5.setDate(inputDate + relativedelta(months=-12))

    def alert_setting(self):
        self.new_window = QDialog(self)
        uic.loadUi(resource_path("ui/input_token.ui"), self.new_window)

        self.new_window.txt_telgramToken.setText(
            telegram_config.get("token", "")
        )
        self.new_window.txt_chatId.setText(
            telegram_config.get("chatId", "")
        )
        self.new_window.txt_kakaoTalkToken.setText(
            kakaoTalk_config.get("token", "")
        )
        self.new_window.btn_Input.clicked.connect(
            lambda: [self.reSettingConfig(), self.new_window.close()]
        )
        self.new_window.show()

    def reSettingConfig(self):
        properies["datagov"]["savePath"] = self.txt_savePath.text()
        properies["datagov"]["indstrytyCd"] = self.txt_code.text().strip()
        properies["datagov"]["keywords"] = self.txt_keyword.text()

        if self.new_window is not None:
            properies["telegram"]["token"] = (
                self.new_window.txt_telgramToken.text().strip()
            )
            properies["telegram"]["chatId"] = (
                self.new_window.txt_chatId.text().strip()
            )
            properies["kakaoTalk"]["token"] = (
                self.new_window.txt_kakaoTalkToken.text().strip()
            )

        try:
            save_config()
            global indstrytyCd
            indstrytyCd = properies["datagov"].get("indstrytyCd", "")
            QMessageBox.information(self, "알림", "설정이 정상적으로 저장되었습니다.")
        except Exception as e:
            logger.log(f"설정 저장 오류: {e}")
            QMessageBox.warning(self, "오류", f"설정 저장에 실패했습니다.\n{e}")

    def defaultCheck(self, savePath):
        if not savePath:
            logger.log("저장경로를 입력해주세요.")
            QMessageBox.information(self, "알림", "저장경로를 입력해주세요.")
            return False

        if not os.path.isdir(savePath):
            logger.log("저장경로가 존재하지 않습니다.")
            QMessageBox.warning(
                self, "알림", "경로가 존재하지 않습니다.\n경로를 확인해주세요."
            )
            return False

        old_file = os.path.join(savePath, filename)
        if os.path.exists(old_file):
            os.remove(old_file)
        return True

    # -----------------------------------------------------
    # 예약 실행
    # -----------------------------------------------------
    def run_schedule(self):
        schedule.clear()
        interval = self.sb_cycle.value()
        schedule.every(interval).hours.do(self.limited_run)

        if self.timer is None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(schedule.run_pending)
        self.timer.start(1000)

        logger.log(f"스케줄 시작됨: {interval}시간 간격")

    def limited_run(self):
        now = datetime.now().time()
        start_time = time(
            self.startTime.time().hour(), self.startTime.time().minute()
        )
        end_time = time(
            self.endTime.time().hour(), self.endTime.time().minute()
        )

        if start_time <= now < end_time:
            self.run()
            logger.log(
                f"예약 실행 허용 시간: {self.startTime.text()} ~ "
                f"{self.endTime.text()}"
            )
        else:
            self.chk_alert.setChecked(False)
            self.cancel_schedule()
            logger.log("허용된 실행 시간이 지나 스케줄을 종료합니다.")

    def cancel_schedule(self):
        if self.timer is not None:
            self.timer.stop()
        schedule.clear()
        logger.log("스케줄 중지됨")

    # -----------------------------------------------------
    # 실행
    # -----------------------------------------------------
    def run(self):
        global indstrytyCd, filename

        self.reSettingConfig()
        indstrytyCd = self.txt_code.text().strip()
        filename = f"나라장터_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"

        savePath = self.txt_savePath.text().strip()
        if not self.defaultCheck(savePath):
            return

        selected = [
            self.gb_1.isChecked(),
            self.gb_2.isChecked(),
            self.gb_3.isChecked(),
        ]
        if not any(selected):
            QMessageBox.information(
                self, "알림", "실행할 조회 항목을 하나 이상 선택해주세요."
            )
            return

        keywords = [
            keyword.strip()
            for keyword in self.txt_keyword.text().split(",")
            if keyword.strip()
        ]
        if not keywords:
            QMessageBox.information(self, "알림", "검색 키워드를 입력해주세요.")
            return

        alert_type = "Y" if self.chk_alert.isChecked() else "N"
        QApplication.processEvents()

        # 입찰공고
        if self.gb_1.isChecked():
            try:
                self.update_status("입찰공고용역 조회 시작")
                start = datetime.strptime(self.date_1.text(), "%Y-%m-%d")
                end = datetime.strptime(self.date_2.text(), "%Y-%m-%d")

                for keyword in keywords:
                    BidPublicInfoService.getBidPblancListInfoServcPPSSrch(
                        start.strftime("%Y%m%d") + "0000",
                        end.strftime("%Y%m%d") + "2359",
                        bidNtceNm=keyword,
                        status_callback=self.update_status,
                    )

                if not Sqlite.selectDB(savePath, type="1", alert=alert_type):
                    raise RuntimeError("입찰공고 엑셀 저장에 실패했습니다.")
                self.record_saved_search(
                    "입찰공고", "1", keywords,
                    start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
                    savePath,
                )
                self.update_status("입찰공고용역 조회 및 내보내기 완료")

            except Exception as e:
                logger.log(f"입찰공고 처리 오류: {e}")
                QMessageBox.warning(self, "오류", f"입찰공고 처리 중 오류가 발생했습니다.\n{e}")
                return

        # 사전규격
        if self.gb_2.isChecked():
            try:
                self.update_status("사전규격 조회 시작")
                start = datetime.strptime(self.date_3.text(), "%Y-%m-%d")
                end = datetime.strptime(self.date_4.text(), "%Y-%m-%d")
                start_text = start.strftime("%Y%m%d") + "0000"
                end_text = end.strftime("%Y%m%d") + "2359"

                status_type = "A" if self.rdo_StatusAll.isChecked() else "Y"

                for keyword in keywords:
                    HrcspSsstndrdInfoService.getPublicPrcureThngInfoServcPPSSrch(
                        inqryDiv="1",
                        inqryBgnDt=start_text,
                        inqryEndDt=end_text,
                        bidNtceNm=keyword,
                        swBizObjYn="Y",
                        statusType=status_type,
                    )

                if not Sqlite.selectDB(
                    savePath, type="2", statusType=status_type, alert=alert_type
                ):
                    raise RuntimeError("사전규격 엑셀 저장에 실패했습니다.")
                self.record_saved_search(
                    "사전규격", "2", keywords,
                    start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
                    savePath, status_type,
                )
                self.update_status("사전규격 조회 및 내보내기 완료")

            except Exception as e:
                logger.log(f"사전규격 처리 오류: {e}")
                QMessageBox.warning(self, "오류", f"사전규격 처리 중 오류가 발생했습니다.\n{e}")
                return

        # 발주계획
        if self.gb_3.isChecked():
            try:
                self.update_status("발주계획 조회 시작")

                order_start = datetime.strptime(
                    self.dt_month1.text(), "%Y-%m"
                ).strftime("%Y%m")
                order_end = datetime.strptime(
                    self.dt_month2.text(), "%Y-%m"
                ).strftime("%Y%m")
                inquiry_start = (
                    datetime.strptime(self.date_5.text(), "%Y-%m-%d")
                    .strftime("%Y%m%d") + "0000"
                )
                inquiry_end = (
                    datetime.strptime(self.date_6.text(), "%Y-%m-%d")
                    .strftime("%Y%m%d") + "2359"
                )

                for keyword in keywords:
                    HrcspSsstndrdInfoService.getOrderPlanSttusListServcPPSSrch(
                        order_start,
                        order_end,
                        inquiry_start,
                        inquiry_end,
                        keyword,
                    )

                if not Sqlite.selectDB(savePath, type="3", alert=alert_type):
                    raise RuntimeError("발주계획 엑셀 저장에 실패했습니다.")
                self.record_saved_search(
                    "발주계획", "3", keywords,
                    self.date_5.text(), self.date_6.text(), savePath,
                )
                self.update_status("발주계획 조회 및 내보내기 완료")

            except Exception as e:
                logger.log(f"발주계획 처리 오류: {e}")
                QMessageBox.warning(self, "오류", f"발주계획 처리 중 오류가 발생했습니다.\n{e}")
                return

        self.update_status("선택한 조회 작업이 모두 완료되었습니다.")
        QMessageBox.information(self, "알림", "조회가 완료되었습니다.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    logger.init(APP_PATH, "FairyQualityTime")
    window = g2b_api()
    window.show()
    sys.exit(app.exec_())