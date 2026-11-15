from PyQt5.QtWidgets import QCalendarWidget, QApplication
from PyQt5.QtCore import Qt, QDate, QRectF
from PyQt5.QtGui import QColor, QPen, QBrush, QFont
import sqlite3
import os, sys

class CustomCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.schedule_data = {}  # 날짜별 일정 리스트를 담을 딕셔너리
        self.load_all_schedules()

    def load_all_schedules(self):
        """데이터베이스에서 모든 업무 일정을 불러와 날짜별로 매핑"""
        self.schedule_data.clear()
        db_path = os.path.join("Database", "work_database.db")
        if not os.path.exists(db_path):
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT title, start_date, end_date, status FROM works")
            rows = cursor.fetchall()
            conn.close()

            for title, start_str, end_str, status in rows:
                if not start_str or not end_str:
                    continue
                
                start_date = QDate.fromString(start_str, "yyyy-MM-dd")
                end_date = QDate.fromString(end_str, "yyyy-MM-dd")
                
                curr_date = start_date
                while curr_date <= end_date:
                    date_str = curr_date.toString("yyyy-MM-dd")
                    if date_str not in self.schedule_data:
                        self.schedule_data[date_str] = []
                    self.schedule_data[date_str].append({"title": title, "status": status})
                    curr_date = curr_date.addDays(1)
        except Exception as e:
            print(f"캘린더 일정 로드 오류: {e}")

    def paintCell(self, painter, rect, date):
        """셀을 직접 그려서 기존 중복 숫자를 없애고, 왼쪽 상단 숫자 및 요일별 색상, 일정 개수 표시"""
        painter.save()

        # 1. 셀 배경 처리 (오늘 날짜이거나 다른 달의 날짜 등 기본적인 배경 톤 맞추기)
        is_current_month = (date.month() == self.monthShown())
        
        # 배경색 채우기
        if not is_current_month:
            painter.fillRect(rect, QColor("#f8fafc"))  # 이번 달이 아니면 연한 회색 배경
        else:
            painter.fillRect(rect, QColor("#ffffff"))  # 기본 흰색 배경

        # 오늘 날짜 테두리 강조 (선택 사항)
        if date == QDate.currentDate():
            painter.setPen(QPen(QColor("#2563eb"), 1.5))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # 2. 요일에 따른 숫자 색상 설정 (일요일: 빨간색, 토요일: 파란색, 평일: 진한 회색)
        day_of_week = date.dayOfWeek() # 1: 월요일 ~ 7: 일요일
        if not is_current_month:
            text_color = QColor("#cbd5e1")  # 이전/다음 달 흐린 색
        elif day_of_week == 7:  # 일요일
            text_color = QColor("#dc2626")  # 빨간색
        elif day_of_week == 6:  # 토요일
            text_color = QColor("#2563eb")  # 파란색
        else:
            text_color = QColor("#1e293b")  # 평일 검정/진한 회색

        # 3. 날짜 숫자를 왼쪽 상단에 직접 그리기
        painter.setPen(QPen(text_color))
        font = QFont()
        font.setPointSize(9)
        if date == QDate.currentDate():
            font.setBold(True)
        painter.setFont(font)

        # 왼쪽 상단 좌표 설정 (여백 X: 6px, Y: 6px)
        number_rect = QRectF(rect.x() + 6, rect.y() + 6, rect.width() - 12, 20)
        painter.drawText(number_rect, Qt.AlignLeft | Qt.AlignTop, str(date.day()))

        # 4. 일정이 있는 경우 하단에 개수 배지 표시 (이번 달 날짜이거나 전체 날짜 중 선택)
        date_str = date.toString("yyyy-MM-dd")
        if date_str in self.schedule_data:
            schedules = self.schedule_data[date_str]
            count = len(schedules)
            
            w = rect.width()
            h = rect.height()
            
            badge_width = 18
            badge_height = 14
            bx = rect.x() + (w - badge_width) / 2
            by = rect.y() + h - 18  # 셀 맨 아래에서 위로 18픽셀 위
            
            badge_rect = QRectF(bx, by, badge_width, badge_height)
            
            # 배지 배경 (파란색)
            painter.setBrush(QBrush(QColor("#2563eb")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(badge_rect, 7, 7)
            
            # 개수 텍스트
            painter.setPen(QPen(QColor("#ffffff")))
            badge_font = QFont()
            badge_font.setPointSize(7)
            badge_font.setBold(True)
            painter.setFont(badge_font)
            
            painter.drawText(badge_rect, Qt.AlignCenter, str(count))

        painter.restore()


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = CustomCalendarWidget()
#     window.show()
#     sys.exit(app.exec_())