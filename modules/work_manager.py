import os
import sys
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QMessageBox, QLabel, QLineEdit, QTextEdit, 
    QDateEdit, QComboBox, QFormLayout, QAbstractItemView, QWidget,
    QApplication
)

from PyQt5 import uic
from PyQt5.QtCore import QDate
from .util import Util  # 공통 유틸 임포트

APP_PATH = Util.get_app_path()
DB_PATH = os.path.join(APP_PATH, "Database", "work_database.db")

# UI 파일 경로 설정
UI_PATH = os.path.join(APP_PATH, "ui", "work_manager.ui")
UI_HISTORY_PATH = os.path.join(APP_PATH, "ui", "work_history.ui")  # 이력 UI 파일 경로 (필요시 파일명 확인)

class workManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 메인 UI 파일 로드
        if os.path.exists(UI_PATH):
            uic.loadUi(UI_PATH, self)
        else:
            QMessageBox.critical(self, "오류", f"UI 파일을 찾을 수 없습니다:\n{UI_PATH}")
            return

        self.selected_work_id = None  # 선택된 업무 ID (수정/삭제용)

        self.init_db()
        self.init_ui_connections()
        self.load_data()

    def get_connection(self):
        db_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        return sqlite3.connect(DB_PATH)

    def init_db(self):
        """데이터베이스 및 테이블(works, work_histories) 초기화"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. 원본 업무 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                status TEXT,
                repeat_cycle TEXT,
                memo TEXT
            )
        """)
        
        # 2. 변경 이력 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_histories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,              -- 'INSERT', 'UPDATE', 'DELETE'
                old_title TEXT, new_title TEXT,
                old_start_date TEXT, new_start_date TEXT,
                old_end_date TEXT, new_end_date TEXT,
                old_status TEXT, new_status TEXT,
                old_memo TEXT, new_memo TEXT,
                modified_at TEXT NOT NULL,
                FOREIGN KEY (work_id) REFERENCES works (id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        conn.close()

    def init_ui_connections(self):
        """UI 컴포넌트 시그널(이벤트) 연결"""
        self.date_start.setDate(QDate.currentDate())
        self.date_deadline.setDate(QDate.currentDate())

        self.btn_save.clicked.connect(self.save_work)
        self.btn_clear.clicked.connect(self.clear_form)
        self.btn_delete.clicked.connect(self.delete_work)
        
        if hasattr(self, 'btn_history'):
            self.btn_history.clicked.connect(self.view_history)

        self.table_works.cellClicked.connect(self.on_cell_clicked)
        
        self.table_works.setColumnCount(7)
        self.table_works.setHorizontalHeaderLabels(["ID", "상태", "업무명", "시작일", "마감일", "반복 주기", "비고"])
        self.table_works.setColumnHidden(0, True)

    def load_data(self):
        """테이블에 업무 목록 불러오기"""
        self.table_works.setRowCount(0)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, status, title, start_date, end_date, repeat_cycle, memo FROM works ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        for row_idx, row_data in enumerate(rows):
            self.table_works.insertRow(row_idx)
            for col_idx, val in enumerate(row_data):
                self.table_works.setItem(row_idx, col_idx, QTableWidgetItem(str(val) if val else ""))
        
        self.clear_form()

    def clear_form(self):
        """입력 폼 초기화 및 선택 해제"""
        self.selected_work_id = None
        self.txt_work_title.clear()
        self.date_start.setDate(QDate.currentDate())
        self.date_deadline.setDate(QDate.currentDate())
        self.cmb_status.setCurrentIndex(0)
        self.cmb_repeat.setCurrentIndex(0)
        self.txt_memo.clear()
        self.btn_save.setText("💾 등록 / 저장")

    def on_cell_clicked(self, row, col):
        """테이블 행 클릭 시 폼에 데이터 채우기"""
        id_item = self.table_works.item(row, 0)
        if not id_item:
            return
        
        self.selected_work_id = id_item.text()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, start_date, end_date, status, repeat_cycle, memo FROM works WHERE id = ?", (self.selected_work_id,))
        row_data = cursor.fetchone()
        conn.close()

        if row_data:
            title, start_date, end_date, status, repeat_cycle, memo = row_data
            self.txt_work_title.setText(title or "")
            if start_date:
                self.date_start.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
            if end_date:
                self.date_deadline.setDate(QDate.fromString(end_date, "yyyy-MM-dd"))
            self.cmb_status.setCurrentText(status or "등록 (대기)")
            self.cmb_repeat.setCurrentText(repeat_cycle or "반복 없음")
            self.txt_memo.setPlainText(memo or "")
            
            self.btn_save.setText("✏️ 수정 내용 저장")

    def save_work(self):
        if self.selected_work_id is None:
            self.add_work()
        else:
            self.update_work()

    def add_work(self):
        title = self.txt_work_title.text().strip()
        if not title:
            QMessageBox.warning(self, "경고", "업무명을 입력해주세요.")
            return

        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_deadline.date().toString("yyyy-MM-dd")
        status = self.cmb_status.currentText()
        repeat_cycle = self.cmb_repeat.currentText()
        memo = self.txt_memo.toPlainText()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO works (title, start_date, end_date, status, repeat_cycle, memo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, start_date, end_date, status, repeat_cycle, memo))
        
        work_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO work_histories (
                work_id, action_type, new_title, new_start_date, new_end_date, 
                new_status, new_memo, modified_at
            ) VALUES (?, 'INSERT', ?, ?, ?, ?, ?, ?)
        """, (work_id, title, start_date, end_date, status, memo, now))

        conn.commit()
        conn.close()

        QMessageBox.information(self, "성공", "업무가 등록되었습니다.")
        self.load_data()

    def update_work(self):
        title = self.txt_work_title.text().strip()
        if not title:
            QMessageBox.warning(self, "경고", "업무명을 입력해주세요.")
            return

        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_deadline.date().toString("yyyy-MM-dd")
        status = self.cmb_status.currentText()
        repeat_cycle = self.cmb_repeat.currentText()
        memo = self.txt_memo.toPlainText()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT title, start_date, end_date, status, memo FROM works WHERE id = ?", (self.selected_work_id,))
        old_data = cursor.fetchone()
        
        if not old_data:
            conn.close()
            return

        old_title, old_start, old_end, old_status, old_memo = old_data

        cursor.execute("""
            UPDATE works 
            SET title = ?, start_date = ?, end_date = ?, status = ?, repeat_cycle = ?, memo = ?
            WHERE id = ?
        """, (title, start_date, end_date, status, repeat_cycle, memo, self.selected_work_id))

        cursor.execute("""
            INSERT INTO work_histories (
                work_id, action_type, 
                old_title, new_title, 
                old_start_date, new_start_date, 
                old_end_date, new_end_date, 
                old_status, new_status, 
                old_memo, new_memo, 
                modified_at
            ) VALUES (?, 'UPDATE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.selected_work_id, 
            old_title, title, 
            old_start, start_date, 
            old_end, end_date, 
            old_status, status, 
            old_memo, memo, 
            now
        ))

        conn.commit()
        conn.close()

        QMessageBox.information(self, "성공", "업무가 수정되었습니다.")
        self.load_data()

    def delete_work(self):
        if not self.selected_work_id:
            QMessageBox.warning(self, "경고", "삭제할 업무를 목록에서 선택해주세요.")
            return

        re = QMessageBox.question(self, "삭제 확인", "정말 이 업무를 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if re != QMessageBox.Yes:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT title, start_date, end_date, status, memo FROM works WHERE id = ?", (self.selected_work_id,))
        old_data = cursor.fetchone()

        if old_data:
            old_title, old_start, old_end, old_status, old_memo = old_data
            cursor.execute("""
                INSERT INTO work_histories (
                    work_id, action_type, old_title, old_start_date, old_end_date, old_status, old_memo, modified_at
                ) VALUES (?, 'DELETE', ?, ?, ?, ?, ?, ?)
            """, (self.selected_work_id, old_title, old_start, old_end, old_status, old_memo, now))

        cursor.execute("DELETE FROM works WHERE id = ?", (self.selected_work_id,))
        conn.commit()
        conn.close()

        QMessageBox.information(self, "성공", "업무가 삭제되었습니다.")
        self.load_data()

    def view_history(self):
        """작성하신 이력 UI 파일(work_history.ui)을 로드하여 변경 이력 표시"""
        if not self.selected_work_id:
            QMessageBox.warning(self, "알림", "이력을 확인할 업무를 목록에서 선택해주세요.")
            return

        # 이력 조회 다이얼로그 생성
        history_dialog = QDialog(self)
        
        # 올려주신 이력 UI 파일 로드 (파일명이 다를 경우 수정해주세요, 예: work_history.ui)
        target_ui = UI_HISTORY_PATH
        if os.path.exists(target_ui):
            uic.loadUi(target_ui, history_dialog)
        else:
            # UI 파일이 없을 경우 대비한 기본 폴백 처리
            from PyQt5.QtWidgets import QVBoxLayout, QTableView
            layout = QVBoxLayout(history_dialog)
            history_dialog.tableView = QTableView()
            layout.addWidget(history_dialog.tableView)

        history_dialog.setWindowTitle("퇴근요정 - 업무 변경 이력 상세")
        history_dialog.resize(650, 350)

        # tableView 가져오기 (ui 파일 내부에 name="tableView"로 정의되어 있음)
        table = getattr(history_dialog, 'tableView', None)
        if table:
            # QTableView용 모델 설정 또는 QTableWidget 변환 활용
            # 편의를 위해 QTableView에 세부 데이터를 넣기 위한 표준 TableWidget 혹은 표준 Model 세팅
            from PyQt5.QtGui import QStandardItemModel, QStandardItem
            
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["변경 일시", "작업 유형", "변경 내용 상세"])

            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT action_type, old_title, new_title, old_status, new_status, modified_at 
                FROM work_histories 
                WHERE work_id = ? 
                ORDER BY id DESC
            """, (self.selected_work_id,))
            h_rows = cursor.fetchall()
            conn.close()

            for r_data in h_rows:
                action, o_title, n_title, o_stat, n_stat, mod_at = r_data
                
                if action == 'INSERT':
                    desc = f"[등록] 업무명: '{n_title}' (상태: {n_stat})"
                elif action == 'UPDATE':
                    desc = f"[수정] 업무명: '{o_title}' ➔ '{n_title}' / 상태: {o_stat} ➔ {n_stat}"
                elif action == 'DELETE':
                    desc = f"[삭제] 업무명: '{o_title}' (상태: {o_stat})"
                else:
                    desc = f"유형: {action}"

                item_date = QStandardItem(mod_at)
                item_action = QStandardItem(action)
                item_desc = QStandardItem(desc)

                model.appendRow([item_date, item_action, item_desc])

            table.setModel(model)
            # 열 너비 자동 조절
            table.horizontalHeader().setStretchLastSection(True)

        history_dialog.exec_()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = workManager()
    window.show()
    sys.exit(app.exec_())