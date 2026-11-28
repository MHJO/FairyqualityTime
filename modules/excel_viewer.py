import json
import os
import re
import sqlite3
import zipfile
from contextlib import closing

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PyQt5 import uic

from .g2b_api import APP_PATH, DB_PATH, Sqlite


SHEET_NAMES = {
    "입찰공고": "입찰공고용역",
    "사전규격": "사전규격",
    "발주계획": "발주계획",
}

UI_DIR = os.path.join(APP_PATH, "ui")
VIEWER_UI_PATH = os.path.join(UI_DIR, "excel_viewer.ui")
REPORT_UI_PATH = os.path.join(UI_DIR, "excel_report.ui")
REPORT_TAB_UI_PATH = os.path.join(UI_DIR, "excel_report_tab.ui")


class ExcelViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(VIEWER_UI_PATH, self)
        self.history_records = []

        self.table.setColumnHidden(1, True)
        self.table.setColumnWidth(0, 34)
        self.table.setColumnWidth(2, 145)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 240)
        self.table.setColumnWidth(5, 180)
        self.table.setColumnWidth(6, 70)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.chk_select_all.toggled.connect(self.set_all_checked)
        self.btn_refresh.clicked.connect(self.load_history)
        self.btn_query.clicked.connect(self.open_selected_reports)
        self.btn_close.clicked.connect(self.reject)
        self.load_history()

    def load_history(self):
        try:
            Sqlite.initialize_search_history()
            with closing(sqlite3.connect(DB_PATH)) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute("""
                    SELECT id, searched_at, search_type, search_keywords,
                           search_start, search_end, result_count, save_path, file_path
                    FROM G2BSearchHistory
                    ORDER BY id DESC
                """).fetchall()
        except (sqlite3.Error, OSError) as error:
            QMessageBox.critical(
                self, "데이터베이스 오류",
                f"나라장터 조회 이력을 불러오지 못했습니다.\n{error}",
            )
            return

        self.history_records = [dict(row) for row in rows]
        self.table.setRowCount(len(rows))
        for row_index, record in enumerate(self.history_records):
            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
            )
            check_item.setCheckState(Qt.Unchecked)
            self.table.setItem(row_index, 0, check_item)

            self._set_item(row_index, 1, record["id"])
            self._set_item(row_index, 2, record["searched_at"])
            self._set_item(row_index, 3, record["search_type"])
            self._set_item(row_index, 4, self.keywords_text(record["search_keywords"]))
            period = self.period_text(record["search_start"], record["search_end"])
            self._set_item(row_index, 5, period)
            self._set_item(row_index, 6, record["result_count"], Qt.AlignRight)
            path_item = self._set_item(row_index, 7, record["file_path"])
            path_item.setToolTip(record["file_path"])

        self.chk_select_all.setChecked(False)
        self.lbl_status.setText(f"조회 이력 {len(rows)}건")

    def _set_item(self, row, column, value, alignment=None):
        item = QTableWidgetItem("" if value is None else str(value))
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if alignment is not None:
            item.setTextAlignment(alignment | Qt.AlignVCenter)
        self.table.setItem(row, column, item)
        return item

    @staticmethod
    def keywords_text(raw_keywords):
        try:
            keywords = json.loads(raw_keywords or "[]")
        except (TypeError, json.JSONDecodeError):
            keywords = [word.strip() for word in str(raw_keywords or "").split(",")]
        if not isinstance(keywords, list):
            keywords = [str(keywords)]
        return ", ".join(str(keyword) for keyword in keywords)

    @staticmethod
    def period_text(start, end):
        if start and end:
            return f"{start} ~ {end}"
        return start or end or "-"

    def set_all_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None:
                item.setCheckState(state)

    def selected_records(self):
        return [
            self.history_records[row]
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() == Qt.Checked
        ]

    def open_selected_reports(self):
        records = self.selected_records()
        if not records:
            QMessageBox.information(self, "선택 필요", "조회할 이력을 체크해주세요.")
            return

        try:
            reports = [self.load_report_data(record) for record in records]
        except (
            OSError, ValueError, KeyError, ImportError,
            InvalidFileException, zipfile.BadZipFile
        ) as error:
            QMessageBox.warning(
                self, "엑셀 조회 오류",
                f"선택한 엑셀 파일을 읽지 못했습니다.\n{error}",
            )
            return

        dialog = G2BReportDialog(reports, self)
        dialog.exec_()

    @staticmethod
    def load_report_data(record):
        file_path = record["file_path"]
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"저장 파일을 찾을 수 없습니다:\n{file_path}")

        sheet_name = SHEET_NAMES.get(record["search_type"])
        if sheet_name is None:
            raise ValueError(f"지원하지 않는 조회 유형입니다: {record['search_type']}")

        keywords_raw = record["search_keywords"] or "[]"
        try:
            keywords = json.loads(keywords_raw)
        except json.JSONDecodeError:
            keywords = [word.strip() for word in keywords_raw.split(",") if word.strip()]
        if not isinstance(keywords, list):
            keywords = [str(keywords)]
        keywords = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]

        with pd.ExcelFile(file_path) as workbook:
            if sheet_name not in workbook.sheet_names:
                raise ValueError(
                    f"엑셀 파일에 '{sheet_name}' 시트가 없습니다.\n{file_path}"
                )
            dataframe = pd.read_excel(workbook, sheet_name=sheet_name).fillna("")

        columns = [str(column) for column in dataframe.columns]
        rows = []
        for values in dataframe.itertuples(index=False, name=None):
            row_values = [ExcelViewerDialog.display_value(value) for value in values]
            searchable_text = " ".join(row_values).casefold()
            matches = [
                keyword for keyword in keywords
                if keyword.casefold() in searchable_text
            ]
            rows.append({
                "values": row_values,
                "keywords": matches,
            })

        return {
            "record": record,
            "sheet_name": sheet_name,
            "columns": columns,
            "rows": rows,
            "keywords": keywords,
        }

    @staticmethod
    def display_value(value):
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return f"{value:,}" if float(value).is_integer() else str(value)
        return str(value)


class G2BReportDialog(QDialog):
    def __init__(self, reports, parent=None):
        super().__init__(parent)
        uic.loadUi(REPORT_UI_PATH, self)
        # 최소화, 최대화, 닫기 버튼 표시
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )

        for report in reports:
            label = f"{report['record']['search_type']} · {ExcelViewerDialog.keywords_text(report['record']['search_keywords'])}"
            self.tab_reports.addTab(HistoryReportWidget(report), label[:48])
        self.btn_close.clicked.connect(self.accept)


class HistoryReportWidget(QWidget):
    def __init__(self, report, parent=None):
        super().__init__(parent)
        uic.loadUi(REPORT_TAB_UI_PATH, self)
        self.report = report
        self.active_keyword = None
        self.search_text = ""
        self.keyword_buttons = []
        self.row_categories = [row["keywords"] for row in report["rows"]]
        self.budget_index = self.find_budget_column(report["columns"])

        info = report["record"]
        self.lbl_file_info.setText(
            f"{info['searched_at']}  ·  {report['sheet_name']}  ·  {info['file_path']}"
        )
        keywords_text = ExcelViewerDialog.keywords_text(info["search_keywords"]) or "-"
        self.lbl_keywords_value.setText(keywords_text)
        self.build_keyword_filters()

        self.table.setColumnCount(len(report["columns"]) + 1)
        self.table.setHorizontalHeaderLabels(["키워드 분류"] + report["columns"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.txt_search.textChanged.connect(self.on_search_changed)
        self.render_table()
        self.update_summary()

    @staticmethod
    def find_budget_column(columns):
        for index, column in enumerate(columns):
            if "금액" in column or "예산" in column:
                return index
        return None

    def build_keyword_filters(self):
        self.clear_layout(self.grid_keyword_filters)
        all_button = QPushButton(f"전체 보기  {len(self.report['rows'])}건")
        all_button.setCheckable(True)
        all_button.setChecked(self.active_keyword is None)
        all_button.clicked.connect(lambda: self.set_active_keyword(None))
        self.keyword_buttons = [all_button]

        for keyword in self.report["keywords"]:
            count = sum(keyword in tags for tags in self.row_categories)
            button = QPushButton(f"{keyword}  {count}건")
            button.setCheckable(True)
            button.setChecked(self.active_keyword == keyword)
            button.clicked.connect(
                lambda checked=False, selected=keyword:
                    self.set_active_keyword(selected)
            )
            self.keyword_buttons.append(button)

        for index, button in enumerate(self.keyword_buttons):
            self.grid_keyword_filters.addWidget(button, index // 4, index % 4)

    @staticmethod
    def clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_active_keyword(self, keyword):
        self.active_keyword = keyword
        self.build_keyword_filters()
        self.render_table()

    def on_search_changed(self, text):
        self.search_text = text.strip().casefold()
        self.render_table()

    def visible_rows(self):
        for row, category_matches in zip(self.report["rows"], self.row_categories):
            if self.active_keyword and self.active_keyword not in category_matches:
                continue
            if self.search_text and self.search_text not in " ".join(row["values"]).casefold():
                continue
            yield row

    def render_table(self):
        rows = list(self.visible_rows())
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            category = ", ".join(row["keywords"]) or "미분류"
            items = [category] + row["values"]
            for column_index, value in enumerate(items):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(row_index, column_index, item)
        self.table.resizeColumnsToContents()

    def update_summary(self):
        self.lbl_count_value.setText(f"{len(self.report['rows']):,}건")
        if self.budget_index is None:
            self.lbl_budget_value.setText("금액 정보 없음")
            return
        amount = sum(
            self.parse_amount(row["values"][self.budget_index])
            for row in self.report["rows"]
        )
        self.lbl_budget_value.setText(f"{amount:,.0f}원")

    @staticmethod
    def parse_amount(value):
        match = re.search(r"-?[\d,]+(?:\.\d+)?", str(value))
        return float(match.group(0).replace(",", "")) if match else 0
