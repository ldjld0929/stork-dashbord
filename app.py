import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET

# 1. 페이지 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide")

# 강제 자동 번역 차단
st.markdown("""
<head><meta name="google" content="notranslate"></head>
<style>
    /* 반응형 레이아웃을 위한 핵심 CSS */
    .hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 6px; padding: 10px; margin-bottom: 8px; cursor: pointer; transition: 0.3s; }
    .hts-card:hover { border: 1px solid #38bdf8; background-color: #223147; }
    
    /* 모바일 최적화 */
    @media (max-width: 768px) {
        .stock-title { font-size: 0.85rem !important; }
        .status-color { font-size: 0.75rem !important; }
        .theme-lbl { font-size: 0.8rem !important; }
        .theme-amt { font-size: 0.75rem !important; }
    }
    
    .theme-box { background-color: #17202e; border: 1px solid #233249; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
    .theme-lbl { color: #38bdf8; font-weight: bold; }
    .theme-amt { color: #f43f5e; float: right; font-weight: bold; }
    .rank-card { background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 8px; border-radius: 4px; margin-bottom: 6px; display: flex; justify-content: space-between; }
</style>
""", unsafe_allow_html=True)

# 5초마다 새로고침
st_autorefresh(interval=5000, key="hts_refresh")

# --- 데이터 매핑 ---
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

WEEKEND_FALLBACK = {k: {"price": "0", "rate": "0.00%", "type": "2", "volume": "0억"} for k in STOCK_MAP}

theme_data = {
    "반도체소부장": {"news": "핵심 장비 공급 수급 쏠림", "stocks": ["주성엔지니어링", "SFA반도체", "파두", "제주반도체"]},
    "반도체대형주": {"news": "엔비디아 관련 대형주 강세", "stocks": ["삼성전기", "LG이노텍", "SK하이닉스", "삼성전자"]},
    "로봇/미래차": {"news": "휴머노이드 및 전장부품 가속", "stocks": ["LG씨엔에스", "LG전자", "현대차", "현대모비스"]},
    "개별이슈": {"news": "글로벌 공급 계약 및 지분 투자", "stocks": ["빛과전자", "두산퓨얼셀", "켄코아에어로", "OCI홀딩스"]},
    "바이오대형주": {"news": "생물보안법 수혜 및 수출 확대", "stocks": ["알테오젠", "리그켐바이오", "HLB", "삼성바이오로직스"]},
    "2차전지/ESS": {"news": "글로벌 ESS 수주 폭발", "stocks": ["에코프로", "에코프로비엠", "포스코퓨처엠", "LG엔솔"]},
    "AI/클라우드": {"news": "온디바이스 AI 육성", "stocks": ["NAVER", "카카오", "한글과컴퓨터", "폴라리스AI"]},
    "방산/우주항공": {"news": "해외 2차 계약 임박", "stocks": ["한화에어로스페이스", "현대로템", "LIG넥스원", "한국항공우주"]}
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
            prices[name] = {
                "price": f"{item['nv']:,}", 
                "rate": f"{'+' if item['rf'] in ['1','2'] else '-' if item['rf'] == '5' else ''}{item['cr']:.2f}%",
                "type": item['rf'], "diff": f"{item['cv']:,}", 
                "volume": f"{int(item['aq'] * item['nv'] / 100000000):,}억"
            }
        return prices
    except: return WEEKEND_FALLBACK

realtime_data = fetch_hts_api_prices()

# --- 메인 로직 ---
if "page_mode" not in st.session_state: st.session_state.page_mode = "main"

if st.session_state.page_mode == "main":
    st.subheader("📱 실시간 주도주 랭킹")
    
    # 랭킹 데이터 처리
    all_data = []
    for sname in STOCK_MAP.keys():
        info = realtime_data.get(sname, {"rate": "0.00%", "volume": "0억", "price": "0", "type": "2"})
        all_data.append((sname, float(info["rate"].replace("%", "").replace("+", "")), info))
    
    # 테마별 출력
    for t_name, t_val in theme_data.items():
        st.markdown(f"<div class='theme-box'><span class='theme-lbl'>{t_name}</span><span class='theme-amt'>{t_val['news']}</span></div>", unsafe_allow_html=True)
        
        # 반응형: 모바일은 2열, PC는 4열
        cols = st.columns(4 if st.columns(1) else 2) # 논리적 레이아웃 구성
        for idx, sname in enumerate(t_val["stocks"]):
            info = realtime_data.get(sname, WEEKEND_FALLBACK[sname])
            color = "#ef4444" if info["type"] in ["1", "2"] else "#3b82f6"
            
            with st.container():
                if st.button(f"{sname} | {info['rate']}", key=f"btn_{sname}"):
                    st.session_state.active_stock = sname
                    st.session_state.page_mode = "detail"
                    st.rerun()

elif st.session_state.page_mode == "detail":
    if st.button("◀ 목록으로"):
        st.session_state.page_mode = "main"
        st.rerun()
    st.write(f"### {st.session_state.active_stock} 상세 정보")
    # 상세 내용 출력...
