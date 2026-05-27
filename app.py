import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz, utils

# 페이지 기본 설정 (와이드 모드)
st.set_page_config(page_title="온열질환 점검 대시보드", layout="wide")

st.title("☀️ 온열질환 예방점검 실시 현황")
st.markdown("---")

# 데이터 로드 및 퍼지 매칭 함수 (캐싱을 통해 속도 최적화)
@st.cache_data
def load_and_process_data():
    # 1. 정식 사업장 DB 로드
    db_df = pd.read_csv('DB.csv')
    db_df['사업장명'] = db_df['사업장명'].str.strip()
    db_df['소속팀'] = db_df['소속팀'].str.strip()
    
    # 매칭 상태를 추적하기 위한 사전 초기화
    db_sites = {
        row['사업장명']: {'team': row['소속팀'], 'is_submitted': False}
        for _, row in db_df.iterrows()
    }
    official_site_names = list(db_sites.keys())

    # 2. 제출 데이터 로드
    try:
        data_df = pd.read_csv('data.csv')
        # C열이 '사업장명'인지 확인 후 처리
        if '사업장명' in data_df.columns:
            for raw_name in data_df['사업장명'].dropna():
                raw_name = str(raw_name).strip()
                if not raw_name:
                    continue
                
                # 퍼지 매칭 실행 (유사도 70점 기준)
                match_result = process.extractOne(
                    raw_name, 
                    official_site_names, 
                    scorer=fuzz.WRatio,
                    processor=utils.default_process
                )
                
                if match_result:
                    best_match, score, _ = match_result
                    if score >= 70:
                        db_sites[best_match]['is_submitted'] = True
    except Exception as e:
        st.error(f"data.csv 파일을 읽는 중 오류가 발생했습니다: {e}")

    # 3. 팀별 데이터 가공
    teams_data = {
        '관리1팀': {'total': 0, 'submitted': 0, 'not_submitted_list': []},
        '관리2팀': {'total': 0, 'submitted': 0, 'not_submitted_list': []},
        '관리3팀': {'total': 0, 'submitted': 0, 'not_submitted_list': []},
        '영업2본부': {'total': 0, 'submitted': 0, 'not_submitted_list': []}
    }

    for site_name, info in db_sites.items():
        team = info['team']
        if team in teams_data:
            teams_data[team]['total'] += 1
            if info['is_submitted']:
                teams_data[team]['submitted'] += 1
            else:
                teams_data[team]['not_submitted_list'].append(site_name)

    return teams_data

# 데이터 가공 실행
teams_data = load_and_process_data()

# 화면에 4개 컬럼(팀별 카드) 생성
cols = st.columns(4)

for i, (team_name, data) in enumerate(teams_data.items()):
    with cols[i]:
        # 상단 통계 카드 스타일링
        rate = int((data['submitted'] / data['total'] * 100)) if data['total'] > 0 else 0
        
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; text-align: center; margin-bottom: 15px;">
            <h3 style="margin: 0; color: #333;">{team_name}</h3>
            <h1 style="margin: 10px 0; color: #007bff;">{rate}%</h1>
            <p style="margin: 0; color: #6c757d; font-size: 0.9rem;">(제출 {data['submitted']} / 전체 {data['total']})</p>
        </div>
        """, unsafe_allow_data_html=True)
        
        # 미실시 현장 드롭다운(Expander) 영역
        not_sub_count = len(data['not_submitted_list'])
        with st.expander(f"❌ 미실시 현장 ({not_sub_count}곳)", expanded=True):
            if not_sub_count == 0:
                st.write("✅ 모든 현장 제출 완료!")
            else:
                for site in data['not_submitted_list']:
                    st.markdown(f"""
                    <div style="background-color: #fff5f5; padding: 8px 12px; margin-bottom: 6px; border-left: 4px solid #e03131; border-radius: 4px; font-size: 0.95rem;">
                        {site}
                    </div>
                    """, unsafe_allow_data_html=True)