import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET 

# 페이지 레이아웃 및 다크테마 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide") 

# 모바일 반응형 및 번역 차단 추가
st.markdown("""
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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

WEEKEND_FALLBACK = {
"주성엔지니어링": {"price": "224,000", "rate": "+20.95%", "type": "2", "volume": "1,389억"},
"SFA반도체": {"price": "10,250", "rate": "+14.53%", "type": "2", "volume": "7,083억"},
"파두": {"price": "128,300", "rate": "+9.94%", "type": "2", "volume": "2,885억"},
"제주반도체": {"price": "118,700", "rate": "+0.76%", "type": "2", "volume": "6,589억"},
"삼성전기": {"price": "1,331,000", "rate": "+10.55%", "type": "2", "volume": "34,089억"},
"LG이노텍": {"price": "863,000", "rate": "+2.98%", "type": "2", "volume": "3,990억"},
"SK하이닉스": {"price": "1,941,000", "rate": "+0.05%", "type": "2", "volume": "102,265억"},
"삼성전자": {"price": "293,000", "rate": "-2.17%", "type": "5", "volume": "104,397억"},
"LG씨엔에스": {"price": "82,700", "rate": "+3.12%", "type": "2", "volume": "6,049억"},
"LG전자": {"price": "237,000", "rate": "+0.85%", "type": "2", "volume": "30,132억"},
"현대차": {"price": "655,000", "rate": "-1.65%", "type": "5", "volume": "15,249억"},
"현대모비스": {"price": "648,000", "rate": "-3.28%", "type": "5", "volume": "11,013억"},
"빛과전자": {"price": "6,610", "rate": "+29.86%", "type": "1", "volume": "2,546억"},
"두산퓨얼셀": {"price": "99,000", "rate": "+18.56%", "type": "2", "volume": "4,394억"},
"켄코아에어로": {"price": "28,500", "rate": "+11.55%", "type": "2", "volume": "742억"},
"OCI홀딩스": {"price": "310,500", "rate": "+10.70%", "type": "2", "volume": "3,154억"},
"알테오젠": {"price": "285,000", "rate": "+8.45%", "type": "2", "volume": "4,129억"},
"리그켐바이오": {"price": "112,000", "rate": "+4.12%", "type": "2", "volume": "1,556억"},
"HLB": {"price": "78,300", "rate": "-1.05%", "type": "5", "volume": "2,044억"},
"삼성바이오로직스": {"price": "945,000", "rate": "+0.52%", "type": "2", "volume": "986억"},
"에코프로": {"price": "88,500", "rate": "+2.31%", "type": "2", "volume": "2,110억"},
"에코프로비엠": {"price": "174,000", "rate": "+1.85%", "type": "2", "volume": "3,450억"},
"포스코퓨처엠": {"price": "245,000", "rate": "-0.95%", "type": "5", "volume": "1,120억"},
"LG엔솔": {"price": "395,000", "rate": "+0.12%", "type": "2", "volume": "2,840억"},
"NAVER": {"price": "184,500", "rate": "+1.15%", "type": "2", "volume": "1,540억"},
"카카오": {"price": "43,200", "rate": "-0.55%", "type": "5", "volume": "980억"},
"한글과컴퓨터": {"price": "24,150", "rate": "+12.45%", "type": "2", "volume": "1,240억"},
"폴라리스AI": {"price": "3,150", "rate": "+29.91%", "type": "1", "volume": "840억"},
"한화에어로스페이스": {"price": "254,000", "rate": "+6.85%", "type": "2", "volume": "4,150억"},
"현대로템": {"price": "44,150", "rate": "+4.12%", "type": "2", "volume": "2,140억"},
"LIG넥스원": {"price": "168,000", "rate": "+2.35%", "type": "2", "volume": "1,890억"},
"한국항공우주": {"price": "54,200", "rate": "-1.15%", "type": "5", "volume": "950억"}
} 

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
            name = [k for k, v in STOCK_MAP.items() if v == code]
            if name:
                name = name[0]
                close = item.get("nv", 0)
                chg_type = item.get("rf")
                rate = item.get("cr", 0.0)
                cv = item.get("cv", 0)
                aq = item.get("aq", 0)
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
    headers = {'User-Agent': 'Mozilla/5.0'}
    news_list = [] 

    exclude_keywords = ["유료", "로그인", "회원전용", "구독"] 

    try:
        res = requests.get(url, headers=headers, timeout=5)
        root = ET.fromstring(res.content) 

        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else "" 

            if any(k in title for k in exclude_keywords): continue
            if "hankyung.com" in link or "sedaily.com" in link: continue 

            source = item.find('source').text if item.find('source') is not None else "경제속보"
            date = item.find('pubDate').text if item.find('pubDate') is not None else "" 

            desc_text = "기사 요약 내용을 불러오는 중입니다."
            desc_elem = item.find('description')
            if desc_elem is not None and desc_elem.text:
                raw_desc = desc_elem.text
                desc_soup = BeautifulSoup(raw_desc, 'html.parser')
                desc_text = desc_soup.get_text(strip=True)[:150] + "..." 

            if " - " in title: title = title.rsplit(" - ", 1)[0]
            news_list.append({"title": title, "link": link, "source": source, "date": date[:16], "desc": desc_text}) 

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
    max_rate = -999.0
    stock_list_with_score = []
    for sname in t_val["stocks"]:
        r_val, v_val, info = get_numeric_score(sname)
        total_vol += v_val
        if r_val > max_rate: max_rate = r_val
        stock_list_with_score.append((sname, r_val, v_val, info))
        all_stocks_data.append((sname, r_val, v_val, info)) 

    stock_list_with_score.sort(key=lambda x: x[1], reverse=True)
    processed_themes[t_name] = {"money": f"{total_vol:,}억", "news": t_val["news"], "stocks_data": stock_list_with_score, "total_vol": total_vol} 

sorted_theme_names = sorted(processed_themes.keys(), key=lambda x: processed_themes[x]["total_vol"], reverse=True) 

top_rate_stocks = sorted(all_stocks_data, key=lambda x: x[1], reverse=True)[:5]
top_vol_stocks = sorted(all_stocks_data, key=lambda x: x[2], reverse=True)[:5] 

st.markdown("""
<style>
[data-testid="stHeader"] {background: #0f141c;}
body { background-color: #0f141c; }
.theme-box { background-color: #17202e; border: 1px solid #233249; border-radius: 6px; padding: 10px; margin-bottom: 8px; margin-top: 15px; }
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
.hts-limit .hts-sub-row { color: #334155 !important; }
.detail-card { background-color: #17202e; border: 1px solid #283954; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
.stExpander { background-color: #1b2636 !important; border: 1px solid #283954 !important; margin-bottom: 6px !important; border-radius: 4px !important; }
.rank-card { background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 8px 12px; border-radius: 4px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
.rank-num { color: #38bdf8; font-weight: bold; margin-right: 10px; }
</style>
""", unsafe_allow_html=True) 

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
    st.markdown("<h3 class='notranslate' style='margin:0 0 15px 0; color:#38bdf8;'>📱 실시간 주도주 랭킹 통합 전광판</h3>", unsafe_allow_html=True)
    stock_options = ["🔍 종목명을 검색하거나 선택하세요 (뉴스 확인)"] + list(STOCK_MAP.keys())
    selected_search = st.selectbox("", stock_options, label_visibility="collapsed") 

    if selected_search != stock_options[0]:
        st.session_state.active_stock = selected_search
        st.session_state.page_mode = "detail"
        st.rerun() 

    st.markdown("<hr style='border-color: #334155; margin: 15px 0;'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h4 style='color:#f8fafc; font-size:16px;'>🔥 전체 상승률 Top 5</h4>", unsafe_allow_html=True)
        for idx, (sname, r_val, v_val, s_info) in enumerate(top_rate_stocks):
            sign, color = ("▲", "#ef4444") if r_val > 0 else ("▼", "#3b82f6")
            st.markdown(f"<div class='rank-card notranslate' style='border-left-color: {color};'><div><span class='rank-num'>{idx+1}</span><span style='color:white; font-weight:bold;'>{sname}</span></div><div style='color:{color}; font-weight:bold;'>{sign} {s_info['rate']}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<h4 style='color:#f8fafc; font-size:16px;'>💰 전체 거래대금 Top 5</h4>", unsafe_allow_html=True)
        for idx, (sname, r_val, v_val, s_info) in enumerate(top_vol_stocks):
            st.markdown(f"<div class='rank-card notranslate' style='border-left-color: #eab308;'><div><span class='rank-num'>{idx+1}</span><span style='color:white; font-weight:bold;'>{sname}</span></div><div style='color:#eab308; font-weight:bold;'>{s_info['volume']}</div></div>", unsafe_allow_html=True) 

    st.markdown("<hr style='border-color: #334155; margin: 15px 0;'>", unsafe_allow_html=True)
    for t_name in sorted_theme_names:
        t_val = processed_themes[t_name]
        st.markdown(f'<div class="theme-box notranslate"><div class="theme-top"><span class="theme-lbl">{t_name} (섹터순위)</span><span class="theme-amt">합산 {t_val["money"]}</span></div><div class="theme-desc">{t_val["news"]}</div></div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, (sname, r_val, v_val, s_info) in enumerate(t_val["stocks_data"]):
            class_mode = "hts-limit" if s_info["type"] == "1" or "29.9" in s_info["rate"] else "hts-down" if s_info["type"] == "5" or "-" in s_info["rate"] else "hts-up"
            sign = "▲ " if class_mode != "hts-down" else "▼ "
            cols[idx % 4].markdown(f"<a class='notranslate' href='?stock={sname}' target='_self' style='text-decoration:none; color:inherit;'><div class='hts-card {class_mode}'><div class='hts-row' style='display:flex; justify-content:space-between;'><span class='stock-title' style='color:#ffffff; font-weight:bold;'>{sname}</span><span class='status-color' style='font-weight:bold;'>{sign}{s_info['rate']}</span></div><div class='hts-sub-row' style='display:flex; justify-content:space-between;'><span class='status-color'>{s_info['price']}원</span><span style='color:#94a3b8; font-size:12px;'>{s_info['volume']}</span></div></div></a>", unsafe_allow_html=True) 

elif st.session_state.page_mode == "detail":
    if st.button("◀ 실시간 랭킹 전광판으로 돌아가기", use_container_width=True):
        go_main()
        st.rerun()
    tgt = st.session_state.active_stock
    tgt_code = STOCK_MAP.get(tgt, "005930")
    _, _, live = get_numeric_score(tgt)
    mode_color = "#eab308" if live["type"] == "1" else "#ef4444" if live["type"] in ["2","1"] and "-" not in live["rate"] else "#3b82f6"
    sign = "▼" if "-" in live["rate"] or live["type"] == "5" else "▲"
    st.markdown(f'<div class="detail-card notranslate"><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:22px; font-weight:bold; color:#f8fafc;">⭐ {tgt}</span><span style="color:#64748b; font-size:14px;">(주식코드 {tgt_code})</span></div><div style="margin: 10px 0; font-size:26px; font-weight:bold; color:{mode_color};">{live["price"]} <span style="font-size:15px;">{sign} {live.get("diff", "0")} ({live["rate"]})</span><span style='float:right; font-size:13px; color:#94a3b8; margin-top:10px;'>거래대금 {live["volume"]}</span></div></div>', unsafe_allow_html=True)
    st.markdown("<p style='font-size:15px; font-weight:bold; color:#38bdf8; margin-top:5px;'>🔥 실시간 뉴스 피드</p>", unsafe_allow_html=True)
    fetched_news = fetch_live_global_financial_news(tgt)
    if fetched_news:
        for nw in fetched_news:
            with st.expander(f"📌 [{nw['source']}] {nw['title']}"):
                st.markdown(f"<p style='color:#cbd5e1; font-size:13px; line-height:1.6; margin-bottom:10px;'>{nw['desc']}</p>", unsafe_allow_html=True)
                st.link_button("🔗 해당 언론사 원문 기사 전체보기", nw['link'])
    else: st.info("수집된 무료 실시간 속보가 없습니다.")
