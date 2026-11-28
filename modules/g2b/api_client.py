# 공공데이터 API 통신
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote

class G2BApiClient:
    """
    나라장터 공공데이터 API 통신 담당
    """

    def __init__(self, base_url, service_key, timeout=30):
        self.base_url = base_url.rstrip("/") + "/"
        self.service_key = service_key
        self.timeout = timeout

        self.session = requests.Session()

    def request_xml(self, service_path, operation, params=None):
        """
        나라장터 API 요청 및 XML 응답 반환

        Args:
            service_path (str): API 서비스 경로
            operation (str): API 오퍼레이션명
            params (dict): 조회 조건

        Returns:
            xml.etree.ElementTree.Element: XML Root
        """

        url = f"{self.base_url}{service_path}/{operation}"

        request_params = {
            "ServiceKey": unquote(self.service_key),
            "type": "xml"
        }

        if params:
            request_params.update(params)

        try:
            response = self.session.get(
                url,
                params=request_params,
                timeout=self.timeout
            )

            response.raise_for_status()

            return ET.fromstring(response.content)

        except requests.RequestException as e:
            raise RuntimeError(
                f"나라장터 API 통신 오류: {e}"
            ) from e

        except ET.ParseError as e:
            raise RuntimeError(
                f"나라장터 API 응답 XML 파싱 오류: {e}"
            ) from e

    def close(self):
        """HTTP 세션 종료"""
        self.session.close()