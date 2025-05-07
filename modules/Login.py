import os, sys
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtCore import pyqtSignal

class Login(QWidget):
    login_success_signal = pyqtSignal(bool)  # 로그인 성공 여부를 전달하는 Signal 생성
    
    def __init__(self, parent=None):
        super().__init__()
        uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '.ui'), self)

        self.is_Login = False

        self.initUi()
        self.init()
        self.listener()

    def initUi(self):
        self.txtAccount.setEnabled(False)
        self.txtPwd.setEnabled(False)
    
    def init(self):
        self.txtAccount.setText("admin")
        self.txtPwd.setText("admin")

    def listener(self):
        self.btnLogin.clicked.connect(self.login)

    def login(self):
        if self.txtAccount.text() == "admin" and self.txtPwd.text() == "admin":
            QMessageBox.information(self, "알림", "로그인 성공!")
            self.is_Login = True
        else:
            QMessageBox.warning(self, "알림", "로그인 실패!")
            self.is_Login = False
        
        self.login_success_signal.emit(self.is_Login)  # Signal emit