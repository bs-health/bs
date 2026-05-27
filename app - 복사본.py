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
    div[data-testid=\"stMetricValue\"] { font-size: 28px; font-weight: 900; color: #0f172a; }\r
    .stAlert { border-radius: 16px; }\r
    .custom-card {\r
        background-color: #ffffff; padding: 20px; border-radius: 16px;\r
        border: 1px solid #e2e8f0; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); margin-bottom: 20px;\r
    }\r
    table { font-size: 14px !important; }\r
    .stButton>button { border-radius: 8px; }\r
    .status-box { padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 14px; }\r
    .done-box { background-color: #f0fdf4; border-left: 5px solid #16a34a; color: #14532d; }\r
    .missing-box { background-color: #fef2f2; border-left: 5px solid #dc2626; color: #7f1d1d; }\r
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 불러오기 및 퍼지 매칭 처리 (오타 해결)
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    # 1) 기준 DB (DB.csv) 로드
    df_db = pd.read_csv('DB.csv')
    df_db['현장명_정형'] = df_db['현장명'].str.strip()
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
        # 대소문자 구별 없고 공백/특수문자 정형화 후 유사도 비교 (fuzz.WRatio)
        res = process.extractOne(raw_name, official_sites, scorer=fuzz.WRatio, processor=utils.default_process)
        if res:
            best_match, score, _ = res
            if score >= 70:  # 유사도가 70점 이상이면 오타로 인정하고 정식 명칭 반환
                return best_match
        return raw_name  # 매칭 실패 시 원래 이름 유지

    df_data['정식매칭현장명'] = df_data['제출현장명'].apply(match_site)

    # 4) 오늘 날짜 데이터 필터링 (UTC -> KST 고려)
    kst = timezone(timedelta(hours=9))
    today_str = datetime.now(kst).strftime('%Y-%m-%d')
    
    # '제출일자' 또는 '응답일시' 기준 오늘 데이터만 추출
    df_data['clean_date'] = df_data['제출일자'].astype(str).str.strip()
    df_today_submissions = df_data[df_data['clean_date'] == today_str]

    # 5) 기준 DB에 오늘 제출 여부 결합
    submitted_official_names = df_today_submissions['정식매칭현장명'].unique()
    df_db['제출여부'] = df_db['현장명_정형'].isin(submitted_official_names).map({True: '실시', False: '미실시'})
    
    return df_db, df_today_submissions

df_db, df_today = load_data()

# ==========================================
# 3. 대시보드 UI 그리기 (기존 로직 유지)
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
        submitted = df_team[df_db['제출여부'] == '실시']
        missing = df_team[df_db['제출여부'] == '미실시']
        
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
                    st.markdown(f"<div class='status-box missing-box'><b>{site}</b></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 13px; color: #16a34a; text-align: center; padding: 10px;'>전원 제출 완료 🎉</div>", unsafe_allow_html=True)
        
        with st.expander(f"✅ 실시 완료 ({len(submitted)}곳)", expanded=False):
            if not submitted.empty:
                for site in submitted['현장명'].tolist():
                    st.markdown(f"<div class='status-box done-box'><b>{site}</b></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 13px; color: #64748b; text-align: center; padding: 10px;'>아직 제출된 현장이 없습니다.</div>", unsafe_allow_html=True)