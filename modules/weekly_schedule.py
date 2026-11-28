import sqlite3
from contextlib import closing
from datetime import datetime

from PyQt5.QtCore import QDate, QRect, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from .work_manager import DB_PATH


class WeeklyScheduleWidget(QWidget):
    START_HOUR = 6
    END_HOUR = 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_date = QDate.currentDate()
        self.schedules = []
        self.setMinimumHeight(340)
        self.setMouseTracking(True)
        self.load_schedules()

    def set_selected_date(self, selected_date):
        if selected_date.isValid():
            self.selected_date = selected_date
            self.update()

    def load_schedules(self):
        with closing(sqlite3.connect(DB_PATH)) as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, title, start_date, end_date, start_time, end_time, status
                FROM works
                WHERE start_date IS NOT NULL AND end_date IS NOT NULL
                ORDER BY start_date, start_time, id
            """)
            self.schedules = cursor.fetchall()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))

        left, right, top = 48, 10, 10
        header_height, all_day_height = 30, 48
        grid_top = top + header_height + all_day_height
        grid_bottom = self.height() - 12
        grid_height = max(1, grid_bottom - grid_top)
        hour_height = grid_height / (self.END_HOUR - self.START_HOUR)
        column_width = max(1, (self.width() - left - right) / 7)
        week_start = self.selected_date.addDays(1 - self.selected_date.dayOfWeek())

        for day_index in range(7):
            x = left + day_index * column_width
            day = week_start.addDays(day_index)
            if day == QDate.currentDate():
                painter.fillRect(
                    self._column_rect(x, top, column_width, self.height() - top),
                    QColor("#f8fbff"),
                )
            painter.setPen(QColor("#334155"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(
                self._column_rect(x, top, column_width, header_height),
                Qt.AlignCenter,
                f"{'월화수목금토일'[day_index]} {day.toString('M/d')}",
            )

            all_day = [
                schedule for schedule in self._schedules_for(day)
                if not self._has_time(schedule)
            ]
            for index, schedule in enumerate(all_day[:2]):
                chip = self._column_rect(
                    x + 3,
                    top + header_height + 2 + index * 19,
                    column_width - 6,
                    17,
                )
                self._draw_schedule(painter, chip, schedule, compact=True)
            if len(all_day) > 2:
                painter.setPen(QColor("#64748b"))
                painter.setFont(QFont("Segoe UI", 7))
                painter.drawText(
                    self._column_rect(
                        x + 3, top + header_height + 39, column_width - 6, 12
                    ),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    f"+{len(all_day) - 2}건",
                )

            painter.setPen(QPen(QColor("#e2e8f0"), 1))
            painter.drawLine(
                int(x),
                top + header_height,
                int(x),
                grid_bottom,
            )
            for hour in range(self.START_HOUR, self.END_HOUR + 1):
                y = grid_top + (hour - self.START_HOUR) * hour_height
                painter.setPen(QPen(QColor("#e2e8f0"), 1))
                painter.drawLine(int(x), int(y), int(x + column_width), int(y))
                if day_index == 0 and hour < self.END_HOUR:
                    painter.setPen(QColor("#64748b"))
                    painter.setFont(QFont("Segoe UI", 7))
                    painter.drawText(
                        2,
                        int(y + 9),
                        42,
                        12,
                        Qt.AlignRight | Qt.AlignVCenter,
                        f"{hour:02d}:00",
                    )

            self._draw_timed_schedules(
                painter, day, x, column_width, grid_top, hour_height
            )

        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.drawLine(left + int(7 * column_width), top + header_height,
                         left + int(7 * column_width), grid_bottom)

    @staticmethod
    def _column_rect(x, y, width, height):
        return QRect(int(x), int(y), max(1, int(width)), max(1, int(height)))

    def _schedules_for(self, day):
        day_text = day.toString("yyyy-MM-dd")
        return [
            schedule for schedule in self.schedules
            if schedule[2] <= day_text <= schedule[3]
        ]

    @staticmethod
    def _has_time(schedule):
        return bool(schedule[4] and schedule[5])

    def _draw_timed_schedules(self, painter, day, x, column_width, grid_top, hour_height):
        day_text = day.toString("yyyy-MM-dd")
        entries = []
        for schedule in self._schedules_for(day):
            if not self._has_time(schedule):
                continue
            try:
                start = (
                    datetime.strptime(schedule[4], "%H:%M")
                    if schedule[2] == day_text
                    else datetime.strptime(f"{self.START_HOUR:02d}:00", "%H:%M")
                )
                end = (
                    datetime.strptime(schedule[5], "%H:%M")
                    if schedule[3] == day_text
                    else datetime.strptime(f"{self.END_HOUR:02d}:00", "%H:%M")
                )
            except ValueError:
                continue

            start_minute = max(
                self.START_HOUR * 60, start.hour * 60 + start.minute
            )
            end_minute = min(self.END_HOUR * 60, end.hour * 60 + end.minute)
            if end_minute <= start_minute:
                continue
            entries.append((start_minute, end_minute, schedule))

        entries.sort(key=lambda entry: (entry[0], entry[1]))
        lane_ends = []
        placed = []
        for start_minute, end_minute, schedule in entries:
            lane = next(
                (index for index, lane_end in enumerate(lane_ends)
                 if lane_end <= start_minute),
                len(lane_ends),
            )
            if lane == len(lane_ends):
                lane_ends.append(end_minute)
            else:
                lane_ends[lane] = end_minute
            placed.append((start_minute, end_minute, lane, schedule))

        lane_count = max(1, len(lane_ends))
        lane_width = max(1, (column_width - 8) / lane_count)
        for start_minute, end_minute, lane, schedule in placed:
            y = grid_top + (
                start_minute - self.START_HOUR * 60
            ) / 60 * hour_height
            height = max(32, (end_minute - start_minute) / 60 * hour_height)
            rect = self._column_rect(
                x + 4 + lane * lane_width,
                y,
                lane_width - 3,
                min(height, self.height() - y - 10),
            )
            self._draw_schedule(painter, rect, schedule)

    @staticmethod
    def _draw_schedule(painter, rect, schedule, compact=False):
        status = str(schedule[6] or "")
        background = QColor("#dcfce7") if status == "완료" else QColor("#dbeafe")
        foreground = QColor("#166534") if status == "완료" else QColor("#1d4ed8")
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(foreground)
        title = str(schedule[1] or "")
        if not compact and schedule[4] and schedule[5]:
            time_text = f"{schedule[4]} ~ {schedule[5]}"
            time_rect = QRect(
                rect.left() + 4, rect.top() + 2,
                max(1, rect.width() - 7), 12,
            )
            title_rect = QRect(
                rect.left() + 4, rect.top() + 14,
                max(1, rect.width() - 7), max(10, rect.height() - 15),
            )
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(
                time_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                painter.fontMetrics().elidedText(
                    time_text, Qt.ElideRight, max(1, time_rect.width())
                ),
            )
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                title_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                painter.fontMetrics().elidedText(
                    title, Qt.ElideRight, max(1, title_rect.width())
                ),
            )
        else:
            painter.setFont(QFont("Segoe UI", 7 if compact else 8, QFont.Bold))
            painter.drawText(
                rect.adjusted(4, 1, -3, -1),
                Qt.AlignLeft | Qt.AlignVCenter,
                painter.fontMetrics().elidedText(
                    title, Qt.ElideRight, max(1, rect.width() - 7)
                ),
            )
        painter.restore()
