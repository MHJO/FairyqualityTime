# 설정 및 API 키 관리
import configparser
import os


class G2BSettings:
    """
    나라장터 API 설정 관리

    담당 기능
    - config.ini 읽기
    - 설정값 조회
    - API 키 저장 및 변경
    - API 키 삭제
    """

    def __init__(self, config_path):
        self.config_path = os.path.abspath(config_path)

        self.config = configparser.ConfigParser(interpolation=None)
        self.load()

    def load(self):
        """설정 파일 읽기"""

        self.config = configparser.ConfigParser(interpolation=None)

        if os.path.exists(self.config_path):
            self.config.read(
                self.config_path,
                encoding="utf-8"
            )

    def save(self):
        """설정 파일 저장"""

        directory = os.path.dirname(self.config_path)

        os.makedirs(directory, exist_ok=True)

        # 임시 파일에 먼저 저장한 후 교체
        temp_path = self.config_path + ".tmp"

        with open(temp_path, "w", encoding="utf-8") as file:
            self.config.write(file)

        os.replace(temp_path, self.config_path)

    def get(self, section, option, fallback=None):
        """일반 설정값 조회"""

        return self.config.get(
            section,
            option,
            fallback=fallback
        )

    def set(self, section, option, value):
        """일반 설정값 저장"""

        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(
            section,
            option,
            str(value)
        )

        self.save()

    # ---------------------------------
    # 나라장터 API 키 관리
    # ---------------------------------

    def get_api_key(self):
        """API 키 조회"""

        return self.get(
            "datagov",
            "apikey",
            fallback=""
        ).strip()

    def save_api_key(self, api_key):
        """API 키 저장 및 변경"""

        api_key = api_key.strip()

        if not api_key:
            raise ValueError("API 키를 입력해 주세요.")

        self.set(
            "datagov",
            "apikey",
            api_key
        )

    def delete_api_key(self):
        """API 키 삭제"""

        self.set(
            "datagov",
            "apikey",
            ""
        )

    def has_api_key(self):
        """API 키 등록 여부 확인"""

        return bool(self.get_api_key())