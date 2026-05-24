import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

# [이전 설정값들 그대로 유지]
# ... (STOCK_MAP, theme_data 등 기존 로직 유지) ...

st.markdown("""
<style>
    /* 기존 PC 디자인 스타일 유지 */
    .hts-card { background-color: #1b2636; border: 1px solid #283954; border-radius: 4px; padding: 10px 12px; margin-bottom: 8px; height: 62px; display: flex; flex-direction: column; justify-content: center; cursor: pointer; }
    .hts-card:hover { border: 1px solid #38bdf8; background-color: #223147; }
    
    /* 모바일 반응형만 살짝 추가 (PC에는 영향 없음) */
    @media (max-width: 768px) {
        [data-testid="column"] { width: 50% !important; flex: 1 1 50% !important; }
        .hts-card { height: auto !important; min-height: 50px; }
    }
</style>
""", unsafe_allow_html=True)

# 실시간 데이터 호출 (오류 발생 시 원본 데이터(WEEKEND_FALLBACK) 유지)
realtime_data = fetch_hts_api_prices()
if not realtime_data:
    realtime_data = WEEKEND_FALLBACK

# 렌더링 로직 (기존 구조 유지)
for t_name in sorted_theme_names:
    t_val = processed_themes[t_name]
    # ... 기존 코드 ...
    cols = st.columns(4)
    for idx, sname in enumerate(t_val["stocks"]):
        # 데이터가 없을 경우를 대비한 안전 장치 추가
        s_info = realtime_data.get(sname, WEEKEND_FALLBACK.get(sname, {"price": "-", "rate": "0.00%", "volume": "0억", "type": "4"}))
        
        # 1000031960.jpg와 동일한 디자인으로 렌더링
        cols[idx % 4].markdown(f"""
        <a href='?stock={sname}' target='_self' style='text-decoration:none; color:inherit;'>
            <div class='hts-card'>
                <div style='display:flex; justify-content:space-between;'>
                    <span style='color:#ffffff; font-weight:bold;'>{sname}</span>
                    <span style='color:{"#ef4444" if "-" not in s_info["rate"] else "#3b82f6"}; font-weight:bold;'>{s_info['rate']}</span>
                </div>
            </div>
        </a>
        """, unsafe_allow_html=True)
