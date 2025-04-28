

import streamlit as st
import pandas as pd
import datetime
import pymysql
from sqlalchemy import create_engine
from ui_dashboard import show_dashboard
from ui_result_table import show_results

st.set_page_config(page_title="자동차 리콜 정보 시스템", layout="wide")

# DB 연결 및 데이터 로드
@st.cache_data
def load_data():
    MYSQL_HOSTNAME = 'localhost'
    MYSQL_USER = 'skn14'
    MYSQL_PASSWORD = 'skn14'
    MYSQL_DATABASE = 'skn14_1st_6team'
    connection_string = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOSTNAME}/{MYSQL_DATABASE}'
    db = create_engine(connection_string)

    df = pd.read_sql_table('origin_data', con=db)

    df['prod_period_from'] = pd.to_datetime(df['prod_period_from'], errors='coerce')
    df['prod_period_to'] = pd.to_datetime(df['prod_period_to'], errors='coerce')
    df['recall_start'] = pd.to_datetime(df['recall_start'], errors='coerce')

    df['is_ev'] = df['EV_EV_id'].map({1: '전기차', 2: '내연차'})
    df['is_di'] = df['Domestic_International_DI_id'].map({1: '국내', 2: '해외'})
    df = df.rename(columns={'car_name': 'car', 'recall_reason': 'keyword'})
    df = df.dropna(subset=['prod_period_from', 'prod_period_to'])

    return df

df = load_data()

# UI
with st.container():
    st.markdown("""
        <h1 style='text-align: center;'>자동차 리콜 정보 시스템</h1>
        <p style='text-align: center; color: gray;'>MySQL에 저장된 리콜 이력과 통계를 조회합니다.</p>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 필터 조건")
    company = st.text_input("제조사")
    car = st.text_input("차종")
    is_ev = st.selectbox("차량 유형", ["전체", "전기차", "내연차"])
    is_di = st.selectbox("국내/해외", ["전체", "국내", "해외"])
    prod_date_range = st.date_input("생산 기간 범위", (datetime.date(2010, 1, 1), datetime.date(2024, 12, 31)))
    keyword = st.text_input("리콜 사유 키워드")

    col1, col2 = st.columns([2, 1])
    with col1:
        search_button = st.button('검색')
    with col2:
        reset_button = st.button('초기화')

filters = {
    "company": company,
    "car": car,
    "is_ev": is_ev,
    "is_di": is_di,
    "prod_date_range": prod_date_range,
    "keyword": keyword
}



################################ sumilee start #####################################
import os
import urllib.parse
import urllib.request

import requests
from dotenv import load_dotenv
load_dotenv()
import json


# ——— 네이버 Open API 설정 ———
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search/image"

def fetch_naver_image(car_name: str) -> str:
    """
    row['car'] 값으로 '차량명 나무위키' 검색 URL을 직접 만들어
    네이버 Image Search API를 호출하고 첫 번째 이미지를 반환.
    """
    # 1) 검색어 문자열 생성
    query = f"{car_name}"

    # 2) URL 인코딩
    encText = urllib.parse.quote(query)

    url = "https://openapi.naver.com/v1/search/image?query="+encText+"&display=1"
    # 요청 url 등록
    request = urllib.request.Request(url)

    # 요청 header 등록(메타정보)
    request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)

    # try:
    # 5) 요청 보내기
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if (rescode == 200):
        response_body = response.read()
        response_json = json.loads(response_body.decode("utf-8"))
        return response_json['items'][0]['link']
    else:
        print("Error Code:" + rescode)
######################### sumilee end ##################################



if search_button:
    filtered_df = df.copy()

    if filters['company']:
        filtered_df = filtered_df[filtered_df['company'].str.contains(filters['company'], na=False)]

    if filters['car']:
        filtered_df = filtered_df[filtered_df['car'].str.contains(filters['car'], na=False)]

    if filters['is_ev'] != "전체":
        filtered_df = filtered_df[filtered_df['is_ev'] == filters['is_ev']]

    if filters['is_di'] != "전체":
        filtered_df = filtered_df[filtered_df['is_di'] == filters['is_di']]

    start_date, end_date = filters['prod_date_range']
    filtered_df = filtered_df[
        (filtered_df['prod_period_from'] >= pd.to_datetime(start_date)) &
        (filtered_df['prod_period_to'] <= pd.to_datetime(end_date))
    ]

    if filters['keyword']:
        filtered_df = filtered_df[filtered_df['keyword'].str.contains(filters['keyword'], na=False)]

    # 📊 대시보드 + 데이터프레임
    show_dashboard(filtered_df)
    show_results(filtered_df)

    # 📋 카드 스타일 리콜 상세 결과 추가 (여기 추가함)
    st.subheader("📋 리콜 상세 결과")

    if filtered_df.empty:
        st.warning("검색 결과가 없습니다.")
    else:
        for i, row in filtered_df.iterrows():
            with st.container():
                st.markdown("---")
                cols = st.columns([1, 4])

                with cols[0]:
                    car_name = row['car']
                    ##sumilee##
                    img_url = fetch_naver_image(car_name)

                    if img_url:
                        st.image(img_url, width=150)

                    else:
                        st.image("https://via.placeholder.com/150x100.png?text=No+Image", width=150)

                with cols[1]:
                    st.markdown(f"### {row['company']} {row['car']}")
                    st.markdown(f"**리콜 사유:** {row['keyword'][:100]}{'...' if len(row['keyword']) > 100 else ''}")
                    st.markdown(f"**생산 기간:** {row['prod_period_from'].date()} ~ {row['prod_period_to'].date()}")
                    st.markdown(f"**차량 유형:** {row['is_ev']} / **지역:** {row['is_di']}")

if reset_button:
    st.rerun()