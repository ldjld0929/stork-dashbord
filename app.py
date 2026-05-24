import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET

# 1. 페이지 레이아웃 및 다크테마 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide")

# 2. 데이터 매핑 (절대 삭제 금지)
STOCK_MAP = {
    "주성엔지니어링": "036930", "SFA반도체": "036540", "파두": "440110", "제주반도체": "080220",
    "삼성전기": "009150", "LG이노텍": "011070", "SK하이닉스": "000660", "삼성전자": "005930",
    "LG씨엔에스": "003550", "LG전자": "066570", "현대차": "005380", "현대모비스": "012330",
    "빛과전자": "069540", "두산퓨얼셀": "336260", "켄코아에어로": "274090", "OCI홀딩스": "010060",
    "알테오젠": "196170", "리그켐바이오": "141080", "HLB": "028300", "삼성바이오로직스": "207940",
    "에코프로": "086520", "에코프로비엠": "247540", "포스코퓨처엠": "003670", "LG엔솔": "373220",
    "NAVER": "035420", "카카오": "035720", "한글과컴퓨터": "030520", "폴라리스AI": "039980",
    "한화에어로스페이스": "012450", "현대로템": "064350", "LIG넥스원": "079550", "한국항공우주": "047810"
}

WEEKEND_FALLBACK = {name: {"price": "0", "rate": "0%", "volume": "0억"} for name in STOCK_MAP.keys()}

theme_data = {
    "반도체소부장": {"news": "핵심 장비 공급", "stocks": ["주성엔지니어링", "SFA반도체", "파두", "제주반도체"]},
    "반도체대형주": {"news": "대형주 차별화", "stocks": ["삼성전기", "LG이노텍", "SK하이닉스", "삼성전자"]},
    "로봇/미래차": {"news": "전장부품 가속", "stocks": ["LG씨엔에스", "LG전자", "현대차", "현대모비스"]},
    "개별이슈/기타": {"news": "공급 계약 모멘텀", "stocks": ["빛과전자", "두산퓨얼셀", "켄코아에어로", "OCI홀딩스"]},
    "바이오대형주": {"news": "기술 수출 본격화", "stocks": ["알테오젠", "리그켐바이오", "HLB", "삼성바이오로직스"]},
    "2차전지/ESS": {"news": "글로벌 ESS 수주", "stocks": ["에코프로", "에코프로비엠", "포스코퓨처엠", "LG엔솔"]},
    "AI/클라우드": {"news": "정부 육성 대책", "stocks": ["NAVER", "카카오", "한글과컴퓨터", "폴라리스AI"]},
    "방산/우주항공": {"news": "수출 지위 부각", "stocks": ["한화에어로스페이스", "현대로템", "LIG넥스원", "한국항공우주"]}
}

# 3. CSS 및 스타일
st.markdown("""
<style>
    .hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 6px; padding: 8px; margin-bottom: 8px; }
    @media (max-width: 600px) { [data-testid="column"] { width: 50% !important; flex: 1 1 50% !important; } }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 수집 함수
@st.cache_data(ttl=10)
def fetch_hts_api_prices():
    codes = list(STOCK_MAP.values())
    query_string = ",".join([f"SERVICE_ITEM:{c}" for c in codes])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_string}"
    prices = {}
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        items = res.get("result", {}).get("areas", [{}])[0].get("datas", [])
        for item in items:
            code = item.get("cd")
            name = next((k for k, v in STOCK_MAP.items() if v == code), None)
            if name:
                prices[name] = {"rate": f"{item.get('cr', 0):.2f}%", "price": f"{item.get('nv', 0):,}"}
        return prices
    except: return {}

# 5. 메인 로직
realtime_data = fetch_hts_api_prices()
st_autorefresh(interval=5000)

st.title("📱 실시간 주도주 전광판")

for t_name, t_val in theme_data.items():
    st.subheader(t_name)
    cols = st.columns(4)
    for idx, sname in enumerate(t_val["stocks"]):
        data = realtime_data.get(sname, WEEKEND_FALLBACK[sname])
        cols[idx % 4].markdown(f"""
        <div class='hts-card'>
            <div style='font-size:12px;'>{sname}</div>
            <div style='color:#ef4444; font-size:11px;'>{data['rate']}</div>
        </div>
        """, unsafe_allow_html=True)
