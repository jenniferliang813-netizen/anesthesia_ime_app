import streamlit as st
import pandas as pd

# 1. 建立基礎藥物資料庫 [cite: 880]
drug_table = {
    "IV morphine (mg)": {"p": 1.0, "t_half": 120},
    "Fentanyl (mcg)": {"p": 0.1, "t_half": 45},
    "Alfentanil (mcg)": {"p": 0.015, "t_half": 15},
    "Remifentanil (mcg)": {"p": 0.1, "t_half": 4},
    "Spinal morphine (mg)": {"p": 100.0, "t_half": 999999} # 恆定背景 [cite: 880]
}

st.title("麻醉嗎啡當量 (IME) 自動化追蹤系統")

# 2. 側邊欄：病人與手術基本資訊 [cite: 877-878]
with st.sidebar:
    st.header("基本設定")
    weight = st.number_input("病人體重 (kg)", min_value=1.0, value=60.0)
    total_surgery_time = st.number_input("目前手術已開始幾分鐘？", min_value=0, value=120)
    st.info(f"系統將自動產生 0 至 {total_surgery_time} 分鐘的追蹤報表")

# 3. 給藥紀錄區：支援多種藥物複選與多次給藥
st.header("💉 新增給藥事件")
if 'med_logs' not in st.session_state:
    st.session_state.med_logs = []

# 輸入介面
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    selected_drug = st.selectbox("選擇藥物", list(drug_table.keys()))
with c2:
    input_dose = st.number_input("劑量", min_value=0.0, key="dose_input")
with c3:
    input_time = st.number_input("麻醉開始後幾分鐘給藥？", min_value=0, key="time_input")

if st.button("➕ 新增此筆紀錄"):
    st.session_state.med_logs.append({
        "name": selected_drug,
        "dose": input_dose,
        "time": input_time
    })

# 顯示目前已輸入的清單
if st.session_state.med_logs:
    st.subheader("📋 目前給藥清單")
    df_logs = pd.DataFrame(st.session_state.med_logs)
    st.table(df_logs)
    if st.button("🗑️ 清除所有紀錄"):
        st.session_state.med_logs = []
        st.rerun()

# 4. 自動化計算邏輯：每半小時統計一次 
def get_status(ime_kg):
    """根據當量返回分級與顏色 """
    if ime_kg < 0.15: return "🟢 綠區", "low"
    if 0.15 <= ime_kg <= 0.3: return "🟡 黃區", "mid"
    return "🔴 紅區", "high"

if st.session_state.med_logs:
    st.header("📊 每 30 分鐘追蹤報表")
    
    report_data = []
    # 使用 range(開始, 結束, 間隔) 
    for t_now in range(0, total_surgery_time + 1, 30):
        current_total_ime = 0
        for log in st.session_state.med_logs:
            p = drug_table[log['name']]['p']
            t_half = drug_table[log['name']]['t_half']
            dt = t_now - log['time']
            
            if dt >= 0: # 只有在給藥時間之後才計算殘留
                # 公式實作 
                residual = (log['dose'] * p) * (0.5 ** (dt / t_half))
                current_total_ime += residual
        
        ime_kg = current_total_ime / weight
        status, level = get_status(ime_kg)
        report_data.append({
            "時間 (min)": t_now,
            "總殘留當量 (mg)": round(current_total_ime, 2),
            "當量/體重 (mg/kg)": round(ime_kg, 3),
            "風險分級": status
        })

    st.table(pd.DataFrame(report_data))

    # 5. 臨床意義提醒 [cite: 886, 900-901]
    last_ime = report_data[-1]["當量/體重 (mg/kg)"]
    if last_ime > 0.3:
        st.error(f"⚠️ 警示：當前紅區數值 ({last_ime}) 可能增加 OIH 風險與延遲甦醒。 [cite: 900, 901]")
    elif last_ime < 0.15:
        st.success("✅ 目前處於綠區，符合 ERAS 精神。 [cite: 886]")
