import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# --- [설정] 구글 시트 연결 (하이브리드 방식) ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

try:
    # 1. 클라우드(Streamlit)에 암호가 있는지 확인
    if 'google_credentials' in st.secrets:
        # 비밀번호가 텍스트로 저장되어 있다면 JSON으로 변환
        creds_dict = json.loads(st.secrets['google_credentials'])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    # 2. 없으면 내 컴퓨터 파일(secrets.json) 찾기
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', SCOPE)
    
    client = gspread.authorize(creds)
    sheet = client.open("ginginbam_db").sheet1
except Exception as e:
    st.error(f"⚠️ 연결 실패! 에러 내용: {e}")
    st.stop()

def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_data(df):
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- [앱 시작] ---
st.set_page_config(page_title="긴긴밤 독서모임", page_icon="🌙", layout="wide")
st.title("🌙 독서모임 '긴긴밤' 시스템")

if 'df' not in st.session_state:
    st.session_state.df = load_data()
df = st.session_state.df

# --- [기능 로직] ---
def add_coin(name, amount, reason):
    idx = df[df['이름'] == name].index[0]
    df.at[idx, '코인'] += amount
    
    if df.at[idx, '코인'] <= 20 and df.at[idx, '역할'] != '코어그룹':
        df.at[idx, '멤버십상태'] = '경고(위험)'
    else:
        df.at[idx, '멤버십상태'] = '유지'
        
    save_data(df)
    st.toast(f"✅ {name}: {amount}코인 {reason} (저장 완료!)")

# --- [화면 구성] ---
tab1, tab2, tab3 = st.tabs(["👤 마이페이지", "📊 운영 현황", "⚙️ 관리자"])

with tab1:
    st.header("나의 활동 내역")
    user = st.selectbox("이름 선택", df['이름'])
    my_data = df[df['이름'] == user].iloc[0]
    col1, col2 = st.columns(2)
    col1.metric("보유 코인", f"{my_data['코인']} C")
    col2.metric("상태", my_data['멤버십상태'])
    if my_data['코인'] >= 30:
        if st.button("🎁 상품권 교환 신청 (-30)"):
            add_coin(user, -30, "상품권 교환")
            st.rerun()

with tab2:
    st.header("📊 실시간 코인 랭킹")
    st.dataframe(df[['이름', '코인', '멤버십상태']].sort_values('코인', ascending=False), hide_index=True)

with tab3:
    st.header("⚙️ 관리자 코인 지급")
    target = st.selectbox("대상", df['이름'], key='admin_target')
    score = st.number_input("조정할 코인", step=1, value=0)
    reason = st.text_input("사유")
    if st.button("코인 반영 및 저장"):
        add_coin(target, score, reason)
        st.success("구글 시트에 저장되었습니다!")
        st.rerun()