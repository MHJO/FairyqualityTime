import os, sys
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QMessageBox

from modules.SQLiteSingleton import SQLiteSingleton

db1 = SQLiteSingleton(r'D:\iway\source_code\FairyqualityTime\Database\company.db')

class Login(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Login.ui 파일 경로에 맞춰 UI 로드. 파일명은 Login.ui라고 가정합니다.
        uic.loadUi(os.path.join(os.getcwd(), "ui", "Login.ui"), self)
        self.is_Login = False

        self.initUi()
        self.init()
        self.listener()

    def initUi(self):
        # 원래 비활성화되어 있던 부분을 활성화시키거나 적절하게 설정
        self.txtAccount.setEnabled(True)
        self.txtPwd.setEnabled(True)
    
    def init(self):
        # 테스트용 기본 계정 설정
        self.txtAccount.setText("admin@i-way.co.kr")
        self.txtPwd.setText("23001")

    def listener(self):
        self.btnLogin.clicked.connect(self.handle_login)

    def handle_login(self):
        count_sql = f'''
            select count(*)
            FROM TB_employee te
            WHERE te.email = '{self.txtAccount.text()}' and te.employee_id ={self.txtPwd.text()}
            '''
        result = db1.execute_query(count_sql)
        count_value = result[0][0] if result else 0
        
        if count_value == 1:
            QMessageBox.information(self, "알림", "로그인 성공!")
            self.is_Login = True
            self.accept()  # QDialog.Accepted를 반환하며 다이얼로그를 닫음
        else:
            self.is_Login = False
            QMessageBox.warning(self, "경고", "아이디 또는 비밀번호가 일치하지 않습니다.")
