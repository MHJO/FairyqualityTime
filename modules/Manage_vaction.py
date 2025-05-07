import os, sys
from PyQt5 import uic
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QWidget,QApplication, QMessageBox, QTableWidgetItem,QTableWidget

from modules.SQLiteSingleton import SQLiteSingleton

class Manage_vaction(QWidget):
    def __init__(self, parent =None):
        super().__init__()
        uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '.ui'), self)

        self.db1 = SQLiteSingleton(r'D:\iway\source_code\FairyqualityTime\Database\company.db')
        
        self.init()
        self.initUi()
        self.listener()

    def init(self):
        self.chk_active.setChecked(True)
        # QTableWidget을 전체 행 선택 모드로 설정 (행 단위 선택)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)

        # 아이템 선택 변경 시 select_row_info 함수를 호출하도록 연결
        self.tableWidget.itemSelectionChanged.connect(self.select_row_info)
        
        
        self.cmb_search.addItems(['이름','사원번호'])
        self.table_setting()
        

    def initUi(self):
        self.setWindowTitle("조회")

    def listener(self):
        self.btn_search.clicked.connect(self.search_db)

    
    
    def table_setting(self):
        init_sql = '''
            SELECT
                lh.history_id ,
                e.employee_id as '사원번호',
                e.name AS '이름',
                (SELECT team_name FROM TB_team t WHERE t.team_id = e.team_id) AS '팀명',
                lh.leave_start_date as '휴가기간1' ,lh.leave_end_date as '휴가기간2',
                lh.leave_amount as '총 사용 연차' ,lh.remarks as '사유'
            FROM TB_employee e
            LEFT JOIN TB_employee_leave_history lh ON e.employee_id = lh.employee_id
            WHERE lh.history_id is not NULL 
            GROUP BY e.employee_id
        '''
        result = self.db1.execute_query(init_sql)
        column_names = [col[0] for col in self.db1.cursor.description]
        # print(column_names)
        self.tableWidget.setColumnCount(len(column_names))
        self.tableWidget.setHorizontalHeaderLabels(column_names)

        # 테이블에 결과를 표시하기 위해 행과 열의 개수를 설정
        self.tableWidget.setRowCount(len(result))
        
        if result:
            self.tableWidget.setColumnCount(len(result[0]))
        
        # 각 셀에 데이터를 채워 넣기
        for row_idx, row_data in enumerate(result):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                self.tableWidget.setItem(row_idx, col_idx, item)


    # 선택한 행의 정보
    def select_row_info(self):
        # 선택된 행들의 QModelIndex 목록 획득
        selected_indexes = self.tableWidget.selectionModel().selectedRows()
        for index in selected_indexes:
            row = index.row()
            row_data = []
            for column in range(self.tableWidget.columnCount()):
                item = self.tableWidget.item(row, column)
                row_data.append(item.text() if item is not None else "")
            print("Row", row, "data:", row_data)
            self.label_8.setText(f"{row_data[0]}_{row_data[1]}") # 사원번호_사원명

    # region [사원조회]
    def search_db(self):
        # 기본값 재직여부
        is_active_value = 1
        if self.chk_active.isChecked():
            is_active_value = 1
        else:
            is_active_value = 0
        
        # 1. 이름으로 검색
        if(self.cmb_search.currentText() == "이름"):
            self.tableWidget.clear()
            search_sql = f'''
                SELECT
                    lh.history_id ,
                    e.employee_id as '사원번호',
                    e.name AS '이름',
                    (SELECT team_name FROM TB_team t WHERE t.team_id = e.team_id) AS '팀명',
                    lh.leave_start_date as '휴가기간1' ,lh.leave_end_date as '휴가기간2',
                    lh.leave_amount as '총 사용 연차' ,lh.remarks as '사유'
                FROM TB_employee e
                LEFT JOIN TB_employee_leave_history lh ON e.employee_id = lh.employee_id
                WHERE lh.history_id is not NULL and
                    e.is_active = {is_active_value} AND
                    e.name like '%{self.txt_search.text()}%'
                GROUP BY e.employee_id
                '''
            result = self.db1.execute_query(search_sql)
            column_names = [col[0] for col in self.db1.cursor.description]
            self.tableWidget.setColumnCount(len(column_names))
            self.tableWidget.setHorizontalHeaderLabels(column_names)

            # 테이블에 결과를 표시하기 위해 행과 열의 개수를 설정
            self.tableWidget.setRowCount(len(result))
            
            if result:
                self.tableWidget.setColumnCount(len(result[0]))
            
            # 각 셀에 데이터를 채워 넣기
            for row_idx, row_data in enumerate(result):
                for col_idx, cell_data in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_data))
                    self.tableWidget.setItem(row_idx, col_idx, item)

        # 2. 사원번호로 검색
        elif(self.cmb_search.currentText() == "사원번호"):
            self.tableWidget.clear()

            search_sql = f'''
                SELECT
                    lh.history_id ,
                    e.employee_id as '사원번호',
                    e.name AS '이름',
                    (SELECT team_name FROM TB_team t WHERE t.team_id = e.team_id) AS '팀명',
                    lh.leave_start_date as '휴가기간1' ,lh.leave_end_date as '휴가기간2',
                    lh.leave_amount as '총 사용 연차' ,lh.remarks as '사유'
                FROM TB_employee e
                LEFT JOIN TB_employee_leave_history lh ON e.employee_id = lh.employee_id
                WHERE lh.history_id is not NULL and
                    e.is_active = {is_active_value} AND
                    e.employee_id = {self.txt_search.text()}
                GROUP BY e.employee_id
                '''
            result = self.db1.execute_query(search_sql)
            column_names = [col[0] for col in self.db1.cursor.description]
            self.tableWidget.setColumnCount(len(column_names))
            self.tableWidget.setHorizontalHeaderLabels(column_names)

            # 테이블에 결과를 표시하기 위해 행과 열의 개수를 설정
            self.tableWidget.setRowCount(len(result))
            
            if result:
                self.tableWidget.setColumnCount(len(result[0]))
            
            # 각 셀에 데이터를 채워 넣기
            for row_idx, row_data in enumerate(result):
                for col_idx, cell_data in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_data))
                    self.tableWidget.setItem(row_idx, col_idx, item)
    # endregion


  

    # endregion