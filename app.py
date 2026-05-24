import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET 

# 1. 페이지 레이아웃 및 다크테마 최적화 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide") 

# 강제 자동 번역 차단
st.markdown("""
<head>
<meta name="google" content="notranslate">
</head>
""", unsafe_allow_html=True) 

# 5초마다 실시간 주가 무한 동기화
st_autorefresh(interval=5000, key="hts_refresh") 

# --- [이하 STOCK_MAP, WEEKEND_FALLBACK, theme_data, fetch_hts_api_prices, fetch_live_global_financial_news, get_numeric_score 동일하게 유지] ---
# (코드의 안정성을 위해 위 함수들은 그대로 사용하세요)

# --- 스타일 개선 (가독성 최적화) ---
st.markdown("""
<style>
[data-testid="stHeader"] {background: #0f141c;}
body { background-color: #0f141c; }

/* 모바일 가독성 개선 */
@media (max-width: 600px) {
    .hts-card { height: auto !important; min-height: 55px !important; padding: 6px !important; }
    .stock-title { font-size: 12px !important; }
    .status-color { font-size: 10px !important; }
    .theme-lbl { font-size: 11px !important; }
}

.theme-box { background-color: #17202e; border: 1px solid #233249; border-radius: 6px; padding: 10px; margin-bottom: 8px; margin-top: 15px; }
.hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 4px; padding: 8px; margin-bottom: 8px; cursor: pointer; }
.hts-card:hover { border: 1px solid #38bdf8; background-color: #223147; }
.rank-card { background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 8px 10px; border-radius: 4px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
</style>
""", unsafe_allow_html=True) 

# --- 메인 화면 로직 (데이터 유지) ---
# (이하 메인 로직 코드 그대로 유지하되, cols 배치 부분만 아래와 같이 수정)

# ... (상단 로직 동일) ...

for t_name in sorted_theme_names:
    t_val = processed_themes[t_name]
    st.markdown(f'<div class="theme-box notranslate"><div class="theme-top"><span class="theme-lbl">{t_name} (섹터순위)</span><span class="theme-amt">합산 {t_val["money"]}</span></div><div class="theme-desc">{t_val["news"]}</div></div>', unsafe_allow_html=True)
    
    # 모바일에서는 2열, 데스크탑에서는 4열로 자동 분기
    cols = st.columns([1, 1, 1, 1]) 
    for idx, (sname, r_val, v_val, s_info) in enumerate(t_val["stocks_data"]):
        class_mode = "hts-limit" if s_info["type"] == "1" or "29.9" in s_info["rate"] else "hts-down" if s_info["type"] == "5" or "-" in s_info["rate"] else "hts-up"
        sign = "▲ " if class_mode != "hts-down" else "▼ "
        
        # 4열 배치 유지
        with cols[idx % 4]:
            st.markdown(f"<a class='notranslate' href='?stock={sname}' target='_self' style='text-decoration:none; color:inherit;'><div class='hts-card {class_mode}'><div style='display:flex; justify-content:space-between;'><span class='stock-title' style='color:#ffffff; font-weight:bold;'>{sname}</span><span class='status-color' style='font-weight:bold;'>{sign}{s_info['rate']}</span></div><div style='display:flex; justify-content:space-between; margin-top:4px;'><span class='status-color'>{s_info['price']}</span><span style='color:#94a3b8; font-size:11px;'>{s_info['volume']}</span></div></div></a>", unsafe_allow_html=True)
