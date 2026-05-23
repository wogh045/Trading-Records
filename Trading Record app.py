import streamlit as st
import pandas as pd
import sqlite3
import datetime

# --- 데이터베이스 초기화 및 CRUD 함수 ---
DB_FILE = "trading_journal_v2.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
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

def update_trade_full(trade_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE trades 
        SET ticker=?, position=?, leverage=?, margin=?, entry_price=?, target_price=?, stop_loss=?, reason=?, exit_price=?, pnl=?, result=?, review=?, status=?
        WHERE id=?
    ''', trade_data)
    conn.commit()
    conn.close()

def delete_trade(trade_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM trades WHERE id=?', (trade_id,))
    conn.commit()
    conn.close()

init_db()
df = get_all_trades()

# --- 앱 UI 구성 ---
st.set_page_config(page_title="Crypto Cloud Journal", layout="wide")
st.title("📈 가상화폐 선물 매매일지 (V4)")

# 사이드바: 총 자산 입력
with st.sidebar:
    st.header("💰 나의 자산 설정")
    seed_money = st.number_input("현재 총 시드머니 (USDT)", min_value=0.0, value=1000.0, step=100.0)
    st.info("이 시드머니를 기준으로 리스크 퍼센트가 표시됩니다.")

tab1, tab2, tab3 = st.tabs(["🚀 진입 기록 및 계산기", "🏁 종료 및 복기", "📊 대시보드"])

# ==========================================
# 탭 1: 진입 기록 및 직관적 리스크 계산기
# ==========================================
with tab1:
    st.subheader("새로운 포지션 진입")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("종목명 (예: BTC/USDT)").upper()
        position = st.selectbox("포지션", ["Long", "Short"])
        leverage = st.number_input("레버리지 (x)", min_value=1, value=10, step=1)
        margin = st.number_input("진입 마진 금액 (USDT)", min_value=0.0, value=100.0, step=10.0)
        
    with col2:
        entry_price = st.number_input("진입가", min_value=0.0, value=0.0, format="%.4f")
        target_price = st.number_input("목표가 (Take Profit)", min_value=0.0, value=0.0, format="%.4f")
        stop_loss = st.number_input("손절가 (Stop Loss)", min_value=0.0, value=0.0, format="%.4f")
        
    with col3:
        reason = st.text_area("진입 근거", placeholder="차트 패턴, 지지/저항 등 진입 이유를 적어주세요.", height=130)
    
    # --- 실시간 예상 수익/손실액 및 손익비 계산 ---
    if entry_price > 0 and margin > 0:
        target_pnl = 0.0
        stop_pnl = 0.0
        
        # 포지션 방향에 맞게 올바른 가격이 입력되었을 때만 계산
        if position == "Long":
            if target_price > entry_price:
                target_pnl = margin * leverage * (target_price - entry_price) / entry_price
            if 0 < stop_loss < entry_price:
                stop_pnl = margin * leverage * (entry_price - stop_loss) / entry_price
        else: # Short
            if 0 < target_price < entry_price:
                target_pnl = margin * leverage * (entry_price - target_price) / entry_price
            if stop_loss > entry_price:
                stop_pnl = margin * leverage * (stop_loss - entry_price) / entry_price

        st.divider()
        st.subheader("⚖️ 진입 시뮬레이션")
        
        c1, c2, c3, c4 = st.columns(4)
        
        # 1. 얻는 금액
        if target_pnl > 0:
            c1.metric("📈 얻는 금액 (목표가 도달)", f"+{target_pnl:.2f} USDT")
        else:
            c1.metric("📈 얻는 금액 (목표가 도달)", "0.00 USDT")
            
        # 2. 잃는 금액
        if stop_pnl > 0:
            c2.metric("📉 잃는 금액 (손절가 도달)", f"-{stop_pnl:.2f} USDT")
            c4.metric("💰 총 자산 대비 리스크", f"{(stop_pnl/seed_money)*100:.1f} %")
        else:
            c2.metric("📉 잃는 금액 (손절가 도달)", "0.00 USDT")
            c4.metric("💰 총 자산 대비 리스크", "0.0 %")
            
        # 3. 손익비 (RR)
        if target_pnl > 0 and stop_pnl > 0:
            rr_ratio = target_pnl / stop_pnl
            c3.metric("⚖️ 손익비 (RR)", f"1 : {rr_ratio:.2f}")
        else:
            c3.metric("⚖️ 손익비 (RR)", "입력 대기중")

    st.markdown("<br>", unsafe_allow_html=True)
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
            st.success(f"진입 기록 저장 완료! (종목: {ticker})")
            st.rerun()
        else:
            st.error("종목명, 진입가, 마진 금액은 필수입니다.")

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
        
        t_entry = selected_trade['entry_price']
        t_pos = selected_trade['position']
        t_lev = selected_trade['leverage']
        t_mar = selected_trade['margin']
        
        st.markdown(f"📌 **진입가:** {t_entry} | **마진:** {t_mar} USDT | **레버리지:** {t_lev}x | **방향:** {t_pos}")
        
        col1, col2 = st.columns(2)
        with col1:
            exit_price = st.number_input("실제 청산가", min_value=0.0, format="%.4f")
            realized_pnl = 0.0
            result = "-"
            
            if exit_price > 0:
                if t_pos == "Long":
                    realized_pnl = t_mar * t_lev * (exit_price - t_entry) / t_entry
                else: # Short
                    realized_pnl = t_mar * t_lev * (t_entry - exit_price) / t_entry
                
                if realized_pnl > 0: result = "Win"
                elif realized_pnl < 0: result = "Loss"
                else: result = "Draw"
                
                st.info(f"**자동 계산 손익:** {realized_pnl:.2f} USDT\n\n**자동 판정 결과:** {result}")
                
        with col2:
            review = st.text_area("매매 복기", placeholder="이번 매매에서 잘한 점과 아쉬운 점을 기록하세요.")
            
        if st.button("청산 완료 및 복기 저장", type="primary"):
            if exit_price > 0:
                update_trade_exit(selected_id, exit_price, realized_pnl, result, review)
                st.success("청산 정보가 성공적으로 업데이트되었습니다.")
                st.rerun()
            else:
                st.error("청산가를 정확히 입력해 주세요.")

# ==========================================
# 탭 3: 대시보드 및 통계 (수정/삭제 기능 포함)
# ==========================================
with tab3:
    st.subheader("나의 매매 성과 통계")
    closed_trades = df[df["status"] == "종료"].copy()
    
    if not closed_trades.empty:
        total_trades = len(closed_trades)
        wins = len(closed_trades[closed_trades["result"] == "Win"])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = closed_trades["pnl"].sum()
        roi = (total_pnl / seed_money) * 100 if seed_money > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 매매 횟수", f"{total_trades}회")
        col2.metric("종합 승률", f"{win_rate:.1f}%")
        col3.metric("누적 손익", f"{total_pnl:,.2f} USDT")
        col4.metric("시드 대비 수익률", f"{roi:.2f}%")
        
        st.divider()
        st.subheader("📉 자산 누적 수익 곡선 (Equity Curve)")
        closed_trades["date"] = pd.to_datetime(closed_trades["date"])
        chart_df = closed_trades.sort_values(by="date").reset_index(drop=True)
        chart_df["Cumulative_PnL"] = chart_df["pnl"].cumsum()
        st.line_chart(chart_df.set_index("date")[["Cumulative_PnL"]], use_container_width=True)
        
    st.divider()
    st.write("📋 전체 데이터 로그 조회")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("🛠️ 데이터 관리 (수정 및 영구 삭제)")
    if not df.empty:
        manage_options = df["id"] + " : " + df["ticker"] + " [" + df["status"] + "]"
        manage_select = st.selectbox("수정하거나 삭제할 거래를 선택하세요", manage_options)
        m_id = manage_select.split(" : ")[0]
        m_trade = df[df["id"] == m_id].iloc[0]
        
        with st.expander(f"선택된 거래 정보 열기 ({m_id})", expanded=False):
            with st.form("manage_form"):
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    m_ticker = st.text_input("종목명", value=m_trade["ticker"])
                    m_status = st.selectbox("상태", ["진행중", "종료"], index=0 if m_trade["status"]=="진행중" else 1)
                    m_position = st.selectbox("포지션", ["Long", "Short"], index=0 if m_trade["position"]=="Long" else 1)
                    m_result = st.selectbox("승패", ["-", "Win", "Loss", "Draw"], index=["-", "Win", "Loss", "Draw"].index(m_trade["result"]))
                with mc2:
                    m_entry = st.number_input("진입가", value=float(m_trade["entry_price"]), format="%.4f")
                    m_target = st.number_input("목표가", value=float(m_trade["target_price"]), format="%.4f")
                    m_stop = st.number_input("손절가", value=float(m_trade["stop_loss"]), format="%.4f")
                    m_exit = st.number_input("청산가", value=float(m_trade["exit_price"]), format="%.4f")
                with mc3:
                    m_lev = st.number_input("레버리지", value=int(m_trade["leverage"]))
                    m_mar = st.number_input("마진", value=float(m_trade["margin"]))
                    m_pnl = st.number_input("실현 손익", value=float(m_trade["pnl"]), format="%.2f")
                
                m_reason = st.text_area("진입 근거", value=m_trade["reason"])
                m_review = st.text_area("매매 복기", value=m_trade["review"])
                
                update_btn = st.form_submit_button("수정 내용 덮어쓰기")
                
                if update_btn:
                    new_data = (
                        m_ticker, m_position, int(m_lev), float(m_mar), float(m_entry), 
                        float(m_target), float(m_stop), m_reason, float(m_exit), 
                        float(m_pnl), m_result, m_review, m_status, m_id
                    )
                    update_trade_full(new_data)
                    st.success("데이터가 성공적으로 수정되었습니다.")
                    st.rerun()

            if st.button("🚨 이 거래 데이터 영구 삭제", type="primary"):
                delete_trade(m_id)
                st.warning("데이터가 삭제되었습니다.")
                st.rerun()
