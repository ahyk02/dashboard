import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(page_title="동네별 인구 피라미드", layout="wide")
st.title("🏘️ 동네별 인구 피라미드")
st.write("우리 동네의 연령별/성별 인구 구조를 따뜻한 톤의 차트로 확인해보세요!")

# ---------------------------------------------------------
# 2. 데이터 불러오기 함수
# @st.cache_data를 사용해 데이터를 한 번만 읽고 메모리에 저장(캐싱)합니다.
# ---------------------------------------------------------
@st.cache_data
def load_data():
    # 압축된 ZIP 파일 형태의 CSV를 pandas로 바로 읽어옵니다.
    url = "https://raw.githubusercontent.com/ahyk02/contents/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(url, compression='zip')
    return df

# 스피너(로딩 애니메이션)와 함께 데이터 로드
with st.spinner("데이터를 불러오는 중입니다..."):
    df = load_data()

# ---------------------------------------------------------
# 3. 데이터 전처리 (최신 연도 필터링)
# ---------------------------------------------------------
# 데이터에 있는 연도 중 가장 큰(최신) 연도를 찾습니다.
latest_year = df['연도'].max()
# 최신 연도의 데이터만 골라냅니다.
df_latest = df[df['연도'] == latest_year]

st.subheader(f"📅 {latest_year}년 기준 인구")

# ---------------------------------------------------------
# 4. 사용자 입력 (드롭다운 3개: 시도 -> 시군구 -> 동)
# ---------------------------------------------------------
# 화면을 3개의 열(컬럼)로 나눕니다.
col1, col2, col3 = st.columns(3)

with col1:
    # 중복 없는 '시도' 목록을 가져옵니다.
    sido_list = df_latest['시도'].dropna().unique()
    selected_sido = st.selectbox("시도 선택", sido_list)

with col2:
    # 선택된 '시도'에 해당하는 데이터만 필터링한 뒤, '시군구' 목록을 만듭니다.
    df_sigungu = df_latest[df_latest['시도'] == selected_sido]
    sigungu_list = df_sigungu['시군구'].dropna().unique()
    selected_sigungu = st.selectbox("시군구 선택", sigungu_list)

with col3:
    # 선택된 '시군구'에 해당하는 '동' 목록을 만듭니다.
    df_dong = df_sigungu[df_sigungu['시군구'] == selected_sigungu]
    dong_list = df_dong['동'].dropna().unique()
    selected_dong = st.selectbox("동 선택", dong_list)

# ---------------------------------------------------------
# 5. 차트 그리기 데이터 준비
# ---------------------------------------------------------
# 최종적으로 선택된 동네의 데이터만 남깁니다.
selected_data = df_dong[df_dong['동'] == selected_dong]

if not selected_data.empty:
    # 해당 동네 데이터의 첫 번째 행(series)을 가져옵니다.
    row = selected_data.iloc[0]

    # 세로축에 들어갈 나이 리스트를 만듭니다 ('0세', '1세', ..., '99세', '100세 이상').
    ages = [f"{i}세" for i in range(100)] + ["100세 이상"]

    male_pop = []
    female_pop = []

    # 나이별로 남/여 인구수를 추출합니다.
    for age in ages:
        male_col = f"남_{age}"
        female_col = f"여_{age}"
        
        # 값이 없으면 0으로 처리합니다.
        m_val = row[male_col] if male_col in row else 0
        f_val = row[female_col] if female_col in row else 0
        
        # **핵심**: 남자는 왼쪽으로 그래프가 그려지도록 음수(-)로 변환합니다.
        male_pop.append(-m_val) 
        # 여자는 오른쪽이므로 그대로 양수를 씁니다.
        female_pop.append(f_val)

    # ---------------------------------------------------------
    # 6. Plotly 인구 피라미드 차트 생성
    # ---------------------------------------------------------
    fig = go.Figure()

    # 남자 바 차트 추가 (음수 방향)
    fig.add_trace(go.Bar(
        y=ages, 
        x=male_pop, 
        orientation='h', # 가로 막대그래프
        name='남자',
        marker_color='#FF8A65', # 따뜻한 톤: 부드러운 코랄(주황)
        # 마우스 오버 시 음수가 아닌 절대값(양수)으로 보이도록 텍스트 설정
        text=[f"{abs(val):,}명" for val in male_pop], 
        hoverinfo='y+text'
    ))

    # 여자 바 차트 추가 (양수 방향)
    fig.add_trace(go.Bar(
        y=ages, 
        x=female_pop, 
        orientation='h',
        name='여자',
        marker_color='#FFD54F', # 따뜻한 톤: 부드러운 머스터드(노랑)
        text=[f"{val:,}명" for val in female_pop],
        hoverinfo='y+text'
    ))

    # 차트 세부 설정
    fig.update_layout(
        barmode='relative', # 막대들을 기준점(0)을 중심으로 양옆으로 배치
        title=f"📍 {selected_sido} {selected_sigungu} {selected_dong} 연령별 인구수",
        plot_bgcolor='white', # 깔끔한 흰색 배경
        yaxis=dict(
            title="나이",
            # **요청 사항 적용**: 세로축 나이를 0세부터 100세 이상까지 강제 고정합니다.
            categoryorder='array',
            categoryarray=ages 
        ),
        xaxis=dict(
            title="인구수",
            showticklabels=False, # x축 눈금 숫자는 양쪽이 -/+로 보여서 헷갈릴 수 있으므로 숨깁니다.
            zeroline=True, 
            zerolinecolor='lightgrey', 
            zerolinewidth=2 # 가운데 0 기준선을 회색으로 그어줍니다.
        ),
        hovermode='y', # 같은 나이의 남/여 정보를 마우스 오버 시 동시에 띄워줍니다.
        margin=dict(l=0, r=0, t=40, b=0)
    )

    # 스트림릿 화면에 차트를 그립니다.
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("선택하신 지역의 데이터가 존재하지 않습니다.")
