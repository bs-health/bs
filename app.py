import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta, timezone
from rapidfuzz import process, fuzz, utils

# ==========================================
# 1. 페이지 기본 설정 및 프리미엄 화이트 테마 적용 
# ==========================================
st.set_page_config(
    page_title="백상가족 건강한 여름나기 종합 대시보드",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: 900; color: #0f172a; }
    .stAlert { border-radius: 16px; }
    .custom-card {
        background-color: #ffffff; padding: 20px; border-radius: 16px;
        border: 1px solid #e2e8f0; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); margin-bottom: 20px;
    }
    table { font-size: 14px !important; }
    .stButton>button { border-radius: 8px; width: 100%; }
    .status-box { padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 14px; }
    .done-box { background-color: #f0fdf4; border-left: 5px solid #16a34a; color: #14532d; }
    .missing-box { background-color: #fef2f2; border-left: 5px solid #dc2626; color: #7f1d1d; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 불러오기 및 퍼지 매칭 처리 (오타 해결)
# ==========================================
# 수동 변경 상태를 유지하기 위해 st.session_state와 연동하고 캐시 메커니즘을 조정합니다.
@st.cache_data(ttl=60)
def load_base_data():
    # 1) 기준 DB (DB.csv) 로드
    df_db = pd.read_csv('DB.csv')
    df_db['현장명_정형'] = df_db['현장명'].str.strip()
    return df_db

def load_data():
    df_db = load_base_data().copy()
    official_sites = df_db['현장명_정형'].tolist()

    # 2) 설문 결과 데이터 (data.csv) 로드
    try:
        df_data = pd.read_csv('data.csv')
    except Exception:
        df_data = pd.DataFrame(columns=['응답일시', '사업장 명을 알려주세요(*)', '오늘의 날짜를 입력해주세요(*)'])

    # 컬럼명 매핑 및 정형화
    df_data = df_data.rename(columns={
        '응답일시': '응답일시',
        '사업장 명을 알려주세요(*)': '제출현장명',
        '오늘의 날짜를 입력해주세요(*)': '제출일자'
    })
    df_data['제출현장명'] = df_data['제출현장명'].astype(str).str.strip()

    # 3) 퍼지 매칭으로 오타가 있는 제출현장명을 정식 현장명으로 변환
    def match_site(raw_name):
        if not raw_name or raw_name == 'nan':
            return None
        res = process.extractOne(raw_name, official_sites, scorer=fuzz.WRatio, processor=utils.default_process)
        if res:
            best_match, score, _ = res
            if score >= 70:  
                return best_match
        return raw_name  

    df_data['정식매칭현장명'] = df_data['제출현장명'].apply(match_site)

    # 4) 오늘 날짜 데이터 필터링 (UTC -> KST 고려)
    kst = timezone(timedelta(hours=9))
    today_str = datetime.now(kst).strftime('%Y-%m-%d')
    
    df_data['clean_date'] = df_data['제출일자'].astype(str).str.strip()
    df_today_submissions = df_data[df_data['clean_date'] == today_str]

    # 5) 기준 DB에 오늘 제출 여부 결합
    submitted_official_names = df_today_submissions['정식매칭현장명'].unique()
    df_db['제출여부'] = df_db['현장명_정형'].isin(submitted_official_names).map({True: '실시', False: '미실시'})
    
    return df_db, df_today_submissions

# 세션 상태 초기화 (수동 완결 처리된 현장 목록 저장용)
if 'manual_done_sites' not in st.session_state:
    st.session_state['manual_done_sites'] = set()

df_db, df_today = load_data()

# 수동으로 상태를 변경한 현장들을 '실시'로 덮어쓰기 적용
if st.session_state['manual_done_sites']:
    df_db.loc[df_db['현장명_정형'].isin(st.session_state['manual_done_sites']), '제출여부'] = '실시'


# ==========================================
# 3. 사이드바 - 관리자 전용 권한 제어 패널
# ==========================================
st.sidebar.title("🔐 관리자 시스템")
admin_password = st.sidebar.text_input("관리자 비밀번호 입력", type="password")

# 💡 원하시는 비밀번호로 변경하여 사용하세요!
CORRECT_PASSWORD = "1234"

is_admin = (admin_password == CORRECT_PASSWORD)

if admin_password:
    if is_admin:
        st.sidebar.success("🔑 관리자 인증 성공")
        st.sidebar.markdown("### 🛠️ 수동 점검 완료 처리")
        
        # 미실시인 현장만 추출하여 선택 박스 구성
        missing_options = df_db[df_db['제출여부'] == '미실시']['현장명_정형'].tolist()
        
        if missing_options:
            selected_site = st.sidebar.selectbox("실시로 변경할 현장 선택", missing_options)
            if st.sidebar.button("선택 현장 '실시'로 변경"):
                st.session_state['manual_done_sites'].add(selected_site)
                st.toast(f"📢 [{selected_site}] 현장이 수동 실시 처리되었습니다.", icon="✅")
                st.rerun()
        else:
            st.sidebar.info("모든 현장이 점검을 완료했습니다!")
            
        # 초기화 기능 추가
        if st.session_state['manual_done_sites']:
            st.sidebar.markdown("---")
            if st.sidebar.button("🔄 수동 변경 내역 전체 초기화"):
                st.session_state['manual_done_sites'].clear()
                st.toast("모든 수동 변경 내역이 초기화되었습니다.")
                st.rerun()
    else:
        st.sidebar.error("❌ 비밀번호가 일치하지 않습니다.")


# ==========================================
# 4. 대시보드 UI 그리기
# ==========================================
st.title("🌡️ 백상가족 건강한 여름나기 종합 대시보드")
st.caption(f"실시간 온열질환 예방점검 현황 (조회 기준일: {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')} KST)")
st.markdown("---")

# 상단 요약 지표
total_sites_count = len(df_db)
submitted_count = len(df_db[df_db['제출여부'] == '실시'])
missing_count = total_sites_count - submitted_count
overall_rate = int((submitted_count / total_sites_count) * 100) if total_sites_count > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("총 관리 대상 사업장", f"{total_sites_count}개소")
m2.metric("금일 점검 완료", f"{submitted_count}개소", delta=f"+{submitted_count}", delta_color="normal")
m3.metric("금일 미실시 현장", f"{missing_count}개소", delta=f"-{missing_count}", delta_color="inverse")
m4.metric("전체 제출률", f"{overall_rate}%")

st.markdown("### 📊 관리팀별 실시 현황")
teams = ['관리1팀', '관리2팀', '관리3팀', '영업2본부']
cols = st.columns(4)

for i, team in enumerate(teams):
    with cols[i]:
        df_team = df_db[df_db['관리팀'] == team]
        total_count = len(df_team)
        submitted = df_team[df_team['제출여부'] == '실시']  # 🐛 기존 코드의 df_db 검색 버그 수정 (df_team으로 변경)
        missing = df_team[df_team['제출여부'] == '미실시']     # 🐛 기존 코드의 df_db 검색 버그 수정 (df_team으로 변경)
        
        sub_count = len(submitted)
        rate = int((sub_count / total_count) * 100) if total_count > 0 else 0
        
        st.markdown(f"""
        <div class='custom-card'>
            <h3 style="margin: 0 0 10px 0; text-align: center;">{team}</h3>
            <div style="text-align: center; margin-bottom: 10px;">
                <span style="font-size: 32px; font-weight: bold; color: {'#22c55e' if rate == 100 else '#3b82f6'};">{rate}%</span>
                <div style="font-size: 13px; color: #64748b;">(제출 {sub_count} / 전체 {total_count})</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander(f"❌ 미실시 현장 ({len(missing)}곳)", expanded=True):
            if not missing.empty:
                for site in missing['현장명'].tolist():
                    # 수동 강제 변경본 표기 구분을 위해 CSS 분리 유지
                    st.markdown(f"<div class='status-box missing-box'><b>{site}</b></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 13px; color: #16a34a; text-align: center; padding: 10px;'>전원 제출 완료 🎉</div>", unsafe_allow_html=True)
        
        with st.expander(f"✅ 실시 완료 ({len(submitted)}곳)", expanded=False):
            if not submitted.empty:
                for site in submitted['현장명'].tolist():
                    # 수동 완결된 곳은 별도 표시 처리 추가
                    if site in st.session_state['manual_done_sites']:
                        st.markdown(f"<div class='status-box done-box'><b>{site} (수동완료)</b></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='status-box done-box'><b>{site}</b></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 13px; color: #64748b; text-align: center; padding: 10px;'>아직 제출된 현장이 없습니다.</div>", unsafe_allow_html=True)