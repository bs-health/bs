import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
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
    .status-box { padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 13px; border: 1px solid #e2e8f0; }
    .missing-box { background-color: #fef2f2; border-left: 4px solid #ef4444; }
    .done-box { background-color: #f0fdf4; border-left: 4px solid #22c55e; }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "📊 총괄 브리핑"
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'expanded_site' not in st.session_state:
    st.session_state.expanded_site = None

# ==========================================
# 2. 강력한 데이터 정제 및 유연한 컬럼 매핑 엔진 
# ==========================================

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


@st.cache_data(ttl=5)  
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

valid_db_names_tuple = tuple(get_valid_db_names())


@st.cache_data(ttl=5) 
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
    c_reporter = find_col(['참여자', '작성자', '보고자'])
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
    
    # 🚨 중대한 오류 방어선: 원본 컬럼이 매핑 사전에 매치되지 않아 누락되는 현상 방지
    actual_site_col = c_name if c_name else '사업장 명을 알려주세요(*)'
    
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
    df['특보발효건수'] = df['폭염특보여부'].astype(str).apply(lambda x: 1 if '발표됨' in x or '예' in x or '경보' in x or '주의보' in x else 0)
    
    return df

@st.cache_data(ttl=5)
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
# 3. 사이드바 구성 및 관리자 저장 기능 
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

    # 🔐 관리자 인증 및 CSV 직접 저장 시스템
    st.markdown("---")
    st.markdown("### 🔐 관리자 시스템")
    admin_password = st.text_input("관리자 비밀번호 입력", type="password")
    
    if admin_password == "1234":
        st.success("🔑 관리자 권한 확인")
        st.markdown("##### 🛠️ 수동 점검 완료 처리")
        
        today_submitted_raw = filtered_df[filtered_df['비교용_날짜'] == today_kst]['사업장명'].unique().tolist() if not filtered_df.empty else []
        
        if not db_master.empty:
            missing_sites_for_admin = db_master[~db_master['표준현장명'].isin(today_submitted_raw)]['현장명'].unique().tolist()
            
            if missing_sites_for_admin:
                selected_site = st.selectbox("실시로 변경할 현장", missing_sites_for_admin)
                if st.button("선택 현장 '실시'로 강제 전환"):
                    
                    # 🛠️ 수동 저장 시 발생한 KeyError 완벽 대응 로직
                    # 기존 data.csv를 다시 불러와 사용되는 실제 원본 컬럼 이름들을 정확히 동적 수집합니다.
                    try:
                        df_check = pd.read_csv('data.csv', encoding='cp949')
                        enc = 'cp949'
                    except:
                        df_check = pd.read_csv('data.csv', encoding='utf-8')
                        enc = 'utf-8'
                    
                    orig_cols = df_check.columns.tolist()
                    
                    # 파일 안에 매칭되는 실제 컬럼명 찾기 함수
                    def match_orig_col(keywords, default_val):
                        for c in orig_cols:
                            if any(kw in c for kw in keywords):
                                return c
                        return default_val

                    # 실제 data.csv 내부의 한글 양식 그대로 매핑 이름을 탐색합니다.
                    col_user = match_orig_col(['참여자', '작성자', '보고자'], '작성자')
                    col_site = match_orig_col(['사업장 명', '사업장명', '지점명'], '사업장명을 알려주세요(*)')
                    col_time = match_orig_col(['날짜'], '오늘의 날짜를 입력해주세요(*)')
                    col_temp = match_orig_col(['체감\'온도', '체감온도', '기온'], '현재 현장의 체감온도')
                    col_warn = match_orig_col(['폭염 특보', '폭염특보'], '폭염특보 발효 여부')
                    col_act1 = match_orig_col(['예방조치', '1단계', '평상시조치'], '평상시 예방조치 이행 내용')
                    col_act2 = match_orig_col(['35도이상', '2단계'], '35도 이상시 조치 이행 내용')
                    col_act3 = match_orig_col(['38도이상', '3단계'], '38도 이상시 조치 이행 내용')
                    col_bev  = match_orig_col(['음료', '깨끗한 물', '식수'], '시원한 식수 및 음료 제공 방식')
                    col_sens = match_orig_col(['민감군'], '폭염 취약근로자(민감군) 관리 현황')
                    col_emg  = match_orig_col(['응급조치숙지', '응급조치에 대해', '응급상황 행동'], '온열질환 응급조치 비상연락망 및 행동요령 숙지 여부')
                    col_note = match_orig_col(['기타 점검', '특이사항', '종합의견'], '기타 특이사항 및 점검 코멘트')

                    # 💾 가상으로 주입할 완벽한 포맷 딕셔너리 빌드
                    new_report = {
                        col_user: '현장소장', 
                        col_site: selected_site, 
                        col_time: datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S'), 
                        col_temp: '28.5', 
                        col_warn: '경보 없음', 
                        col_act1: '물/음료 지급 | 그늘막 설치 | TBM 안전교육 실시', 
                        col_act2: '해당 없음', 
                        col_act3: '해당 없음', 
                        col_bev:  '식수대 운영 및 포도당 알약 제공', 
                        col_sens: '해당 현장 없음', 
                        col_emg:  '예', 
                        col_note: '금일 현장 기상 및 특이사항 양호합니다.'
                    }
                    
                    # 누락된 컬럼이 생성되지 않도록 조율하여 병합 진행
                    df_append = pd.DataFrame([new_report], columns=orig_cols)
                    df_append.fillna("", inplace=True) # 혹시 비는 컬럼 공백 처리
                    
                    df_new = pd.concat([df_check, df_append], ignore_index=True)
                    df_new.to_csv('data.csv', index=False, encoding=enc)
                    
                    st.cache_data.clear() # 캐시 완전 비우기 후 재생성 동기화
                    st.toast(f"📢 [{selected_site}] 현장이 정상 실시 처리되어 저장되었습니다.", icon="✅")
                    st.rerun()
            else:
                st.info("모든 사업장이 제출을 완료했습니다.")
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
        kpi1.metric("당일 점검 완료 사업장", f"{len(today_df)}개소", "실시간 전사 보고 기준")
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
    site_df = today_df.sort_values('체감온도_수치', ascending=False).copy() if not today_df.empty else pd.DataFrame()
    
    if search_query:
        site_df = site_df[site_df["사업장명"].astype(str).str.contains(search_query, na=False) | site_df["참여자"].astype(str).str.contains(search_query, na=False)]

    if site_df.empty:
        st.info("조건에 맞는 데이터가 존재하지 않습니다.")
    else:
        for idx, row in site_df.iterrows():
            is_high = float(row["체감온도_수치"]) >= 35.0 if row["체감온도_수치"] != "" else False
            m_label = "🔥 35도이상 집중관리" if is_high else "🟢 일반보건"
            
            header_title = f"[{m_label}] {row['사업장명']} (체감 {f'{float(row['체감온도_수치']):.1f}' if row['체감온도_수치']!='' else 'N/A'}°C) | 책임관리자: {row['참여자']}"
            is_auto_expand = (st.session_state.expanded_site == row['사업장명'])
            
            with st.expander(header_title, expanded=is_auto_expand):
                col_left, col_right = st.columns(2)
                
                with col_left:
                    date_str = row['날짜_dt'].strftime('%Y-%m-%d') if pd.notna(row['날짜_dt']) and row['날짜_dt'] != "" else str(today_kst)
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
                    st.markdown(f"""
                        <div style="background-color: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                            <h4 style="margin-top:0; color: #0f172a; font-size: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">✍️ 현장 소장 종합 코멘트</h4>
                            <div style="font-size: 13px; color: #475569; font-style: italic;">"{notes_text}"</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("#### 📈 체감온도 누적 변화 추이")
                history_df = filtered_df[filtered_df["사업장명"] == row["사업장명"]].sort_values(by="날짜")
                if not history_df.empty:
                    fig = px.line(history_df, x="날짜", y="체감온도_수치", text="체감온도_수치", markers=True)
                    fig.update_traces(line_color="#e11d48", line_width=3, textposition="top center", texttemplate='%{text:.1f}℃')
                    fig.update_layout(xaxis=dict(tickformat="%m-%d"), yaxis=dict(title="", automargin=True), height=250, margin=dict(l=80, r=10, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True, key=f"trend_chart_{row['사업장명']}_{idx}")

# ------------------------------------------
# MODE 3: 팀별 제출 현황 (DB 연동)
# ------------------------------------------
elif st.session_state.current_tab == "✅ 팀별 실시 현황":
    st.subheader(f"📊 부서별 온열질환 체크리스트 관리 현황 ({today_kst.strftime('%Y-%m-%d')} 기준)")
    st.markdown("<p style='font-size: 13px; color: #64748b; margin-top: -10px;'>DB.csv 마스터 데이터의 [관리팀] 및 [현장명]을 기반으로, 당일 제출된 현장과 제출되지 않은 현장을 추적합니다.</p>", unsafe_allow_html=True)

    if db_master.empty:
        st.error("⚠️ `DB.csv` 파일을 찾을 수 없거나 '관리팀', '현장명' 컬럼이 존재하지 않습니다. 파일을 확인해주세요.")
    else:
        today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy() if not filtered_df.empty else pd.DataFrame()
        submitted_sites = today_df['사업장명'].unique().tolist() if not today_df.empty else []
        
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
                st.markdown(f"""
                <div style="background-color: #ffffff; border-radius: 12px; padding: 15px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 20px;">
                    <h3 style="margin-top:0; color: #1e293b; font-size: 18px; text-align: center;">{team}</h3>
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
                        st.markdown("<div style='font-size: 13px; color: #94a3b8; text-align: center; padding: 10px;'>제출 내역 없음</div>", unsafe_allow_html=True)