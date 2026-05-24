import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import re

# 1. 페이지 레이아웃 최적화 (모바일 뷰어 스타일에 맞춤)
st.set_page_config(page_title="테마별 주도주", layout="wide")

# [핵심] 보내주신 이미지와 똑같이 밝은 톤, 민트색 헤더, 2열 구조, 노란색 하이라이트 CSS 적용
st.markdown("""
<style>
    /* 전체 배경을 밝게 */
    body, .stApp, [data-testid="stAppViewContainer"], .main { background-color: #f0f4f5 !important; color: #111 !important; }
    
    /* 테마 카드 컨테이너 */
    .theme-card { background: #ffffff; border: 1px solid #d1d5db; border-radius: 8px; margin-bottom: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    
    /* 테마 헤더 (민트색) */
    .theme-header { background-color: #17b6b6; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; color: white; font-weight: bold; font-size: 1.1em; }
    .theme-vol { background: white; color: #ef4444; padding: 2px 8px; border-radius: 4px; font-size: 0.9em; font-weight: bold; border: 1px solid #ef4444; }
    
    /* 테마 뉴스 (회색바탕) */
    .theme-news { background: #f8fafc; padding: 6px 12px; font-size: 0.85em; color: #475569; border-bottom: 1px solid #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    
    /* 개별 종목 컨테이너 */
    .stock-item { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; display: block; text-decoration: none; color: inherit; }
    .stock-item:last-child { border-bottom: none; }
    .stock-item:hover { background-color: #f8fafc; }
    
    /* 상한가 노란색 강조 배경 */
    .bg-upper-limit { background-color: #fffac0 !important; border-left: 3px solid #ef4444; }
    
    /* 텍스트 색상 및 정렬 */
    .row1, .row2 { display: flex; justify-content: space-between; align-items: center; }
    .row1 { margin-bottom: 4px; }
    
    .s-name { font-weight: 600; font-size: 1.05em; color: #1f2937; }
    .s-rate { font-weight: bold; font-size: 1.05em; }
    .s-price { font-weight: bold; font-size: 0.95em; }
    .s-vol { font-weight: bold; color: #374151; font-size: 0.9em; }
    
    .text-red { color: #ef4444 !important; }
    .text-blue { color: #3b82f6 !important; }
    .text-black { color: #1f2937 !important; }
    
    /* 시각적 바 (가짜 게이지 효과) */
    .visual-bar { height: 4px; background: #e2e8f0; border-radius: 2px; margin-top: 6px; width: 100%; position: relative; }
    .visual-bar-fill { height: 100%; background: #ef4444; border-radius: 2px; position: absolute; right: 10%; width: 40%; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="hts_refresh")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9'
}

@st.cache_data(ttl=600)
def fetch_dynamic_themes_v3():
    url = "https://finance.naver.com/sise/theme.naver"
    data, stock_map = {}, {}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        html_text = res.content.decode('euc-kr', 'replace')
        soup = BeautifulSoup(html_text, 'html.parser')
        themes = []
        for tr in soup.select('table.type_1 tr')[:8]:
            a = tr.select_one('a')
            if a: themes.append({'name': a.text.strip(), 'link': "https://finance.naver.com" + a['href']})
            
        for t in themes:
            res_t = requests.get(t['link'], headers=headers, timeout=5)
            html_t = res_t.content.decode('euc-kr', 'replace')
            soup_t = BeautifulSoup(html_t, 'html.parser')
            stocks = []
            for tr in soup_t.select('table.type_5 tr'):
                td = tr.select_one('td.name')
                if td and td.a:
                    s_name = td.a.text.replace("*", "").strip()
                    s_code = td.a['href'].split('code=')[-1][:6]
                    stocks.append(s_name)
                    stock_map[s_name] = s_code
            data[t['name']] = {"news": f"{t['name']} 관련 속보 및 종목 분석", "stocks": stocks[:5]} # 5개까지만
        return data, stock_map
    except Exception: 
        return {}, {}

@st.cache_data(ttl=3600)
def fetch_market_caps_v3(stock_map):
    # 시가총액은 메인 화면에서는 안 쓰지만, 상세 화면용으로 유지합니다.
    def get_mcap(name_code):
        name, code = name_code
        try:
            url = f"https://m.stock.naver.com/api/stock/{code}/basic"
            res = requests.get(url, headers=headers, timeout=3)
            if res.status_code == 200:
                data = res.json()
                m_sum_str = str(data.get("marketSum", "")).strip()
                if m_sum_str:
                    val = re.sub(r'\s+', '', m_sum_str) 
                    if val and val[-1].isdigit(): val += "억"
                    return name, val
        except: pass
        return name, "-"
        
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(get_mcap, stock_map.items()))
    return dict(results)

@st.cache_data(ttl=5)
def fetch_prices_v3(stock_map):
    prices = {}
    codes = list(stock_map.values())
    for i in range(0, len(codes), 20):
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{','.join(codes[i:i+20])}"
        try:
            res = requests.get(url, headers=headers, timeout=3).json()
            for area in res.get("result", {}).get("areas", []):
                for item in area.get("datas", []):
                    matched = [k for k, v in stock_map.items() if v == item.get("cd")]
                    if matched:
                        name = matched[0]
                        aa_val = item.get("aa")
                        try:
                            if aa_val is not None:
                                clean_aa = str(aa_val).replace(',', '').split('.')[0]
                                vol_eok = int(clean_aa) // 100
                            else:
                                vol_eok = int(item.get("aq", 0) * item.get("nv", 0) / 100000000)
                        except:
                            vol_eok = int(item.get("aq", 0) * item.get("nv", 0) / 100000000)
                            
                        prices[name] = {
                            "price": f"{item.get('nv', 0):,}", 
                            "rate": f"{item.get('cr', 0):.2f}%", # '+' 기호 제거 (CSS로 색상 처리)
                            "volume": f"{vol_eok:,}억"
                        }
        except: pass
    return prices

# 2. 상태 관리
if "page_mode" not in st.session_state: st.session_state.page_mode = "main"
if "active_stock" not in st.session_state: st.session_state.active_stock = ""

if "stock" in st.query_params:
    st.session_state.active_stock = st.query_params["stock"]
    st.session_state.page_mode = "detail"
    del st.query_params["stock"]
    st.rerun()

# 3. 데이터 로드 (v3)
theme_data, STOCK_MAP = fetch_dynamic_themes_v3()
MCAP_DATA = fetch_market_caps_v3(STOCK_MAP)
realtime_data = fetch_prices_v3(STOCK_MAP)

processed_themes = {}
for t_name, t_val in theme_data.items():
    stocks_list = []
    for sname in t_val["stocks"]:
        info = realtime_data.get(sname, {"price": "-", "rate": "0.00%", "volume": "0억"})
        try:
            rate_str = info["rate"].replace("%", "").replace(",", "")
            vol_str = info["volume"].replace("억", "").replace(",", "")
            r = float(rate_str) if rate_str and rate_str != "-" else 0.0
            v = int(vol_str) if vol_str else 0
        except ValueError:
            r, v = 0.0, 0
        stocks_list.append((sname, r, v, info))
        
    total_vol = sum(x[2] for x in stocks_list)
    avg_rate = sum(x[1] for x in stocks_list) / len(stocks_list) if stocks_list else 0.0
    processed_themes[t_name] = {"news": t_val["news"], "stocks_data": stocks_list, "total_vol": total_vol, "avg_rate": avg_rate}


# 4. 화면 출력 (완벽한 이미지 복원 UI)
if st.session_state.page_mode == "main":
    
    search = st.selectbox("", ["🔍 종목, 테마명을 입력하세요."] + list(STOCK_MAP.keys()), label_visibility="collapsed")
    if search != "🔍 종목, 테마명을 입력하세요.": 
        st.session_state.active_stock = search
        st.session_state.page_mode = "detail"
        st.rerun()
    
    # 테마 리스트 (정렬)
    sorted_themes = sorted(processed_themes.keys(), key=lambda x: (processed_themes[x]["avg_rate"], processed_themes[x]["total_vol"]), reverse=True)
    
    # 2열(그리드) 배치
    for i in range(0, len(sorted_themes), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(sorted_themes):
                t_name = sorted_themes[i + j]
                t = processed_themes[t_name]
                
                with cols[j]:
                    total_vol_str = f"{int(t['total_vol']):,}억"
                    
                    # HTML 작성
                    html_str = f"""
                    <div class="theme-card">
                        <div class="theme-header">
                            <span>{t_name}</span>
                            <span class="theme-vol">{total_vol_str}</span>
                        </div>
                        <div class="theme-news">{t['news']}</div>
                    """
                    
                    # 종목 리스트 렌더링
                    for sname, r, v, info in sorted(t["stocks_data"], key=lambda x: x[1], reverse=True):
                        # 상한가(29% 이상)일 때 노란색 배경 클래스 적용
                        bg_class = "bg-upper-limit" if r >= 29.0 else ""
                        
                        # 색상 및 화살표 처리
                        if r > 0:
                            color_class = "text-red"
                            rate_display = f"↑{r:.2f}%" if r >= 29.0 else f"{r:.2f}%"
                        elif r < 0:
                            color_class = "text-blue"
                            rate_display = f"{r:.2f}%"
                        else:
                            color_class = "text-black"
                            rate_display = "0.00%"
                            
                        price_color = "text-red" if r > 0 else "text-blue" if r < 0 else "text-black"
                        
                        html_str += f"""
                        <a href="?stock={sname}" class="stock-item {bg_class}">
                            <div class="row1">
                                <span class="s-name">{sname}</span>
                                <span class="s-rate {color_class}">{rate_display}</span>
                            </div>
                            <div class="row2">
                                <span class="s-price {price_color}">{info['price']}</span>
                                <span class="s-vol">{info['volume']}</span>
                            </div>
                            <div class="visual-bar"><div class="visual-bar-fill" style="background-color: {'#ef4444' if r>0 else '#3b82f6'};"></div></div>
                        </a>
                        """
                    html_str += "</div>"
                    st.markdown(html_str, unsafe_allow_html=True)

else:
    # 상세 페이지
    if st.button("◀ 목록으로 돌아가기"): st.session_state.page_mode = "main"; st.rerun()
    tgt = st.session_state.active_stock
    info = realtime_data.get(tgt, {"price": "-", "rate": "0%", "volume": "0억"})
    
    try:
        r_val = float(info['rate'].replace('%', '').replace('+', '').replace(',', ''))
        color = "#ef4444" if r_val > 0 else "#3b82f6" if r_val < 0 else "#1f2937"
    except: color = "#ef4444"
        
    st.markdown(f"""
        <div style='background:#fff; border:1px solid #d1d5db; padding:20px; border-radius:8px;'>
            <h3 style='color:#111;'>⭐ {tgt}</h3>
            <h2 style='color:{color}; margin:10px 0;'>{info['price']}원 ({info['rate']})</h2>
            <p style='color:#475569;'>시가총액: <b>{MCAP_DATA.get(tgt, '-')}</b> | 거래대금: <b>{info['volume']}</b></p>
        </div>
    """, unsafe_allow_html=True)
