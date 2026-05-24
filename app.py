import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET

# 1. 페이지 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide")

# 2. 모바일 대응 반응형 CSS (중요!)
st.markdown("""
<style>
    [data-testid="stHeader"] {background: #0f141c;}
    body { background-color: #0f141c; color: #f8fafc; }
    
    /* 카드 디자인 최적화 */
    .hts-card { 
        background-color: #1b2636; 
        border: 1px solid #283954; 
        border-radius: 6px; 
        padding: 8px; 
        margin-bottom: 8px; 
        cursor: pointer;
        min-height: 55px;
    }
    .hts-card:hover { border: 1px solid #38bdf8; }
    
    /* 모바일에서는 2단, 데스크탑에서는 4단 자동 배치 */
    [data-testid="column"] {
        padding: 2px !important;
    }
    @media (max-width: 600px) {
        [data-testid="column"] { width: 50% !important; flex: 1 1 50% !important; }
    }
    
    .theme-box { background-color: #17202e; border: 1px solid #233249; border-radius: 6px; padding: 10px; margin: 10px 0; }
    .theme-lbl { color: #38bdf8; font-weight: bold; font-size: 13px; }
    .rank-card { background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 6px 10px; margin-bottom: 4px; border-radius: 4px; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# 5초마다 실시간 동기화
st_autorefresh(interval=5000, key="hts_refresh")

# [STOCK_MAP, WEEKEND_FALLBACK, theme_data 등 기존 데이터는 그대로 두세요]
# (여기에 기존 코드의 매핑 데이터를 넣으시면 됩니다)

@st.cache_data(ttl=10)
def fetch_hts_api_prices():
    # 기존과 동일
    codes = list(STOCK_MAP.values())
    query_string = ",".join([f"SERVICE_ITEM:{c}" for c in codes])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_string}"
    prices = {}
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        items = res.get("result", {}).get("areas", [{}])[0].get("datas", [])
        for item in items:
            code = item.get("cd")
            name = [k for k, v in STOCK_MAP.items() if v == code]
            if name:
                n = name[0]
                close = item.get("nv", 0)
                chg_type = item.get("rf")
                rate = item.get("cr", 0.0)
                cv = item.get("cv", 0)
                aq = item.get("aq", 0)
                prices[n] = {
                    "price": f"{close:,}", 
                    "rate": f"{'+' if chg_type in ['1','2'] else '-' if chg_type in ['5'] else ''}{rate:.2f}%",
                    "type": chg_type, "diff": f"{cv:,}", 
                    "volume": f"{int(aq * close / 100000000):,}억" if aq else "0억"
                }
        return prices
    except: return {}

realtime_data = fetch_hts_api_prices()

# 데이터 통합 및 UI 렌더링
if "page_mode" not in st.session_state: st.session_state.page_mode = "main"

if st.session_state.page_mode == "main":
    st.markdown("<h3 style='color:#38bdf8;'>📱 실시간 주도주 전광판</h3>", unsafe_allow_html=True)
    
    # 랭킹 Top 5 (생략 가능)
    
    # 섹터별 카드 렌더링 (핵심 수정 부분)
    for t_name, t_val in theme_data.items():
        st.markdown(f"<div class='theme-box'><span class='theme-lbl'>{t_name}</span></div>", unsafe_allow_html=True)
        
        # 여기서 4컬럼을 강제하지 않고, 반응형 컬럼 활용
        cols = st.columns(4) 
        for idx, sname in enumerate(t_val["stocks"]):
            info = realtime_data.get(sname, WEEKEND_FALLBACK.get(sname, {"price": "-", "rate": "0%", "volume": "0억"}))
            
            # 텍스트 크기를 작게 조절하여 모바일에서도 깨지지 않게 설정
            cols[idx % 4].markdown(f"""
            <a href='?stock={sname}' target='_self' style='text-decoration:none;'>
                <div class='hts-card'>
                    <div style='color:white; font-size:12px; font-weight:bold;'>{sname}</div>
                    <div style='color:#ef4444; font-size:11px;'>{info['rate']}</div>
                </div>
            </a>
            """, unsafe_allow_html=True)

elif st.session_state.page_mode == "detail":
    # 상세 페이지 로직 (기존과 동일하게 유지)
    pass
