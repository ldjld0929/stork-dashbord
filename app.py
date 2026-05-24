import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

# 1. 페이지 레이아웃 및 다크테마 최적화
st.set_page_config(page_title="NXT 자동형 주도주 전광판", layout="wide")

st.markdown("""
<style>
    body, .stMarkdown, .stText, .stExpander, .stSelectbox, h4 { color: #ffffff !important; }
    [data-testid="stHeader"] {background: #0f141c !important;}
    body, .stApp, [data-testid="stAppViewContainer"], .main { background-color: #0f141c !important; }
    
    .theme-box { background-color: #17202e; border: 1px solid #233249; border-radius: 6px; padding: 10px; margin-bottom: 8px; margin-top: 15px; }
    .theme-top { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
    
    /* 하얀 버튼 제거: a 태그용 hts-card */
    .hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 4px; padding: 10px 12px; margin-bottom: 8px; display: block; text-decoration: none; color: inherit; }
    .hts-card:hover { border: 1px solid #38bdf8; background-color: #223147; }
    
    .detail-card { background-color: #17202e; border: 1px solid #283954; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
    .stExpander { background-color: #1b2636 !important; border: 1px solid #283954 !important; }
    .rank-card { background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 8px 12px; border-radius: 4px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
    .rank-num { color: #38bdf8; font-weight: bold; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="hts_refresh")

headers = {'User-Agent': 'Mozilla/5.0'}

@st.cache_data(ttl=600)
def fetch_dynamic_themes():
    url = "https://finance.naver.com/sise/theme.naver"
    data, stock_map = {}, {}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        themes = []
        for tr in soup.select('table.type_1 tr')[:8]:
            a = tr.select_one('a')
            if a: themes.append({'name': a.text.strip(), 'link': "https://finance.naver.com" + a['href']})
        for t in themes:
            res_t = requests.get(t['link'], headers=headers, timeout=5)
            res_t.encoding = 'euc-kr'
            soup_t = BeautifulSoup(res_t.text, 'html.parser')
            stocks = []
            for tr in soup_t.select('table.type_5 tr'):
                td = tr.select_one('td.name')
                if td and td.a:
                    s_name = td.a.text.replace("*", "").strip()
                    s_code = td.a['href'].split('code=')[-1][:6]
                    stocks.append(s_name)
                    stock_map[s_name] = s_code
            data[t['name']] = {"news": f"🚀 {t['name']} 섹터 집중 분석", "stocks": stocks}
        return data, stock_map
    except: return {}, {}

# [핵심 1] 시가총액 2중 안전장치 파싱
def get_single_mcap(name_code):
    name, code = name_code
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1차 시도 (ID로 찾기)
        m_sum = soup.select_one("#_market_sum")
        if m_sum:
            val = int(m_sum.text.replace(",", "").strip())
            return name, (f"{val/10000:.1f}조" if val >= 10000 else f"{val:,}억")
        
        # 2차 시도 (텍스트로 찾기 - 예: 우선주, ETF 등)
        for th in soup.select('th'):
            if "시가총액" in th.text:
                td = th.find_next_sibling('td')
                if td:
                    text = td.text.strip().replace("\\n", "").replace("\\t", "").replace(" ", "")
                    return name, text
    except: pass
    return name, "-"

# [핵심 2] 병렬 처리로 속도 향상 (멈춤 현상 방지)
@st.cache_data(ttl=3600)
def fetch_market_caps(stock_map):
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(get_single_mcap, stock_map.items()))
    return dict(results)

@st.cache_data(ttl=5)
def fetch_prices(stock_map):
    prices = {}
    codes = list(stock_map.values())
    for i in range(0, len(codes), 20):
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{','.join(codes[i:i+20])}"
        try:
            res = requests.get(url, headers=headers, timeout=3).json()
            for area in res.get("result", {}).get("areas", []):
                for item in area.get("datas", []):
                    name = [k for k, v in stock_map.items() if v == item.get("cd")]
                    if name:
                        prices[name[0]] = {
                            "price": f"{item.get('nv', 0):,}", 
                            "rate": f"{'+' if item.get('cr', 0) > 0 else ''}{item.get('cr', 0):.2f}%",
                            "volume": f"{int(item.get('aq', 0) * item.get('nv', 0) / 100000000):,}억"
                        }
        except: pass
    return prices

@st.cache_data(ttl=300)
def fetch_news(stock_name):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(stock_name)}+주식&hl=ko&gl=KR"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        root = ET.fromstring(res.content)
        return [{"title": item.find('title').text, "link": item.find('link').text, "source": item.find('source').text if item.find('source') is not None else "경제속보"} for item in root.findall('.//item')[:5]]
    except: return []

# 3. 로직 실행
theme_data, STOCK_MAP = fetch_dynamic_themes()
MCAP_DATA = fetch_market_caps(STOCK_MAP)
realtime_data = fetch_prices(STOCK_MAP)

all_stocks_data, processed_themes = [], {}
for t_name, t_val in theme_data.items():
    stocks_list = []
    for sname in t_val["stocks"]:
        info = realtime_data.get(sname, {"price": "-", "rate": "0.00%", "volume": "0억"})
        try:
            r = float(info["rate"].replace("%", "").replace("+", ""))
            v = int(info["volume"].replace("억", "").replace(",", ""))
        except: r, v = 0.0, 0
        stocks_list.append((sname, r, v, info))
        all_stocks_data.append((sname, r, v, info))
    processed_themes[t_name] = {"news": t_val["news"], "stocks_data": stocks_list, "total_vol": sum(x[2] for x in stocks_list), "avg_rate": sum(x[1] for x in stocks_list)/len(stocks_list) if stocks_list else 0}

top_rate = sorted(all_stocks_data, key=lambda x: x[1], reverse=True)[:5]
top_vol = sorted(all_stocks_data, key=lambda x: x[2], reverse=True)[:5]

if "page_mode" not in st.session_state: st.session_state.page_mode = "main"
if "stock" in st.query_params:
    st.session_state.active_stock = st.query_params["stock"]
    st.session_state.page_mode = "detail"
    st.query_params.clear()

# 4. 화면 출력
if st.session_state.page_mode == "main":
    st.markdown("<h3 style='color:#38bdf8;'>📱 실시간 주도주 랭킹 통합 전광판</h3>", unsafe_allow_html=True)
    
    # [복구 완료] 1. 종목 검색창
    search = st.selectbox("", ["🔍 종목명을 검색하세요"] + list(STOCK_MAP.keys()), label_visibility="collapsed")
    if search != "🔍 종목명을 검색하세요": st.session_state.active_stock = search; st.session_state.page_mode = "detail"; st.rerun()
    
    # [복구 완료] 2. 급등주 & 거래대금 TOP 5
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🔥 급등 Top 5")
        for i, (s, r, v, info) in enumerate(top_rate):
            st.markdown(f"<div class='rank-card'><span class='rank-num'>{i+1}</span><span style='flex:1;'>{s}</span><span style='color:#ef4444; font-weight:bold;'>{info['rate']}</span></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("#### 💰 거래대금 Top 5")
        for i, (s, r, v, info) in enumerate(top_vol):
            st.markdown(f"<div class='rank-card'><span class='rank-num'>{i+1}</span><span style='flex:1;'>{s}</span><span style='color:#eab308; font-weight:bold;'>{info['volume']}</span></div>", unsafe_allow_html=True)
    
    # [복구 완료] 3. 테마 및 종목 (하얀 띠 없는 카드)
    for t_name in sorted(processed_themes.keys(), key=lambda x: (processed_themes[x]["avg_rate"], processed_themes[x]["total_vol"]), reverse=True):
        t = processed_themes[t_name]
        st.markdown(f"<div class='theme-box'><div class='theme-top'><b>{t_name}</b> <span>평균 {t['avg_rate']:.2f}%</span></div></div>", unsafe_allow_html=True)
        for sname, r, v, info in sorted(t["stocks_data"], key=lambda x: x[1], reverse=True):
            st.markdown(f"""
                <a href='?stock={sname}' style='text-decoration:none;'>
                    <div class='hts-card'>
                        <div style='display:flex; justify-content:space-between;'><span style='font-weight:bold;'>{sname}</span><span style='color:#ef4444; font-weight:bold;'>{info['rate']}</span></div>
                        <div style='font-size:11px; color:#94a3b8; margin-top:4px;'>{info['price']}원 | 시총 {MCAP_DATA.get(sname, '-')} | {info['volume']}</div>
                    </div>
                </a>
            """, unsafe_allow_html=True)
else:
    # [복구 완료] 4. 상세 페이지 및 뉴스 피드
    if st.button("◀ 목록으로 돌아가기"): st.session_state.page_mode = "main"; st.rerun()
    tgt = st.session_state.active_stock
    info = realtime_data.get(tgt, {"price": "-", "rate": "0%", "volume": "0억"})
    st.markdown(f"<div class='detail-card'><h3>⭐ {tgt}</h3><h2 style='color:#ef4444; margin:10px 0;'>{info['price']}원 ({info['rate']})</h2><p style='color:#cbd5e1;'>시가총액: <b>{MCAP_DATA.get(tgt, '-')}</b> | 거래대금: <b>{info['volume']}</b></p></div>", unsafe_allow_html=True)
    
    st.write("🔥 실시간 뉴스 피드")
    for nw in fetch_news(tgt):
        with st.expander(f"📌 [{nw['source']}] {nw['title']}"): st.link_button("🔗 원문 보기", nw['link'])
