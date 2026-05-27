import csv
from flask import Flask, render_template
from rapidfuzz import process, fuzz, utils

app = Flask(__name__)

# 데이터 로드 및 전처리 함수
def load_data():
    # 1. 정식 사업장 DB 로드 (소속 팀 정보 매핑용)
    # { "정식사업장명": {"team": "관리1팀", "is_submitted": False}, ... }
    db_sites = {}
    with open('DB.csv', mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            site_name = row['사업장명'].strip()
            team_name = row['소속팀'].strip()
            db_sites[site_name] = {
                'team': team_name,
                'is_submitted': False  # 기본값은 미제출
            }

    # 퍼지 매칭을 위한 정식 사업장 이름 리스트 생성
    official_site_names = list(db_sites.keys())

    # 2. 현장 제출 데이터(오타 포함) 로드 및 퍼지 매칭 처리
    with open('data.csv', mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # C열인 '사업장명' 데이터 추출 (오타가 있을 수 있음)
            raw_site_name = row['사업장명'].strip() if row['사업장명'] else ""
            if not raw_site_name:
                continue
            
            # [퍼지 매칭 실행] 
            # utils.default_process를 통해 대소문자 통일 및 특수문자 제거 후 비교합니다.
            match_result = process.extractOne(
                raw_site_name, 
                official_site_names, 
                scorer=fuzz.WRatio,
                processor=utils.default_process
            )
            
            if match_result:
                best_match, score, index = match_result
                
                # 유사도 점수가 70점 이상인 경우에만 정상 제출로 인정
                if score >= 70:
                    db_sites[best_match]['is_submitted'] = True
                    print(f"[매칭 성공] 입력: '{raw_site_name}' -> 인식: '{best_match}' (유사도: {score:.1f}%)")
                else:
                    print(f"[매칭 실패] 입력: '{raw_site_name}' (유사한 정식 명칭을 찾지 못함. 점수: {score:.1f}%)")

    # 3. 템플릿으로 보낼 최종 데이터 가공 (팀별 통계 및 현장 리스트)
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

    # 팀별 제출률(%) 계산
    for team, data in teams_data.items():
        if data['total'] > 0:
            data['rate'] = int((data['submitted'] / data['total']) * 100)
        else:
            data['rate'] = 0

    return teams_data

@app.route('/')
def index():
    teams_data = load_data()
    return render_template('index.html', teams_data=teams_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)