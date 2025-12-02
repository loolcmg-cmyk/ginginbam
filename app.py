import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- [설정] 구글 시트 연결 ---
# 주의: secrets.json 파일이 같은 폴더에 있어야 합니다.
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open("ginginbam_db").sheet1  # 시트 이름이 정확해야 함
except Exception as e:
    st.error(f"⚠️ 구글 시트 연결 실패! secrets.json 파일과 시트 공유를 확인하세요.\n에러내용: {e}")
    st.stop()

def load_data():
    """구글 시트에서 데이터 가져오기"""
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_data(df):
    """구글 시트에 데이터 덮어쓰기 (업데이트)"""
    # 헤더와 데이터를 리스트 형태로 변환하여 업로드
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- [앱 시작] ---
st.set_page_config(page_title="긴긴밤 독서모임 (DB연동)", page_icon="🌙", layout="wide")
st.title("🌙 독서모임 '긴긴밤' 시스템 (Online DB)")

# 데이터 불러오기
if 'df' not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# --- [함수] 비즈니스 로직 ---
def add_coin(name, amount, reason):
    """코인 변경 및 자동 저장"""
    idx = df[df['이름'] == name].index[0]
    
    # 값 변경
    current_coin = df.at[idx, '코인']
    new_coin = current_coin + amount
    df.at[idx, '코인'] = new_coin
    
    # 멤버십 상태 업데이트
    if new_coin <= 20 and df.at[idx, '역할'] != '코어그룹':
        df.at[idx, '멤버십상태'] = '경고(위험)'
    else:
        df.at[idx, '멤버십상태'] = '유지'
        
    # [핵심] 변경된 데이터를 즉시 구글 시트에 저장!
    save_data(df)
    
    st.toast(f"✅ {name}: {amount}코인 {reason} (저장 완료!)")

# --- [UI] 화면 구성 ---
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
    score = st.number_input("조정할 코인 (예: +5, -10)", step=1, value=0)
    reason = st.text_input("사유 (예: 1월 정기모임 참석)")
    
    if st.button("코인 반영 및 저장"):
        add_coin(target, score, reason)
        st.success("구글 시트에 저장되었습니다!")
        st.rerun()