import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET

# 1. 페이지 설정 및 다크 테마 커스텀 CSS
st.set_page_config(page_title="NXT 주도주 상승률 전광판", layout="wide")

st.markdown("""
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google" content="notranslate">
</head>
<style>
    /* 배경 및 기본 텍스트 설정 */
    [data-testid="stHeader"] {background: #0f141c !important;}
    body, .stApp, [data-testid="stAppViewContainer"], .main { background-color: #0f141c !important; color: #ffffff !important; }
    
    /* 섹터(테마) 박스 스타일 */
    .theme-box { 
        background-color: #17202e; border: 1px solid #233249; border-radius: 8px; 
        padding: 12px; margin-bottom: 10px; margin-top: 20px;
    }
    .theme-top { display: flex; justify-content: space-between; align-items: center; }
    .theme-lbl { background-color: #1e3a5f; color: #38bdf8 !important; font-size: 14px; font-weight: bold; padding: 4px 12px; border-radius: 4px; }
    .theme-stats { text-align: right; }
    .avg-rate { color: #ef4444; font-size: 15px; font-weight: bold; margin-right: 10px; }
    .sum-vol { color: #f43f5e; font-size: 13px; font-weight: bold; }
    
    /* 종목 카드 스타일 (HTS 스타일) */
    .hts-card { 
        background-color: #1b2636; border: 1px solid #283954; border-radius: 6px; 
        padding: 10px 12px; margin-bottom: 10px; height: 75px; 
        display: flex; flex-direction: column; justify-content: center; transition: 0.2s;
    }
    .hts-card:hover { border: 1px solid #38bdf8; background-color: #223147; transform: translateY(-2px); }
    
    /* 등락 색상 */
    .hts-up { border-left: 4px solid #ef4444; }
    .hts-down { border-left: 4px solid #3b82f6; }
    .hts-limit { background-color: #450a0a !important; border: 1px solid #ef4444 !important; }
    
    .stock-name { font-size: 15px; font-weight: bold; color: #ffffff; }
    .stock-rate { font-size: 15px; font-weight: bold; }
    .stock-price { font-size: 13px; color: #cbd5e1; }
    .stock-mcap { font-size: 11px; color: #94a3b8; font-weight: bold; }
    .stock-vol { font-size: 11px; color: #94a3b8; }

    /* 랭킹 카드 */
    .rank-card { 
        background-color: #1e293b; border-radius: 6px; padding: 10px; 
        margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;
    }
    .rank-num { color: #38bdf8; font-weight: bold; font-size: 16px; margin-right: 10px; }

    /* 상세 페이지 뉴스 스타일 */
    .stExpander { background-color: #1b2636 !important; border: 1px solid #283954 !important; border-radius: 6px !important; }
</style>
""", unsafe_allow_html=True)

# 5초마다 자동 새로고침
st_autorefresh(interval=5000, key="data_refresh")

# 전역 세션 생성 (성능 최적화)
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# 2. 데이터 크롤링 함수들
@st.cache_data(ttl=600)
def get_themes():
    url = "https://finance.naver.com/sise/theme.naver"
    theme_dict = {}
    stock_map = {}
    try:
        res = session.get(url, timeout=5)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 상위 10개 테마만 가져오기
        themes = []
        for tr in soup.select('table.type_1 tr'):
            tds = tr.select('td')
            if len(tds) >= 2:
                a = tds[0].select_one('a')
                if a: themes.append({'name': a.text.strip(), 'link': "https://finance.naver.com" + a['href']})
            if len(themes) >= 10: break

        for t in themes:
            res_t = session.get(t['link'], timeout=5)
            res_t.encoding = 'euc-kr'
            soup_t = BeautifulSoup(res_t.text, 'html.parser')
            stocks = []
            for tr in soup_t.select('table.type_5 tr'):
                name_td = tr.select_one('td.name')
                if name_td:
                    a = name_td.select_one('a')
                    s_name = a.text.replace("*", "").strip()
                    s_code = a['href'].split('code=')[-1][:6]
                    stocks.append(s_name)
                    stock_map[s_name] = s_code
            theme_dict[t['name']] = stocks
        return theme_dict, stock_map
    except:
        return {}, {}

@st.cache_data(ttl=3600)
def get_market_caps(stock_map):
    caps = {}
    for name, code in stock_map.items():
        try:
            url = f"https://m.stock.naver.com/api/stock/{code}/basic"
            data = session.get(url, timeout=2).json()
            m_sum = int(str(data.get("marketSum", "0")).replace(",", ""))
            caps[name] = f"{m_sum/10000:.1f}조" if m_sum >= 10000 else f"{m_sum:,}억"
        except: caps[name] = "-"
    return caps

def get_realtime_prices(stock_map):
    if not stock_map: return {}
    codes = list(stock_map.values())
    prices = {}
    for i in range(0, len(codes), 20): # 20종목씩 묶어서 요청
        chunk = ",".join(codes[i:i+20])
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{chunk}"
        try:
            res = session.get(url, timeout=3).json()
            for area in res.get("result", {}).get("areas", []):
                for item in area.get("datas", []):
                    code = item.get("cd")
                    name = [k for k, v in stock_map.items() if v == code][0]
                    close = item.get("nv", 0)
                    rate = item.get("cr", 0.0)
                    chg_type = item.get("rf") # 1: 상한가, 2: 상승, 5: 하락
                    aq = item.get("aq", 0) # 거래량
                    prices[name] = {
                        "price": f"{close:,}", "rate": rate, 
                        "rate_str": f"{'+' if chg_type in ['1','2'] else ''}{rate:.2f}%",
                        "type": chg_type, "vol_val": int(aq * close / 100000000) # 거래대금(억)
                    }
        except: pass
    return prices

# 3. 데이터 엔진 작동
THEME_STOCKS, STOCK_MAP = get_themes()
MCAP_DATA = get_market_caps(STOCK_MAP)
PRICE_DATA = get_realtime_prices(STOCK_MAP)

# 데이터 가공 및 상승률 정렬
processed_data = []
theme_summary = []

for t_name, s_list in THEME_STOCKS.items():
    t_sum_rate = 0
    t_sum_vol = 0
    t_stock_details = []
    
    for s_name in s_list:
        p = PRICE_DATA.get(s_name, {"price": "0", "rate": 0.0, "rate_str": "0.00%", "type": "3", "vol_val": 0})
        mcap = MCAP_DATA.get(s_name, "-")
        
        detail = {
            "name": s_name, "price": p["price"], "rate": p["rate"], 
            "rate_str": p["rate_str"], "type": p["type"], 
            "vol": f"{p['vol_val']:,}억", "vol_val": p['vol_val'], "mcap": mcap
        }
        t_stock_details.append(detail)
        t_sum_rate += p["rate"]
        t_sum_vol += p["vol_val"]
        processed_data.append(detail)
    
    avg_rate = t_sum_rate / len(s_list) if s_list else 0
    theme_summary.append({
        "name": t_name, "avg_rate": avg_rate, "sum_vol": t_sum_vol, 
        "stocks": sorted(t_stock_details, key=lambda x: x['rate'], reverse=True)
    })

# 전 섹터 및 종목 정렬 기준: 상승률
theme_summary = sorted(theme_summary, key=lambda x: x['avg_rate'], reverse=True)
top_gainers = sorted(processed_data, key=lambda x: x['rate'], reverse=True)[:5]
top_volumes = sorted(processed_data, key=lambda x: x['vol_val'], reverse=True)[:5]

# 4. 화면 렌더링
if "page" not in st.session_state: st.session_state.page = "main"
if "selected_stock" not in st.session_state: st.session_state.selected_stock = None

# 상세 페이지로 이동 함수
def open_detail(name):
    st.session_state.selected_stock = name
    st.session_state.page = "detail"

if st.session_state.page == "main":
    st.markdown("<h2 style='text-align:center; color:#38bdf8;'>🚀 NXT 주도주 실시간 상승률 전광판</h2>", unsafe_allow_html=True)
    
    # 상단 요약 랭킹 (상승률 / 거래대금)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h4 style='color:#ef4444;'>🔥 실시간 상승률 TOP 5</h4>", unsafe_allow_html=True)
        for i, s in enumerate(top_gainers):
            st.markdown(f"<div class='rank-card'><span class='rank-num'>{i+1}</span><span style='flex:1;'>{s['name']}</span><span style='color:#ef4444; font-weight:bold;'>{s['rate_str']}</span></div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h4 style='color:#eab308;'>💰 실시간 거래대금 TOP 5</h4>", unsafe_allow_html=True)
        for i, s in enumerate(top_volumes):
            st.markdown(f"<div class='rank-card'><span class='rank-num'>{i+1}</span><span style='flex:1;'>{s['name']}</span><span style='color:#eab308; font-weight:bold;'>{s['vol']}</span></div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#233249;'>", unsafe_allow_html=True)

    # 섹터별 종목 리스트 (상승률 순 정렬)
    for t in theme_summary:
        avg_color = "#ef4444" if t['avg_rate'] > 0 else "#3b82f6"
        st.markdown(f"""
            <div class="theme-box">
                <div class="theme-top">
                    <span class="theme-lbl">{t['name']}</span>
                    <div class="theme-stats">
                        <span class="avg-rate" style="color:{avg_color};">평균 +{t['avg_rate']:.2f}%</span>
                        <span class="sum-vol">거래합산 {t['sum_vol']:,}억</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(4)
        for idx, s in enumerate(t['stocks']):
            card_class = "hts-limit" if s['type'] == "1" else "hts-up" if s['rate'] > 0 else "hts-down"
            with cols[idx % 4]:
                if st.button(f"{s['name']}\n{s['rate_str']}", key=f"btn_{s['name']}_{idx}", use_container_width=True):
                    open_detail(s['name'])
                    st.rerun()
                # 버튼 바로 아래에 상세 정보 표시 (HTML)
                st.markdown(f"""
                    <div class='hts-card {card_class}'>
                        <div style='display:flex; justify-content:space-between;'>
                            <span class='stock-name'>{s['name']}</span>
                            <span class='stock-rate' style='color:{"#ef4444" if s['rate']>0 else "#3b82f6"};'>{s['rate_str']}</span>
                        </div>
                        <div style='margin-top:4px;'>
                            <span class='stock-price'>{s['price']}원</span>
                        </div>
                        <div style='display:flex; justify-content:space-between; margin-top:2px;'>
                            <span class='stock-mcap'>시총 {s['mcap']}</span>
                            <span class='stock-vol'>{s['vol']}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

elif st.session_state.page == "detail":
    name = st.session_state.selected_stock
    code = STOCK_MAP.get(name)
    
    if st.button("◀ 리스트로 돌아가기", use_container_width=True):
        st.session_state.page = "main"
        st.rerun()
    
    # 상세 상단 카드
    p = PRICE_DATA.get(name, {})
    mcap = MCAP_DATA.get(name, "-")
    st.markdown(f"""
        <div style='background-color:#17202e; padding:20px; border-radius:10px; border:1px solid #38bdf8;'>
            <h2 style='margin:0;'>{name} <span style='font-size:16px; color:#94a3b8;'>({code})</span></h2>
            <h1 style='color:#ef4444; margin:10px 0;'>{p.get("price","0")}원 <span style='font-size:20px;'>({p.get("rate_str","0%")})</span></h1>
            <p style='font-size:16px; color:#cbd5e1;'>시가총액: <b>{mcap}</b> | 거래대금: <b>{p.get("vol","0억")}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    # 뉴스 섹션
    st.subheader(f"🔥 {name} 관련 실시간 뉴스")
    encoded_name = urllib.parse.quote(name)
    news_url = f"https://news.google.com/rss/search?q={encoded_name}+주식&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        res = session.get(news_url)
        root = ET.fromstring(res.content)
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text[:16]
            with st.expander(f"📌 {title}"):
                st.write(f"발행일: {pub_date}")
                st.link_button("기사 원문 보기", link)
    except:
        st.error("뉴스를 불러오는 중 오류가 발생했습니다.")
