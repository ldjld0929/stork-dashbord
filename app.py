import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET 

st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide") 

st.markdown("""
<head>
<meta name="google" content="notranslate">
</head>
""", unsafe_allow_html=True) 

st_autorefresh(interval=5000, key="hts_refresh") 

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

WEEKEND_FALLBACK = {name: {"price": "-", "rate": "0.00%", "type": "2", "volume": "0억"} for name in STOCK_MAP.keys()}

theme_data = {
"반도체소부장": {"news": "핵심 장비 공급 계약 수급 쏠림", "stocks": ["주성엔지니어링", "SFA반도체", "파두", "제주반도체"]},
"반도체대형주": {"news": "대형주 차별화 및 기관 매수세", "stocks": ["삼성전기", "LG이노텍", "SK하이닉스", "삼성전자"]},
"로봇/미래차": {"news": "전장부품 가속", "stocks": ["LG씨엔에스", "LG전자", "현대차", "현대모비스"]},
"개별이슈/기타": {"news": "대규모 글로벌 공급 계약", "stocks": ["빛과전자", "두산퓨얼셀", "켄코아에어로", "OCI홀딩스"]},
"바이오대형주": {"news": "기술 수출 본격화", "stocks": ["알테오젠", "리그켐바이오", "HLB", "삼성바이오로직스"]},
"2차전지/ESS": {"news": "글로벌 ESS 수주 폭발", "stocks": ["에코프로", "에코프로비엠", "포스코퓨처엠", "LG엔솔"]},
"AI/클라우드": {"news": "정부 AI 온디바이스 육성", "stocks": ["NAVER", "카카오", "한글과컴퓨터", "폴라리스AI"]},
"방산/우주항공": {"news": "해외 대규모 인도 계약", "stocks": ["한화에어로스페이스", "현대로템", "LIG넥스원", "한국항공우주"]}
}

@st.cache_data(ttl=10)
def fetch_hts_api_prices():
    codes = list(STOCK_MAP.values())
    query_string = ",".join([f"SERVICE_ITEM:{c}" for c in codes])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_string}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        items = res.get("result", {}).get("areas", [{}])[0].get("datas", [])
        prices = {}
        for item in items:
            code = item.get("cd")
            name = [k for k, v in STOCK_MAP.items() if v == code][0]
            close = item.get("nv", 0)
            prices[name] = {"price": f"{close:,}", "rate": f"{item.get('cr'):.2f}%", "type": item.get("rf"), "volume": f"{int(item.get('aq',0) * close / 100000000):,}억"}
        return prices
    except: return WEEKEND_FALLBACK

realtime_data = fetch_hts_api_prices()

# 데이터 처리 로직 재정의 (오류 방지)
all_stocks_data = []
processed_themes = {}
for t_name, t_val in theme_data.items():
    total_vol = 0
    stocks_data = []
    for sname in t_val["stocks"]:
        info = realtime_data.get(sname, WEEKEND_FALLBACK.get(sname))
        vol = int(info["volume"].replace("억", "").replace(",", ""))
        total_vol += vol
        stocks_data.append((sname, info))
    processed_themes[t_name] = {"money": f"{total_vol:,}억", "stocks_data": stocks_data, "total_vol": total_vol}

sorted_theme_names = sorted(processed_themes.keys(), key=lambda x: processed_themes[x]["total_vol"], reverse=True)

# 메인 UI
st.markdown("<style>.hts-card { background: #1b2636; padding: 10px; border-radius: 4px; margin: 5px; }</style>", unsafe_allow_html=True)
for t_name in sorted_theme_names:
    st.subheader(f"{t_name} (합산 {processed_themes[t_name]['money']})")
    cols = st.columns(4)
    for idx, (sname, info) in enumerate(processed_themes[t_name]["stocks_data"]):
        cols[idx % 4].markdown(f"<div class='hts-card'><b>{sname}</b><br>{info['rate']}<br>{info['volume']}</div>", unsafe_allow_html=True)
