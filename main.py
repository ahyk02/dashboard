
# ============================================================
# 동네별 인구 피라미드
# Streamlit + Pandas + Plotly
# ============================================================

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏡",
    layout="wide",
)

# 따뜻한 색상을 사용하는 간단한 CSS
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF9F2;
    }

    h1, h2, h3 {
        color: #70452E;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #F0DFCE;
        padding: 16px;
        border-radius: 14px;
    }

    div[data-testid="stSelectbox"] label {
        color: #70452E;
        font-weight: 600;
    }

    .intro {
        color: #806B5A;
        font-size: 16px;
        line-height: 1.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 2. 데이터 불러오기
#    Streamlit Cloud가 실행될 때 CSV ZIP 파일을 읽습니다.
#    캐시를 사용해 화면이 바뀔 때마다 다시 내려받지 않습니다.
# ------------------------------------------------------------
DATA_URL = (
    "https://raw.githubusercontent.com/ahyk02/contents/main/"
    "population_ts_yearly_gender.zip"
)


@st.cache_data(ttl=3600, show_spinner="전국 인구 데이터를 불러오는 중...")
def load_population_data():
    # ZIP 주소를 read_csv에 바로 전달하면 압축 파일을 읽을 수 있습니다.
    df = pd.read_csv(
        DATA_URL,
        compression="zip",
        encoding="utf-8-sig",
        low_memory=False,
    )

    # 열 이름 양쪽에 공백이 있으면 제거합니다.
    df.columns = df.columns.astype(str).str.strip()

    # 연도 열이 숫자로 처리되도록 변환합니다.
    if "연도" not in df.columns:
        raise ValueError("'연도' 열을 찾을 수 없습니다.")

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"]).copy()
    df["연도"] = df["연도"].astype(int)

    # 가장 최신 연도만 남깁니다.
    latest_year = int(df["연도"].max())
    df = df.loc[df["연도"] == latest_year].copy()

    # 지역 이름은 문자열로 통일하고 불필요한 공백을 제거합니다.
    for col in ["시도", "시군구", "동"]:
        if col not in df.columns:
            raise ValueError(f"'{col}' 열을 찾을 수 없습니다.")

        df[col] = df[col].fillna("").astype(str).str.strip()

    # 나이별 남녀 인구 열을 찾습니다.
    # 예: 남_0세, 여_0세, 남_100세 이상
    male_cols = {}
    female_cols = {}

    for col in df.columns:
        male_match = re.fullmatch(r"남_(\d+)세", col)
        female_match = re.fullmatch(r"여_(\d+)세", col)

        if male_match:
            age = int(male_match.group(1))
            male_cols[age] = col

        elif female_match:
            age = int(female_match.group(1))
            female_cols[age] = col

        elif col == "남_100세 이상":
            male_cols[100] = col

        elif col == "여_100세 이상":
            female_cols[100] = col

    # 0~100세 이상까지 남녀 열이 모두 있는지 확인합니다.
    required_ages = list(range(101))
    missing_male = [age for age in required_ages if age not in male_cols]
    missing_female = [age for age in required_ages if age not in female_cols]

    if missing_male or missing_female:
        raise ValueError(
            "나이별 인구 열을 모두 찾지 못했습니다. "
            f"남자 누락 나이: {missing_male}, "
            f"여자 누락 나이: {missing_female}"
        )

    # 인구 데이터에 숫자가 아닌 값이 있으면 0으로 처리합니다.
    for col in list(male_cols.values()) + list(female_cols.values()):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df, latest_year, male_cols, female_cols


# ------------------------------------------------------------
# 3. 제목과 소개
# ------------------------------------------------------------
st.title("🏡 동네별 인구 피라미드")

st.markdown(
    """
    <p class="intro">
    우리 동네에는 어떤 연령대의 주민이 많을까요?<br>
    시도, 시군구, 동을 선택하면 최신 연도의 남녀 인구 구성을 확인할 수 있어요.
    </p>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 4. 데이터 읽기 및 오류 안내
# ------------------------------------------------------------
try:
    df, latest_year, male_cols, female_cols = load_population_data()

except Exception as e:
    st.error("인구 데이터를 불러오는 중 문제가 발생했습니다.")
    st.info(
        "인터넷 연결과 데이터 주소를 확인한 후 다시 시도해 주세요. "
        "오류가 계속되면 CSV의 열 이름과 형식을 확인해 주세요."
    )
    with st.expander("오류 상세 내용"):
        st.code(str(e))
    st.stop()


# ------------------------------------------------------------
# 5. 지역 선택 드롭다운 3개
#    상위 지역을 고르면 아래 선택 항목이 자동으로 좁혀집니다.
# ------------------------------------------------------------
st.subheader("📍 우리 동네 선택")

col1, col2, col3 = st.columns(3)

with col1:
    sido_options = sorted(
        [v for v in df["시도"].unique() if v]
    )

    selected_sido = st.selectbox(
        "① 시도",
        options=sido_options,
        index=0 if sido_options else None,
        key="selected_sido",
        placeholder="시도를 선택하세요",
    )

# 선택한 시도에 해당하는 시군구만 표시합니다.
sido_df = df[df["시도"] == selected_sido]

with col2:
    sigungu_options = sorted(
        [v for v in sido_df["시군구"].unique() if v]
    )

    selected_sigungu = st.selectbox(
        "② 시군구",
        options=sigungu_options,
        index=0 if sigungu_options else None,
        key="selected_sigungu",
        placeholder="시군구를 선택하세요",
    )

# 선택한 시군구에 해당하는 동만 표시합니다.
sigungu_df = sido_df[sido_df["시군구"] == selected_sigungu]

with col3:
    dong_options = sorted(
        [v for v in sigungu_df["동"].unique() if v]
    )

    selected_dong = st.selectbox(
        "③ 동",
        options=dong_options,
        index=0 if dong_options else None,
        key="selected_dong",
        placeholder="동을 선택하세요",
    )


# ------------------------------------------------------------
# 6. 선택한 지역의 남녀 인구 계산
#    같은 지역에 여러 행이 있으면 나이별 인구를 합산합니다.
# ------------------------------------------------------------
if not selected_sido or not selected_sigungu or not selected_dong:
    st.warning("시도, 시군구, 동을 모두 선택해 주세요.")
    st.stop()

selected_df = df[
    (df["시도"] == selected_sido)
    & (df["시군구"] == selected_sigungu)
    & (df["동"] == selected_dong)
]

if selected_df.empty:
    st.warning("선택한 지역의 인구 자료가 없습니다.")
    st.stop()

# 나이 라벨을 0세부터 100세 이상까지 순서대로 만듭니다.
age_labels = [f"{age}세" for age in range(100)] + ["100세 이상"]

# 나이별 남녀 인구를 각각 합산합니다.
male_population = [
    int(selected_df[male_cols[age]].sum())
    for age in range(101)
]

female_population = [
    int(selected_df[female_cols[age]].sum())
    for age in range(101)
]

total_male = sum(male_population)
total_female = sum(female_population)
total_population = total_male + total_female


# ------------------------------------------------------------
# 7. 인구 요약 카드
# ------------------------------------------------------------
st.divider()

st.subheader(f"📊 {selected_sido} {selected_sigungu} {selected_dong}")

st.caption(f"기준 연도: {latest_year}년")

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric("전체 인구", f"{total_population:,}명")

with metric2:
    st.metric("남자 인구", f"{total_male:,}명")

with metric3:
    st.metric("여자 인구", f"{total_female:,}명")


# ------------------------------------------------------------
# 8. 인구 피라미드 그리기
#    남자 인구는 음수로 만들어 왼쪽에 표시합니다.
#    여자 인구는 양수로 만들어 오른쪽에 표시합니다.
# ------------------------------------------------------------
st.subheader("👥 연령별 인구 피라미드")

fig = go.Figure()

# 남자: 왼쪽의 주황색 막대
fig.add_trace(
    go.Bar(
        name="남자",
        y=age_labels,
        x=[-value for value in male_population],
        orientation="h",
        marker_color="#D98A65",
        customdata=male_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "남자 인구: %{customdata:,}명"
            "<extra></extra>"
        ),
    )
)

# 여자: 오른쪽의 차분한 분홍색 막대
fig.add_trace(
    go.Bar(
        name="여자",
        y=age_labels,
        x=female_population,
        orientation="h",
        marker_color="#E8A7A1",
        customdata=female_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "여자 인구: %{customdata:,}명"
            "<extra></extra>"
        ),
    )
)

# 좌우 축의 크기를 동일하게 맞춰 비교하기 쉽게 합니다.
max_population = max(
    max(male_population, default=0),
    max(female_population, default=0),
    1,
)

# 축 눈금은 인구수를 양수 형태로 표시합니다.
# 실제 남자 데이터는 왼쪽으로 가도록 음수인 상태를 유지합니다.
tick_step = max(1, int(max_population / 4))
tick_limit = ((max_population + tick_step - 1) // tick_step) * tick_step

tick_values = list(range(-tick_limit, tick_limit + 1, tick_step))
tick_text = [f"{abs(value):,}" for value in tick_values]

fig.update_layout(
    template="plotly_white",
    height=1500,
    barmode="overlay",
    bargap=0.12,
    title={
        "text": f"{selected_dong} 연령별 남녀 인구",
        "x": 0.5,
        "xanchor": "center",
        "font": {"size": 22, "color": "#70452E"},
    },
    xaxis={
        "title": "인구수 (명)",
        "range": [-tick_limit, tick_limit],
        "tickmode": "array",
        "tickvals": tick_values,
        "ticktext": tick_text,
        "zeroline": True,
        "zerolinewidth": 2,
        "zerolinecolor": "#B8A99A",
        "gridcolor": "#F0E5DA",
    },
    yaxis={
        "title": "나이",
        "type": "category",

        # 핵심: 나이 라벨을 0세부터 100세 이상까지 고정합니다.
        # y축을 통째로 뒤집거나 인구수 크기로 정렬하지 않습니다.
        "categoryorder": "array",
        "categoryarray": age_labels,

        # 첫 번째 범주인 0세가 아래쪽에 오도록 별도로 지정합니다.
        "autorange": "normal",
        "tickmode": "array",
        "tickvals": age_labels,
        "ticktext": age_labels,
        "gridcolor": "#F8F0E8",
        "automargin": True,
    },
    legend={
        "title": "성별",
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.01,
        "xanchor": "center",
        "x": 0.5,
    },
    paper_bgcolor="#FFF9F2",
    plot_bgcolor="#FFFDF9",
    font={"family": "Arial, sans-serif", "color": "#594638"},
    margin={"l": 100, "r": 40, "t": 100, "b": 70},
)

st.plotly_chart(fig, use_container_width=True)

# 축 순서가 올바른지 코드에서도 확인합니다.
# categoryarray의 첫 항목은 0세, 마지막 항목은 100세 이상입니다.
assert age_labels[0] == "0세"
assert age_labels[-1] == "100세 이상"

st.caption(
    "왼쪽은 남자, 오른쪽은 여자입니다. "
    "막대에 마우스를 올리면 해당 연령대의 인구수를 확인할 수 있어요."
)

st.markdown(
    """
    **그래프 읽는 방법**
    - 왼쪽 주황색 막대가 길수록 해당 나이의 남자 인구가 많습니다.
    - 오른쪽 분홍색 막대가 길수록 해당 나이의 여자 인구가 많습니다.
    - 아래쪽은 어린 연령대, 위쪽은 높은 연령대입니다.
    """
)

# ------------------------------------------------------------
# 끝
# ------------------------------------------------------------
