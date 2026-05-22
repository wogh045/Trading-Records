import streamlit as st
import pandas as pd
import sqlite3
import datetime

# --- 데이터베이스 초기화 및 함수 ---
DB_FILE = "trading_journal.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # margin 컬럼이 추가된 새로운 스키마
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            status TEXT,
            date TEXT,
            ticker TEXT,
            position TEXT,
            leverage INTEGER,
            margin REAL,
            entry_price REAL,
            target_price REAL,
            stop_loss REAL,
            reason TEXT,
            exit_price REAL,
            pnl REAL,
            result TEXT,
            review TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_all_trades():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()
    return df

def insert_trade(trade_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', trade_data)
    conn.commit()
    conn.close()

def update_trade_exit(trade_id, exit_price, pnl, result, review):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE trades 
        SET exit_price = ?, pnl = ?, result = ?, review = ?, status = '종료'
        WHERE id = ?
    ''', (exit_price, pnl, result, review, trade_id))
    conn.commit()
    conn.close()

init_db()
df = get_all_trades()

# --- 앱 UI 구성 ---
st.set_page_config(page_title="Crypto Cloud Journal", layout="wide")
st.title("📈 가상화폐 선물 매매일지 (V2)")

# 사이드바: 총 자산 입력 (모든 탭에서 공유됨)
with st.sidebar:
    st.header("💰 나의 자산 설정")
    seed_money = st.number_input("현재 총 시드머니 (USDT)", min_value=0.0, value=1000.0, step=100.0)
    st.info("여기에 입력한 총 자산을 기준으로 진입 비중이 계산됩니다.")

tab1, tab2, tab3 = st.tabs(["🚀 진입 기록 및 계산기", "🏁 종료 및 복기", "📊 대시보드"])

# ==========================================
# 탭 1: 진입 기록 및 손익비 계산기
# ==========================================
with tab1:
    st.subheader("새로운 포지션 진입")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("종목명 (예: BTC/USDT)").upper()
        position = st.selectbox("포지션", ["Long", "Short"])
        leverage = st.number_input("레버리지 (x)", min_value=1, value=10, step=1)
        margin = st.number_input("진입 마진 금액 (USDT)", min_value=0.0, value=0.0, step=10.0)
        
        # 총 자산 대비 비중 실시간 계산
        if seed_money > 0 and margin > 0:
            margin_percent = (margin / seed_money) * 100
            st.caption(f"총 자산의 **{margin_percent:.2f}%** 진입")

    with col2:
        entry_price = st.number_input("진입가", min_value=0.0, value=0.0, format="%.4f")
        target_price = st.number_input("목표가 (Take Profit)", min_value=0.0, value=0.0, format="%.4f")
        stop_loss = st.number_input("손절가 (Stop Loss)", min_value=0.0, value=0.0, format="%.4f")
        
    with col3:
        reason = st.text_area("진입 근거", placeholder="차트 패턴, 지지/저항 등 진입 이유를 적어주세요.")
        
    # --- 실시간 예상 수익/손실액 계산 ---
    if entry_price > 0 and margin > 0:
        target_pnl = 0.0
        stop_pnl = 0.0
        
        if position == "Long":
            if target_price > 0:
                target_pnl = margin * leverage * (target_price - entry_price) / entry_price
            if stop_loss > 0:
                stop_pnl = margin * leverage * (stop_loss - entry_price) / entry_price
        else: # Short
            if target_price > 0:
                target_pnl = margin * leverage * (entry_price - target_price) / entry_price
            if stop_loss > 0:
                stop_pnl = margin * leverage * (entry_price - stop_loss) / entry_price

        st.markdown("---")
        st.write("💡 **실시간 진입 시뮬레이션**")
        
        c1, c2, c3 = st.columns(3)
        if target_price > 0:
            c1.metric("예상 목표 수익 (PnL)", f"+{target_pnl:.2f} USDT")
        if stop_loss > 0:
            c2.metric("예상 손절 금액 (PnL)", f"{stop_pnl:.2f} USDT")
        if target_pnl > 0 and stop_pnl < 0:
            rr_ratio = abs(target_pnl / stop_pnl)
            c3.metric("손익비 (RR)", f"1 : {rr_ratio:.2f}")

    # 폼 대신 일반 버튼 사용 (실시간 계산을 위해)
    if st.button("진입 기록 저장", type="primary"):
        if ticker and entry_price > 0 and margin > 0:
            trade_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
            trade_data = (
                trade_id, "진행중", date_str, ticker, position, int(leverage), float(margin),
                float(entry_price), float(target_price), float(stop_loss), reason,
                0.0, 0.0, "-", "-"
            )
            insert_trade(trade_data)
            st.success(f"{ticker} {position} 진입 기록이 안전하게 저장되었습니다.")
            st.rerun()
        else:
            st.error("종목명, 진입가, 진입 마진은 필수 입력 사항입니다.")

# ==========================================
# 탭 2: 종료 및 복기
# ==========================================
with tab2:
    st.subheader("진행 중인 포지션 청산")
    open_trades = df[df["status"] == "진행중"]
    
    if open_trades.empty:
        st.info("현재 진행 중인 포지션이 없습니다.")
    else:
        trade_options = open_trades["id"] + " : " + open_trades["ticker"] + " (" + open_trades["position"] + ")"
        selected_trade_str = st.selectbox("청산할 포지션 선택", trade_options)
        selected_id = selected_trade_str.split(" : ")[0]
        
        selected_trade = open_trades[open_trades["id"] == selected_id].iloc[0]
        
        # 진입 정보 안내
        t_entry = selected_trade['entry_price']
        t_pos = selected_trade['position']
        t_lev = selected_trade['leverage']
        t_mar = selected_trade['margin']
        
        st.markdown(f"📌 **진입가:** {t_entry} | **마진:** {t_mar} USDT | **레버리지:** {t_lev}x | **방향:** {t_pos}")
        
        col1, col2 = st.columns(2)
        with col1:
            exit_price = st.number_input("실제 청산가", min_value=0.0, format="%.4f")
            
            # --- 청산가 입력 시 실현 손익 및 승패 자동 계산 ---
            realized_pnl = 0.0
            result = "-"
            
            if exit_price > 0:
                if t_pos == "Long":
                    realized_pnl = t_mar * t_lev * (exit_price - t_entry) / t_entry
                else: # Short
                    realized_pnl = t_mar * t_lev * (t_entry - exit_price) / t_entry
                
                if realized_pnl > 0:
                    result = "Win"
                elif realized_pnl < 0:
                    result = "Loss"
                else:
                    result = "Draw"
                
                st.info(f"**자동 계산 손익:** {realized_pnl:.2f} USDT\n\n**자동 판정 결과:** {result}")
                
        with col2:
            review = st.text_area("매매 복기", placeholder="이번 매매에서 잘한 점과 아쉬운 점을 기록하세요.")
            
        if st.button("청산 완료 및 복기 저장", type="primary"):
            if exit_price > 0:
                update_trade_exit(selected_id, exit_price, realized_pnl, result, review)
                st.success("청산 정보가 성공적으로 업데이트되었습니다.")
                st.rerun()
            else:
                st.error("실제 청산가를 정확히 입력해 주세요.")

# ==========================================
# 탭 3: 대시보드 및 통계
# ==========================================
with tab3:
    st.subheader("나의 매매 성과 통계")
    closed_trades = df[df["status"] == "종료"].copy()
    
    if closed_trades.empty:
        st.info("통계를 낼 종료된 거래 내역이 없습니다.")
    else:
        total_trades = len(closed_trades)
        wins = len(closed_trades[closed_trades["result"] == "Win"])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = closed_trades["pnl"].sum()
        roi = (total_pnl / seed_money) * 100 if seed_money > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 매매 횟수", f"{total_trades}회")
        col2.metric("종합 승률", f"{win_rate:.1f}%")
        col3.metric("누적 손익", f"{total_pnl:,.2f} USDT")
        col4.metric("시드 대비 수익률", f"{roi:.2f}%") # 사이드바의 시드머니를 기준으로 수익률 추가
        
        st.divider()
        st.subheader("📉 자산 누적 수익 곡선 (Equity Curve)")
        
        closed_trades["date"] = pd.to_datetime(closed_trades["date"])
        chart_df = closed_trades.sort_values(by="date").reset_index(drop=True)
        chart_df["Cumulative_PnL"] = chart_df["pnl"].cumsum()
        
        chart_data = chart_df.set_index("date")[["Cumulative_PnL"]]
        st.line_chart(chart_data, use_container_width=True)
        
    st.divider()
    st.write("📋 전체 데이터 로그 조회")
    # 불필요한 인덱스 숨기고 데이터프레임 표시
    st.dataframe(df, use_container_width=True, hide_index=True)
