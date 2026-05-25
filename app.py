import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET
import concurrent.futures
import re

# 1. 페이지 레이아웃 및 다크테마 최적화 세팅
st.set_page_config(page_title="NXT 자동형 주도주 전광판", layout="wide")

# [모바일 가독성, 강제 번역 차단, 배경색 강제 고정 및 CSS 텍스트 노출 방지]
st.markdown("""
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google" content="notranslate">
</head>
<style>
body, .stMarkdown, .stText, .stExpander, .stSelectbox, h4 { color: #ffffff !important; }
[data-testid="stHeader"] {background: #0f141c !important;}
body, .stApp, [data-testid="stAppViewContainer"], .main { background-color: #0f141c !important; }
.theme-box { background-color: #17202e; border: 1px solid #233249; border-radius: 6px; padding: 10px; margin-bottom: 8px; margin-top: 15px; }
.theme-top { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
.theme-lbl { background-color: #1e3a5f; color: #38bdf8 !important; font-size: 13px; font-weight: bold; padding: 2px 10px; border-radius: 4px; }
.theme-amt { color: #f43f5e !important; font-size: 13px; font-weight: bold; }
.theme-desc { color: #94a3b8 !important; font-size: 11px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 모바일 화면에서 글씨 뚫고 나가는 현상 방지 (고정높이 제거 및 유연한 여백 적용) */
.hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 4px; padding: 10px 12px; margin-bottom: 8px; min-height: 66px; height: auto; display: flex; flex-direction: column; justify-content: center; cursor: pointer; }
.hts-card:hover { border: 1px solid #38bdf8; background-color: #223147; }
.hts-up .status-color { color: #ef4444 !important; }
.hts-down .status-color { color: #3b82f6 !important; }
.hts-limit { background-color: #eab308 !important; border: 1px solid #facc15 !important; }
.hts-limit .stock-title { color: #000000 !important; }
.hts-limit .status-color { color: #d32f2f !important; font-weight: 900; }
.hts-limit .hts-sub-row { color: #334155 !important; }
.detail-card { background-color: #17202e; border: 1px solid #283954; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
.stExpander { background-color: #1b2636 !important; border: 1px solid #283954 !important; margin-bottom: 6px !important; border-radius: 4px !important; }
.rank-card { background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 8px 12px; border-radius: 4px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
.rank-num { color: #38bdf8; font-weight: bold; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="hts_refresh")

@st.cache_data(ttl=600)
def fetch_dynamic_themes():
    url = "https://finance.naver.com/sise/theme.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    dynamic_theme_data = {}
    dynamic_stock_map = {}

    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')

        themes = []
        for tr in soup.select('table.type_1 tr'):
            tds = tr.select('td')
            if len(tds) >= 2:
                a_tag = tds[0].select_one('a')
                if not a_tag: continue
                theme_name = a_tag.text.strip()
                theme_link = "https://finance.naver.com" + a_tag['href']
                themes.append({'name': theme_name, 'link': theme_link})
                if len(themes) >= 8: break

        for t in themes:
            res_t = requests.get(t['link'], headers=headers, timeout=5)
            res_t.encoding = 'euc-kr'
            soup_t = BeautifulSoup(res_t.text, 'html.parser')

            stocks = []
            for tr in soup_t.select('table.type_5 tr'):
                name_td = tr.select_one('td.name')
                if name_td:
                    a_tag = name_td.select_one('a')
                    if a_tag:
                        s_name = a_tag.text.replace("*", "").strip()
                        s_code = a_tag['href'].split('code=')[-1][:6]
                        stocks.append(s_name)
                        dynamic_stock_map[s_name] = s_code

            dynamic_theme_data[t['name']] = {
                "news": f"🚀 {t['name']} 섹터 집중 분석",
                "stocks": stocks
            }
        return dynamic_theme_data, dynamic_stock_map
    except Exception as e:
        return {"시스템 안내": {"news": "데이터 로딩 중...", "stocks": ["삼성전자"]}}, {"삼성전자": "005930"}

theme_data, STOCK_MAP = fetch_dynamic_themes()

# --- [수정] 대형주 '조' 단위 에러 완벽 해결 ---
@st.cache_data(ttl=3600)
def fetch_market_caps(stock_map):
    caps = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    def fetch_single_cap(name, code):
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            res = requests.get(url, headers=headers, timeout=3)
            soup = BeautifulSoup(res.text, 'html.parser')

            m_sum_tag = soup.select_one("#_market_sum")
            if m_sum_tag:
                val_str = " ".join(m_sum_tag.text.strip().split())
                if val_str.endswith("조"):
                    cap_str = val_str
                else:
                    cap_str = f"{val_str}억"
                return name, cap_str
            else:
                return name, "-"
        except:
            return name, "-"

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_stock = {executor.submit(fetch_single_cap, name, code): name for name, code in stock_map.items()}
        for future in concurrent.futures.as_completed(future_to_stock):
            name, cap_str = future.result()
            caps[name] = cap_str

    return caps
# -----------------------------------------------------

MCAP_DATA = fetch_market_caps(STOCK_MAP)

# ★★★ 여기서부터 네이버 마감과 똑같이 맞추는 실시간 거래대금 연동 핵심 수정 ★★★
@st.cache_data(ttl=5)
def fetch_hts_api_prices(stock_map):
    if not stock_map: return {}
    codes = list(stock_map.values())
    prices = {}
    
    # 1. 실시간 API 호출을 통한 기본 가격 및 변동률 바인딩
    chunk_size = 20
    for i in range(0, len(codes), chunk_size):
        chunk = codes[i:i+chunk_size]
        codes_str = ",".join(chunk)
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{codes_str}"
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
            for area in res.get("result", {}).get("areas", []):
                for item in area.get("datas", []):
                    code = item.get("cd")
                    name = [k for k, v in stock_map.items() if v == code]
                    if name:
                        name = name[0]
                        close = item.get("nv", 0)
                        chg_type = item.get("rf")
                        rate = item.get("cr", 0.0)
                        cv = item.get("cv", 0)
                        aq = item.get("aq", 0)
                        
                        fallback_vol = f"{int(aq * close / 100000000):,}억" if aq else "0억"
                        
                        if close > 0:
                            prices[name] = {
                                "price": f"{close:,}", 
                                "rate": f"{'+' if chg_type in ['1','2'] else '-' if chg_type in ['5'] else ''}{rate:.2f}%",
                                "type": chg_type, 
                                "diff": f"{cv:,}", 
                                "volume": fallback_vol
                            }
        except: pass

    # 2. 네이버 금융 상세페이지 웹크롤러 정밀 교정 (실시간 '거래대금' 타겟 추적)
    def fetch_exact_volume(name, code):
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            res.encoding = 'euc-kr'
            html_text = res.text
            
            soup = BeautifulSoup(html_text, 'html.parser')
            # 네이버 웹페이지에서 '거래대금' 글자를 찾은 뒤 바로 다음에 위치하는 <em> 태그의 숫자를 가져옵니다.
            element = soup.find(text=re.compile('거래대금'))
            if element:
                em = element.find_next('em')
                if em:
                    val = em.text.replace(',', '').strip()
                    if val.isdigit():
                        val_int = int(val)
                        if val_int >= 100:
                            return name, f"{val_int // 100:,}억"
                        else:
                            return name, f"{val_int / 100:.1f}억"
            
            # 돔 구조 탐색 예외 발생 시 정규식을 이용한 2차 백업 스크래핑 기법 가동
            match = re.search(r'거래대금[\s\S]*?<em>([\d,]+)</em>', html_text)
            if match:
                val = match.group(1).replace(',', '').strip()
                if val.isdigit():
                    val_int = int(val)
                    if val_int >= 100:
                        return name, f"{val_int // 100:,}억"
                    else:
                        return name, f"{val_int / 100:.1f}억"
        except:
            pass
        return name, None

    # 초고속 병렬 처리를 이용해 종목별 네이버 웹 화면의 찐 거래대금 실시간 동시 주입
    if prices:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_stock = {executor.submit(fetch_exact_volume, name, stock_map[name]): name for name in prices.keys()}
            for future in concurrent.futures.as_completed(future_to_stock):
                name, exact_vol_str = future.result()
                if exact_vol_str:
                    prices[name]["volume"] = exact_vol_str

    return prices
# ★===================================================================★

realtime_data = fetch_hts_api_prices(STOCK_MAP)

@st.cache_data(ttl=300)
def fetch_live_global_financial_news(stock_name):
    encoded_name = urllib.parse.quote(stock_name)
    url = f"https://news.google.com/rss/search?q={encoded_name}+-site:hankyung.com+-site:sedaily.com&hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0'}
    news_list = []
    try:
        res = requests.get(url, headers=headers, timeout=5)
        root = ET.fromstring(res.content)
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            if any(k in title for k in ["유료", "로그인", "회원전용", "구독"]): continue
            if "hankyung.com" in link or "sedaily.com" in link: continue
            source = item.find('source').text if item.find('source') is not None else "경제속보"
            desc_text = "기사 요약 내용을 불러오는 중입니다."
            desc_elem = item.find('description')
            if desc_elem is not None and desc_elem.text:
                raw_desc = desc_elem.text
                desc_soup = BeautifulSoup(raw_desc, 'html.parser')
                desc_text = desc_soup.get_text(strip=True)[:150] + "..."
            if " - " in title: title = title.rsplit(" - ", 1)[0]
            news_list.append({"title": title, "link": link, "source": source, "desc": desc_text})
            if len(news_list) >= 5: break
        return news_list
    except: return []

def get_numeric_score(sname):
    info = realtime_data.get(sname, {"price": "-", "rate": "0.00%", "type": "3", "volume": "0억", "diff": "0"})
    info["mcap"] = MCAP_DATA.get(sname, "-")
    try:
        rate_val = float(info["rate"].replace("%", "").replace("+", ""))
        vol_raw = info["volume"].replace("억", "").replace(",", "")
        if '.' in vol_raw:
            vol_val = int(float(vol_raw))
        else:
            vol_val = int(vol_raw)
    except:
        rate_val = 0.0
        vol_val = 0
    return rate_val, vol_val, info

all_stocks_data = []
processed_themes = {}

for t_name, t_val in theme_data.items():
    total_vol = 0
    sum_rate = 0.0
    stock_list_with_score = []

    for sname in t_val["stocks"]:
        r_val, v_val, info = get_numeric_score(sname)
        total_vol += v_val
        sum_rate += r_val
        stock_list_with_score.append((sname, r_val, v_val, info))
        all_stocks_data.append((sname, r_val, v_val, info))

    valid_stocks = len(t_val["stocks"])
    avg_rate = sum_rate / valid_stocks if valid_stocks > 0 else 0.0

    processed_themes[t_name] = {
        "money": f"{total_vol:,}억",
        "news": t_val["news"],
        "stocks_data": stock_list_with_score,
        "total_vol": total_vol,
        "avg_rate": avg_rate
    }

sorted_theme_names = sorted(processed_themes.keys(), key=lambda x: (processed_themes[x]["avg_rate"], processed_themes[x]["total_vol"]), reverse=True)
top_rate_stocks = sorted(all_stocks_data, key=lambda x: x[1], reverse=True)[:5] if all_stocks_data else []
top_vol_stocks = sorted(all_stocks_data, key=lambda x: x[2], reverse=True)[:5] if all_stocks_data else []

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
    st.markdown("<h3 class='notranslate' style='margin:0 0 15px 0; color:#38bdf8;'>📱 실시간 주도주 랭킹 통합 전광판 (Full 집계)</h3>", unsafe_allow_html=True)
    stock_options = ["🔍 종목명을 검색하세요"] + list(STOCK_MAP.keys())
    selected_search = st.selectbox("", stock_options, label_visibility="collapsed")
    if selected_search != stock_options[0]:
        st.session_state.active_stock = selected_search
        st.session_state.page_mode = "detail"
        st.rerun()
    st.markdown("<hr style='border-color: #334155; margin: 15px 0;'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h4 style='color:#ffffff; font-size:16px;'>🔥 현재 장중 급등 Top 5</h4>", unsafe_allow_html=True)
        for idx, (sname, r_val, v_val, s_info) in enumerate(top_rate_stocks):
            sign, color = ("▲", "#ef4444") if r_val > 0 else ("▼", "#3b82f6")
            st.markdown(f"<div class='rank-card notranslate' style='border-left-color: {color};'><div><span class='rank-num'>{idx+1}</span><span style='color:white; font-weight:bold;'>{sname}</span></div><div style='color:{color}; font-weight:bold;'>{sign} {s_info['rate']}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<h4 style='color:#ffffff; font-size:16px;'>💰 현재 거래대금 Top 5</h4>", unsafe_allow_html=True)
        for idx, (sname, r_val, v_val, s_info) in enumerate(top_vol_stocks):
            st.markdown(f"<div class='rank-card notranslate' style='border-left-color: #eab308;'><div><span class='rank-num'>{idx+1}</span><span style='color:white; font-weight:bold;'>{sname}</span></div><div style='color:#eab308; font-weight:bold;'>{s_info['volume']}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #334155; margin: 15px 0;'>", unsafe_allow_html=True)
    for t_name in sorted_theme_names:
        t_val = processed_themes[t_name]
        avg_str = f"+{t_val['avg_rate']:.2f}%" if t_val['avg_rate'] > 0 else f"{t_val['avg_rate']:.2f}%"
        avg_color = "#ef4444" if t_val['avg_rate'] > 0 else "#3b82f6" if t_val['avg_rate'] < 0 else "#94a3b8"
        st.markdown(f'''<div class="theme-box notranslate"><div class="theme-top"><span class="theme-lbl">{t_name} (섹터순위)</span><div style="text-align: right;"><span style="color: {avg_color} !important; font-size: 13px; font-weight: bold; margin-right: 8px;">평균 {avg_str}</span><span class="theme-amt">합산 {t_val["money"]}</span></div></div><div class="theme-desc">{t_val["news"]}</div></div>''', unsafe_allow_html=True)
        cols = st.columns(4)
        sorted_stocks = sorted(t_val["stocks_data"], key=lambda x: x[1], reverse=True)
        for idx, (sname, r_val, v_val, s_info) in enumerate(sorted_stocks):
            class_mode = "hts-limit" if s_info["type"] == "1" else "hts-down" if s_info["type"] == "5" or "-" in s_info["rate"] else "hts-up"
            sign = "▲ " if class_mode != "hts-down" else "▼ "

            cols[idx % 4].markdown(f"<a class='notranslate' href='?stock={sname}' target='_self' style='text-decoration:none; color:inherit;'><div class='hts-card {class_mode}'><div class='hts-row' style='display:flex; justify-content:space-between;'><span class='stock-title' style='color:#ffffff; font-weight:bold; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;'>{sname}</span><span class='status-color' style='font-weight:bold; margin-left:4px;'>{sign}{s_info['rate']}</span></div><div class='hts-sub-row' style='display:flex; justify-content:space-between; margin-top:4px;'><span class='status-color'>{s_info['price']}원</span><div style='text-align:right; font-size:10px;'><span style='color:#94a3b8;'>시 {s_info['mcap']}</span> <span style='color:#cbd5e1;'>| 거래 {s_info['volume']}</span></div></div></div></a>", unsafe_allow_html=True)

elif st.session_state.page_mode == "detail":
    if st.button("◀ 실시간 랭킹 전광판으로 돌아가기", use_container_width=True): go_main(); st.rerun()
    tgt = st.session_state.active_stock
    tgt_code = STOCK_MAP.get(tgt, "005930")
    _, _, live = get_numeric_score(tgt)
    mode_color = "#eab308" if live["type"] == "1" else "#ef4444" if live["type"] in ["2","1"] and "-" not in live["rate"] else "#3b82f6"
    st.markdown(f"""<div class="detail-card notranslate"><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:22px; font-weight:bold; color:#f8fafc;">⭐ {tgt}</span><span style="color:#64748b; font-size:14px;">(코드 {tgt_code})</span></div><div style="margin: 10px 0; font-size:26px; font-weight:bold; color:{mode_color};">{live["price"]} <span style="font-size:15px; color:#cbd5e1;">({live["rate"]})</span><span style="float:right; font-size:13px; color:#94a3b8; margin-top:10px;">시총 {live["mcap"]} | 거래대금 {live["volume"]}</span></div></div>""", unsafe_allow_html=True)
    st.markdown("<p style='font-size:15px; font-weight:bold; color:#38bdf8; margin-top:5px;'>🔥 실시간 뉴스 피드</p>", unsafe_allow_html=True)
    for nw in fetch_live_global_financial_news(tgt):
        with st.expander(f"📌 [{nw['source']}] {nw['title']}"):
            st.markdown(f"<p style='color:#cbd5e1; font-size:13px; line-height:1.6;'>{nw['desc']}</p>", unsafe_allow_html=True)
            st.link_button("🔗 원문 보기", nw['link'])
