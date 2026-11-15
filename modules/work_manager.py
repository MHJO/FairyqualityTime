import os
import sys
import sqlite3

from PyQt5 import uic
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QDialog, QApplication, QMessageBox, QTableWidgetItem, QAbstractItemView
)

from .util import Util
# if __package__:
#     from .util import Util
# else:
#     from util import Util

APP_PATH = Util.get_app_path()
DB_PATH = os.path.join(APP_PATH, "Database", "work_database.db")

class workManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.getcwd(), "ui", "work_manager.ui")
        uic.loadUi(ui_path, self)
        
        # 데이터베이스 및 테이블 초기화
        self.init_db()
        
        # 날짜 기본값 오늘로 세팅
        self.date_start.setDate(QDate.currentDate())
        self.date_deadline.setDate(QDate.currentDate())
        
        # 선택된 업무 ID (수정 모드 판별용)
        self.selected_id = None
        
        # 버튼 및 테이블 이벤트 연결
        self.btn_save.clicked.connect(self.save_work)
        self.btn_clear.clicked.connect(self.clear_inputs)
        self.btn_delete.clicked.connect(self.delete_work)
        self.table_works.cellClicked.connect(self.load_work_to_form)
        
        # 테이블 데이터 불러오기
        self.load_table_data()

    def init_db(self):
        """업무 관리용 SQLite 테이블 생성"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                status TEXT,
                repeat_cycle TEXT,
                memo TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def load_table_data(self):
        """DB에서 데이터를 조회하여 우측 테이블에 출력"""
        self.table_works.setRowCount(0)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, status, title, start_date, end_date, repeat_cycle, memo FROM works ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        for row_idx, row_data in enumerate(rows):
            self.table_works.insertRow(row_idx)
            
            # 셀에 데이터 채우기 (상태, 업무명, 시작일, 마감일, 반복 주기, 비고)
            for col_idx, val in enumerate(row_data[1:]):
                item = QTableWidgetItem(str(val) if val else "")
                # 첫 번째 컬럼(상태) 아이템에 DB 고유 ID를 커스텀 데이터로 숨겨서 저장
                if col_idx == 0:
                    item.setData(100, row_data[0])
                self.table_works.setItem(row_idx, col_idx, item)

    def save_work(self):
        """업무 신규 등록 또는 수정 저장"""
        title = self.txt_work_title.text().strip()
        if not title:
            QMessageBox.warning(self, "경고", "업무명을 입력해주세요!")
            self.txt_work_title.setFocus()
            return

        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_deadline.date().toString("yyyy-MM-dd")
        status = self.cmb_status.currentText()
        repeat_cycle = self.cmb_repeat.currentText()
        memo = self.txt_memo.toPlainText()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if self.selected_id is None:
            # 신규 등록
            cursor.execute('''
                INSERT INTO works (title, start_date, end_date, status, repeat_cycle, memo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, start_date, end_date, status, repeat_cycle, memo))
            msg = "업무가 성공적으로 등록되었습니다."
        else:
            # 수정 저장
            cursor.execute('''
                UPDATE works 
                SET title = ?, start_date = ?, end_date = ?, status = ?, repeat_cycle = ?, memo = ?
                WHERE id = ?
            ''', (title, start_date, end_date, status, repeat_cycle, memo, self.selected_id))
            msg = "업무가 성공적으로 수정되었습니다."

        conn.commit()
        conn.close()

        QMessageBox.information(self, "완료", msg)
        self.clear_inputs()
        self.load_table_data()

    def load_work_to_form(self, row, column):
        """테이블 행 클릭 시 해당 데이터를 좌측 입력 폼에 불러오기 (수정 모드)"""
        item = self.table_works.item(row, 0)
        if not item:
            return
        work_id = item.data(100)
        if not work_id:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, start_date, end_date, status, repeat_cycle, memo FROM works WHERE id = ?", (work_id,))
        row_data = cursor.fetchone()
        conn.close()

        if row_data:
            self.selected_id = row_data[0]
            self.txt_work_title.setText(row_data[1])
            if row_data[2]:
                self.date_start.setDate(QDate.fromString(row_data[2], "yyyy-MM-dd"))
            if row_data[3]:
                self.date_deadline.setDate(QDate.fromString(row_data[3], "yyyy-MM-dd"))
            
            self.cmb_status.setCurrentText(row_data[4])
            self.cmb_repeat.setCurrentText(row_data[5])
            self.txt_memo.setPlainText(row_data[6] if row_data[6] else "")
            
            # 저장 버튼 텍스트 변경으로 수정 모드임을 직관적으로 표시
            self.btn_save.setText("✏️ 수정하기")

    def clear_inputs(self):
        """입력 폼 초기화 및 신규 등록 모드로 전환"""
        self.txt_work_title.clear()
        self.date_start.setDate(QDate.currentDate())
        self.date_deadline.setDate(QDate.currentDate())
        self.cmb_status.setCurrentIndex(0)
        self.cmb_repeat.setCurrentIndex(0)
        self.txt_memo.clear()
        self.selected_id = None
        self.btn_save.setText("💾 등록 / 저장")
        self.table_works.clearSelection()

    def delete_work(self):
        """선택한 업무 삭제"""
        selected_rows = self.table_works.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "경고", "삭제할 업무를 선택해주세요!")
            return

        reply = QMessageBox.question(self, "확인", "선택한 업무를 정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            row = selected_rows[0].row()
            item = self.table_works.item(row, 0)
            work_id = item.data(100)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
            conn.commit()
            conn.close()

            QMessageBox.information(self, "완료", "삭제되었습니다.")
            self.clear_inputs()
            self.load_table_data()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = workManager()
    window.show()
    sys.exit(app.exec_())