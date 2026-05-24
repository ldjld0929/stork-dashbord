import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET 

# 1. 페이지 레이아웃 및 다크테마 최적화 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide") 

# [수정] 모바일 가독성 및 강제 번역 차단
st.markdown("""
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google" content="notranslate">
</head>
<style>
    /* 글자색을 흰색 계열로 강제하여 가독성 확보 */
    body, .stMarkdown, .stText, .stExpander, .stSelectbox { color: #e2e8f0 !important; }
    .theme-box { background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 12px; margin-bottom: 8px; margin-top: 15px; }
    .theme-top { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
    .theme-lbl { background-color: #1e3a5f; color: #38bdf8 !important; font-size: 13px; font-weight: bold; padding: 2px 10px; border-radius: 4px; }
    .theme-amt { color: #f43f5e !important; font-size: 13px; font-weight: bold; }
    .theme-desc { color: #94a3b8 !important; font-size: 11px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 4px; padding: 10px 12px; margin-bottom: 8px; height: 62px; display: flex; flex-direction: column; justify-content: center; cursor: pointer; }
    .hts-card:hover { border: 1px solid #38bdf8; background-color: #223147; }
    .hts-up .status-color { color: #ef4444 !important; } .hts-down .status-color { color: #3b82f6 !important; }
    .hts-limit { background-color: #eab308 !important; border: 1px solid #facc15 !important; }
    .hts-limit .stock-title { color: #000000 !important; }
    .hts-limit .status-color { color: #d32f2f !important; font-weight: 900; }
    .detail-card { background-color: #17202e; border: 1px solid #283954; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
    .stExpander { background-color: #1e293b !important; border: 1px solid #334155 !important; margin-bottom: 6px !important; border-radius: 4px !important; color: #f1f5f9 !important; }
    .rank-card { background-color: #1e293b; border-left: 4px solid #38bdf8; padding: 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; color: #f8fafc !important; }
    .rank-num { color: #38bdf8; font-weight: bold; margin-right: 10px; }
</style>
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

WEEKEND_FALLBACK = {name: {"price": "0", "rate": "0.00%", "type": "4", "volume": "0억"} for name in STOCK_MAP}

theme_data = {
    "반도체소부장": {"news": "美 소부장 기대감 속 핵심 장비 공급 계약 수급 쏠림", "stocks": ["주성엔지니어링", "SFA반도체", "파두", "제주반도체"]},
    "반도체대형주": {"news": "엔비디아 실적 발표 앞두고 대형주 차별화 및 기관 매수세", "stocks": ["삼성전기", "LG이노텍", "SK하이닉스", "삼성전자"]},
    "로봇/미래차": {"news": "휴머노이드 로봇 양산화 본격 돌입 소식 및 전장부품 가속", "stocks": ["LG씨엔에스", "LG전자", "현대차", "현대모비스"]},
    "개별이슈/기타": {"news": "대규모 글로벌 공급 계약 및 지분 투자 모멘텀 부각", "stocks": ["빛과전자", "두산퓨얼셀", "켄코아에어로", "OCI홀딩스"]},
    "바이오대형주": {"news": "생물보안법 반사이익 수혜 및 글로벌 기술 수출 본격화", "stocks": ["알테오젠", "리그켐바이오", "HLB", "삼성바이오로직스"]},
    "2차전지/ESS": {"news": "유럽 전력망 인프라 확충에 따른 글로벌 ESS 수주 폭발", "stocks": ["에코프로", "에코프로비엠", "포스코퓨처엠", "LG엔솔"]},
    "AI/클라우드": {"news": "정부 AI 온디바이스 육성 대책 발표 및 서비스 개시", "stocks": ["NAVER", "카카오", "한글과컴퓨터", "폴라리스AI"]},
    "방산/우주항공": {"news": "해외 대규모 2차 인도 계약 임박 및 독점적 수출 지위", "stocks": ["한화에어로스페이스", "현대로템", "LIG넥스원", "한국항공우주"]}
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
            name = next((k for k, v in STOCK_MAP.items() if v == code), None)
            if name:
                close, chg_type, rate, cv, aq = item.get("nv", 0), item.get("rf"), item.get("cr", 0.0), item.get("cv", 0), item.get("aq", 0)
                if close > 0:
                    prices[name] = {
                        "price": f"{close:,}", "rate": f"{'+' if chg_type in ['1','2'] else '-' if chg_type in ['5'] else ''}{rate:.2f}%",
                        "type": chg_type, "diff": f"{cv:,}", "volume": f"{int(aq * close / 100000000):,}억" if aq else "0억"
                    }
        return prices
    except: return {} 

realtime_data = fetch_hts_api_prices() 

@st.cache_data(ttl=300)
def fetch_live_global_financial_news(stock_name):
    encoded_name = urllib.parse.quote(stock_name)
    url = f"https://news.google.com/rss/search?q={encoded_name}+-site:hankyung.com+-site:sedaily.com&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        root = ET.fromstring(res.content) 
        news_list = [] 
        for item in root.findall('.//item'):
            title = item.find('title').text
            link = item.find('link').text
            if any(k in title for k in ["유료", "로그인", "회원전용", "구독"]) or "hankyung.com" in link: continue
            desc_elem = item.find('description')
            desc_text = BeautifulSoup(desc_elem.text, 'html.parser').get_text(strip=True)[:150] + "..." if desc_elem is not None else ""
            news_list.append({"title": title.rsplit(" - ", 1)[0], "link": link, "source": item.find('source').text, "date": item.find('pubDate').text[:16], "desc": desc_text}) 
            if len(news_list) >= 5: break
        return news_list
    except: return [] 

def get_numeric_score(sname):
    info = realtime_data.get(sname, WEEKEND_FALLBACK.get(sname, {"price": "-", "rate": "0.00%", "type": "4", "volume": "0억"}))
    try: rate_val = float(info["rate"].replace("%", "").replace("+", ""))
    except: rate_val = 0.0
    try: vol_val = int(info["volume"].replace("억", "").replace(",", ""))
    except: vol_val = 0
    return rate_val, vol_val, info 

all_stocks_data = []
processed_themes = {} 
for t_name, t_val in theme_data.items():
    total_vol = 0
    stock_list_with_score = []
    for sname in t_val["stocks"]:
        r_val, v_val, info = get_numeric_score(sname)
        total_vol += v_val
        stock_list_with_score.append((sname, r_val, v_val, info))
        all_stocks_data.append((sname, r_val, v_val, info)) 
    processed_themes[t_name] = {"money": f"{total_vol:,}억", "news": t_val["news"], "stocks_data": stock_list_with_score, "total_vol": total_vol} 

sorted_theme_names = sorted(processed_themes.keys(), key=lambda x: processed_themes[x]["total_vol"], reverse=True) 
top_rate_stocks = sorted(all_stocks_data, key=lambda x: x[1], reverse=True)[:5]
top_vol_stocks = sorted(all_stocks_data, key=lambda x: x[2], reverse=True)[:5] 

if "page_mode" not in st.session_state: st.session_state.page_mode = "main"
if "active_stock" not in st.session_state: st.session_state.active_stock = None 

query_params = st.query_params
if "stock" in query_params and query_params["stock"]:
    st.session_state.active_stock = query_params["stock"]
    st.session_state.page_mode = "detail"
    st.query_params.clear() 

def go_main():
    st.session_state.page_mode = "main"
    st.session_state.active_stock = None 

if st.session_state.page_mode == "main":
    st.markdown("<h3 style='color:#38bdf8;'>📱 실시간 주도주 랭킹 통합 전광판</h3>", unsafe_allow_html=True)
    selected = st.selectbox("", ["🔍 종목 검색/선택"] + list(STOCK_MAP.keys()), label_visibility="collapsed")
    if selected != "🔍 종목 검색/선택":
        st.session_state.active_stock = selected
        st.session_state.page_mode = "detail"
        st.rerun()

    for t_name in sorted_theme_names:
        t_val = processed_themes[t_name]
        st.markdown(f'<div class="theme-box"><div class="theme-top"><span class="theme-lbl">{t_name}</span><span class="theme-amt">{t_val["money"]}</span></div><div class="theme-desc">{t_val["news"]}</div></div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, (sname, r_val, v_val, s_info) in enumerate(t_val["stocks_data"]):
            mode = "hts-limit" if s_info["type"] == "1" or "29.9" in s_info["rate"] else "hts-down" if s_info["type"] == "5" or "-" in s_info["rate"] else "hts-up"
            cols[idx % 4].markdown(f"<a href='?stock={sname}' target='_self' style='text-decoration:none;'><div class='hts-card {mode}'><div style='display:flex; justify-content:space-between;'><span style='font-weight:bold;'>{sname}</span><span class='status-color' style='font-weight:bold;'>{s_info['rate']}</span></div><div style='display:flex; justify-content:space-between; margin-top:5px;'><span class='status-color'>{s_info['price']}</span><span style='color:#94a3b8; font-size:11px;'>{s_info['volume']}</span></div></div></a>", unsafe_allow_html=True)

elif st.session_state.page_mode == "detail":
    if st.button("◀ 목록으로"):
        go_main()
        st.rerun()
    tgt = st.session_state.active_stock
    _, _, live = get_numeric_score(tgt)
    st.markdown(f"""<div class="detail-card"><h3>{tgt}</h3><p>{live['price']}원 ({live['rate']})</p></div>""", unsafe_allow_html=True)
    fetched_news = fetch_live_global_financial_news(tgt)
    for nw in fetched_news:
        with st.expander(f"📌 [{nw['source']}] {nw['title']}"):
            st.markdown(f"{nw['desc']}")
            st.link_button("🔗 원문 보기", nw['link'])
