import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import xml.etree.ElementTree as ET 

# 1. 페이지 레이아웃 및 다크테마 최적화 세팅
st.set_page_config(page_title="NXT 주도주 통합 전광판", layout="wide") 

# [수정사항] 모바일 반응형 가독성 및 강제 번역 차단
st.markdown("""
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="google" content="notranslate">
</head>
<style>
    @media (max-width: 768px) {
        .hts-card { height: auto !important; min-height: 62px; }
        [data-testid="column"] { margin-bottom: 10px; }
    }
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

# (이하 원본 코드와 동일한 STOCK_MAP, WEEKEND_FALLBACK, 함수, 로직 부분 전부 포함)
# [참고: 위 CSS/메타태그를 제외한 나머지는 처음 주신 코드 그대로 사용하시면 됩니다.]
