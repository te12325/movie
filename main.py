import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# 웹 앱 페이지 기본 설정 (제목, 레이아웃)
st.set_page_config(page_title="어제 박스오피스 순위", layout="wide")

st.title("🎬 어제 일별 박스오피스 순위")

# 1. KOBIS API 키 불러오기 (.streamlit/secrets.toml 또는 스트림릿 클라우드 Secrets에 설정된 키)
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 API 키가 설정되지 않았습니다. Streamlit Secrets에 KOBIS_KEY를 등록해 주세요.")
    st.info("""
    **확인 방법:**
    1. 스트림릿 클라우드 앱 설정의 **Secrets** 메뉴로 이동합니다.
    2. `KOBIS_KEY = "발급받은_인증키"` 형식으로 작성 후 저장하세요.
    """)
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# 2. 한국 시간(KST, UTC+9) 기준 어제 날짜 계산 (배포 서버 시계 기준 차이 방지)
kst_timezone = timezone(timedelta(hours=9))
today_kst = datetime.now(kst_timezone)
yesterday_kst = today_kst - timedelta(days=1)
target_date = yesterday_kst.strftime("%Y%m%d")
display_date = yesterday_kst.strftime("%Y년 %m월 %d일")

st.write(f"📅 **조회 기준일:** {display_date}")

# 3. KOBIS API 요청 주소 및 파라미터 설정
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {
    "key": api_key,
    "targetDt": target_date
}

# 4. API 데이터 가져오기 및 예외 처리
try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    # [에러 처리 1] 인증키 오류 등으로 faultInfo 상자가 돌아온 경우
    if "faultInfo" in data:
        st.error("⚠️ 영화진흥위원회 API 오류 발생")
        st.warning(f"오류 내용: {data['faultInfo'].get('message', '알 수 없는 오류')}")
        st.info("💡 **확인해 보세요:** 등록된 API 키(KOBIS_KEY)가 정확한지 확인해 주세요.")
        st.stop()

    # [에러 처리 2] 정상 응답 내부 목록 확인
    box_office_result = data.get("boxOfficeResult", {})
    daily_list = box_office_result.get("dailyBoxOfficeList", [])

    if not daily_list:
        st.warning("⚠️ 조회된 박스오피스 데이터가 없습니다.")
        st.info("💡 오늘 자정 직후이거나 데이터 집계가 아직 완료되지 않았을 수 있습니다.")
        st.stop()

    # 5. 데이터 프레임 변환 및 숫자형 데이터 정제 (문자열 -> 숫자)
    df = pd.DataFrame(daily_list)

    # 데이터 타입 변환 (KOBIS 응답값은 모두 문자열 형태)
    df["rank"] = df["rank"].astype(int)
    df["audiCnt"] = df["audiCnt"].astype(int)
    df["audiAcc"] = df["audiAcc"].astype(int)
    df["scrnCnt"] = df["scrnCnt"].astype(int)

    # 6. 1위 영화 상단 메트릭 카드 3장 표시
    top_movie = df.iloc[0]
    st.subheader(f"🥇 1위 영화: {top_movie['movieNm']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("일별 관객수", f"{top_movie['audiCnt']:,} 명")
    col2.metric("누적 관객수", f"{top_movie['audiAcc']:,} 명")
    col3.metric("스크린수", f"{top_movie['scrnCnt']:,} 개")

    st.divider()

    # 7. 관객수 상위 5편 막대그래프 시각화
    st.subheader("📊 관객수 상위 5개 영화")
    top5_df = df.head(5)[["movieNm", "audiCnt"]].set_index("movieNm")
    top5_df.columns = ["관객수"]
    st.bar_chart(top5_df)

    st.divider()

    # 8. 전체 박스오피스 순위표 정리 및 출력
    st.subheader("📋 일별 박스오피스 전체 순위")

    # 표시할 컬럼 선택 및 이름 변경
    table_df = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
    table_df.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

    # 표 출력 (숫자 세 자릿수 콤마 적용)
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "관객수": st.column_config.NumberColumn(format="%d명"),
            "누적관객": st.column_config.NumberColumn(format="%d명"),
            "스크린수": st.column_config.NumberColumn(format="%d개"),
        }
    )

except requests.exceptions.RequestException as e:
    st.error("🌐 네트워크 통신 오류가 발생했습니다.")
    st.info("💡 인터넷 연결 상태를 확인하시거나 잠시 후 다시 시도해 주세요.")
