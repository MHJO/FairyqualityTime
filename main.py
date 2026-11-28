import os, sys
from datetime import datetime
import configparser
import sqlite3

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QDialog, QTableWidgetItem, QAbstractItemView, QHeaderView
from PyQt5.QtCore import QTimer, QDate, Qt
from PyQt5.QtGui import QIcon, QColor

from modules.g2b.settings import G2BSettings
from modules.g2b_api import g2b_api
from modules.work_manager import workManager, ensure_work_database_schema
from modules.weekly_schedule import WeeklyScheduleWidget
from modules.excel_viewer import ExcelViewerDialog
from modules.Manage_vaction import Manage_vaction
from modules.custom_calendar import CustomCalendarWidget  # 👈 커스텀 캘린더 임포트

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")
WEEK_NAV_UI_PATH = os.path.join(BASE_DIR, "ui", "week_navigation.ui")
g2b_settings = G2BSettings(CONFIG_PATH)

# properies = configparser.ConfigParser(interpolation=None)
# configPath = rf"{os.getcwd()}\config.ini"
# if os.path.exists(CONFIG_PATH):
#     properies.read(CONFIG_PATH, encoding='utf-8')

class main(QMainWindow):
    def __init__(self):
        super().__init__()
        # 통합 대시보드형 main.ui 로드
        # uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '.ui'), self)
        uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '_new.ui'), self)
        self.load_style()

        ensure_work_database_schema()
        # 1. UI 파일의 기본 QCalendarWidget을 밀도형 CustomCalendarWidget으로 교체
        self.replace_calendar_widget()
        self.replace_week_schedule()

        self.init_ui()
        self.listener()
        self.load_dashboard_data() # 프로그램 시작 시 전체 데이터 로드

    def load_style(self):
        try:
            css_path = os.path.join(
            os.getcwd(),
            "css",
            os.path.splitext(os.path.basename(__file__))[0] + ".css"
            )

            print("CSS 경로:", css_path)

            with open(css_path, "r", encoding="utf-8") as f:
                style = f.read()

            self.setStyleSheet(style)
            print("CSS 적용 완료")
        except Exception as e:
            print("스타일 로딩 오류:", e)

    def replace_calendar_widget(self):
        """기존 캘린더 위젯을 커스텀 밀도형 캘린더로 동적 교체"""
        old_calendar = self.calendarWidget
        layout = old_calendar.parent().layout()
        index = layout.indexOf(old_calendar)
        first_day_of_week = old_calendar.firstDayOfWeek()
        horizontal_header = old_calendar.horizontalHeaderFormat()
        vertical_header = old_calendar.verticalHeaderFormat()
        selected_date = old_calendar.selectedDate()
        shown_year = old_calendar.yearShown()
        shown_month = old_calendar.monthShown()
        grid_visible = old_calendar.isGridVisible()
        object_name = old_calendar.objectName()
        
        # 기존 위젯 제거
        layout.removeWidget(old_calendar)
        old_calendar.deleteLater()
        
        # 커스텀 캘린더 생성 및 장착
        self.calendarWidget = CustomCalendarWidget(self)
        self.calendarWidget.setObjectName(object_name)
        self.calendarWidget.setFirstDayOfWeek(first_day_of_week)
        self.calendarWidget.setHorizontalHeaderFormat(horizontal_header)
        self.calendarWidget.setVerticalHeaderFormat(vertical_header)
        self.calendarWidget.setCurrentPage(shown_year, shown_month)
        self.calendarWidget.setSelectedDate(selected_date)
        self.calendarWidget.setMinimumSize(0, 260)
        self.calendarWidget.setGridVisible(grid_visible)
        layout.insertWidget(index, self.calendarWidget)

    def replace_week_schedule(self):
        layout = self.weekPage.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.weekNavigationWidget = uic.loadUi(WEEK_NAV_UI_PATH)
        self.weekScheduleWidget = WeeklyScheduleWidget(self.weekPage)
        layout.addWidget(self.weekNavigationWidget, 0, 0, 1, 8)
        layout.addWidget(self.weekScheduleWidget, 1, 0, 1, 8)
        layout.setRowStretch(1, 1)
        self.update_week_range_label()

    def init_ui(self):
        self.setWindowTitle("퇴근요정 - 개인 업무 지원 및 일정 관리 시스템")
        self.setWindowIcon(QIcon('fairy.ico'))

        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.timeout)
        self.timeout()

        # 테이블 속성 설정 (수정 불가, 행 단위 선택)
        self.table_main_schedule.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_main_schedule.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_main_schedule.verticalHeader().setVisible(False)
        header = self.table_main_schedule.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

    def listener(self):
        self.btn_home.clicked.connect(self.home_clear)
        self.action2.triggered.connect(self.work_Manager) # 업무관리
        self.action3.triggered.connect(self.load_excel_viewer)
        
        # 버튼 연결 (대시보드 UI 기준)
        self.btn_1.clicked.connect(self.load_g2b)         # 나라장터 조회 팝업
        self.btn_4.clicked.connect(self.work_Manager)     # 업무관리 팝업
        self.btn_3.clicked.connect(self.load_excel_viewer)
        self.btn_toolbar_g2b.clicked.connect(self.load_g2b)
        self.btn_toolbar_work.clicked.connect(self.work_Manager)
        self.btn_toolbar_excel.clicked.connect(self.load_excel_viewer)
        self.weekNavigationWidget.btnWeekPrevious.clicked.connect(
            lambda: self.navigate_week(-1)
        )
        self.weekNavigationWidget.btnWeekNext.clicked.connect(
            lambda: self.navigate_week(1)
        )
        self.weekNavigationWidget.btnWeekToday.clicked.connect(self.navigate_to_today)
        
        # 캘린더 날짜 클릭 시그널 연동 (날짜별 일정 확인용)
        self.calendarWidget.clicked.connect(self.on_date_selected)
        self.calendarWidget.activated.connect(self.on_date_activated)
        self.table_main_schedule.cellDoubleClicked.connect(
            self.on_schedule_double_clicked
        )

    def timeout(self):
        current_time = datetime.now()
        weekdays = ("월", "화", "수", "목", "금", "토", "일")
        self.lbl_date.setText(
            f"{current_time.year}년 {current_time.month}월 "
            f"{current_time.day}일 ({weekdays[current_time.weekday()]})"
        )
        self.lbl_clock.setText(current_time.strftime("%H:%M:%S"))
        self.statusbar.showMessage("로컬 DB 연결됨 (work_database.db)")

    def home_clear(self):
        # 홈 버튼 클릭 시 전체 대시보드 및 캘린더 새로고침
        self.load_dashboard_data()
        self.calendarWidget.load_all_schedules()
        self.calendarWidget.update()
        self.weekScheduleWidget.set_selected_date(self.calendarWidget.selectedDate())
        self.weekScheduleWidget.load_schedules()
        self.update_week_range_label()

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
            cursor.execute(
                "SELECT id, status, title, start_date, end_date FROM works ORDER BY id DESC"
            )
            rows = cursor.fetchall()
            conn.close()

            self.populate_schedule_rows(rows)
        except Exception as e:
            pass

    def on_date_selected(self, qdate):
        """캘린더에서 특정 날짜를 클릭했을 때, 해당 날짜 기간에 포함된 업무만 필터링"""
        self.weekScheduleWidget.set_selected_date(qdate)
        self.update_week_range_label()
        self.load_schedules_for_date(qdate)

    def navigate_week(self, offset):
        selected_date = self.weekScheduleWidget.selected_date.addDays(7 * offset)
        self.calendarWidget.setCurrentPage(selected_date.year(), selected_date.month())
        self.calendarWidget.setSelectedDate(selected_date)
        self.on_date_selected(selected_date)

    def navigate_to_today(self):
        today = QDate.currentDate()
        self.calendarWidget.setCurrentPage(today.year(), today.month())
        self.calendarWidget.setSelectedDate(today)
        self.on_date_selected(today)

    def update_week_range_label(self):
        if not hasattr(self, "weekNavigationWidget"):
            return
        week_start = self.weekScheduleWidget.selected_date.addDays(
            1 - self.weekScheduleWidget.selected_date.dayOfWeek()
        )
        week_end = week_start.addDays(6)
        self.weekNavigationWidget.lblWeekRange.setText(
            f"{week_start.toString('yyyy.MM.dd')} ~ "
            f"{week_end.toString('yyyy.MM.dd')}"
        )

    def on_date_activated(self, qdate):
        """캘린더 날짜를 더블클릭했을 때 해당 날짜로 업무관리 창을 연다."""
        if self.load_schedules_for_date(qdate):
            self.open_work_manager(qdate)

    def populate_schedule_rows(self, rows):
        for row_idx, row_data in enumerate(rows):
            self.table_main_schedule.insertRow(row_idx)
            work_id, status = row_data[:2]
            is_completed = str(status or "").strip() == "완료"
            for col_idx, val in enumerate(row_data[1:]):
                item = QTableWidgetItem(str(val) if val else "")
                if is_completed:
                    item.setBackground(QColor("#e4f2e8"))
                    if col_idx == 0:
                        item.setForeground(QColor("#386b48"))
                if col_idx == 0:
                    item.setData(Qt.UserRole, work_id)
                self.table_main_schedule.setItem(row_idx, col_idx, item)

    def on_schedule_double_clicked(self, row, column):
        status_item = self.table_main_schedule.item(row, 0)
        if status_item is None:
            return
        work_id = status_item.data(Qt.UserRole)
        if work_id is None:
            return
        self.open_work_manager(self.calendarWidget.selectedDate(), work_id)

    def load_schedules_for_date(self, qdate):
        selected_date_str = qdate.toString("yyyy-MM-dd")
        self.table_main_schedule.setRowCount(0)

        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, status, title, start_date, end_date
                FROM works 
                WHERE ? BETWEEN start_date AND end_date
                ORDER BY id DESC
            """, (selected_date_str,))
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            QMessageBox.warning(self, "데이터베이스 오류", f"선택한 날짜의 업무를 불러오지 못했습니다.\n{e}")
            return False
        finally:
            conn.close()

        self.populate_schedule_rows(rows)
        return True
    # endregion

    # region [g2b 불러오기]
    def load_g2b(self):
        g2b_dialog = g2b_api(self)
        g2b_dialog.exec_()
    # endregion

    # region [업무관리]
    def work_Manager(self):
        self.open_work_manager()

    def open_work_manager(self, selected_date=None, selected_work_id=None):
        # 업무관리 팝업 창 호출
        dialog = workManager(self, selected_date, selected_work_id)
        dialog.exec_()  
        
        # 업무관리 창을 닫으면 메인 화면의 캘린더와 테이블 데이터가 실시간으로 갱신됨
        self.load_dashboard_data()
        self.calendarWidget.load_all_schedules()
        self.calendarWidget.update()
        self.weekScheduleWidget.load_schedules()
        if selected_date is not None:
            self.weekScheduleWidget.set_selected_date(selected_date)
        if selected_date is not None:
            self.load_schedules_for_date(selected_date)
    # endregion

    # region [엑셀뷰어]
    def load_excel_viewer(self):
        dialog = ExcelViewerDialog(self)
        dialog.exec_()
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