import streamlit as st
import pandas as pd
import struct

# --- 데이터 처리 로직 ---
def parse_ble_packet(hex_str):
    try:
        # 공백 제거 및 바이트 변환
        hex_str = hex_str.replace(" ", "").replace("\n", "")
        data = bytes.fromhex(hex_str)
        
        # 1. 모델 맵핑 테이블 (그림 2 참조)
        model_map = {
            10: "ARX.AT115", 11: "ARX.AT116", 20: "ARX.AT125", 21: "ARX.AT126",
            30: "ARX.AT145", 31: "ARX.AT146", 40: "ARX.AT185", 41: "ARX.AT186",
            50: "ARX.AT205", 60: "ARX.AT435", 61: "ARX.AT436", 70: "ARX.AT445", 71: "ARX.AT446"
        }

        # 2. Value 변환 함수 (리틀 엔디안 4바이트 Signed Int -> /100)
        def convert_signed_value(b_slice):
            if len(b_slice) < 4: return "-"
            # < : Little Endian, i : Signed Int (4 bytes)
            val = struct.unpack('<i', b_slice)[0]
            return f"{val / 100:.2f}"

        results = []

        # 3. 파싱 스펙 정의 (항목 이름, 시작 바이트, 끝 바이트, 변환 로직)
        specs = [
            ("Length", 3, 4, lambda b: f"{b[0]}"),
            ("Manufacture ID", 4, 5, lambda b: f"0x{b[0]:02X}"),
            ("Company ID", 5, 7, lambda b: f"0x{b.hex().upper()}"),
            ("Struct Ver", 7, 8, lambda b: f"{b[0]}"),
            ("Model Number", 8, 9, lambda b: model_map.get(b[0], f"Unknown({b[0]})")),
            ("Error Code", 9, 10, lambda b: f"{b[0]}"),
            ("Error Info", 10, 11, lambda b: f"{b[0]}"),
            ("MCU Temp", 11, 12, lambda b: f"{int(b[0])} °C"),
            ("Battery", 12, 13, lambda b: f"{int(b[0])} %"),
            ("Value Mask", 13, 14, lambda b: f"MSB {bin(b[0])[2:].zfill(8)} LSB"),
            ("Value 1", 14, 18, convert_signed_value),
            ("Value 2", 18, 22, convert_signed_value),
            ("Value 3", 22, 26, convert_signed_value),
            ("Value 4", 26, 30, convert_signed_value),
            ("Value 5", 30, 34, convert_signed_value),
            ("Value 6", 34, 38, convert_signed_value),
        ]

        for name, start, end, conv_func in specs:
            if len(data) >= end:
                byte_slice = data[start:end]
                hex_val = byte_slice.hex().upper()
                conv_val = conv_func(byte_slice)
                results.append({"항목": name, "값(Hex)": hex_val, "변환값": conv_val})
            else:
                results.append({"항목": name, "값(Hex)": "-", "변환값": "Data Too Short"})

        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"데이터 형식이 올바르지 않습니다: {e}")
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="BLE Analyzer", layout="centered")

st.title("📡 BLE Advertisement Packet Analyzer")
st.caption("그림 1, 2의 데이터 변환 규칙이 적용된 분석기입니다.")

# 데이터 입력창
raw_input = st.text_area("BLE Raw Hex String 입력", 
                         placeholder="예: 0201061AFF4C00...",
                         height=150)

if raw_input:
    df = parse_ble_packet(raw_input)
    
    if df is not None:
        st.subheader("📊 분석 데이터 표")
        # 깔끔한 표 출력을 위해 index는 숨깁니다.
        st.table(df)
        
        # 간단한 요약 정보
        st.success(f"총 {len(raw_input.replace(' ',''))//2} 바이트 패킷 분석 완료")
