import os, sys
from datetime import datetime
import configparser

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow,QApplication, QMessageBox, QDialog
from PyQt5.QtCore import QTimer



from modules.g2b_api import g2b_api
from modules.employeeInfo import employeeInfo
from modules.Manage_vaction import Manage_vaction


properies = configparser.ConfigParser(interpolation=None)
configPath =rf"{os.getcwd()}\config.ini"
properies.read(configPath, encoding='utf-8')

user = properies['user']


class main(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(os.getcwd()+"/ui", os.path.splitext(os.path.basename(__file__))[0] + '.ui'), self)

        self.init_ui()
        self.listener()

    def init_ui(self):
        # self.setWindowTitle(f"도우미 요정 - {user['id']} ") # 계정 생기면 작동
        self.setWindowTitle(f"업무 도우미") # 계정 생기면 작동

        # self.statusbar.showMessage(str(datetime.today().strftime("%Y-%m-%d")))
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.timeout)
      
        # login = self.default_login()
       
        
    def listener(self):
        self.action1.triggered.connect(self.load_g2b)
        self.action2.triggered.connect(self.load_employeeInfo)
        self.action3.triggered.connect(self.load_vacation)
        self.btn_1.clicked.connect(self.load_g2b)
        self.btn_2.clicked.connect(self.load_employeeInfo)
        self.btn_3.clicked.connect(self.load_vacation)
        self.btn_4.clicked.connect(self.new_employee)
        

    def timeout(self):
        current_time = datetime.now()
        # text_time = current_time.toString("hh:mm:ss")
        text_time = current_time.strftime("%H:%M:%S")
        time_msg = "현재시간 : " + text_time

        self.statusbar.showMessage(time_msg)


    # region [g2b 불러오기]
    def load_g2b(self):
        self.clear_frame()
        g2b_dialog = g2b_api(self.frame)  # 부모를 QFrame으로 설정
        # g2b_dialog.setGeometry(0, 0, self.frame.width(), self.frame.height())  # QFrame 크기 맞춤
        g2b_dialog.setGeometry(0, 0, 608, 290)  
        g2b_dialog.setParent(self.frame)  # QFrame 내부에 직접 추가
        g2b_dialog.show()

    # endregion
    
    # region [신규등록]
    def new_employee(self):
        self.clear_frame()
    # endregion

    # region [사원조회]
    def load_employeeInfo(self):
        self.clear_frame()
        # QMessageBox.information(self, "알림","휴가장부 예정")
        employeeInfo_dialog = employeeInfo(self.frame)  # 부모를 QFrame으로 설정
        employeeInfo_dialog.setGeometry(0, 0, self.frame.width(), self.frame.height())  # QFrame 크기 맞춤
        
        employeeInfo_dialog.setParent(self.frame)  # QFrame 내부에 직접 추가
        employeeInfo_dialog.show()
    # endregion


    # region [휴가장부]
    def load_vacation(self):
        self.clear_frame()
        # QMessageBox.information(self, "알림","휴가장부 예정")
        employeeInfo_dialog = Manage_vaction(self.frame)  # 부모를 QFrame으로 설정
        employeeInfo_dialog.setGeometry(0, 0, self.frame.width(), self.frame.height())  # QFrame 크기 맞춤
        
        employeeInfo_dialog.setParent(self.frame)  # QFrame 내부에 직접 추가
        employeeInfo_dialog.show()
    # endregion

    # 로그인 창
    # def default_login(self):
    #     login_widget = Login(self.frame)
    #     login_widget.setGeometry(320, 210, self.frame.width(), self.frame.height())
    #     login_widget.setParent(self.frame)
    #     login_widget.login.connect(self.)
    #     login_widget.show()
    #     if :
    #         result = login_widget.login()
    #         if result == True:
    #             self.clear_frame()
    #             self.btn_1.show()
    #             self.btn_2.show()

            

    def clear_frame(self):
        # self.frame 내부의 모든 자식 위젯 삭제
        for child in self.frame.children():
            child.deleteLater()

    
    def closeEvent(self, QCloseEvent):
        re = QMessageBox.question(self, "종료 확인", "종료 하시겠습니까?",
                    QMessageBox.Yes|QMessageBox.No)

        if re == QMessageBox.Yes:
            QCloseEvent.accept()
        else:
            QCloseEvent.ignore()  

    


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = main()
    window.show()
    sys.exit(app.exec_())