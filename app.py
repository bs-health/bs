import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
from datetime import datetime, timedelta, timezone

# ==========================================
# 💡 [관리자 전용] 영구 오타 교정 사전 (Single Source of Truth)
# ==========================================
# 현장에서 자주 틀리게 입력하는 사업장명이 있다면 아래 형식에 맞춰 계속 추가하세요.
# 형식: '현장이입력한이상한이름': 'DB에등록된정확한명칭'
# 주의: 영어는 모두 소문자로, 띄어쓰기는 없이 붙여서 작성해야 완벽히 인식됩니다.
CUSTOM_TYPO_MAPPING = {
    '서울보증': '서울보증보험',
    '현대차전주하이테크': '현대자동차전주하이테크',
    '쿠팡광주1FC': '쿠팡경기광주1센터',
    '슈피겐빌딩': '슈피겐HQ빌딩',
    '경주교원드림센터': '교원경주드림센터',
    '원주공장kgc': 'kgc원주공장',
    '성지1차오피스텔': '성지하이츠1',
    '한남동청암빌딩': '청암빌딩',
    '교원성수채영병': '성수물류센터',
    '현대자동차군산하이테크센터': '현대차 군산하이테크',
    '교원경주드림': '교원경주드림센터',
    '용산LGU+사옥': 'LG유플러스 용산사옥',
    '경주교원드림': '교원경주드림센터',
    '쿠팡안성5쎈타': '쿠팡안성5센터',
    '교원안성물류센터': '안성교원물류',
    '홍익대(서울)': '홍익대학교서울',
    '쿠팡양지4,7센타': '쿠팡양지4,7센터',
    '양지3센타': '쿠팡양지3센터',
    '가든5툴': '가든파이브툴',               
    'LGCNS증미통합이행센터': 'NH서울타워LGCNS',
    '가든5툴백상코퍼레이션': '가든파이브툴',
    '가든파이툴': '가든파이브툴',             
    '쿠팡경산1,2fc': '쿠팡경산1,2센터',
    '쿠팡양지4&7센터': '쿠팡양지4,7센터',
    '쿠팡양지4&7센타': '쿠팡양지4,7센터',
    '쿠팡인천TW': '쿠팡인천TW센터',
    '현대자동차군산하이테크': '현대차 군산하이테크',
    '교원대구빌딩': '대구교원',
    '쿠팡평택5센타': '쿠팡평택5센터',
# 💡 슈피겐코리아 예외 처리 (공백 제거, K->k 소문자 적용)
    '슈피겐코리아k231인천물류센터': '슈피겐인천물류센터',
    '한남동청암빌딩': '청암빌딩',
    '국립소방병원': '소방병원',
    'LG사이언스파크_DP3_동측1차부지': '사이언스파크DP3',
    '쿠팡양산1fc': '쿠팡양산1센터',
    '여수세이지우드': '세이지우드',
    '곤지암2': '쿠팡곤지암2센터',
    '쿠팡13센터': '쿠팡인천13센터',
    '교원파주물류센타': '파주교원물류센터',
    'LG에너지솔루션 과천R&D캠퍼스': '에너지솔루션과천',
    '안성8FC': '쿠팡안성8센터',
    '현대자동차부산하이테크센터': '현대차부산하이테크',
    '분당퍼스트타워,백상코퍼레이션': '퍼스트타워',
    '현대자동차전주공장미화팀': '전주현대자동차',
    '모비스의왕연구소': '의왕연구소',
    '파크원LG에너지솔루션': '파크원에너지솔루션',
    '용산LGU+사옥': 'LG유플러스 용산사옥',
    'KB증권대치사옥': 'KB증권대치',
    '효성해링턴스퀘어': '공덕해링턴스퀘어',
    '쿠팡이천1센타': '쿠팡이천1센터',
    '쿠팡경산1,2': '쿠팡경산1,2센터',
    '쿠파인천16센타': '쿠팡인천16센터',
    '인하대병원정서타운': '정석빌딩',
    '쿠팡인천5센타': '쿠팡인천5센터',
    '쿠팡평택5센타': '쿠팡평택5센터',
    'KB국민은행연수원대천연수원': '국민은행대천연수원',
    '천경을지로운영센터': '을지로타워',
    '파크원LG에너지솔루션': '파크원에너지솔루션',
    '국민건강보험공단별관': '건강보험공단별관',
    '경주교원드림센터임현석': '교원경주드림센터',
    '교원일산빌딩': '일산후곡빌딩',
    '전주자동차': '전주현대자동차',
    '교원파주물류센터': '파주교원물류센터',
    '교원파주물류센타': '파주교원물류센터',
    '현대자동차금정지점': '현대차금정지점',
    '현대자동차부산하이테크센터': '현대차부산하이테크',
    '홍대세종캠시설': '홍대세종캠퍼스시설',
    '매리츠화재부천사옥': '메리츠화재부천',
    '백상엘리츠1차': '백상앨리츠1차',
    '알엠물류센터': '알앰물류센터',
    '쿠팡안성8센타': '쿠팡안성8센터',
    '용산LGU+': 'LG유플러스용산사옥',
    '쿠팡1fc': '쿠팡 이천1센터',
    '교직원공제여의도': '교직원공제회여의도',
    '쿠파민천16센터': '쿠팡인천16센터',
    '가평교원비전센터': '교원가평비전센터',
    '파주교원물류센타': '파주교원물류센터',
    '국민은행친한연수원': '국민은행천안연수원',
    'KB증권울산사옥': 'KB증권남울산',
    'NH통합IT센터': '농협통합IT센터',
    '서울예대캠버스': '서울예대캠퍼스',
    '마곡뉴파워프라자': '뉴파워프라즈마',
    '현대차전주하이테크센터': '현대자동차전주하이테크',
    '현대자동차군산하이테크센터': '현대차군산하이테크',
    '용산LGU+사옥': 'LG유플러스용산사옥',    
    ',쿠팡13센터': '쿠팡인천13센터',
    '구팡용인3,5FC': '쿠팡용인3,5센터',
    '슈피겐코리아K231인천물류': '슈피겐인천물류센터',
    '쿠팡아성5센터': '쿠팡안성5센터',
    '쿠팡인천16세터': '쿠팡인천16센터',
    '백상개발(성수BS)': 'BS성수타워',
    '마곡건와빋딩': '건와빌딩',
    '장재식': '백상빌딩',
    '분당퍼스타워,백상코퍼레이션': '퍼스트타워',
    '한진임천국제물류센터': '인천국제물류센터',
    '가평교원비던센터': '교원가평비전센터',
    '양지3쎈타': '쿠팡양지3센터',
    '쿱팡호법1FC': '쿠팡호법1센터',
    '쿠팡양지4.7센타': '쿠팡양지4,7센터',
    '가평교원밴센터': '가평교원비전센터',
# 예시 추가: '뉴파워프라즈마마곡신기술센터': '뉴파워프라즈마'
}

# ==========================================
# ⚙️ 테스트 편의를 위한 샘플 CSV 파일 자동 생성 모듈
# ==========================================
def create_sample_files_if_missing():
    """DB.csv와 data.csv 파일이 없을 때 예시 데이터 파일들을 자동으로 만들어주는 든든한 헬퍼 함수"""
    kst = timezone(timedelta(hours=9))
    today_str = datetime.now(kst).strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(kst) - timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago_str = (datetime.now(kst) - timedelta(days=2)).strftime("%Y-%m-%d")

    # DB.csv 생성 (기준 마스터 데이터)
    if not os.path.exists("DB.csv"):
        sample_db = pd.DataFrame({
            "관리팀": [
                "관리1팀", "관리1팀", "관리1팀", 
                "관리2팀", "관리2팀", "관리2팀", 
                "관리3팀", "관리3팀", 
                "영업2본부", "영업2본부"
            ],
            "현장명": [
                "가든파이브툴", "쿠팡경산1,2센터", "대구교원",
                "교원경주드림센터", "쿠팡인천TW센터", "쿠팡양지4,7센터",
                "현대차 군산하이테크", "소방병원",
                "서울보증보험", "사이언스파크DP3"
            ]
        })
        sample_db.to_csv("DB.csv", index=False, encoding="utf-8-sig")

    # data.csv 생성 (점검 일지 데이터)
    if not os.path.exists("data.csv"):
        sample_data = pd.DataFrame([
            {
                "날짜": today_str, "작성자": "김지킴", "사업장명": "가든5툴", "체감온도": "34.2℃", "폭염특보여부": "주의보",
                "평상시조치": "시원한 생수 제공 완료 | 휴게공간 그늘막 정비 | TBM 보건교육 진행", "35도이상조치": "N/A", "38도이상조치": "N/A",
                "음료제공방식": "냉온수기 수시 세척 및 개인 텀블러 사용 권장", "민감군관리": "혈압 이상자 정기 자가측정 유도", "응급조치숙지": "예",
                "특이사항": "현장 온열예방 이행 실태 최적 수준 유지 중"
            },
            {
                "날짜": today_str, "작성자": "박안전", "사업장명": "쿠팡경산1,2fc", "체감온도": "36.8℃", "폭염특보여부": "경보",
                "평상시조치": "물/소금 공급 완료 | 에어컨 필터 세척 후 가동 | 의무 휴식시간 부여", "35도이상조치": "옥외 무리한 작업 축소 및 휴식 15분 확대", "38도이상조치": "N/A",
                "음료제공방식": "정수용 얼음 및 식염포도당 자동 배출기 가동", "민감군관리": "민감 대상 근로자 2명 개별 집중 대화 관리 진행", "응급조치숙지": "예",
                "특이사항": "폭염 특보에 따른 집중 단축근무 가이드라인 시행"
            },
            {
                "날짜": yesterday_str, "작성자": "최관리", "사업장명": "서울보증", "체감온도": "31.5", "폭염특보여부": "일반",
                "평상시조치": "음용수 정수 상태 점검 | 실내 공기 순환용 팬 풀 가동", "35도이상조치": "N/A", "38도이상조치": "N/A",
                "음료제공방식": "개별 생수 및 냉장고 얼음 제공", "민감군관리": "특이 근로자 없음", "응급조치숙지": "예",
                "특이사항": "사무동 실내 미화 작업으로 온열 스트레스 수준 낮음"
            },
            {
                "날짜": two_days_ago_str, "작성자": "박안전", "사업장명": "쿠팡경산1,2fc", "체감온도": "33.5℃", "폭염특보여부": "주의보",
                "평상시조치": "이온음료 보충 | 선풍기 증설", "35도이상조치": "N/A", "38도이상조치": "N/A",
                "음료제공방식": "시원한 이온음료 제공", "민감군관리": "해당 사항 없음", "응급조치숙지": "예",
                "특이사항": "이상 없음"
            }
        ])
        sample_data.to_csv("data.csv", index=False, encoding="utf-8-sig")

create_sample_files_if_missing()

# ==========================================
# 1. 페이지 기본 설정 및 반응형 테마 적용 
# ==========================================
st.set_page_config(
    page_title="백상가족 건강한 여름나기 종합 대시보드",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 반응형 디자인 및 사용자 편의성 향상을 위한 커스텀 스타일 정의
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: 900; }
    .stAlert { border-radius: 16px; }
    .custom-card {
        background-color: var(--secondary-background-color); padding: 20px; border-radius: 16px;
        border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); margin-bottom: 20px;
    }
    table { font-size: 14px !important; }
    .stButton>button { border-radius: 8px; width: 100%; }
    
    .status-box { padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 13px; border: 1px solid rgba(128, 128, 128, 0.2); text-align: left; }
    .missing-box { background-color: transparent; border: 1px solid rgba(128, 128, 128, 0.4); font-weight: normal; }
    .done-box { background-color: rgba(34, 197, 94, 0.1); border-left: 4px solid #22c55e; }
    
    div.stButton > button[key^="toggle_missing_"], div.stButton > button[key^="toggle_done_"] {
        background-color: transparent !important;
        color: var(--text-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
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
        background-color: rgba(128, 128, 128, 0.1) !important;
        border-color: var(--text-color) !important;
    }
    div.stButton > button[key^="toggle_done_"]:hover {
        background-color: rgba(239, 68, 68, 0.1) !important;
        border-color: #ef4444 !important;
    }
    
    .report-card {
        background-color: var(--secondary-background-color);
        padding: 18px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 15px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }
    .report-card h4 {
        margin-top: 0;
        margin-bottom: 12px;
        font-size: 15px;
        border-bottom: 2px solid rgba(128, 128, 128, 0.2);
        padding-bottom: 8px;
    }
    .info-table {
        width: 100%;
        border-collapse: collapse;
    }
    .info-table td {
        padding: 6px 0;
        font-size: 13.5px;
        vertical-align: top;
        color: var(--text-color);
    }
    .info-table td.label {
        font-weight: bold;
        width: 35%;
        opacity: 0.7;
    }
    .action-step {
        font-size: 13.5px;
        line-height: 1.6;
    }
    .action-step strong {
        display: block;
        margin-top: 8px;
        margin-bottom: 4px;
    }
    .action-step ul {
        margin: 0;
        padding-left: 18px;
    }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "manual_done_sites.txt"

# ==========================================
# 임시 수동 입력 파일 로드 (날짜별 영구 보존 및 자동 마이그레이션 적용)
# ==========================================
def load_manual_sites():
    kst = timezone(timedelta(hours=9))
    today_str = datetime.now(kst).strftime("%Y-%m-%d")
    
    raw_sites = set()
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                raw_sites = set([line.strip().lower() for line in f.readlines() if line.strip()])
        except Exception as e:
            st.error(f"수동 조치 파일 로드 중 이상이 발견되었습니다: {e}")
            
    # 💡 [보완] 날짜 구분이 없는 레거시 데이터 발견 시 현재 오늘 날짜로 바인딩 마이그레이션 실행
    migrated = False
    clean_sites = set()
    for item in raw_sites:
        if '|' not in item:
            clean_sites.add(f"{item}|{today_str}")
            migrated = True
        else:
            clean_sites.add(item)
            
    if migrated:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                for site in sorted(clean_sites):
                    f.write(f"{site}\n")
        except:
            pass
            
    return clean_sites

def add_manual_site(site_with_date):
    current_sites = load_manual_sites()
    current_sites.add(site_with_date.strip().lower())
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            for site in sorted(current_sites):
                f.write(f"{site}\n")
    except Exception as e:
        st.error(f"수동 승인 정보 저장 중 실패: {e}")
    st.session_state['manual_done_sites'] = current_sites

def remove_manual_site(site_with_date):
    current_sites = load_manual_sites()
    current_sites.discard(site_with_date.strip().lower())
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            for site in sorted(current_sites):
                f.write(f"{site}\n")
    except Exception as e:
        st.error(f"수동 승인 변경사항 저장 중 실패: {e}")
    st.session_state['manual_done_sites'] = current_sites


# Session State 기본값 초기화
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
    # 특수 문자 및 띄어쓰기를 완벽하게 정제
    name = str(name).replace(" ", "").lower().strip()
    name = re.sub(r'[ㄱ-ㅎㅏ-ㅣ]', '', name)
    
    # [적용] CUSTOM_TYPO_MAPPING을 이용한 글로벌 오타 정정 체계 호출
    early_mapping = {k.lower(): v.lower() for k, v in CUSTOM_TYPO_MAPPING.items()}
    name = early_mapping.get(name, name)
    
    # 예외 리스트 원본 보존 검사
    protected_names = [v.lower() for v in CUSTOM_TYPO_MAPPING.values()]
    if name in protected_names:
        return name

    # 잔여 명칭 규격화 표준 필터 적용
    name = name.replace('현장', '').replace('지점', '')
    name = name.replace('샌타', '센터')
    name = name.replace('fc', '센터')
        
    name_mapping = {'성우프로젝트': '성우', '성우건설': '성우', '(주)성우': '성우'}
    name_mapping = {k.lower(): v.lower() for k, v in name_mapping.items()}
    
    return name_mapping.get(name, name)


def standardize_site_name(name, valid_db_names):
    name = standardize_site_name_base(name)
    if valid_db_names:
        for db_name in sorted(valid_db_names, key=len, reverse=True):
            if db_name.lower() in name.lower() or name.lower() in db_name.lower():
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
    df['특보발효건수'] = df['폭염특보여부'].astype(str).apply(lambda x: 1 if any(kw in x for kw in ['발표됨', '예', '경보', '주의보']) else 0)
    
    return df

# 💡 [버그 수정 완료] KeyError를 발생시키던 불필요한 매핑 로직을 안전한 다이렉트 슬라이싱 및 정제 코드로 복구했습니다.
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
    
    csv_dates = raw_df['비교용_날짜'].dropna().unique().tolist()
    manual_dates = []
    for item in st.session_state['manual_done_sites']:
        if '|' in item:
            parts = item.split('|')
            if len(parts) >= 2:
                try:
                    parsed_date = datetime.strptime(parts[1].strip(), "%Y-%m-%d").date()
                    manual_dates.append(parsed_date)
                except ValueError:
                    pass
                    
    combined_dates_set = set(csv_dates + manual_dates)
    available_dates = sorted(list(combined_dates_set), reverse=True)
    
    if current_today in available_dates:
        default_idx = available_dates.index(current_today)
    else:
        default_idx = 0 
        if available_dates:
            st.sidebar.warning(f"⚠️ 금일({current_today}) 데이터가 아직 제출되지 않아, 가장 최근 일자로 자동 매칭되었습니다.")

    if available_dates:
        today_kst = st.selectbox("📅 모니터링 기준일 선택", available_dates, index=default_idx, key="monitoring_date_select")
        filtered_df = raw_df[raw_df['비교용_날짜'] <= today_kst]
    else:
        today_kst = current_today
        filtered_df = pd.DataFrame()

    date_str_key = str(today_kst)

    # 💡 [보안] 현재 선택된 일자(date_str_key)에 일치하는 수동 저장 내역만 타겟팅하여 수집 (이월 방지 핵심 구조)
    current_day_done_sites = set()
    for item in st.session_state['manual_done_sites']:
        if '|' in item:
            s_name, s_date = item.split('|', 1)
            if s_date == date_str_key:
                current_day_done_sites.add(s_name.lower().strip())

    # 🔐 관리자 인증 시스템
    st.markdown("---")
    st.markdown("### 🔐 관리자 시스템")
    admin_password = st.text_input("관리자 비밀번호 입력", type="password")
    is_admin = (admin_password == "1234")
    
    if is_admin:
        st.success("🔑 관리자 권한 확인")
        st.markdown("##### 🛠️ 사이드바 조작창")
        
        st.info("⚠️ 수동 지정된 내역은 파일에 등록되어 영구적으로 보존됩니다. 단, 신규 data.csv 업로드로 서버 환경이 리셋되면 소멸할 수 있으므로, 실제 결과 보고서 작성을 위해 나중에 원본 엑셀에도 꼭 반영해 주세요.")
        
        today_submitted_raw = [s.lower().strip() for s in (filtered_df[filtered_df['비교용_날짜'] == today_kst]['사업장명'].dropna().unique().tolist() if not filtered_df.empty else [])]
        
        if not db_master.empty:
            missing_sites_for_admin = db_master[
                (~db_master['표준현장명'].str.lower().str.strip().isin(today_submitted_raw)) & 
                (~db_master['표준현장명'].str.lower().str.strip().isin(current_day_done_sites))
            ]['현장명'].unique().tolist()
            
            if missing_sites_for_admin:
                missing_sites_for_admin.sort()
                selected_site = st.selectbox("당일 임시 실시로 변경할 현장", missing_sites_for_admin)
                if st.button("선택 현장 '실시'로 강제 전환 (당일 유지)"):
                    standard_name = standardize_site_name(selected_site, valid_db_names_tuple)
                    add_manual_site(f"{standard_name.strip()}|{date_str_key}")
                    st.toast(f"📢 [{selected_site}] 현장이 임시 실시 처리되었습니다.", icon="✅")
                    st.rerun()
            else:
                st.success("모든 사업장이 제출을 완료했습니다.")
                
            # 💡 [개선] 과거 데이터 안전 보장을 위한 날짜별 맞춤형 세분화 초기화 관리 메뉴 도입
            st.markdown("---")
            with st.expander("🗑️ 수동 조치 초기화 메뉴"):
                current_date_items = [item for item in st.session_state['manual_done_sites'] if item.endswith(f"|{date_str_key}")]
                if current_date_items:
                    if st.button(f"🔄 {date_str_key} 수동 조치만 초기화", key="reset_current_day"):
                        new_sites = {item for item in st.session_state['manual_done_sites'] if not item.endswith(f"|{date_str_key}")}
                        try:
                            with open(DB_FILE, "w", encoding="utf-8") as f:
                                for site in sorted(new_sites):
                                    f.write(f"{site}\n")
                        except Exception as e:
                            st.error(f"데이터 파일 수정 오류: {e}")
                        st.session_state['manual_done_sites'] = new_sites
                        st.toast(f"📢 [{date_str_key}] 자의 수동 조치 내역이 초기화되었습니다.")
                        st.rerun()
                else:
                    st.markdown(f"<div style='font-size: 12.5px; opacity:0.8;'>ℹ️ {date_str_key} 자에 등록된 수동 조치가 없습니다.</div>", unsafe_allow_html=True)
                
                if st.session_state['manual_done_sites']:
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                    st.warning("⚠️ 모든 날짜의 전체 기록을 소멸시키려면 아래 버튼을 사용하세요.")
                    if st.button("🚨 전체 날짜 수동 조치 영구 삭제", key="reset_all_history"):
                        if os.path.exists(DB_FILE):
                            try:
                                os.remove(DB_FILE)
                            except:
                                pass
                        st.session_state['manual_done_sites'] = set()
                        st.toast("모든 날짜의 전체 수동조치 이력이 삭제되었습니다.")
                        st.rerun()
                        
    elif admin_password:
        st.error("❌ 비밀번호가 틀렸습니다.")

# ==========================================
# 4. 화면 구성 및 메인 타이틀
# ==========================================
st.markdown("<h1 style='font-size: 2.5rem; margin-bottom: 0px;'>☀️ 백상가족 건강한 여름나기 종합 대시보드</h1>", unsafe_allow_html=True)
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
            existing_site_list = [s.lower().strip() for s in today_df['사업장명'].dropna().values] if not today_df.empty else []
            if m_site not in existing_site_list:
                original_site_row = db_master[db_master['표준현장명'].str.lower().str.strip() == m_site]
                original_site_name = original_site_row['현장명'].values[0] if not original_site_row.empty else m_site
                
                new_row = {col: "" for col in today_df.columns}
                new_row['사업장명'] = original_site_name
                new_row['체감온도_수치'] = 25.0 
                new_row['폭염특보여부'] = "일반"
                new_row['참여자'] = "본사 보건관리자 (수동승인)"
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

        g_critical = today_df[today_df['경보단계_명칭'].str.contains("중대경보")]["사업장명"].tolist()
        g_warning = today_df[today_df['경보단계_명칭'].str.contains("경보") & ~today_df['경보단계_명칭'].str.contains("중대경보")]["사업장명"].tolist()
        g_advisory = today_df[today_df['경보단계_명칭'].str.contains("주의보")]["사업장명"].tolist()
        g_normal = today_df[today_df['경보단계_명칭'].str.contains("일반")]["사업장명"].tolist()

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
            st.markdown(f'<div style="background-color: rgba(239, 68, 68, 0.1); border-left: 5px solid #ef4444; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #ef4444; font-size: 13px;">🔴 폭염중대경보</span><div style="font-size: 26px; font-weight: 900; color: #ef4444; margin-top: 5px;">{len(g_critical)}개소</div><p style="font-size: 11px; margin-top: 5px; opacity: 0.8; font-weight: bold;">{", ".join(g_critical) if g_critical else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div style="background-color: rgba(249, 115, 22, 0.1); border-left: 5px solid #f97316; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #f97316; font-size: 13px;">🟠 폭염경보</span><div style="font-size: 26px; font-weight: 900; color: #f97316; margin-top: 5px;">{len(g_warning)}개소</div><p style="font-size: 11px; margin-top: 5px; opacity: 0.8; font-weight: bold;">{", ".join(g_warning) if g_warning else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="background-color: rgba(234, 179, 8, 0.1); border-left: 5px solid #eab308; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #eab308; font-size: 13px;">🟡 폭염주의보</span><div style="font-size: 26px; font-weight: 900; color: #eab308; margin-top: 5px;">{len(g_advisory)}개소</div><p style="font-size: 11px; margin-top: 5px; opacity: 0.8; font-weight: bold;">{", ".join(g_advisory) if g_advisory else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div style="background-color: rgba(34, 197, 94, 0.1); border-left: 5px solid #22c55e; padding: 15px; border-radius: 12px; min-height: 120px;"><span style="font-weight: bold; color: #22c55e; font-size: 13px;">🟢 일반</span><div style="font-size: 26px; font-weight: 900; color: #22c55e; margin-top: 5px;">{len(g_normal)}개소</div><p style="font-size: 11px; margin-top: 5px; opacity: 0.8; font-weight: bold;">{", ".join(g_normal) if g_normal else "대상 현장 없음"}</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 전사 고온 위험 사업장 관리 현황 요약")
        
        summary_rows = []
        for idx, r in today_df.iterrows():
            badge = r['경보단계_명칭']
            if "일반" in badge: continue
            
            p1_text_raw = str(r['평상시조치'])
            if any(kw in p1_text_raw for kw in ['깨끗하고 시원한 물', '이온음료', '포도당', '식수']):
                water_status = '🟢'
            else:
                water_status = '🟢' if any(kw in p1_text_raw for kw in ['물', '음료', '식수', '포도당']) else '🔴'
                
            summary_rows.append({
                '사업장명': r['사업장명'], '경보단계': badge, '체감온도': f"{float(r['체감온도_수치']):.1f} ℃" if r['체감온도_수치'] != "" else "N/A",
                '물/음료': water_status,
                '그늘막': '🟢' if any(kw in p1_text_raw for kw in ['그늘', '휴게', '쉼터', '그늘막']) else '🔴',
                'TBM교육': '🟢' if any(kw in p1_text_raw for kw in ['교육', 'TBM', '안전보건']) else '🔴',
                '민감군': '🟢' if '예' in str(r['민감군관리']) or '관리' in str(r['민감군관리']) or any(kw in str(r['민감군관리']) for kw in ['이행', '완료']) else '🔴',
                '응급숙지': '🟢' if '예' in str(r['응급조치숙지']) or '이해' in str(r['응급조치숙지']) or '숙지' in str(r['응급조치숙지']) else '🔴'
            })
            
        if summary_rows:
            col_widths = [2.5, 2.2, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0]
            with st.container(height=450):
                cols = st.columns(col_widths, vertical_alignment="center")
                headers = ["사업장명 (클릭이동)", "경보단계", "체감온도", "물/음료", "그늘막", "TBM", "민감군", "응급숙지", "상세분석"]
                for i, text in enumerate(headers):
                    align = "left" if i==1 else "center"
                    cols[i].markdown(f"<div style='text-align: {align};'><b style='font-size: 13px; opacity: 0.8;'>{text}</b></div>", unsafe_allow_html=True)
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
            st.success("✅ 금일 기준 체감온도 33℃ 이상인 고온 우려 사업장이 존재하지 않습니다.")
            
    else:
        st.info("ℹ️ 선택한 기준일에 제출된 점검 결과가 부재합니다.")

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
            existing_site_list = [s.lower().strip() for s in today_df['사업장명'].dropna().values] if not today_df.empty else []
            if m_site not in existing_site_list:
                original_site_row = db_master[db_master['표준현장명'].str.lower().str.strip() == m_site]
                original_site_name = original_site_row['현장명'].values[0] if not original_site_row.empty else m_site
                
                new_row = {col: "" for col in today_df.columns}
                new_row['사업장명'] = original_site_name
                new_row['체감온도_수치'] = 25.0
                new_row['폭염특보여부'] = "일반"
                new_row['참여자'] = "본사 보건관리자 (수동승인)"
                new_row['평상시조치'] = "본사 이행 상태 확인"
                new_row['특이사항'] = "현장 점검 완료 임시 처리된 사업장입니다."
                today_df = pd.concat([today_df, pd.DataFrame([new_row])], ignore_index=True)

    site_df = today_df.sort_values('체감온도_수치', ascending=False).copy() if not today_df.empty else pd.DataFrame()
    
    if search_query:
        site_df = site_df[site_df["사업장명"].astype(str).str.contains(search_query, na=False) | site_df["참여자"].astype(str).str.contains(search_query, na=False)]

    if site_df.empty:
        st.info("조건에 일치하는 데이터 보고 내역이 없습니다.")
    else:
        for idx, row in site_df.iterrows():
            is_high = float(row["체감온도_수치"]) >= 35.0 if row["체감온도_수치"] != "" else False
            m_label = "🟢 일반보건" if is_high == False else "🔥 35도이상 집중관리"
            
            temp_val = row['체감온도_수치']
            temp_str = f"{float(temp_val):.1f}" if temp_val != "" else "N/A"
            
            header_title = f"[{m_label}] {row['사업장명']} (체감 {temp_str}°C) | 책임관리자: {row['참여자']}"
            is_auto_expand = (st.session_state.expanded_site == row['사업장명'])
            
            with st.expander(header_title, expanded=is_auto_expand):
                col_left, col_right = st.columns(2)
                
                with col_left:
                    p1_text_raw = str(row['평상시조치'])
                    if any(kw in p1_text_raw for kw in ['깨끗하고 시원한 물', '이온음료', '포도당', '식수']):
                        p1_text = "✅ 식수 및 음료 지급 실시 중"
                    else:
                        p1_text = row['음료제공방식'] if row['음료제공방식'] != "" else "데이터 미지정"
                        
                    p2_text = row['민감군관리'] if row['민감군관리'] != "" else "데이터 미지정"
                    p3_text = row['응급조치숙지'] if row['응급조치숙지'] != "" else "데이터 미지정"
                    
                    date_display = row['날짜_dt'].strftime('%Y-%m-%d') if pd.notna(row['날짜_dt']) and row['날짜_dt'] != "" else date_str_key
                    
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>📋 현장 기본 정보</h4>
                        <table class="info-table">
                            <tr><td class="label">보고자</td><td>{row['참여자']}</td></tr>
                            <tr><td class="label">점검시간</td><td>{date_display}</td></tr>
                            <tr><td class="label">측정 체감온도</td><td><span style="color:#e11d48; font-weight:bold;">{temp_str} ℃</span></td></tr>
                            <tr><td class="label">기상청 특보발효</td><td style="color:#ea580c; font-weight:bold;">{row['폭염특보여부'] if row['폭염특보여부'] != "" else "해당 사항 없음"}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>✔️ 핵심 보건 관리 항목</h4>
                        <table class="info-table">
                            <tr><td class="label">식수 및 음료지급</td><td style="font-weight:bold;">{p1_text}</td></tr>
                            <tr><td class="label">민감근로자 관리</td><td>{p2_text}</td></tr>
                            <tr><td class="label">비상 응급조치</td><td>{p3_text}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                with col_right:
                    p1_html = "".join([f"<li>{act.strip()}</li>" for act in str(row['평상시조치']).split('|') if act.strip()])
                    p2_html = "".join([f"<li>{act.strip()}</li>" for act in str(row['35도이상조치']).split('|') if act.strip() and act.strip() != 'nan'])
                    p3_html = "".join([f"<li>{act.strip()}</li>" for act in str(row['38도이상조치']).split('|') if act.strip() and act.strip() != 'nan'])
                    
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>🌡️ 단계별 조치 이행 실태</h4>
                        <div class="action-step">
                            <span style="color:#0d9488; font-weight:bold;">[1단계] 평상시 예방 조치:</span>
                            <ul style="opacity: 0.9; margin-bottom: 8px;">{p1_html if p1_html else "<li>제출 데이터 없음</li>"}</ul>
                            <span style="color:#ea580c; font-weight:bold; display:block;">[2단계] 35도 돌파 시 조치:</span>
                            <ul style="opacity: 0.9; margin-bottom: 8px;">{p2_html if p2_html else "<li>해당 사항 없음 (또는 미기재)</li>"}</ul>
                            <span style="color:#dc2626; font-weight:bold; display:block;">[3단계] 38도 돌파 시 조치:</span>
                            <ul style="opacity: 0.9;">{p3_html if p3_html else "<li>해당 사항 없음 (또는 미기재)</li>"}</ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    notes_text = row['특이사항'] if pd.notna(row['특이사항']) and str(row['특이사항']).strip() != "" and str(row['특이사항']) != "nan" else "금일 현장 기상 및 특이사항 양호합니다."
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>✍️ 현장 소장 종합 코멘트</h4>
                        <div style="font-size: 13.5px; opacity: 0.8; font-style: italic; line-height:1.5;">"{notes_text}"</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                if "수동승인" not in str(row['참여자']):
                    st.markdown("#### 📈 체감온도 누적 변화 추이")
                    history_df = filtered_df[filtered_df["사업장명"] == row["사업장명"]].sort_values(by="날짜")
                    if not history_df.empty:
                        fig = px.line(history_df, x="날짜", y="체감온도_수치", text="체감온도_수치", markers=True)
                        fig.update_traces(line_color="#e11d48", line_width=3, textposition="top center", texttemplate='%{text:.1f}℃')
                        fig.update_layout(xaxis=dict(tickformat="%m-%d"), yaxis=dict(title="", automargin=True), height=250, margin=dict(l=80, r=10, t=40, b=10))
                        st.plotly_chart(fig, use_container_width=True, key=f"trend_chart_{row['사업장명']}_{idx}")

# ------------------------------------------
# MODE 3: 팀별 실시 현황 (DB 연동)
# ------------------------------------------
elif st.session_state.current_tab == "✅ 팀별 실시 현황":
    st.subheader(f"📊 부서별 온열질환 체크리스트 관리 현황 ({today_kst.strftime('%Y-%m-%d')} 기준)")
    st.markdown("<p style='font-size: 13px; opacity: 0.8; margin-top: -10px;'>DB.csv 마스터 데이터의 [관리팀] 및 [현장명]을 기반으로, 당일 제출 완료 현장과 미실시 상태를 실시간 매칭합니다.</p>", unsafe_allow_html=True)

    if db_master.empty:
        st.error("⚠️ `DB.csv` 파일을 찾을 수 없거나 '관리팀', '현장명' 구조가 상이합니다. 양식을 점검해 주십시오.")
    else:
        today_df = filtered_df[filtered_df['비교용_날짜'] == today_kst].copy() if not filtered_df.empty else pd.DataFrame()
        
        submitted_sites = [s.lower().strip() for s in (today_df['사업장명'].dropna().unique().tolist() if not today_df.empty else [])]
        
        if current_day_done_sites:
            submitted_sites = list(set(submitted_sites + list(current_day_done_sites)))

        target_teams = ['관리1팀', '관리2팀', '관리3팀', '영업2본부']
        
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        for i, team in enumerate(target_teams):
            team_df = db_master[db_master['관리팀'] == team]
            total_count = len(team_df)
            
            submitted = team_df[team_df['표준현장명'].str.lower().str.strip().isin(submitted_sites)].sort_values(by='현장명')
            missing = team_df[~team_df['표준현장명'].str.lower().str.strip().isin(submitted_sites)].sort_values(by='현장명')
            
            sub_count = len(submitted)
            rate = int((sub_count / total_count * 100)) if total_count > 0 else 0
            
            cols = [col_t1, col_t2, col_t3, col_t4]
            with cols[i]:
                st.markdown(f"""
                <div style="background-color: var(--secondary-background-color); border-radius: 12px; padding: 15px; border: 1px solid rgba(128,128,128,0.2); box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 10px;">
                    <h3 style="margin-top:0; font-size: 18px; text-align: center;">{team}</h3>
                    <div style="text-align: center; margin-bottom: 10px;">
                        <span style="font-size: 32px; font-weight: bold; color: {'#22c55e' if rate == 100 else '#3b82f6'};">{rate}%</span>
                        <div style="font-size: 13px; opacity: 0.7;">(제출 {sub_count} / 전체 {total_count})</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                team_search_query = st.text_input(
                    f"🔍 {team} 미실시 검색", 
                    key=f"search_{team}", 
                    placeholder="사업장명 검색...",
                    label_visibility="collapsed"
                )
                
                if team_search_query:
                    filtered_missing = missing[missing['현장명'].astype(str).str.lower().str.contains(team_search_query.lower(), na=False)].sort_values(by='현장명')
                else:
                    filtered_missing = missing
                
                # ❌ 미실시 현장 관리 영역
                with st.expander(f"❌ 미실시 현장 ({len(filtered_missing)}곳)", expanded=True):
                    if not filtered_missing.empty:
                        for idx, row_missing in filtered_missing.iterrows():
                            site_raw_name = row_missing['현장명']
                            std_name = row_missing['표준현장명']
                            
                            if is_admin:
                                if st.button(f"{site_raw_name}", key=f"toggle_missing_{std_name}_{idx}"):
                                    add_manual_site(f"{std_name.strip()}|{date_str_key}")
                                    st.toast(f"📢 [{site_raw_name}] 현장이 {date_str_key} 자로 임시 실시 처리되었습니다.", icon="✅")
                                    st.rerun()
                            else:
                                st.markdown(f"<div class='status-box missing-box'>{site_raw_name}</div>", unsafe_allow_html=True)
                    else:
                        if team_search_query:
                            st.markdown("<div style='font-size: 13px; opacity: 0.7; text-align: center; padding: 10px;'>검색 결과가 없습니다.</div>", unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='font-size: 13px; color: #16a34a; text-align: center; padding: 10px;'>전원 제출 완료 🎉</div>", unsafe_allow_html=True)
                
                # ✅ 실시 완료 현장 관리 영역
                with st.expander(f"✅ 실시 완료 ({len(submitted)}곳)", expanded=False):
                    if not submitted.empty:
                        for idx, row_submitted in submitted.iterrows():
                            site_raw_name = row_submitted['현장명']
                            std_name = row_submitted['표준현장명']
                            
                            is_manual_activated = (f"{std_name.lower().strip()}|{date_str_key}" in st.session_state['manual_done_sites'])
                            
                            if is_admin and is_manual_activated:
                                if st.button(f"↩️ {site_raw_name}", key=f"toggle_done_{std_name}_{idx}"):
                                    remove_manual_site(f"{std_name.strip()}|{date_str_key}")
                                    st.toast(f"📢 [{site_raw_name}] 현장이 {date_str_key} 자로 다시 미실시 환원되었습니다.", icon="🔄")
                                    st.rerun()
                            else:
                                st.markdown(f"<div class='status-box done-box'><b>{site_raw_name}</b></div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='font-size: 13px; opacity: 0.7; text-align: center; padding: 10px;'>제출 내역 없음</div>", unsafe_allow_html=True)