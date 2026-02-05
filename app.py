import streamlit as st
import pandas as pd
import struct

def parse_ble_packet(hex_str):
    try:
        clean_hex = hex_str.lower().replace("0x", "").replace(" ", "").replace("\n", "")
        data = bytes.fromhex(clean_hex)
        
        model_info = {
            0x10: ("ARX.AT115", "mmH2O"), 0x11: ("ARX.AT116", "mmH2O"),
            0x20: ("ARX.AT125", "mmH2O"), 0x21: ("ARX.AT126", "mmH2O"),
            0x30: ("ARX.AT145", "Bar"), 0x31: ("ARX.AT146", "Bar"),
            0x40: ("ARX.AT185", "mmH2O"), 0x41: ("ARX.AT186", "mmH2O"),
            0x50: ("ARX.AT205", "℃"), 0x51: ("ARX.AT206", "℃"),
            0x60: ("ARX.AT435", "m/s2"), 0x61: ("ARX.AT436", "m/s2"),
            0x70: ("ARX.AT445", "mm/s"), 0x71: ("ARX.AT446", "mm/s")
        }

        model_byte = data[5] if len(data) > 5 else 0x00
        m_name, m_unit = model_info.get(model_byte, (f"Unknown(0x{model_byte:02X})", ""))
        mask_byte = data[10] if len(data) > 10 else 0x00
        mask_str = bin(mask_byte & 0x3F)[2:].zfill(6)

        def convert_signed_value(b_slice, v_idx):
            if len(b_slice) < 4: return "-"
            val = struct.unpack('<i', b_slice)[0]
            base_val = f"{val / 100:.2f}"
            if mask_str[-v_idx] == '1':
                return f"{base_val} {m_unit}"
            return base_val

        results = []
        specs = [
            ("length", 0, 1, lambda b: f"{int(b[0])}"),
            ("manufacture", 1, 2, lambda b: f"{b.hex().upper()} (hex)"),
            ("company", 2, 4, lambda b: f"{b.hex().upper()} (hex)"),
            ("struct ver", 4, 5, lambda b: f"{b.hex().upper()} (hex)"),
            ("model", 5, 6, lambda b: m_name),
            ("error", 6, 7, lambda b: f"{b.hex().upper()} (hex)"),
            ("error info", 7, 8, lambda b: f"{b.hex().upper()} (hex)"),
            ("mcu temp", 8, 9, lambda b: f"{int(b[0])} °C"),
            ("battery", 9, 10, lambda b: f"{int(b[0])} %"),
            ("value mask", 10, 11, lambda b: mask_str), 
            ("value 1", 11, 15, lambda b: convert_signed_value(b, 1)),
            ("value 2", 15, 19, lambda b: convert_signed_value(b, 2)),
            ("value 3", 19, 23, lambda b: convert_signed_value(b, 3)),
            ("value 4", 23, 27, lambda b: convert_signed_value(b, 4)),
            ("value 5", 27, 31, lambda b: convert_signed_value(b, 5)),
            ("value 6", 31, 35, lambda b: convert_signed_value(b, 6)),
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

        def apply_styles(row):
            styles = [''] * len(row)
            name = row['항목']
            raw_val = row['Raw 값']
            is_bold = False
            if name in ['model', 'battery']:
                is_bold = True
            elif name.startswith('value '):
                try:
                    v_num = int(name.split(' ')[1])
                    if mask_str[-v_num] == '1': is_bold = True
                except: pass

            if is_bold:
                styles = ['font-weight: 900; background-color: #f9f9f9;'] * len(row)
            if name == 'error' and raw_val != "0x00":
                styles[2] = (styles[2] if is_bold else '') + ' color: red; font-weight: 900;'
            return styles

        styled = df.style.apply(apply_styles, axis=1).hide(axis='index')
        
        # 표 스타일 설정 (선 색상: 짙은 회색 #666666, 높이 30% 증가)
        header_css = [
            {'selector': 'th', 'props': [
                ('background-color', 'black'), ('color', 'white'), 
                ('font-weight', 'bold'), ('text-align', 'center'), 
                ('border', '0.5px solid #666666'), ('padding', '12px 15px')
            ]},
            {'selector': 'td', 'props': [
                ('border', '0.5px solid #666666'), 
                ('padding', '12px 15px'),  # 행 높이를 위해 상하 패딩 증가
                ('font-size', '14px')
            ]}
        ]
        styled.set_table_styles(header_css)
        
        return styled

    except Exception as e:
        st.error(f"분석 중 오류 발생: {e}")
        return None

# --- UI ---
st.set_page_config(page_title="BLE Analyzer", layout="wide")
st.title("📡 BLE Raw Packet Analyzer")

raw_input = st.text_input("Raw 패킷 입력 (0x...)", placeholder="0x010203...")

if raw_input:
    styled_df = parse_ble_packet(raw_input)
    if styled_df is not None:
        st.markdown("### 📊 분석 결과")
        # HTML 렌더링 시 테두리 붕괴 방지 스타일 추가
        table_html = styled_df.to_html()
        st.markdown(
            f'<style>table {{ border-collapse: collapse; width: 100%; }}</style>{table_html}', 
            unsafe_allow_html=True
        )
