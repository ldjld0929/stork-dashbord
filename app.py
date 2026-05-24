import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET 

# 1. 페이지 레이아웃 및 다크테마 최적화 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide") 

# 강제 자동 번역 차단 (버튼 먹통 방지)
st.markdown("""
<head>
<meta name="google" content="notranslate">
</head>
""", unsafe_allow_html=True) 

# 5초마다 실시간 주가 무한 동기화
st_autorefresh(interval=5000, key="hts_refresh") 

# --- 🗂️ 8대 섹터 32개 주도주 마스터 코드 마핑 ---
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

# 주말/야간용 백업 데이터 (생략된 부분은 동일)
WEEKEND_FALLBACK = {
"주성엔지니어링": {"price": "224,000", "rate": "+20.95%", "type": "2", "volume": "1,389억"},
"SFA반도체": {"price": "10,250", "rate": "+14.53%", "type": "2", "volume": "7,083억"},
"빛과전자": {"price": "6,610", "rate": "+29.86%", "type": "1", "volume": "2,546억"},
"두산퓨얼셀": {"price": "99,000", "rate": "+18.56%", "type": "2", "volume": "4,394억"},
"삼성전자": {"price": "293,000", "rate": "-2.17%", "type": "5", "volume": "104,397억"},
"SK하이닉스": {"price": "1,941,000", "rate": "+0.05%", "type": "2", "volume": "102,265억"},
"삼성전기": {"price": "1,331,000", "rate": "+10.55%", "type": "2", "volume": "34,089억"},
"LG전자": {"price": "237,000", "rate": "+0.85%", "type": "2", "volume": "30,132억"},
"현대차": {"price": "655,000", "rate": "-1.65%", "type": "5", "volume": "15,249억"}
}
# (나머지 종목들도 동일하게 유지...)

# 테마 및 API 함수 (동일)
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
    prices = {}
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        items = res.get("result", {}).get("areas", [{}])[0].get("datas", [])
        for item in items:
            code = item.get("cd")
            name = [k for k, v in STOCK_MAP.items() if v == code][0]
            close = item.get("nv", 0)
            prices[name] = {"price": f"{close:,}", "rate": f"{item.get('cr'):.2f}%", "type": item.get("rf"), "volume": f"{int(item.get('aq',0) * close / 100000000):,}억"}
        return prices
    except: return WEEKEND_FALLBACK

realtime_data = fetch_hts_api_prices() 

# --- 개선된 스타일 (모바일 최적화) ---
st.markdown("""
<style>
@media (max-width: 600px) {
    .hts-card { height: 50px !important; padding: 5px !important; }
    .stock-title { font-size: 12px !important; }
    .status-color { font-size: 11px !important; }
    .theme-lbl { font-size: 10px !important; }
    .theme-amt { font-size: 10px !important; }
}
[data-testid="stHeader"] {background: #0f141c;}
body { background-color: #0f141c; }
.theme-box { background-color: #17202e; border: 1px solid #233249; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
.hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 4px; padding: 8px; margin-bottom: 5px; cursor: pointer; }
.rank-card { background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 6px 10px; border-radius: 4px; margin-bottom: 4px; display: flex; justify-content: space-between; }
</style>
""", unsafe_allow_html=True) 

# --- 메인 화면 로직 ---
st.markdown("<h3 style='color:#38bdf8;'>📱 실시간 주도주 랭킹</h3>", unsafe_allow_html=True)

# 섹터별 리스트 출력 (모바일에서는 2열로 구성하여 가독성 확보)
for t_name, t_val in theme_data.items():
    st.markdown(f'<div class="theme-box">{t_name}</div>', unsafe_allow_html=True)
    # 모바일/PC 반응형을 위해 2열 구성
    cols = st.columns(2) 
    for idx, sname in enumerate(t_val["stocks"]):
        info = realtime_data.get(sname, WEEKEND_FALLBACK.get(sname, {"price": "-", "rate": "0%", "type": "2", "volume": "0억"}))
        cols[idx % 2].markdown(f"""
        <div class='hts-card'>
            <div style='color:white; font-weight:bold; font-size:13px;'>{sname}</div>
            <div style='color:#ef4444; font-size:11px;'>{info['rate']} | {info['volume']}</div>
        </div>
        """, unsafe_allow_html=True)
