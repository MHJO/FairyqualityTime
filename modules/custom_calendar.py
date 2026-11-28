from PyQt5.QtWidgets import QCalendarWidget, QApplication
from PyQt5.QtCore import Qt, QDate, QRectF
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QFontMetrics
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
            cursor.execute(
                "SELECT id, title, start_date, end_date, status FROM works ORDER BY id DESC"
            )
            rows = cursor.fetchall()
            conn.close()

            for work_id, title, start_str, end_str, status in rows:
                if not start_str or not end_str:
                    continue
                
                start_date = QDate.fromString(start_str, "yyyy-MM-dd")
                end_date = QDate.fromString(end_str, "yyyy-MM-dd")
                
                curr_date = start_date
                while curr_date <= end_date:
                    date_str = curr_date.toString("yyyy-MM-dd")
                    if date_str not in self.schedule_data:
                        self.schedule_data[date_str] = []
                    self.schedule_data[date_str].append(
                        {"id": work_id, "title": title, "status": status}
                    )
                    curr_date = curr_date.addDays(1)
        except Exception as e:
            print(f"캘린더 일정 로드 오류: {e}")

    def paintCell(self, painter, rect, date):
        """날짜와 우선순위 상위 두 업무명을 표시하고, 초과 일정 수를 안내"""
        painter.save()

        # 1. 셀 배경 처리 (오늘 날짜이거나 다른 달의 날짜 등 기본적인 배경 톤 맞추기)
        is_current_month = (
            date.year() == self.yearShown() and date.month() == self.monthShown()
        )
        
        # 배경색 채우기
        if not is_current_month:
            painter.fillRect(rect, QColor("#f8fafc"))  # 이번 달이 아니면 연한 회색 배경
        else:
            painter.fillRect(rect, QColor("#ffffff"))  # 기본 흰색 배경

        is_selected = date == self.selectedDate()
        if is_selected:
            painter.fillRect(rect, QColor("#e8f1fa"))

        # 오늘 날짜와 선택 날짜를 캘린더에서 구분
        if is_selected:
            painter.setPen(QPen(QColor("#397dbb"), 1.5))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        elif date == QDate.currentDate():
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
        elif is_selected:
            text_color = QColor("#22558a")
        else:
            text_color = QColor("#1e293b")  # 평일 검정/진한 회색

        # 3. 날짜 숫자를 왼쪽 상단에 직접 그리기
        painter.setPen(QPen(text_color))
        font = QFont()
        font.setPointSize(9)
        if date == QDate.currentDate() or is_selected:
            font.setBold(True)
        painter.setFont(font)

        # 왼쪽 상단 좌표 설정 (여백 X: 6px, Y: 6px)
        number_rect = QRectF(rect.x() + 6, rect.y() + 6, rect.width() - 12, 20)
        painter.drawText(number_rect, Qt.AlignLeft | Qt.AlignTop, str(date.day()))

        # 4. 날짜마다 우선순위 상위 두 업무명을 표시하고, 초과분은 개수로 안내
        date_str = date.toString("yyyy-MM-dd")
        if date_str in self.schedule_data:
            schedules = self.schedule_data[date_str]
            event_font = QFont()
            event_font.setPointSize(7)
            metrics = QFontMetrics(event_font)
            max_visible = max(2, min(4, int((rect.height() - 22) / 14)))
            visible_schedules = schedules[:max_visible]
            overflow_count = len(schedules) - len(visible_schedules)
            overflow_height = 10 if overflow_count > 0 else 0
            available_height = rect.height() - 21 - overflow_height
            event_height = max(
                8,
                min(
                    14,
                    int(
                        (available_height - max(0, len(visible_schedules) - 1))
                        / max(1, len(visible_schedules))
                    ),
                ),
            )
            event_x = rect.x() + 3
            event_width = max(0, rect.width() - 6)

            for index, schedule in enumerate(visible_schedules):
                event_rect = QRectF(
                    event_x,
                    rect.y() + 21 + index * (event_height + 1),
                    event_width,
                    event_height,
                )
                status = schedule["status"] or ""
                if "완료" in status:
                    background = QColor("#e4f2e8")
                    foreground = QColor("#386b48")
                elif "대기" in status or "등록" in status:
                    background = QColor("#fff2d8")
                    foreground = QColor("#865d20")
                else:
                    background = QColor("#dcecf8")
                    foreground = QColor("#22558a")

                painter.setBrush(QBrush(background))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(event_rect, 3, 3)

                title = metrics.elidedText(
                    schedule["title"] or "",
                    Qt.ElideRight,
                    max(0, int(event_width) - 6),
                )
                painter.setFont(event_font)
                painter.setPen(QPen(foreground))
                painter.drawText(
                    event_rect.adjusted(3, 0, -3, 0),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    title,
                )

            if overflow_count > 0:
                overflow_font = QFont()
                overflow_font.setPointSize(7)
                painter.setFont(overflow_font)
                painter.setPen(QPen(QColor("#64748b")))
                painter.drawText(
                    QRectF(
                        event_x + 2,
                        rect.y() + rect.height() - overflow_height,
                        max(0, event_width - 4),
                        overflow_height,
                    ),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    f"+{overflow_count}건",
                )

        painter.restore()


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = CustomCalendarWidget()
#     window.show()
#     sys.exit(app.exec_())