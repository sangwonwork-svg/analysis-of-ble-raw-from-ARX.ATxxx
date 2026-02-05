import streamlit as st
import pandas as pd
import struct

def parse_ble_packet(hex_str):
    try:
        clean_hex = hex_str.lower().replace("0x", "").replace(" ", "").replace("\n", "")
        data = bytes.fromhex(clean_hex)
        
        model_map = {
            0x10: "ARX.AT115", 0x11: "ARX.AT116", 0x20: "ARX.AT125", 0x21: "ARX.AT126",
            0x30: "ARX.AT145", 0x31: "ARX.AT146", 0x40: "ARX.AT185", 0x41: "ARX.AT186",
            0x50: "ARX.AT205", 0x60: "ARX.AT435", 0x61: "ARX.AT436", 0x70: "ARX.AT445", 0x71: "ARX.AT446"
        }

        def convert_signed_value(b_slice):
            if len(b_slice) < 4: return "-"
            val = struct.unpack('<i', b_slice)[0]
            return f"{val / 100:.2f}"

        results = []
        specs = [
            ("length", 0, 1, lambda b: f"{int(b[0])}"),
            ("manufacture", 1, 2, lambda b: f"{b.hex().upper()} (hex)"),
            ("company", 2, 4, lambda b: f"{b.hex().upper()} (hex)"),
            ("struct ver", 4, 5, lambda b: f"{b.hex().upper()} (hex)"),
            ("model", 5, 6, lambda b: model_map.get(b[0], f"Unknown(0x{b[0]:02X})")),
            ("error", 6, 7, lambda b: f"{b.hex().upper()} (hex)"),
            ("error info", 7, 8, lambda b: f"{b.hex().upper()} (hex)"),
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
                hex_val = f"0x{byte_slice.hex().upper()}"
                conv_val = conv_func(byte_slice)
                results.append({"항목": name, "Raw 값": hex_val, "변환값": conv_val})
            else:
                results.append({"항목": name, "Raw 값": "-", "변환값": "데이터 부족"})

        df = pd.DataFrame(results)
        
        # 1. 스타일링 함수 (전체 행 대상)
        def style_rows(row):
            styles = [''] * len(row)
            name = row['항목']
            raw_val = row['Raw 값']
            
            # Value Mask 가져오기 (문자열 형태 예: "111111")
            mask_row = df[df['항목'] == 'value mask']
            mask_val = mask_row['변환값'].values[0] if not mask_row.empty else "000000"
            
            is_bold = False
            
            # (A) Model, Battery 무조건 Bold
            if name in ['model', 'battery']:
                is_bold = True
            
            # (B) Value Mask 기반 Bold (LSB부터 역순 확인)
            elif name.startswith('value '):
                try:
                    num = int(name.split(' ')[1]) # value 1 -> 1
                    # mask_val이 "000111"일 때 mask_val[-1]은 value 1
                    if mask_val[-num] == '1':
                        is_bold = True
                except: pass

            if is_bold:
                styles = ['font-weight: 900; background-color: #f0f2f6;'] * len(row)

            # (C) Error 빨간색 처리 (Bold 유지하면서 색상만 추가)
            if name == 'error' and raw_val != "0x00":
                styles[2] = (styles[2] if is_bold else '') + ' color: red; font-weight: 900;'
                
            return styles

        # 스타일 적용 및 좌측 인덱스 제거
        styled_df = df.style.apply(style_rows, axis=1).hide(axis='index')
        
        # 헤더 스타일 설정 (검은 배경, 흰 글씨)
        styled_df.set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', 'black'),
                ('color', 'white'),
                ('font-weight', 'bold'),
                ('text-align', 'center'),
                ('border', '1px solid white')
            ]},
            {'selector': 'td', 'props': [('border', '1px solid #dee2e6')]}
        ])
        
        return styled_df

    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# --- UI ---
st.set_page_config(page_title="BLE Analyzer", layout="wide")
st.title("📡 BLE Raw Packet Analyzer")

raw_input = st.text_input("Raw 패킷 입력 (0x...)", placeholder="0x010203040510...")

if raw_input:
    styled_df = parse_ble_packet(raw_input)
    if styled_df is not None:
        st.write("### 📊 분석 결과")
        # HTML로 렌더링하여 스타일 보장
        st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)
