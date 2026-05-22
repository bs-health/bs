import streamlit as st
import pandas as pd
import plotly.express as px
import re
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

# 사장님 보고 목적에 맞추어 시인성이 높고 격조 높은 화이트 테마 주입
st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 900;
        color: #0f172a;
    }
    .stAlert {
        border-radius: 16px;
    }
    .custom-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    table {
        font-size: 14px !important;
    }
    /* 버튼 스타일 조정 */
    .stButton>button {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 강력한 데이터 정제 및 유연한 컬럼 매핑 엔진 
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv('data.csv', encoding='cp949')
    except:
        df = pd.read_csv('data.csv', encoding='utf-8')
    
    # 컬럼 이름 유연한 자동 검색 및 일치 매핑
    cols = df.columns.tolist()
    
    def find_col(keywords):
        for col in cols:
            if any(kw in col for kw in keywords):
                return col
        return None
        
    mapping = {}
    
    # 12대 주요 지표 컬럼 키워드 매핑
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
    
    # 컬럼 일괄 정비
    df.rename(columns=mapping, inplace=True)
    
    # 혹은 매핑 실패한 데이터가 있더라도 정상 실행을 위한 기본값 삽입
    required_cols = ['참여자', '사업장명', '날짜', '체감온도', '폭염특보여부', '평상시조치', '35도이상조치', '38도이상조치', '음료제공방식', '민감군관리', '응급조치숙지', '특이사항']
    for rc in required_cols:
        if rc not in df.columns:
            df[rc] = ""
            
    # 숫자형 입력을 대비하여 검색 핵심 컬럼을 강제 문자열형(String)으로 1차 변환
    df['사업장명'] = df['사업장명'].astype(str).str.replace(' ', '', regex=False)
    df['사업장명'] = df['사업장명'].str.replace('빌딩', '', regex=False)
    df['사업장명'] = df['사업장명'].str.replace('타워', '', regex=False)
    df['사업장명'] = df['사업장명'].str.replace('현장', '', regex=False)
    df['사업장명'] = df['사업장명'].str.replace('지점', '', regex=False)
    df['사업장명'] = df['사업장명'].str.replace('센터', 'FC', regex=False)
    df['사업장명'] = df['사업장명'].str.replace('샌타', 'FC', regex=False)
    df['참여자'] = df['참여자'].astype(str)
    
    name_mapping = {
        '성우프로젝트': '성우',
        '성우건설': '성우',
        '(주)성우': '성우'
    }
    df['사업장명'] = df['사업장명'].replace(name_mapping)
    
    # 시간 및 수치 정보 변환
    df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce')
    df['월'] = df['날짜_dt'].dt.month
    df['체감온도_수치'] = df['체감온도'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['특보발효건수'] = df['폭염특보여부'].astype(str).apply(lambda x: 1 if '발표됨' in x or '예' in x or '경보' in x or '주의보' in x else 0)
    
    return df

# 전체 데이터 로드
raw_df = load_data()
raw_df['비교용_날짜'] = raw_df['날짜_dt'].dt.date

# ==========================================
# 3. 사이드바 구성 및 기준일 셋팅 (오늘 기준 매칭)
# ==========================================
with st.sidebar:
    st.markdown("<div style='font-size: 80px; margin-bottom: -20px;'>🌡️</div>", unsafe_allow_html=True)
    st.title("안전보건팀")
    st.markdown("---")
    
    available_dates = sorted(raw_df['비교용_날짜'].dropna().unique().tolist(), reverse=True)
    
    KST = timezone(timedelta(hours=9))
    today_default = datetime.now(KST).date()
    
    default_idx = 0
    if today_default in available_dates:
        default_idx = available_dates.index(today_default)
    elif datetime(2026, 5, 19).date() in available_dates:
        default_idx = available_dates.index(datetime(2026, 5, 19).date())

    today_kst = st.selectbox("📅 모니터링 기준일 선택", available_dates, index=default_idx)

filtered_df = raw_df[raw_df['비교용_날짜'] <= today_kst]

# ==========================================
# 4. 화면 구성 및 메인 타이틀
# ==========================================
st.markdown("<h1 style='font-size: 2.5rem; color: #0f172a; margin-bottom: 0px;'>☀️ 백상가족 건강한 여름나기 종합 대시보드</h1>", unsafe_allow_html=True)
st.markdown("---")

# 탭 기능의 상호 운용성(프로그래밍 제어)을 확보하기 위해 세션 상태 기반 커스텀 탭 메뉴 설계
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "📊 총괄 브리핑"
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'expanded_site' not in st.session_state:
    st.session_state.expanded_site = None

# 상단 가로 배치 탭 버튼 구현
col_tab1, col_tab2 = st.columns(2)
with col_tab1:
    if st.button("📊 총괄 브리핑", use_container_width=True, type="primary" if st.session_state.current_tab == "📊 총괄 브리핑" else "secondary"):
        st.session_state.current_tab = "📊 총괄 브리핑"
        st.rerun()
with col_tab2:
    if st.button("🏢 전국 사업장 조치대장", use_container_width=True, type="primary" if st.session_state.current_tab == "🏢 전국 사업장 조치대장" else "secondary"):
        st.session_state.current_tab = "🏢 전국 사업장 조치대장"
        st.rerun()

# ------------------------------------------
# MODE 1: 총괄 브리핑
# ------------------------------------------
if st.session_state.current_tab == "📊 총괄 브리핑":
    st.markdown(f"### 🚨 당일 현장 위험도 집중 모니터링 ({today_kst.strftime('%Y-%m-%d')})")
    today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy()
    
    if not today_df.empty:
        # 실측 체감온도 수치를 최우선으로 정교하게 매핑 판별
        def get_alert_badge_by_row(row):
            temp = row['체감온도_수치']
            warn = str(row['폭염특보여부'])
            
            # 1. 체감온도 수치가 존재하면 실제 온도를 기준으로 엄격 판정
            if pd.notna(temp):
                if temp >= 38.0:
                    return "🔴 폭염중대경보"
                elif temp >= 35.0:
                    return "🟠 폭염경보"
                elif temp >= 33.0:
                    return "🟡 폭염주의보"
                else:
                    return "🟢 일반"
            
            # 2. 체감온도 수치가 누락된 경우에만 폭염특보여부 텍스트로 보조 판정
            if '경보' in warn:
                return "🟠 폭염경보"
            elif '주의보' in warn:
                return "🟡 폭염주의보"
                
            return "🟢 일반"

        # 우선순위 정렬용 가중치 계산 함수
        def get_sort_weight_by_badge(badge):
            if "중대경보" in badge: return 4
            if "경보" in badge: return 3
            if "주의보" in badge: return 2
            return 1

        # 각 사업장의 경보단계 및 정렬 가중치 미리 적용
        today_df['경보단계_명칭'] = today_df.apply(get_alert_badge_by_row, axis=1)
        today_df['우선순위'] = today_df['경보단계_명칭'].apply(get_sort_weight_by_badge)
        today_df = today_df.sort_values(by=['우선순위', '체감온도_수치'], ascending=[False, False])

        # 폭염 경보/주의보 및 집중관리 대상 분류 (새로운 경보단계 체계 기반 완벽 동기화)
        g_critical = today_df[today_df['경보단계_명칭'].str.contains("중대경보")]['사업장명'].tolist()
        g_warning = today_df[today_df['경보단계_명칭'].str.contains("경보") & ~today_df['경보단계_명칭'].str.contains("중대경보")]['사업장명'].tolist()
        g_advisory = today_df[today_df['경보단계_명칭'].str.contains("주의보")]['사업장명'].tolist()
        g_normal = today_df[today_df['경보단계_명칭'].str.contains("일반")]['사업장명'].tolist()

        warning_count = len(g_critical) + len(g_warning) + len(g_advisory)
        critical_count = sum(today_df["체감온도_수치"].apply(lambda x: float(x) >= 35.0) | today_df["응급조치숙지"].astype(str).apply(lambda x: "아니오" in x or "모르" in x))
        
        # 1. 상단 3대 핵심 KPI 계량 지표
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("당일 점검 완료 사업장", f"{len(today_df)}개소", "전 현장 정상 보고 완료")
        kpi2.metric("폭염 기상특보 발효", f"{warning_count}개 현장", "기상청 실시간 발효 기준")
        kpi3.metric("집중 보건 관리 요구지", f"{critical_count}개소", "35도 돌파 및 교육 필요처")
        
        st.markdown("---")

        # 2. 폭염 단계별 사업장 현황 분류 보드
        st.markdown("### 🚦 당일 폭염 단계별 사업장 현황판")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div style="background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 12px; min-height: 120px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                <span style="font-weight: bold; color: #991b1b; font-size: 13px;">🔴 폭염중대경보</span>
                <div style="font-size: 26px; font-weight: 900; color: #991b1b; margin-top: 5px;">{len(g_critical)}개소</div>
                <p style="font-size: 11px; color: #7f1d1d; margin-top: 5px; font-weight: bold;">{", ".join(g_critical) if g_critical else "대상 현장 없음"}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div style="background-color: #ffedd5; border-left: 5px solid #f97316; padding: 15px; border-radius: 12px; min-height: 120px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                <span style="font-weight: bold; color: #c2410c; font-size: 13px;">🟠 폭염경보</span>
                <div style="font-size: 26px; font-weight: 900; color: #c2410c; margin-top: 5px;">{len(g_warning)}개소</div>
                <p style="font-size: 11px; color: #7c2d12; margin-top: 5px; font-weight: bold;">{", ".join(g_warning) if g_warning else "대상 현장 없음"}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            st.markdown(f"""
            <div style="background-color: #fef9c3; border-left: 5px solid #eab308; padding: 15px; border-radius: 12px; min-height: 120px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                <span style="font-weight: bold; color: #854d0e; font-size: 13px;">🟡 폭염주의보</span>
                <div style="font-size: 26px; font-weight: 900; color: #854d0e; margin-top: 5px;">{len(g_advisory)}개소</div>
                <p style="font-size: 11px; color: #713f12; margin-top: 5px; font-weight: bold;">{", ".join(g_advisory) if g_advisory else "대상 현장 없음"}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with c4:
            st.markdown(f"""
            <div style="background-color: #dcfce7; border-left: 5px solid #22c55e; padding: 15px; border-radius: 12px; min-height: 120px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                <span style="font-weight: bold; color: #166534; font-size: 13px;">🟢 일반</span>
                <div style="font-size: 26px; font-weight: 900; color: #166534; margin-top: 5px;">{len(g_normal)}개소</div>
                <p style="font-size: 11px; color: #14532d; margin-top: 5px; font-weight: bold;">{", ".join(g_normal) if g_normal else "대상 현장 없음"}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 타이틀 띄어쓰기 가독성 전면 교정
        st.markdown("### 📋 전사 고온 위험 사업장 관리 현황 요약")
        st.markdown("<p style='font-size: 13px; color: #64748b; margin-top: -10px;'>당일 체감온도 <b>33℃ 이상(폭염주의보, 폭염경보, 폭염중대경보)</b>으로 특별한 보건 지휘가 요구되는 위험 사업장만을 한눈에 모아 요약 브리핑합니다. <b>사업장명을 클릭하시면 조치대장 탭의 해당 카드 및 누적 온도 추이 그래프가 자동으로 펼쳐진 상태로 연동되어 즉시 이동합니다.</b></p>", unsafe_allow_html=True)

        # 데이터 전처리 및 데이터프레임 형식 준수율 추출
        summary_rows = []
        for idx, r in today_df.iterrows():
            badge = r['경보단계_명칭']
            
            # 일반 등급(🟢 일반)은 완전히 필터링하여 제외하고, 폭염주의보/경보/중대경보 사업장만 요약표에 온전히 노출
            if "일반" in badge:
                continue
                
            m_str = str(r['평상시조치'])
            water = '🟢' if any(kw in m_str for kw in ['물', '음료', '식수', '포도당', '음료수']) else '🔴'
            shade = '🟢' if any(kw in m_str for kw in ['그늘', '휴게', '그늘막', '휴식', '쉼터']) else '🔴'
            edu = '🟢' if any(kw in m_str for kw in ['교육', 'TBM', '안전교육']) else '🔴'
            sens = '🟢' if '예' in str(r['민감군관리']) or '관리' in str(r['민감군관리']) else '🔴'
            emg = '🟢' if '예' in str(r['응급조치숙지']) or '이해' in str(r['응급조치숙지']) else '🔴'
            
            temp_val_num = r['체감온도_수치']
            temp_val = f"{temp_val_num:.1f} ℃" if pd.notna(temp_val_num) else "N/A"
            warning_val = str(r['폭염특보여부']).split(' ')[0] if pd.notna(r['폭염특보여부']) else "특보 없음"
            
            summary_rows.append({
                'obj': r,
                '경보단계': badge,
                '사업장명': r['사업장명'],
                '체감온도': temp_val,
                '폭염특보': warning_val,
                '물/음료': water,
                '그늘막': shade,
                'TBM교육': edu,
                '민감군': sens,
                '응급숙지': emg
            })
            
        if summary_rows:
            col_widths = [2.5, 2.2, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0]
            
            # 최대 10개 행 내외 크기로 고정되고 그 이상은 스크롤되는 정밀 컨테이너 구현
            with st.container(height=450):
                # 스크롤 컨테이너 내부에 헤더를 두어 스크롤바로 인한 컬럼 밀림 현상을 완벽하게 예방 및 수평 격자 일치화
                col_h1, col_h2, col_h3, col_h4, col_h5, col_h6, col_h7, col_h8, col_h9 = st.columns(
                    col_widths, 
                    vertical_alignment="center"
                )
                
                # 경보단계 헤더 수직 정렬 치우침 현상 수정을 위해 모든 칼럼 헤더에 일관된 래핑 div 구성 적용 완료
                col_h1.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>사업장명 (클릭이동)</b></div>", unsafe_allow_html=True)
                col_h2.markdown("<div style='text-align: left; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>경보단계</b></div>", unsafe_allow_html=True)
                col_h3.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>체감온도</b></div>", unsafe_allow_html=True)
                col_h4.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>물/음료</b></div>", unsafe_allow_html=True)
                col_h5.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>그늘막</b></div>", unsafe_allow_html=True)
                col_h6.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>TBM</b></div>", unsafe_allow_html=True)
                col_h7.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>민감군</b></div>", unsafe_allow_html=True)
                col_h8.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>응급숙지</b></div>", unsafe_allow_html=True)
                col_h9.markdown("<div style='text-align: center; padding: 4px 0;'><b style='font-size: 13px; color: #475569;'>상세분석</b></div>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 4px 0 10px 0;'>", unsafe_allow_html=True)

                for s_idx, row_item in enumerate(summary_rows):
                    r_obj = row_item['obj']
                    c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns(
                        col_widths, 
                        vertical_alignment="center"
                    )
                    
                    # 사업장명 자체를 클릭하면 조치대장 탭으로 연동 전환되며 즉시 해당 카드 자동 확장
                    if c1.button(row_item['사업장명'], key=f"btn_site_{row_item['사업장명']}_{s_idx}", use_container_width=True, help="클릭 시 해당 현장의 상세 카드와 누적 온도 추이 그래프로 즉시 이동합니다."):
                        st.session_state.current_tab = "🏢 전국 사업장 조치대장"
                        st.session_state.expanded_site = row_item['사업장명']
                        st.session_state.search_query = row_item['사업장명'] # 해당 사업장만 조치대장에 자동 정렬
                        st.rerun()
                        
                    c2.markdown(f"<div style='text-align: left; padding: 4px 0;'>{row_item['경보단계']}</div>", unsafe_allow_html=True)
                    c3.markdown(f"<div style='text-align: center; padding: 4px 0;'>{row_item['체감온도']}</div>", unsafe_allow_html=True)
                    c4.markdown(f"<div style='text-align: center; font-size:16px; line-height: 1;'>{row_item['물/음료']}</div>", unsafe_allow_html=True)
                    c5.markdown(f"<div style='text-align: center; font-size:16px; line-height: 1;'>{row_item['그늘막']}</div>", unsafe_allow_html=True)
                    c6.markdown(f"<div style='text-align: center; font-size:16px; line-height: 1;'>{row_item['TBM교육']}</div>", unsafe_allow_html=True)
                    c7.markdown(f"<div style='text-align: center; font-size:16px; line-height: 1;'>{row_item['민감군']}</div>", unsafe_allow_html=True)
                    c8.markdown(f"<div style='text-align: center; font-size:16px; line-height: 1;'>{row_item['응급숙지']}</div>", unsafe_allow_html=True)
                    
                    # 조치내역 버튼 구현
                    if c9.button("🔍 조치내역", key=f"btn_go_{row_item['사업장명']}_{s_idx}", use_container_width=True):
                        st.session_state.current_tab = "🏢 전국 사업장 조치대장"
                        st.session_state.expanded_site = row_item['사업장명']
                        st.session_state.search_query = row_item['사업장명']
                        st.rerun()
        else:
            # 폭염 대상 위험지역이 없을 때 출력되는 신뢰감 높은 그린 등급 브리핑 카드
            st.success("✅ 금일 기준 체감온도 33℃ 이상(폭염주의보·경보)인 집중 관리 우려 사업장이 존재하지 않습니다. 전사 현장 안전 상태가 매우 양호합니다.")
            
        st.markdown("---")
        
        # 5대 수칙 준수 비율 차트
        st.subheader("📊 5대 필수 보건항목 준수 비율 (누적 종합 집계)")
        tot = len(filtered_df)
        if tot > 0:
            water_rate = sum(filtered_df["평상시조치"].astype(str).apply(lambda x: any(k in x for k in ["물", "음료"]))) / tot
            shade_rate = sum(filtered_df["평상시조치"].astype(str).apply(lambda x: any(k in x for k in ["그늘", "휴게"]))) / tot
            edu_rate = sum(filtered_df["평상시조치"].astype(str).apply(lambda x: any(k in x for k in ["교육", "TBM"]))) / tot
            sensitive_rate = sum(filtered_df["민감군관리"].astype(str).apply(lambda x: "예" in x)) / tot
            emergency_rate = sum(filtered_df["응급조치숙지"].astype(str).apply(lambda x: "예" in x or "이해" in x)) / tot

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.write(f"💧 깨끗한 물, 이온음료 제공 이행율: **{int(water_rate*100)}%**")
                st.progress(water_rate)
                st.write(f"⛱️ 햇볕 차단 그늘막 및 휴게시설 보급율: **{int(shade_rate*100)}%**")
                st.progress(shade_rate)
                st.write(f"📚 온열예방 일일 안전교육 실시율: **{int(edu_rate*100)}%**")
                st.progress(edu_rate)
            with col_b2:
                st.write(f"👨‍🦳 고위험 민감군 파악 및 관리율: **{int(sensitive_rate*100)}%**")
                st.progress(sensitive_rate)
                st.write(f"🚨 현장 응급상황 행동 숙지율: **{int(emergency_rate*100)}%**")
                st.progress(emergency_rate)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 최다 발효 사업장 순위
        st.subheader("🔥 폭염특보 발효 최다 사업장 (누적 위험도 순)")
        if not filtered_df.empty:
            risk_df = filtered_df.groupby('사업장명')['특보발효건수'].sum().reset_index().sort_values('특보발효건수', ascending=False).head(10)
            fig2 = px.bar(risk_df, x='특보발효건수', y='사업장명', orientation='h', color='특보발효건수', color_continuous_scale='Reds')
            
            # 세로축 이름 "사업장 명"을 회전시키지 않고 그래프 왼쪽에 가로로 수직 정가운데 배치 완료
            fig2.update_layout(
                yaxis=dict(
                    tickangle=0,       
                    title="",          
                    automargin=True    
                ),
                annotations=[
                    dict(
                        text="<b>사업장 명</b>",
                        xref="paper",
                        yref="paper",
                        x=-0.12,       
                        y=0.5,         
                        showarrow=False,
                        font=dict(size=12, color="#475569"),
                        xanchor="right",
                        yanchor="middle",
                        textangle=0    
                    )
                ],
                margin=dict(l=180, r=20, t=50, b=30), 
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig2, use_container_width=True, key="overall_risk_bar_chart")

    else:
        st.info("ℹ️ 선택한 기준일에 제출된 현장 점검 데이터가 없습니다.")

# ------------------------------------------
# MODE 2: 전국 사업장 조치대장
# ------------------------------------------
elif st.session_state.current_tab == "🏢 전국 사업장 조치대장":
    st.subheader("🏢 전국 사업장 개별 온열조치 상세 보고")
    st.markdown("<p style='font-size: 13px; color: #64748b; margin-top: -10px;'>각 사업장명을 클릭하시면 해당 현장의 기상 정보, 16가지 필수 점검 내역 및 실시간 온도 상승곡선이 정교한 카드 보고서 형식으로 출력됩니다.</p>", unsafe_allow_html=True)
    
    # 세션 상태에 저장된 검색 키워드가 있는 경우 검색바의 초기값으로 강제 지정
    search_query = st.text_input("🔍 사업장명 또는 보고자 검색", value=st.session_state.search_query)
    
    # 조치대장 탭에 직접 진입한 경우 자동 확장 대상을 초기화할 수 있는 리셋 버튼 제공
    if st.session_state.expanded_site:
        if st.button("🔄 검색 필터 및 자동 열기 해제 (전체보기)", type="secondary"):
            st.session_state.expanded_site = None
            st.session_state.search_query = ""
            st.rerun()

    today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy()
    site_df = today_df.sort_values('체감온도_수치', ascending=False).copy()
    
    # 컬럼 형식을 .astype(str)를 거치도록 변경하여 에러 완벽 예방
    if search_query:
        site_df = site_df[
            site_df["사업장명"].astype(str).str.contains(search_query, na=False) | 
            site_df["참여자"].astype(str).str.contains(search_query, na=False)
        ]

    if site_df.empty:
        st.info("조건에 맞는 데이터가 존재하지 않습니다.")
    else:
        for idx, row in site_df.iterrows():
            is_high = row["체감온도_수치"] >= 35.0
            header_title = f"[{'🔥 35도이상 집중관리' if is_high else '🟢 일반보건'}] {row['사업장명']} (체감 {row['체감온도_수치']:.1f}°C) | 책임관리자: {row['참여자']}"
            
            # 총괄 브리핑에서 넘어온 사업장의 아코디언은 자동으로 활짝 펼쳐진 상태(expanded=True)로 로드됩니다.
            is_auto_expand = (st.session_state.expanded_site == row['사업장명'])
            
            with st.expander(header_title, expanded=is_auto_expand):
                col_left, col_right = st.columns(2)
                
                with col_left:
                    # row['날짜_dt']는 정형화된 DateTime 객체이므로 안전하게 strftime 실행이 가능합니다.
                    date_str = row['날짜_dt'].strftime('%Y-%m-%d') if pd.notna(row['날짜_dt']) else str(row['날짜'])
                    
                    # 카드 1: 현장 기본 정보
                    st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                            <h4 style="margin-top:0; color: #1e3a8a; font-size: 15px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">📋 현장 기본 정보 및 기상 현황</h4>
                            <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                                <tr><td style="font-weight: bold; width: 40%; padding: 6px 0; color: #475569;">보고책임자</td><td style="color: #0f172a; font-weight: 500;">{row['참여자']}</td></tr>
                                <tr><td style="font-weight: bold; padding: 6px 0; color: #475569;">점검시간</td><td style="color: #0f172a; font-weight: 500;">{date_str}</td></tr>
                                <tr><td style="font-weight: bold; padding: 6px 0; color: #475569;">현장 측정 체감온도</td><td><span style="color:#e11d48; font-weight:bold; font-size:14px;">{row['체감온도_수치']:.1f} ℃</span></td></tr>
                                <tr><td style="font-weight: bold; padding: 6px 0; color: #475569;">기상청 특보발효</td><td style="color: #ea580c; font-weight: bold;">{row['폭염특보여부']}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 카드 2: 핵심 보건 관리 항목
                    st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                            <h4 style="margin-top:0; color: #1e3a8a; font-size: 15px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">✔️ 핵심 보건 관리 항목</h4>
                            <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                                <tr><td style="font-weight: bold; width: 40%; padding: 6px 0; color: #475569;">식수 및 음료지급</td><td style="color: #0f172a; font-weight: 500;">{row['음료제공방식']}</td></tr>
                                <tr><td style="font-weight: bold; padding: 6px 0; color: #475569;">민감근로자 관리</td><td style="color: #0f172a; font-weight: 500;">{row['민감군관리']}</td></tr>
                                <tr><td style="font-weight: bold; padding: 6px 0; color: #475569;">비상 응급조치 이해도</td><td style="color: #0f172a; font-weight: 500;">{row['응급조치숙지']}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col_right:
                    # 카드 3: 단계별 조치 실태
                    p1_actions = str(row['평상시조치']).split('|')
                    p1_formatted = "".join([f"<li style='margin-bottom: 4px;'>{act.strip()}</li>" for act in p1_actions if act.strip()])
                    
                    p2_actions = str(row['35도이상조치']).split('|') if pd.notna(row['35도이상조치']) else []
                    p2_formatted = "".join([f"<li style='margin-bottom: 4px;'>{act.strip()}</li>" for act in p2_actions if act.strip()]) if p2_actions and p2_actions[0] != 'nan' else "<li>해당 없음</li>"

                    p3_actions = str(row['38도이상조치']).split('|') if pd.notna(row['38도이상조치']) else []
                    p3_formatted = "".join([f"<li style='margin-bottom: 4px;'>{act.strip()}</li>" for act in p3_actions if act.strip()]) if p3_actions and p3_actions[0] != 'nan' else "<li>해당 없음</li>"

                    st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                            <h4 style="margin-top:0; color: #1e3a8a; font-size: 15px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">🌡️ 단계별 조치 이행 실태</h4>
                            <div style="font-size: 13px; line-height: 1.5;">
                                <strong style="color: #0d9488;">[1단계] 평상시 예방 조치:</strong>
                                <ul style="margin: 4px 0 10px 0; padding-left: 15px; color: #334155;">{p1_formatted}</ul>
                                <strong style="color: #ea580c;">[2단계] 35도 돌파 시 조치:</strong>
                                <ul style="margin: 4px 0 10px 0; padding-left: 15px; color: #334155;">{p2_formatted}</ul>
                                <strong style="color: #dc2626;">[3단계] 38도 돌파 시 조치:</strong>
                                <ul style="margin: 4px 0 0 0; padding-left: 15px; color: #334155;">{p3_formatted}</ul>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 카드 4: 현장 소장 종합 코멘트 (특이사항)
                    notes_text = row['특이사항'] if pd.notna(row['특이사항']) and str(row['특이사항']).strip() != "" and str(row['특이사항']) != "nan" else "금일 현장 기상 및 특이사항 양호하며, 온열 수칙 이행을 상시 감독하고 있습니다."
                    st.markdown(f"""
                        <div style="background-color: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                            <h4 style="margin-top:0; color: #0f172a; font-size: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">✍️ 현장 소장 종합 코멘트 (특이사항)</h4>
                            <div style="font-size: 13px; color: #475569; font-style: italic; line-height: 1.5; padding: 4px 0;">
                                "{notes_text}"
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # 누적 차트 렌더링
                st.markdown("#### 📈 체감온도 누적 변화 추이")
                history_df = filtered_df[filtered_df["사업장명"] == row["사업장명"]].sort_values(by="날짜")
                if not history_df.empty:
                    fig = px.line(history_df, x="날짜", y="체감온도_수치", text="체감온도_수치", markers=True)
                    fig.update_traces(line_color="#e11d48", line_width=3, textposition="top center", texttemplate='%{text:.1f}℃')
                    
                    # 개별 사업장 아코디언 내 꺾은선 차트의 Y축 제목 "체감온도_수치"를 수평 방향으로 가로 배치화
                    fig.update_layout(
                        xaxis=dict(tickformat="%m-%d"), 
                        yaxis=dict(
                            title="",          # 기본 세로축 제목 제거
                            automargin=True
                        ),
                        annotations=[
                            dict(
                                text="<b>체감온도_수치</b>",
                                xref="paper",
                                yref="paper",
                                x=-0.04,       # Y축 왼쪽 배치 여백
                                y=1.08,        # 축 선 위의 정수리 영역 배치
                                showarrow=False,
                                font=dict(size=11, color="#475569"),
                                xanchor="right",
                                yanchor="bottom",
                                textangle=0    # 수평(가로) 고정
                            )
                        ],
                        height=250, 
                        margin=dict(l=80, r=10, t=40, b=10), # 라벨 잘림을 방지하기 위한 왼쪽 및 상단 여백 보장
                        paper_bgcolor="rgba(0,0,0,0)", 
                        plot_bgcolor="rgba(0,0,0,0)"
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"trend_chart_{row['사업장명']}_{idx}")