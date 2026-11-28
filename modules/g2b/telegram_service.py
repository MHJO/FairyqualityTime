 # 텔레그램 알림
# modules/g2b/telegram_service.py

import os
import logging
import requests


class TelegramService:

    API_URL = "https://api.telegram.org"

    def __init__(self, bot_token, chat_id, timeout=30):
        self.bot_token = bot_token.strip()
        self.chat_id = str(chat_id).strip()
        self.timeout = timeout

        if not self.bot_token:
            raise ValueError("텔레그램 Bot Token이 설정되지 않았습니다.")

        if not self.chat_id:
            raise ValueError("텔레그램 Chat ID가 설정되지 않았습니다.")

        self.session = requests.Session()

    # ==================================================
    # 메시지 전송
    # ==================================================

    def send_message(self, message):

        url = f"{self.API_URL}/bot{self.bot_token}/sendMessage"

        try:
            response = self.session.post(
                url,
                data={
                    "chat_id": self.chat_id,
                    "text": message
                },
                timeout=self.timeout
            )

            response.raise_for_status()

            result = response.json()

            if not result.get("ok"):
                raise RuntimeError("텔레그램 메시지 전송에 실패했습니다.")

            logging.info("텔레그램 메시지 전송 완료")

            return True

        except Exception:
            logging.exception("텔레그램 메시지 전송 실패")
            return False

    # ==================================================
    # 파일 전송
    # ==================================================

    def send_document(self, file_path, caption=""):

        if not os.path.isfile(file_path):
            logging.error("텔레그램 전송 파일이 없습니다: %s", file_path)
            return False

        url = f"{self.API_URL}/bot{self.bot_token}/sendDocument"

        try:
            with open(file_path, "rb") as file:

                response = self.session.post(
                    url,
                    data={
                        "chat_id": self.chat_id,
                        "caption": caption
                    },
                    files={
                        "document": file
                    },
                    timeout=self.timeout
                )

            response.raise_for_status()

            result = response.json()

            if not result.get("ok"):
                raise RuntimeError("텔레그램 파일 전송에 실패했습니다.")

            logging.info(
                "텔레그램 파일 전송 완료: %s",
                os.path.basename(file_path)
            )

            return True

        except Exception:
            logging.exception("텔레그램 파일 전송 실패")
            return False

    # ==================================================
    # 연결 종료
    # ==================================================

    def close(self):
        self.session.close()