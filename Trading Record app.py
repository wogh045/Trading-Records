import streamlit as st
import pandas as pd
import sqlite3
import datetime

# --- 데이터베이스 초기화 및 함수 ---
DB_FILE = "trading_journal.db"

def init_db():
    """데이터베이스 테이블이 없으면 생성합니다."""
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
    """전체 매매 데이터를 가져옵니다."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()
    return df

def insert_trade(trade_data):
    """새로운 진입 기록을 추가합니다."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', trade_data)
    conn.commit()
    conn.close()

def update_trade_exit(trade_id, exit_price, pnl, result, review):
    """청산 기록을 업데이트합니다."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE trades 
        SET exit_price = ?, pnl = ?, result = ?, review = ?, status = '종료'
        WHERE id = ?
    ''', (exit_price, pnl, result, review, trade_id))
    conn.commit()
    conn.close()

# DB 초기화 실행
init_db()
df = get_all_trades()

# --- 앱 UI 구성 ---
st.set_page_config(page_title="Crypto Cloud Journal", layout="wide")
st.title("📈 가상화폐 선물 매매일지 (클라우드 버전)")

tab1, tab2, tab3 = st.tabs(["🚀 진입 기록 및 계산기", "🏁 종료 및 복기", "📊 대시보드"])

# ==========================================
# 탭 1: 진입 기록 및 손익비 계산기
# ==========================================
with tab1:
    st.subheader("새로운 포지션 진입")
    
    with st.form("entry_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker = st.text_input("종목명 (예: BTC/USDT)").upper()
            position = st.selectbox("포지션", ["Long", "Short"])
            leverage = st.number_input("레버리지 (x)", min_value=1, value=10, step=1)
        with col2:
            entry_price = st.number_input("진입가", min_value=0.0, value=0.0, format="%.4f")
            target_price = st.number_input("목표가 (Take Profit)", min_value=0.0, value=0.0, format="%.4f")
            stop_loss = st.number_input("손절가 (Stop Loss)", min_value=0.0, value=0.0, format="%.4f")
        with col3:
            reason = st.text_area("진입 근거", placeholder="차트 패턴, 지지/저항 등 진입 이유를 적어주세요.")
            
        # --- 실시간 손익비(RR) 계산 및 정보 제공 ---
        if entry_price > 0 and target_price > 0 and stop_loss > 0:
            if position == "Long":
                gain = target_price - entry_price
                loss = entry_price - stop_loss
            else:
                gain = entry_price - target_price
                loss = stop_loss - entry_price
                
            if loss > 0:
                rr_ratio = gain / loss
                st.info(f"💡 **실시간 리스크 계산기**\n* 예상 손익비(RR): **1 : {rr_ratio:.2f}**\n* 목표가 도달 시 수익률: {((gain/entry_price)*leverage*100):.1f}%\n* 손절가 도달 시 손실률: {((loss/entry_price)*leverage*100):.1f}%")
            else:
                st.warning("⚠️ 경고: 손절가 설정이 포지션 방향과 맞지 않습니다.")
                
        submitted = st.form_submit_button("진입 기록 저장")
        
        if submitted:
            if ticker and entry_price > 0:
                trade_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # 튜플 형태로 데이터 준비
                trade_data = (
                    trade_id, "진행중", date_str, ticker, position, int(leverage),
                    float(entry_price), float(target_price), float(stop_loss), reason,
                    0.0, 0.0, "-", "-"
                )
                insert_trade(trade_data)
                st.success(f"{ticker} {position} 진입 기록이 클라우드 DB에 안전하게 저장되었습니다.")
                st.rerun()
            else:
                st.error("종목명과 진입가는 필수 입력 사항입니다.")

# ==========================================
# 탭 2: 종료 및 복기
# ==========================================
with tab2:
    st.subheader("진행 중인 포지션 청산")
    open_trades = df[df["status"] == "진행중"]
    
    if open_trades.empty:
        st.info("현재 폰지션이 비어 있습니다. 새로운 포지션을 먼저 등록해 주세요.")
    else:
        trade_options = open_trades["id"] + " : " + open_trades["ticker"] + " (" + open_trades["position"] + ")"
        selected_trade_str = st.selectbox("청산할 포지션 선택", trade_options)
        selected_id = selected_trade_str.split(" : ")[0]
        
        selected_trade = open_trades[open_trades["id"] == selected_id].iloc[0]
        
        st.markdown(f"📌 **선택된 포지션 요약**\n* **진입가:** {selected_trade['entry_price']} | **목표가:** {selected_trade['target_price']} | **손절가:** {selected_trade['stop_loss']} | **레버리지:** {selected_trade['leverage']}x")
        
        with st.form("exit_form"):
            col1, col2 = st.columns(2)
            with col1:
                exit_price = st.number_input("실제 청산가", min_value=0.0, format="%.4f")
                pnl = st.number_input("실현 손익 (PnL / USDT)", format="%.2f")
                result = st.radio("승패 결과", ["Win", "Loss", "Draw"], horizontal=True)
            with col2:
                review = st.text_area("매매 복기", placeholder="원칙을 지켰는지, 뇌동매매는 아니었는지 복기 내용을 적어주세요.")
                
            exit_submitted = st.form_submit_button("청산 완료 및 복기 저장")
            
            if exit_submitted:
                update_trade_exit(selected_id, exit_price, pnl, result, review)
                st.success("청산 정보가 업데이트되었습니다.")
                st.rerun()

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
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 매매 횟수", f"{total_trades}회")
        col2.metric("종합 승률", f"{win_rate:.1f}%")
        col3.metric("누적 손익", f"{total_pnl:,.2f} USDT")
        
        st.divider()
        st.subheader("📉 자산 누적 수익 곡선 (Equity Curve)")
        
        # 날짜 정렬 및 누적 합산
        closed_trades["date"] = pd.to_datetime(closed_trades["date"])
        chart_df = closed_trades.sort_values(by="date").reset_index(drop=True)
        chart_df["Cumulative_PnL"] = chart_df["pnl"].cumsum()
        
        chart_data = chart_df.set_index("date")[["Cumulative_PnL"]]
        st.line_chart(chart_data, use_container_width=True)
        
    st.divider()
    st.write("📋 전체 데이터 로그 조회")
    st.dataframe(df, use_container_width=True)
