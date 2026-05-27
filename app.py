import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os  # 파일 저장 및 확인을 위해 추가
from datetime import datetime, timedelta, timezone

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
    .status-box { padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 13px; border: 1px solid #e2e8f0; text-align: left; }
    .missing-box { background-color: #ffffff; border: 1px solid #cbd5e1; color: #0f172a; font-weight: normal; }
    .done-box { background-color: #f0fdf4; border-left: 4px solid #22c55e; }
    
    /* 관리자 인증 시 클릭 가능한 미실시/실시 변경 버튼 스타일 커스텀 */
    div.stButton > button[key^="toggle_missing_"], div.stButton > button[key^="toggle_done_"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        text-align: left !important;
        padding: 8px 14px !important;
        font-weight: normal !important;
        margin-bottom: -4px !important;
        width: 100% !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }
    div.stButton > button[key^="toggle_missing_"]:hover {
        background-color: #f1f5f9 !important;
        border-color: #cbd5e1 !important;
    }
    div.stButton > button[key^="toggle_done_"]:hover {
        background-color: #fee2e2 !important;
        border-color: #fca5a5 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 💾 파일 입출력 헬퍼 함수 (영구 저장용)
DB_FILE = "manual_done_sites.txt"

def load_manual_sites():
    """파일에서 수동 완료 처리된 현장 목록을 불러옵니다."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set([line.strip() for line in f.readlines() if line.strip()])
    return set()

def save_manual_sites(sites_set):
    """수동 완료 처리된 현장 목록을 파일에 저장합니다."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        for site in sites_set:
            f.write(f"{site}\n")

# 세션 상태 초기화 (최초 로드 시 파일에서 데이터를 읽어옴)
if 'manual_done_sites' not in st.session_state:
    st.session_state['manual_done_sites'] = load_manual_sites()
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "📊 총괄 브리핑"
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'expanded_site' not in st.session_state:
    st.session_state.expanded_site = None

# ==========================================
# 2. 강력한 데이터 정제 및 유연한 컬럼 매핑 엔진 
# ==========================================

@st.cache_data(ttl=60)
def get_valid_db_names():
    try:
        db_df = pd.read_csv('DB.csv', encoding='cp949')
    except:
        try:
            db_df = pd.read_csv('DB.csv', encoding='utf-8')
        except:
            return []
            
    if '현장명' in db_df.columns:
        return db_df['현장명'].dropna().apply(standardize_site_name_base).unique().tolist()
    return []


def standardize_site_name_base(name):
    name = re.sub(r'[ㄱ-ㅎㅏ-ㅣ\s]', '', str(name))
    early_mapping = {
        '서울보증': '서울보증보험', '경주교원드림센터': '교원경주드림센터', '교원경주드림': '교원경주드림센터',
        '경주교원드림': '교원경주드림센터', '가든5툴': '가든파이브툴', '가든5툴백상코퍼레이션': '가든파이브툴',
        '가든파이툴': '가든파이브툴', '쿠팡경산1,2FC': '쿠팡경산1,2센터', '쿠팡경산1,2': '쿠팡경산1,2센터'
    }
    name = early_mapping.get(name, name)
    if name in ['교원경주드림센터', '서울보증보험', '가든파이브툴', '쿠팡경산1,2센터']: return name
    name = name.replace('현장', '').replace('지점', '').replace('샌타', '센터')
    name = re.sub(r'(?i)fc', '센터', name)
    name_mapping = {'성우프로젝트': '성우', '성우건설': '성우', '(주)성우': '성우'}
    return name_mapping.get(name, name)


def standardize_site_name(name, valid_db_names):
    name = standardize_site_name_base(name)
    if valid_db_names:
        for db_name in sorted(valid_db_names, key=len, reverse=True):
            if db_name in name: return db_name
    return name


valid_db_names_tuple = tuple(get_valid_db_names())

@st.cache_data(ttl=60)
def load_data(valid_db_names):
    try:
        df = pd.read_csv('data.csv', encoding='cp949')
    except:
        df = pd.read_csv('data.csv', encoding='utf-8')
    
    cols = df.columns.tolist()
    def find_col(keywords):
        for col in cols:
            if any(kw in col for kw in keywords): return col
        return None
        
    mapping = {}
    c_reporter = find_col(['참여자', '작성자'])
    if c_reporter: mapping[c_reporter] = '참여자'
    c_name = find_col(['사업장 명', '사업장명', '지점명'])
    if c_name: mapping[c_name] = '사업장명'
    c_date = find_col(['날짜'])
    if c_date: mapping[c_date] = '날짜'
    c_temp = find_col(['체감\'온도', '체감온도', '기온'])
    if c_temp: mapping[c_temp] = '체감온도'
    c_warn = find_col(['폭염 특보', '폭염특보'])
    if c_warn: mapping[c_warn] = '폭염특보여부'
    c_p1 = find_col(['예방조치', '1단계', '평상시조치'])
    if c_p1: mapping[c_p1] = '평상시조치'
    c_p2 = find_col(['35도이상', '2단계'])
    if c_p2: mapping[c_p2] = '35도이상조치'
    c_p3 = find_col(['38도이상', '3단계'])
    if c_p3: mapping[c_p3] = '38도이상조치'
    c_beverage = find_col(['음료', '깨끗한 물', '식수'])
    if c_beverage: mapping[c_beverage] = '음료제공방식'
    c_sensitive = find_col(['민감군'])
    if c_sensitive: mapping[c_sensitive] = '민감군관리'
    c_emergency = find_col(['응급조치숙지', '응급조치에 대해', '응급상황 행동'])
    if c_emergency: mapping[c_emergency] = '응급조치숙지'
    c_notes = find_col(['기타 점검', '특이사항', '종합의견'])
    if c_notes: mapping[c_notes] = '특이사항'
    
    df.rename(columns=mapping, inplace=True)
    required_cols = ['참여자', '사업장명', '날짜', '체감온도', '폭염특보여부', '평상시조치', '35도이상조치', '38도이상조치', '음료제공방식', '민감군관리', '응급조치숙지', '특이사항']
    for rc in required_cols:
        if rc not in df.columns: df[rc] = ""
            
    df['사업장명'] = df['사업장명'].apply(lambda x: standardize_site_name(x, valid_db_names))
    df['참여자'] = df['참여자'].astype(str)
    df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce')
    df['월'] = df['날짜_dt'].dt.month
    df['체감온도_수치'] = df['체감온도'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['특보발효건수'] = df['폭염특보여부'].astype(str).apply(lambda x: 1 if '발표됨' in x or '예' in x or '경보' in x or '주의보' in x else 0)
    
    return df

@st.cache_data(ttl=60)
def load_db_data(valid_db_names):
    try:
        db_df = pd.read_csv('DB.csv', encoding='cp949')
    except:
        db_df = pd.read_csv('DB.csv', encoding='utf-8')
        
    if '관리팀' in db_df.columns and '현장명' in db_df.columns:
        db_df = db_df[['관리팀', '현장명']].dropna(subset=['관리팀', '현장명']).copy()
    else:
        return pd.DataFrame()
        
    db_df['표준현장명'] = db_df['현장명'].apply(lambda x: standardize_site_name(x, valid_db_names))
    return db_df


raw_df = load_data(valid_db_names_tuple)
raw_df['비교용_날짜'] = raw_df['날짜_dt'].dt.date
raw_df = raw_df.sort_values(by='체감온도_수치', ascending=False)
raw_df = raw_df.drop_duplicates(subset=['비교용_날짜', '사업장명'], keep='first').reset_index(drop=True)

db_master = load_db_data(valid_db_names_tuple)

# ==========================================
# 3. 사이드바 구성 및 관리자 인증/기능 구현
# ==========================================
with st.sidebar:
    st.markdown("<div style='font-size: 80px; margin-bottom: -20px;'>🌡️</div>", unsafe_allow_html=True)
    st.title("안전보건팀")
    st.markdown("---")
    
    KST = timezone(timedelta(hours=9))
    current_today = datetime.now(KST).date()
    available_dates = sorted(raw_df['비교용_날짜'].dropna().unique().tolist(), reverse=True)
    
    if current_today in available_dates:
        default_idx = available_dates.index(current_today)
    else:
        default_idx = 0 
        if available_dates:
            st.sidebar.warning(f"⚠️ 금일({current_today}) 데이터가 아직 제출되지 않아, 가장 최근 데이터 일자로 자동 매칭되었습니다.")

    if available_dates:
        today_kst = st.selectbox("📅 모니터링 기준일 선택", available_dates, index=default_idx)
        filtered_df = raw_df[raw_df['비교용_날짜'] <= today_kst]
    else:
        today_kst = current_today
        filtered_df = pd.DataFrame()

    # 🔐 관리자 인증 시스템
    st.markdown("---")
    st.markdown("### 🔐 관리자 시스템")
    admin_password = st.text_input("관리자 비밀번호 입력", type="password")
    is_admin = (admin_password == "1234")
    
    if is_admin:
        st.success("🔑 관리자 권한 확인")
        st.markdown("##### 🛠️ 사이드바 조작창 (루트 1)")
        
        today_submitted_raw = filtered_df[filtered_df['비교용_날짜'] == today_kst]['사업장명'].unique().tolist() if not filtered_df.empty else []
        
        if not db_master.empty:
            missing_sites_for_admin = db_master[
                (~db_master['표준현장명'].isin(today_submitted_raw)) & 
                (~db_master['표준현장명'].isin(st.session_state['manual_done_sites']))
            ]['현장명'].unique().tolist()
            
            if missing_sites_for_admin:
                selected_site = st.selectbox("실시로 변경할 현장 선택", missing_sites_for_admin)
                if st.button("선택 현장 '실시'로 강제 전환 및 저장"):
                    standard_name = standardize_site_name(selected_site, valid_db_names_tuple)
                    st.session_state['manual_done_sites'].add(standard_name)
                    save_manual_sites(st.session_state['manual_done_sites'])
                    st.toast(f"📢 [{selected_site}] 현장이 실시 처리 및 저장되었습니다.", icon="✅")
                    st.rerun()
            else:
                st.info("모든 사업장이 제출을 완료했습니다.")
                
            if st.session_state['manual_done_sites']:
                if st.button("🔄 수동 변경 내역 전체 초기화 (파일 삭제)"):
                    st.session_state['manual_done_sites'].clear()
                    if os.path.exists(DB_FILE):
                        os.remove(DB_FILE)
                    st.toast("모든 수동 조치 내역이 초기화되었습니다.")
                    st.rerun()
    elif admin_password:
        st.error("❌ 비밀번호가 틀렸습니다.")

# ==========================================
# 4. 화면 구성 및 메인 타이틀
# ==========================================
st.markdown("<h1 style='font-size: 2.5rem; color: #0f172a; margin-bottom: 0px;'>☀️ 백상가족 건강한 여름나기 종합 대시보드</h1>", unsafe_allow_html=True)
st.markdown("---")

col_tab1, col_tab2, col_tab3 = st.columns(3)
with col_tab1:
    if st.button("📊 총괄 브리핑", use_container_width=True, type="primary" if st.session_state.current_tab == "📊 총괄 브리핑" else "secondary"):
        st.session_state.current_tab = "📊 총괄 브리핑"
        st.rerun()
with col_tab2:
    if st.button("🏢 전국 사업장 조치대장", use_container_width=True, type="primary" if st.session_state.current_tab == "🏢 전국 사업장 조치대장" else "secondary"):
        st.session_state.current_tab = "🏢 전국 사업장 조치대장"
        st.rerun()
with col_tab3:
    if st.button("✅ 팀별 실시 현황 (DB연동)", use_container_width=True, type="primary" if st.session_state.current_tab == "✅ 팀별 실시 현황" else "secondary"):
        st.session_state.current_tab = "✅ 팀별 실시 현황"
        st.rerun()

# ------------------------------------------
# MODE 1: 총괄 브리핑 및 MODE 2는 생략 (기존과 동일하게 작동)
# ------------------------------------------
if st.session_state.current_tab == "📊 총괄 브리핑":
    st.markdown(f"### 🚨 당일 현장 위험도 집중 모니터링 ({today_kst.strftime('%Y-%m-%d')})")
    today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy() if not filtered_df.empty else pd.DataFrame()
    if st.session_state['manual_done_sites'] and not db_master.empty:
        for m_site in st.session_state['manual_done_sites']:
            if today_df.empty or m_site not in today_df['사업장명'].values:
                new_row = {col: "" for col in today_df.columns}
                new_row['사업장명'] = m_site
                new_row['체감온도_수치'] = 25.0 
                new_row['폭염특보여부'] = "일반"
                new_row['참여자'] = "본사 보건관리자"
                new_row['평상시조치'] = "본사 점검 승인 완료"
                today_df = pd.concat([today_df, pd.DataFrame([new_row])], ignore_index=True)
    if not today_df.empty:
        def get_alert_badge_by_row(row):
            temp = row['체감온도_수치']
            warn = str(row['폭염특보여부'])
            if pd.notna(temp) and temp != "":
                try:
                    temp = float(temp)
                    if temp >= 38.0: return "🔴 폭염중대경보"
                    elif temp >= 35.0: return "🟠 폭염경보"
                    elif temp >= 33.0: return "🟡 폭염주의보"
                    else: return "🟢 일반"
                except: pass
            if '경보' in warn: return "🟠 폭염경보"
            elif '주의보' in warn: return "🟡 폭염주의보"
            return "🟢 일반"
        today_df['경보단계_명칭'] = today_df.apply(get_alert_badge_by_row, axis=1)
        today_df['우선순위'] = today_df['경보단계_명칭'].apply(lambda x: 4 if "중대" in x else (3 if "경보" in x else (2 if "주의" in x else 1)))
        today_df = today_df.sort_values(by=['우선순위', '체감온도_수치'], ascending=[False, False])
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("당일 점검 완료 사업장", f"{len(today_df)}개소", f"수동 승인 {len(st.session_state['manual_done_sites'])}곳 포함")
        st.info("💡 세부 조치현황은 상단 버튼을 통해 '전국 사업장 조치대장' 및 '팀별 실시 현황' 탭에서 확인하세요.")

elif st.session_state.current_tab == "🏢 전국 사업장 조치대장":
    st.subheader("🏢 전국 사업장 개별 온열조치 상세 보고")
    st.info("기존 대장 기능 유지 중")

# ------------------------------------------
# MODE 3: 팀별 제출 현황 (DB 연동) ⭐️ 전면 업데이트 구역
# ------------------------------------------
elif st.session_state.current_tab == "✅ 팀별 실시 현황":
    st.subheader(f"📊 부서별 온열질환 체크리스트 관리 현황 ({today_kst.strftime('%Y-%m-%d')} 기준)")
    st.markdown("<p style='font-size: 13px; color: #64748b; margin-top: -10px;'>DB.csv 마스터 데이터의 [관리팀] 및 [현장명]을 기반으로, 당일 제출된 현장과 제출되지 않은 현장을 추적합니다.</p>", unsafe_allow_html=True)

    if db_master.empty:
        st.error("⚠️ `DB.csv` 파일을 찾을 수 없거나 '관리팀', '현장명' 컬럼이 존재하지 않습니다. 파일을 확인해주세요.")
    else:
        today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy() if not filtered_df.empty else pd.DataFrame()
        submitted_sites = today_df['사업장명'].unique().tolist() if not today_df.empty else []
        
        if st.session_state['manual_done_sites']:
            submitted_sites = list(set(submitted_sites + list(st.session_state['manual_done_sites'])))

        target_teams = ['관리1팀', '관리2팀', '관리3팀', '영업2본부']
        
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        for i, team in enumerate(target_teams):
            team_df = db_master[db_master['관리팀'] == team]
            total_count = len(team_df)
            submitted = team_df[team_df['표준현장명'].isin(submitted_sites)]
            missing = team_df[~team_df['표준현장명'].isin(submitted_sites)]
            
            sub_count = len(submitted)
            rate = int((sub_count / total_count * 100)) if total_count > 0 else 0
            
            cols = [col_t1, col_t2, col_t3, col_t4]
            with cols[i]:
                # 1. 팀별 통계 카드 디자인
                st.markdown(f"""
                <div style="background-color: #ffffff; border-radius: 12px; padding: 15px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 10px;">
                    <h3 style="margin-top:0; color: #1e293b; font-size: 18px; text-align: center;">{team}</h3>
                    <div style="text-align: center; margin-bottom: 5px;">
                        <span style="font-size: 32px; font-weight: bold; color: {'#22c55e' if rate == 100 else '#3b82f6'};">{rate}%</span>
                        <div style="font-size: 13px; color: #64748b;">(제출 {sub_count} / 전체 {total_count})</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 🔍 [핵심 요청 사항] 각 팀의 리스트 상단에 전용 검색 콤보박스 배치
                search_term = st.text_input(f"🔍 {team} 사업장 검색", key=f"search_{team}", placeholder="사업장명 입력...", label_visibility="collapsed")
                
                # ❌ 미실시 현장 관리 영역 (검색 필터 적용)
                # 검색어가 있으면 현장명에 포함된 것만 필터링
                if search_term:
                    filtered_missing = missing[missing['현장명'].astype(str).str.contains(search_term, na=False)]
                else:
                    filtered_missing = missing
                    
                with st.expander(f"❌ 미실시 현장 ({len(filtered_missing)} / {len(missing)}곳)", expanded=True):
                    if not filtered_missing.empty:
                        for idx, row_missing in filtered_missing.iterrows():
                            site_raw_name = row_missing['현장명']
                            std_name = row_missing['표준현장명']
                            
                            if is_admin:
                                if st.button(f"{site_raw_name}", key=f"toggle_missing_{std_name}_{idx}_{team}"):
                                    st.session_state['manual_done_sites'].add(std_name)
                                    save_manual_sites(st.session_state['manual_done_sites'])
                                    st.toast(f"📢 [{site_raw_name}] 현장이 실시 상태로 변경되었습니다.", icon="✅")
                                    st.rerun()
                            else:
                                st.markdown(f"<div class='status-box missing-box'>{site_raw_name}</div>", unsafe_allow_html=True)
                    else:
                        if search_term:
                            st.markdown("<div style='font-size: 12px; color: #94a3b8; text-align: center; padding: 5px;'>검색 결과 없음</div>", unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='font-size: 13px; color: #16a34a; text-align: center; padding: 10px;'>전원 제출 완료 🎉</div>", unsafe_allow_html=True)
                
                # ✅ 실시 완료 현장 관리 영역 (검색 필터 적용)
                if search_term:
                    filtered_submitted = submitted[submitted['현장명'].astype(str).str.contains(search_term, na=False)]
                else:
                    filtered_submitted = submitted

                with st.expander(f"✅ 실시 완료 ({len(filtered_submitted)}곳)", expanded=False):
                    if not filtered_submitted.empty:
                        for idx, row_submitted in filtered_submitted.iterrows():
                            site_raw_name = row_submitted['현장명']
                            std_name = row_submitted['표준현장명']
                            
                            if is_admin and (std_name in st.session_state['manual_done_sites']):
                                if st.button(f"↩️ {site_raw_name}", key=f"toggle_done_{std_name}_{idx}_{team}"):
                                    st.session_state['manual_done_sites'].discard(std_name)
                                    save_manual_sites(st.session_state['manual_done_sites'])
                                    st.toast(f"📢 [{site_raw_name}] 현장이 다시 미실시 상태로 되돌아갔습니다.", icon="🔄")
                                    st.rerun()
                            else:
                                st.markdown(f"<div class='status-box done-box'><b>{site_raw_name}</b></div>", unsafe_allow_html=True)
                    else:
                        if search_term:
                            st.markdown("<div style='font-size: 12px; color: #94a3b8; text-align: center; padding: 5px;'>검색 결과 없음</div>", unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='font-size: 13px; color: #94a3b8; text-align: center; padding: 10px;'>제출 내역 없음</div>", unsafe_allow_html=True)