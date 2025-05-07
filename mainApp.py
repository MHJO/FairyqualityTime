import os, sys
from PyQt5.QtWidgets import QApplication
from main import main
from modules import Login

def mainApp():
    app = QApplication(sys.argv)

    win_login = Login.Login()
    win_login.login_success_signal.connect(lambda status: open_main(win_login, status))  # Signal 연결

    win_login.show()
    app.exec_()  # 여기서 한 번만 호출

def open_main(win_login, status):
    print("여기??", status)  # 로그인 여부 즉시 확인
    
    if status:
        win_login.close()
        # main_window = main()
        # main_window.setParent(None)  # 부모 없이 독립 실행
        # main_window.show()
        main.show()

    else:
        print("로그인 실패!")

if __name__ == "__main__":
    sys.path.append(os.getcwd().replace('\\', '/'))
    mainApp()