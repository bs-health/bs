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
    
    /* 관리자 인증 시 클릭 가능한 미실시/실시 변경 버튼 스타일 커스텀 (이전 UI 복원) */
    div.stButton > button[key^="toggle_missing_"], div.stButton > button[key^="toggle_done_"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        text-align: left !important;
        padding: 8px 14px !important;
        font-weight: normal !important;
        margin-bottom: -4px !important;
        width: auto !important;
        min-width: 150px;
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
    """DB.csv에서 기준이 되는 현장명 리스트를 먼저 학습하여 추출합니다."""
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
    """(1단계 정제) 공백, 자음/모음 오타 제거 및 기본 매핑을 수행합니다."""
    name = re.sub(r'[ㄱ-ㅎㅏ-ㅣ\s]', '', str(name))
    
    early_mapping = {
        '서울보증': '서울보증보험',
        '경주교원드림센터': '교원경주드림센터',
        '교원경주드림': '교원경주드림센터',
        '경주교원드림': '교원경주드림센터',
        '가든5툴': '가든파이브툴',               
        '가든5툴백상코퍼레이션': '가든파이브툴',
        '가든파이툴': '가든파이브툴',             
        '쿠팡경산1,2FC': '쿠팡경산1,2센터',
        '쿠팡경산1,2': '쿠팡경산1,2센터'
    }
    name = early_mapping.get(name, name)
    
    if name in ['교원경주드림센터', '서울보증보험', '가든파이브툴', '쿠팡경산1,2센터']:
        return name

    name = name.replace('현장', '').replace('지점', '')
    name = name.replace('샌타', '센터')
    name = re.sub(r'(?i)fc', '센터', name)
        
    name_mapping = {'성우프로젝트': '성우', '성우건설': '성우', '(주)성우': '성우'}
    return name_mapping.get(name, name)


def standardize_site_name(name, valid_db_names):
    """(2단계 정제) 1단계 정제된 이름을 바탕으로 DB 기준 이름 포함 여부를 확인하여 최종 통일합니다."""
    name = standardize_site_name_base(name)
    if valid_db_names:
        for db_name in sorted(valid_db_names, key=len, reverse=True):
            if db_name in name:
                return db_name
                
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
            if any(kw in col for kw in keywords):
                return col
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
        if rc not in df.columns:
            df[rc] = ""
            
    df['사업장명'] = df['사업장명'].apply(lambda x: standardize_site_name(x, valid_db_names))
    df['참여자'] = df['참여자'].astype(str)
    
    df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce')
    df['월'] = df['날짜_dt'].dt.month
    df['체감온도_수치'] = df['체감온도'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    
    warn_series = df['폭염특보여부'].fillna("").astype(str)
    df['특보발효건수'] = warn_series.str.contains('발표됨|예|경보|주의보', regex=True).astype(int)
    
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

    # 기준일 문자열 포맷 추출 (YYYY-MM-DD)
    date_str_key = str(today_kst)

    # 선택된 날짜에 조치한 수동 완료 데이터 필터링
    current_day_done_sites = set()
    for item in st.session_state['manual_done_sites']:
        if '|' in item:
            s_name, s_date = item.split('|', 1)
            if s_date == date_str_key:
                current_day_done_sites.add(s_name)

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
                (~db_master['표준현장명'].isin(current_day_done_sites))
            ]['현장명'].unique().tolist()
            
            if missing_sites_for_admin:
                selected_site = st.selectbox("실시로 변경할 현장 선택", missing_sites_for_admin)
                if st.button("선택 현장 '실시'로 강제 전환 및 저장"):
                    standard_name = standardize_site_name(selected_site, valid_db_names_tuple)
                    
                    st.session_state['manual_done_sites'].add(f"{standard_name}|{date_str_key}")
                    save_manual_sites(st.session_state['manual_done_sites'])
                    st.toast(f"📢 [{selected_site}] 현장이 {date_str_key} 일자로 실시 처리 및 저장되었습니다.", icon="✅")
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
# MODE 1: 총괄 브리핑
# ------------------------------------------
if st.session_state.current_tab == "📊 총괄 브리핑":
    st.markdown(f"### 🚨 당일 현장 위험도 집중 모니터링 ({today_kst.strftime('%Y-%m-%d')})")
    today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy() if not filtered_df.empty else pd.DataFrame()
    
    if current_day_done_sites and not db_master.empty:
        for m_site in current_day_done_sites:
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

        def get_sort_weight_by_badge(badge):
            if "중대경보" in badge: return 4
            if "경보" in badge: return 3
            if "주의보" in badge: return 2
            return 1

        today_df['경보단계_명칭'] = today_df.apply(get_alert_badge_by_row, axis=1)
        today_df['우선순위'] = today_df['경보단계_명칭'].apply(get_sort_weight_by_badge)
        today_df = today_df.sort_values(by=['우선순위', '체감온도_수치'], ascending=[False, False])

        g_critical = today_df[today_df['경보단계_명칭'].str.contains("중대경보")]['사업장명'].tolist()
        g_warning = today_df[today_df['경보단계_명칭'].str.contains("경보") & ~today_df['경보단계_명칭'].str.contains("중대경보")]['사업장명'].tolist()
        g_advisory = today_df[today_df['경보단계_명칭'].str.contains("주의보")]['사업장명'].tolist()
        g_normal = today_df[today_df['경보단계_명칭'].str.contains("일반")]['사업장명'].tolist()

        warning_count = len(g_critical) + len(g_warning) + len(g_advisory)
        critical_count = sum(today_df["체감온도_수치"].apply(lambda x: float(x) >= 35.0 if x != "" else False) | today_df["응급조치숙지"].astype(str).apply(lambda x: "아니오" in x or "모르" in x))
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("당일 점검 완료 사업장", f"{len(today_df)}개소", f"수동 승인 {len(current_day_done_sites)}곳 포함")
        kpi2.metric("폭염 기상특보 발효", f"{warning_count}개 현장", "기상청 실시간 발효 기준")
        kpi3.metric("집중 보건 관리 요구지", f"{critical_count}개소", "35도 돌파 및 교육 필요처")
        
        st.markdown("---")
        st.markdown("### 🚦 당일 폭염 단계별 사업장 현황판")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div style="background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #991b1b; font-size: 13px;">🔴 폭염중대경보</span><div style="font-size: 26px; font-weight: 900; color: #991b1b; margin-top: 5px;">{len(g_critical)}개소</div><p style="font-size: 11px; color: #7f1d1d; margin-top: 5px; font-weight: bold;">{", ".join(g_critical) if g_critical else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div style="background-color: #ffedd5; border-left: 5px solid #f97316; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #c2410c; font-size: 13px;">🟠 폭염경보</span><div style="font-size: 26px; font-weight: 900; color: #c2410c; margin-top: 5px;">{len(g_warning)}개소</div><p style="font-size: 11px; color: #7c2d12; margin-top: 5px; font-weight: bold;">{", ".join(g_warning) if g_warning else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="background-color: #fef9c3; border-left: 5px solid #eab308; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #854d0e; font-size: 13px;">🟡 폭염주의보</span><div style="font-size: 26px; font-weight: 900; color: #854d0e; margin-top: 5px;">{len(g_advisory)}개소</div><p style="font-size: 11px; color: #713f12; margin-top: 5px; font-weight: bold;">{", ".join(g_advisory) if g_advisory else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div style="background-color: #dcfce7; border-left: 5px solid #22c55e; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #166534; font-size: 13px;">🟢 일반</span><div style="font-size: 26px; font-weight: 900; color: #166534; margin-top: 5px;">{len(g_normal)}개소</div><p style="font-size: 11px; color: #14532d; margin-top: 5px; font-weight: bold;">{", ".join(g_normal) if g_normal else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 전사 고온 위험 사업장 관리 현황 요약")
        
        summary_rows = []
        for idx, r in today_df.iterrows():
            badge = r['경보단계_명칭']
            if "일반" in badge: continue
            m_str = str(r['평상시조치'])
            summary_rows.append({
                '사업장명': r['사업장명'], '경보단계': badge, '체감온도': f"{float(r['체감온도_수치']):.1f} ℃" if r['체감온도_수치'] != "" else "N/A",
                '물/음료': '🟢' if any(kw in m_str for kw in ['물', '음료', '식수', '포도당']) else '🔴',
                '그늘막': '🟢' if any(kw in m_str for kw in ['그늘', '휴게', '쉼터']) else '🔴',
                'TBM교육': '🟢' if any(kw in m_str for kw in ['교육', 'TBM']) else '🔴',
                '민감군': '🟢' if '예' in str(r['민감군관리']) or '관리' in str(r['민감군관리']) else '🔴',
                '응급숙지': '🟢' if '예' in str(r['응급조치숙지']) or '이해' in str(r['응급조치숙지']) else '🔴'
            })
            
        if summary_rows:
            col_widths = [2.5, 2.2, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0]
            with st.container(height=450):
                cols = st.columns(col_widths, vertical_alignment="center")
                headers = ["사업장명 (클릭이동)", "경보단계", "체감온도", "물/음료", "그늘막", "TBM", "민감군", "응급숙지", "상세분석"]
                for i, text in enumerate(headers):
                    align = "left" if i==1 else "center"
                    cols[i].markdown(f"<div style='text-align: {align};'><b style='font-size: 13px; color: #475569;'>{text}</b></div>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 4px 0 10px 0;'>", unsafe_allow_html=True)

                for s_idx, row_item in enumerate(summary_rows):
                    c = st.columns(col_widths, vertical_alignment="center")
                    if c[0].button(row_item['사업장명'], key=f"btn_site_{row_item['사업장명']}_{s_idx}", use_container_width=True):
                        st.session_state.current_tab = "🏢 전국 사업장 조치대장"
                        st.session_state.expanded_site = row_item['사업장명']
                        st.session_state.search_query = row_item['사업장명']
                        st.rerun()
                    c[1].markdown(f"<div>{row_item['경보단계']}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div style='text-align: center;'>{row_item['체감온도']}</div>", unsafe_allow_html=True)
                    c[3].markdown(f"<div style='text-align: center;'>{row_item['물/음료']}</div>", unsafe_allow_html=True)
                    c[4].markdown(f"<div style='text-align: center;'>{row_item['그늘막']}</div>", unsafe_allow_html=True)
                    c[5].markdown(f"<div style='text-align: center;'>{row_item['TBM교육']}</div>", unsafe_allow_html=True)
                    c[6].markdown(f"<div style='text-align: center;'>{row_item['민감군']}</div>", unsafe_allow_html=True)
                    c[7].markdown(f"<div style='text-align: center;'>{row_item['응급숙지']}</div>", unsafe_allow_html=True)
                    if c[8].button("🔍 조치내역", key=f"btn_go_{row_item['사업장명']}_{s_idx}", use_container_width=True):
                        st.session_state.current_tab = "🏢 전국 사업장 조치대장"
                        st.session_state.expanded_site = row_item['사업장명']
                        st.session_state.search_query = row_item['사업장명']
                        st.rerun()
        else:
            st.success("✅ 금일 기준 체감온도 33℃ 이상인 우려 사업장이 없습니다.")
            
    else:
        st.info("ℹ️ 선택한 기준일에 제출된 현장 점검 데이터가 없습니다.")

# ------------------------------------------
# MODE 2: 전국 사업장 조치대장
# ------------------------------------------
elif st.session_state.current_tab == "🏢 전국 사업장 조치대장":
    st.subheader("🏢 전국 사업장 개별 온열조치 상세 보고")
    search_query = st.text_input("🔍 사업장명 또는 보고자 검색", value=st.session_state.search_query)
    
    if st.session_state.expanded_site:
        if st.button("🔄 검색 필터 및 자동 열기 해제 (전체보기)", type="secondary"):
            st.session_state.expanded_site = None
            st.session_state.search_query = ""
            st.rerun()

    today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy() if not filtered_df.empty else pd.DataFrame()
    
    if current_day_done_sites and not db_master.empty:
        for m_site in current_day_done_sites:
            if today_df.empty or m_site not in today_df['사업장명'].values:
                new_row = {col: "" for col in today_df.columns}
                new_row['사업장명'] = m_site
                new_row['체감온도_수치'] = 25.0
                new_row['폭염특보여부'] = "일반"
                new_row['참여자'] = "본사 보건관리자"
                new_row['평상시조치'] = "본사 이행 상태 확인"
                new_row['특이사항'] = "현장 점검 완료 처리된 사업장입니다."
                today_df = pd.concat([today_df, pd.DataFrame([new_row])], ignore_index=True)

    site_df = today_df.sort_values('체감온도_수치', ascending=False).copy() if not today_df.empty else pd.DataFrame()
    
    if search_query:
        site_df = site_df[site_df["사업장명"].astype(str).str.contains(search_query, na=False) | site_df["참여자"].astype(str).str.contains(search_query, na=False)]

    if site_df.empty:
        st.info("조건에 맞는 데이터가 존재하지 않습니다.")
    else:
        for idx, row in site_df.iterrows():
            is_high = float(row["체감온도_수치"]) >= 35.0 if row["체감온도_수치"] != "" else False
            m_label = "🟢 일반보건" if is_high == False else "🔥 35도이상 집중관리"
            
            header_title = f"[{m_label}] {row['사업장명']} (체감 {f'{float(row['체감온도_수치']):.1f}' if row['체감온도_수치']!='' else 'N/A'}°C) | 책임관리자: {row['참여자']}"
            is_auto_expand = (st.session_state.expanded_site == row['사업장명'])
            
            with st.expander(header_title, expanded=is_auto_expand):
                col_left, col_right = st.columns(2)
                
                with col_left:
                    date_str = row['날짜_dt'].strftime('%Y-%m-%d') if pd.notna(row['날짜_dt']) and row['날짜_dt'] != "" else str(today_kst)
                    # 🎯 오타 수정 연동 완료 구역 (row['폭염특보여7부'] -> row['폭염특보여부'])
                    st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                            <h4 style="margin-top:0; color: #1e3a8a; font-size: 15px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">📋 현장 기본 정보</h4>
                            <table style="width: 100%; font-size: 13px;">
                                <tr><td style="font-weight: bold; width: 40%; color: #475569;">보고자</td><td>{row['참여자']}</td></tr>
                                <tr><td style="font-weight: bold; color: #475569;">점검시간</td><td>{date_str}</td></tr>
                                <tr><td style="font-weight: bold; color: #475569;">측정 체감온도</td><td><span style="color:#e11d48; font-weight:bold;">{f"{float(row['체감온도_수치']):.1f} ℃" if row['체감온도_수치']!='' else 'N/A'}</span></td></tr>
                                <tr><td style="font-weight: bold; color: #475569;">기상청 특보발효</td><td style="color: #ea580c; font-weight: bold;">{row['폭염특보여부']}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                            <h4 style="margin-top:0; color: #1e3a8a; font-size: 15px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">✔️ 핵심 보건 관리 항목</h4>
                            <table style="width: 100%; font-size: 13px;">
                                <tr><td style="font-weight: bold; width: 40%; color: #475569; padding-bottom:4px;">식수 및 음료지급</td><td>{row['음료제공방식']}</td></tr>
                                <tr><td style="font-weight: bold; color: #475569; padding-bottom:4px;">민감근로자 관리</td><td>{row['민감군관리']}</td></tr>
                                <tr><td style="font-weight: bold; color: #475569; padding-bottom:4px;">비상 응급조치</td><td>{row['응급조치숙지']}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)

                with col_right:
                    p1_formatted = "".join([f"<li style='margin-bottom: 4px;'>{act.strip()}</li>" for act in str(row['평상시조치']).split('|') if act.strip()])
                    p2_actions = str(row['35도이상조치']).split('|') if pd.notna(row['35도이상조치']) else []
                    p2_formatted = "".join([f"<li style='margin-bottom: 4px;'>{act.strip()}</li>" for act in p2_actions if act.strip()]) if p2_actions and p2_actions[0] != 'nan' else "<li>해당 없음</li>"
                    p3_actions = str(row['38도이상조치']).split('|') if pd.notna(row['38도이상조치']) else []
                    p3_formatted = "".join([f"<li style='margin-bottom: 4px;'>{act.strip()}</li>" for act in p3_actions if act.strip()]) if p3_actions and p3_actions[0] != 'nan' else "<li>해당 없음</li>"

                    st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                            <h4 style="margin-top:0; color: #1e3a8a; font-size: 15px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">🌡️ 단계별 조치 이행 실태</h4>
                            <div style="font-size: 13px;">
                                <strong style="color: #0d9488;">[1단계] 평상시 예방 조치:</strong><ul style="padding-left: 15px; color: #334155; margin-bottom: 8px;">{p1_formatted}</ul>
                                <strong style="color: #ea580c;">[2단계] 35도 돌파 시 조치:</strong><ul style="padding-left: 15px; color: #334155; margin-bottom: 8px;">{p2_formatted}</ul>
                                <strong style="color: #dc2626;">[3단계] 38도 돌파 시 조치:</strong><ul style="padding-left: 15px; color: #334155; margin-bottom: 0px;">{p3_formatted}</ul>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    notes_text = row['특이사항'] if pd.notna(row['특이사항']) and str(row['특이사항']).strip() != "" and str(row['특이사항']) != "nan" else "금일 현장 기상 및 특이사항 양호합니다."
                    st.markdown(f