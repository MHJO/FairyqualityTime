import os, sys
from PyQt5 import uic
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QDialog,QApplication, QMessageBox, QTableWidgetItem,QTableWidget

from modules.SQLiteSingleton import SQLiteSingleton

class employeeInfo(QDialog):
    

    def __init__(self, parent =None):
        super().__init__()
        uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '.ui'), self)

        self.db1 = SQLiteSingleton(r'D:\iway\source_code\FairyqualityTime\Database\company.db')
        
        self.init()
        self.initUi()
        self.listener()

    def init(self):
        self.default_setting_vacation()
        self.chk_active.setChecked(True)
        # QTableWidget을 전체 행 선택 모드로 설정 (행 단위 선택)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)

        # 아이템 선택 변경 시 select_row_info 함수를 호출하도록 연결
        self.tableWidget.itemSelectionChanged.connect(self.select_row_info)
        
        
        self.cmb_search.addItems(['이름','사원번호'])
        self.table_setting()
        

    def initUi(self):
        self.setWindowTitle("사원정보 조회")

    def listener(self):
        self.btn_search.clicked.connect(self.search_db)
        self.gb_vac.toggled.connect(self.change_setting)
        self.btn_vac.clicked.connect(self.add_vaction)

    def change_setting(self, checked):
        for widget in self.gb_vac.findChildren(QWidget):
            widget.setEnabled(checked)
    
    def table_setting(self):
        init_sql = '''
            SELECT
                e.employee_id as '사원번호',
                e.name AS '이름',
                (SELECT team_name FROM TB_team t WHERE t.team_id = e.team_id) AS '팀명',
                e.email,
                e.phone,
                e.hire_date AS '입사일자',
                e.annual_leave_allocated as '연차수',
                e.annual_leave_allocated - COALESCE(SUM(lh.leave_amount), 0) AS 사용가능연차,
                CASE 
                    WHEN e.is_active = 1 THEN '재직'
                    ELSE '퇴직'
                END AS '재직여부'
            FROM TB_employee e
            LEFT JOIN TB_employee_leave_history lh ON e.employee_id = lh.employee_id
            WHERE e.is_active = 1 
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

    def default_setting_vacation(self):
        self.gb_vac.setChecked(False)
        self.cmb_vac.addItems(['연차', '반반차'])
        self.start_date.setDate(QDate.currentDate())
        self.end_date.setDate(QDate.currentDate())


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
                    e.employee_id as '사원번호',
                    e.name AS '이름',
                    (SELECT team_name FROM TB_team t WHERE t.team_id = e.team_id) AS '팀명',
                    e.email,
                    e.phone,
                    e.hire_date AS '입사일자',
                    e.annual_leave_allocated as '연차수',
                    e.annual_leave_allocated - COALESCE(SUM(lh.leave_amount), 0) AS 사용가능연차,
                    CASE 
                        WHEN e.is_active = 1 THEN '재직'
                        ELSE '퇴직'
                    END AS '재직여부'
                FROM TB_employee e
                LEFT JOIN TB_employee_leave_history lh ON e.employee_id = lh.employee_id
                WHERE e.is_active = {is_active_value} AND
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
                    e.employee_id as '사원번호',
                    e.name AS '이름',
                    (SELECT team_name FROM TB_team t WHERE t.team_id = e.team_id) AS '팀명',
                    e.email,
                    e.phone,
                    e.hire_date AS '입사일자',
                    e.annual_leave_allocated as '연차수',
                    e.annual_leave_allocated - COALESCE(SUM(lh.leave_amount), 0) AS 사용가능연차,
                    CASE 
                        WHEN e.is_active = 1 THEN '재직'
                        ELSE '퇴직'
                    END AS '재직여부'
                FROM TB_employee e
                LEFT JOIN TB_employee_leave_history lh ON e.employee_id = lh.employee_id
                WHERE e.is_active = {is_active_value} AND
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


    # region [휴가 등록]
    def add_vaction(self):
        vac_insert_sql = f'''
        INSERT INTO TB_employee_leave_history (employee_id, leave_start_date, leave_end_date, leave_amount, remarks)
        VALUES ({self.label_8.text().split("_")[0]}, 
        date('{self.start_date.date().toString("yyyy-MM-dd")}'), date('{self.end_date.date().toString("yyyy-MM-dd")}'), 
        {self.txt_vac.text()}, '{self.txt_vacComment.text()}')
        '''
        print (vac_insert_sql)
        try:
            self.db1.execute_query(vac_insert_sql)
            # commit이 필요한 경우 (자동 커밋이 아니라면)
            self.db1.connection.commit()  # 또는 self.db1.commit() 이라 할 수도 있음.
            print("연차 기록이 추가되었습니다.")
            self.table_setting()
        except Exception as e:
            print("DB 삽입 중 오류 발생:", str(e))
            

    # endregion