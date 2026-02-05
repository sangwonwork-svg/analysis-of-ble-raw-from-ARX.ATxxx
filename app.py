import streamlit as st
import pandas as pd
import struct

def parse_ble_packet(hex_str):
    try:
        # '0x' 제거 및 공백/줄바꿈 정리
        clean_hex = hex_str.lower().replace("0x", "").replace(" ", "").replace("\n", "")
        data = bytes.fromhex(clean_hex)
        
        # 모델 맵핑 테이블 (0x10 -> 10으로 매핑하기 위해 16진수 형태 사용)
        # 패킷의 바이트 값을 그대로 16진수 정수로 비교합니다.
        model_map = {
            0x10: "ARX.AT115", 0x11: "ARX.AT116", 0x20: "ARX.AT125", 0x21: "ARX.AT126",
            0x30: "ARX.AT145", 0x31: "ARX.AT146", 0x40: "ARX.AT185", 0x41: "ARX.AT186",
            0x50: "ARX.AT205", 0x60: "ARX.AT435", 0x61: "ARX.AT436", 0x70: "ARX.AT445", 0x71: "ARX.AT446"
        }

        def convert_signed_value(b_slice):
            if len(b_slice) < 4: return "-"
            # 리틀엔디안(<) 4바이트 부호정수(i) 변환 후 100으로 나눔
            val = struct.unpack('<i', b_slice)[0]
            return f"{val / 100:.2f}"

        results = []

        # 바이트 순서 (표 기준: 1번 바이트 시작 -> 인덱스는 0부터)
        specs = [
            ("length", 0, 1, lambda b: "-"),
            ("manufacture", 1, 2, lambda b: "-"),
            ("company", 2, 4, lambda b: "-"),
            ("struct ver", 4, 5, lambda b: "-"),
            ("model", 5, 6, lambda b: model_map.get(b[0], f"Unknown(0x{b[0]:02X})")),
            ("error", 6, 7, lambda b: "-"),
            ("error info", 7, 8, lambda b: "-"),
            ("mcu temp", 8, 9, lambda b: f"{int(b[0])} °C"),
            ("battery", 9, 10, lambda b: f"{int(b[0])} %"),
            ("value mask", 10, 11, lambda b: bin(b[0] & 0x3F)[2:].zfill(6)), 
            ("value 1", 11, 15, convert_signed_value),
            ("value 2", 15, 19, convert_signed_value),
            ("value 3", 19, 23, convert_signed_value),
            ("value 4", 23, 27, convert_signed_value),
            ("value 5", 27, 31, convert_signed_value),
            ("value 6", 31, 35, convert_signed_value),
        ]

        for name, start, end, conv_func in specs:
            if len(data) >= end:
                byte_slice = data[start:end]
                hex_val = byte_slice.hex().upper()
                conv_val = conv_func(byte_slice)
                results.append({"항목": name, "값": f"0x{hex_val}", "변환값": conv_val})
            else:
                results.append({"항목": name, "값": "-", "변환값": "데이터 부족"})

        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# --- UI ---
st.set_page_config(page_title="BLE Analyzer", layout="centered")
st.title("📡 BLE Raw Packet Analyzer")
st.info("입력된 패킷의 6번째 바이트(Model)를 Hex 값 그대로 읽어 모델명을 매칭합니다.")

raw_input = st.text_input("Raw 패킷 입력 (0x...)", placeholder="0x010203040510...")

if raw_input:
    df = parse_ble_packet(raw_input)
    if df is not None:
        st.table(df)
