import os, sys
from datetime import datetime
import configparser
import sqlite3

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QDialog, QTableWidgetItem, QAbstractItemView
from PyQt5.QtCore import QTimer, QDate
from PyQt5.QtGui import QIcon

from modules.g2b_api import g2b_api
from modules.work_manager import workManager
from modules.Manage_vaction import Manage_vaction
from modules.custom_calendar import CustomCalendarWidget  # 👈 커스텀 캘린더 임포트

properies = configparser.ConfigParser(interpolation=None)
configPath = rf"{os.getcwd()}\config.ini"
if os.path.exists(configPath):
    properies.read(configPath, encoding='utf-8')

class main(QMainWindow):
    def __init__(self):
        super().__init__()
        # 통합 대시보드형 main.ui 로드
        uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '.ui'), self)

        # 1. UI 파일의 기본 QCalendarWidget을 밀도형 CustomCalendarWidget으로 교체
        self.replace_calendar_widget()

        self.init_ui()
        self.listener()
        self.load_dashboard_data() # 프로그램 시작 시 전체 데이터 로드

    def replace_calendar_widget(self):
        """기존 캘린더 위젯을 커스텀 밀도형 캘린더로 동적 교체"""
        old_calendar = self.calendarWidget
        layout = old_calendar.parent().layout()
        index = layout.indexOf(old_calendar)
        
        # 기존 위젯 제거
        layout.removeWidget(old_calendar)
        old_calendar.deleteLater()
        
        # 커스텀 캘린더 생성 및 장착
        self.calendarWidget = CustomCalendarWidget(self)
        self.calendarWidget.setMinimumSize(0, 260)
        self.calendarWidget.setGridVisible(True)
        layout.insertWidget(index, self.calendarWidget)

    def init_ui(self):
        self.setWindowTitle("퇴근요정 - 개인 업무 지원 및 일정 관리 시스템")
        self.setWindowIcon(QIcon('fairy.ico'))

        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.timeout)

        # 테이블 속성 설정 (수정 불가, 행 단위 선택)
        self.table_main_schedule.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_main_schedule.setSelectionBehavior(QAbstractItemView.SelectRows)

    def listener(self):
        self.btn_home.clicked.connect(self.home_clear)
        self.action2.triggered.connect(self.work_Manager) # 업무관리
        self.action3.triggered.connect(self.load_vacation)
        
        # 버튼 연결 (대시보드 UI 기준)
        self.btn_1.clicked.connect(self.load_g2b)         # 나라장터 조회 팝업
        self.btn_4.clicked.connect(self.work_Manager)     # 업무관리 팝업
        self.btn_3.clicked.connect(self.load_vacation)    # 엑셀뷰어 등
        
        # 캘린더 날짜 클릭 시그널 연동 (날짜별 일정 확인용)
        self.calendarWidget.clicked.connect(self.on_date_selected)

    def timeout(self):
        current_time = datetime.now()
        text_time = current_time.strftime("%H:%M:%S")
        time_msg = "현재시간 : " + text_time
        self.statusbar.showMessage(time_msg)

    def home_clear(self):
        # 홈 버튼 클릭 시 전체 대시보드 및 캘린더 새로고침
        self.load_dashboard_data()
        self.calendarWidget.load_all_schedules()
        self.calendarWidget.update()

    # region [DB 연결 및 대시보드 데이터 연동]
    def get_db_connection(self):
        db_dir = "Database"
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        return sqlite3.connect(os.path.join(db_dir, "work_database.db"))

    def load_dashboard_data(self):
        """Database/work_database.db에서 전체 업무 데이터를 읽어와 우측 테이블에 표시"""
        self.table_main_schedule.setRowCount(0)
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT status, title, start_date, end_date FROM works ORDER BY id DESC")
            rows = cursor.fetchall()
            conn.close()

            for row_idx, row_data in enumerate(rows):
                self.table_main_schedule.insertRow(row_idx)
                for col_idx, val in enumerate(row_data):
                    item = QTableWidgetItem(str(val) if val else "")
                    self.table_main_schedule.setItem(row_idx, col_idx, item)
        except Exception as e:
            pass

    def on_date_selected(self, qdate):
        """캘린더에서 특정 날짜를 클릭했을 때, 해당 날짜 기간에 포함된 업무만 필터링"""
        selected_date_str = qdate.toString("yyyy-MM-dd")
        self.table_main_schedule.setRowCount(0)
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            # 시작일과 마감일 사이에 선택한 날짜가 포함된 업무 조회
            cursor.execute("""
                SELECT status, title, start_date, end_date 
                FROM works 
                WHERE ? BETWEEN start_date AND end_date
                ORDER BY id DESC
            """, (selected_date_str,))
            rows = cursor.fetchall()
            conn.close()

            for row_idx, row_data in enumerate(rows):
                self.table_main_schedule.insertRow(row_idx)
                for col_idx, val in enumerate(row_data):
                    item = QTableWidgetItem(str(val) if val else "")
                    self.table_main_schedule.setItem(row_idx, col_idx, item)
        except Exception as e:
            pass
    # endregion

    # region [g2b 불러오기]
    def load_g2b(self):
        g2b_dialog = g2b_api(self)
        g2b_dialog.exec_()
    # endregion

    # region [업무관리]
    def work_Manager(self):
        # 업무관리 팝업 창 호출
        dialog = workManager(self)
        dialog.exec_()  
        
        # 업무관리 창을 닫으면 메인 화면의 캘린더와 테이블 데이터가 실시간으로 갱신됨
        self.load_dashboard_data()
        self.calendarWidget.load_all_schedules()
        self.calendarWidget.update()
    # endregion

    # region [휴가장부 / 엑셀뷰어]
    def load_vacation(self):
        QMessageBox.information(self, "알림", "준비중인 기능입니다.")
    # endregion

    def closeEvent(self, QCloseEvent):
        re = QMessageBox.question(self, "종료 확인", "종료 하시겠습니까?",
                    QMessageBox.Yes|QMessageBox.No)

        if re == QMessageBox.Yes:
            QCloseEvent.accept()
        else:
            QCloseEvent.ignore()  

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = main()
    window.show()
    sys.exit(app.exec_())