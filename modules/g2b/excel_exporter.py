# 엑셀 생성 및 저장
# modules/g2b/excel_exporter.py

import os
import logging
import pandas as pd

from datetime import datetime

from modules.g2b.database import Sqlite


class ExcelExporter:

    SHEET_NAMES = {
        "1": "입찰공고용역",
        "2": "사전규격",
        "3": "발주계획"
    }

    # ==================================================
    # 엑셀 파일 저장
    # ==================================================

    @staticmethod
    def export(save_path, type, statusType="A"):

        try:
            # ------------------------------------------
            # 1. 시트명 확인
            # ------------------------------------------

            sheet_name = ExcelExporter.SHEET_NAMES.get(type)

            if not sheet_name:
                raise ValueError(
                    f"잘못된 엑셀 출력 타입입니다: {type}"
                )

            # ------------------------------------------
            # 2. DB 데이터 조회
            # ------------------------------------------

            columns, rows = Sqlite.selectDB(
                type=type,
                statusType=statusType
            )

            # ------------------------------------------
            # 3. 데이터프레임 생성
            # ------------------------------------------

            df = pd.DataFrame(
                rows,
                columns=columns
            )

            # ------------------------------------------
            # 4. 저장 경로 설정
            # ------------------------------------------

            if not save_path:
                raise ValueError("엑셀 저장 경로가 없습니다.")

            os.makedirs(save_path, exist_ok=True)

            filename = datetime.now().strftime(
                "나라장터_%Y%m%d.xlsx"
            )

            file_path = os.path.join(
                save_path,
                filename
            )

            # ------------------------------------------
            # 5. 엑셀 저장
            # ------------------------------------------

            if os.path.exists(file_path):

                # 기존 파일의 다른 시트는 유지하고
                # 현재 시트만 교체
                with pd.ExcelWriter(
                    file_path,
                    engine="openpyxl",
                    mode="a",
                    if_sheet_exists="replace"
                ) as writer:

                    df.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )

            else:

                # 파일이 없으면 새로 생성
                with pd.ExcelWriter(
                    file_path,
                    engine="openpyxl",
                    mode="w"
                ) as writer:

                    df.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )

            logging.info(
                "엑셀 저장 완료: %s / 시트: %s / 데이터: %s건",
                file_path,
                sheet_name,
                len(df)
            )

            return file_path

        except Exception:
            logging.exception(
                "엑셀 저장 실패: type=%s",
                type
            )
            raise