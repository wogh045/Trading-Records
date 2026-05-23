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

init_db()
df = get_all_trades()

# --- 앱 UI 구성 ---
st.set_page_config(page_title="Crypto Position Planner", layout="wide")
st.title("📈 가상화폐 타점 계산기 & 매매일지 (V5)")

tab1, tab2, tab3 = st.tabs(["🚀 타점 계산기 및 진입", "🏁 종료 및 복기", "📊 대시보드"])

# ==========================================
# 탭 1: 타점 계산기 및 시뮬레이터 (완전 개편)
# ==========================================
with tab1:
    st.subheader("1. 기본 설정 (고정값)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        margin = st.number_input("이번 진입 마진 (고정값)", min_value=1.0, value=1000.0, step=100.0)
        target_risk = st.number_input("허용 손실금 (손절 시 잃을 금액)", min_value=1.0, value=200.0, step=50.0)
        position = st.radio("포지션", ["Long", "Short"], horizontal=True)
    with col2:
        # 예시로 말씀하신 BTC 가격을 기본값으로 세팅했습니다.
        entry_price = st.number_input("진입가", min_value=0.0, value=80000.0, format="%.2f")
        target_price = st.number_input("목표가", min_value=0.0, value=82000.0, format="%.2f")
        stop_loss = st.number_input("손절가", min_value=0.0, value=79000.0, format="%.2f")
    with col3:
        ticker = st.text_input("종목명", value="BTC/USDT").upper()
        reason = st.text_area("진입 근거", height=100)

    st.divider()
    
    # 방향성에 따른 수익/손실폭 계산
    if entry_price > 0:
        if position == "Long":
            profit_dist = target_price - entry_price
            loss_dist = entry_price - stop_loss
        else: # Short
            profit_dist = entry_price - target_price
            loss_dist = stop_loss - entry_price

        # 정상적인 타점(목표가/손절가 방향이 맞을 때)인 경우에만 계산
        if profit_dist > 0 and loss_dist > 0:
            rr = profit_dist / loss_dist
            loss_pct = loss_dist / entry_price
            
            # 필요 레버리지 공식 = 허용손실금 / (마진 * 손실률)
            req_lev = target_risk / (margin * loss_pct)
            expected_profit = target_risk * rr

            st.subheader("2. 현재 타점 분석 결과")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("⚖️ 현재 손익비", f"1 : {rr:.2f}")
            c2.metric("📉 잃는 금액 (손절 시)", f"-{target_risk:.0f} USDT")
            c3.metric("📈 얻는 금액 (익절 시)", f"+{expected_profit:.0f} USDT")
            c4.metric("💡 필요한 레버리지", f"{req_lev:.1f} x")

            # --- 시뮬레이터 (조절 버튼) 파트 ---
            st.divider()
            st.subheader("🎛️ 타점 시뮬레이터 (연동 조절)")
            st.write("슬라이더를 움직여 손익비나 레버리지를 변경하면, **목표가를 고정한 상태에서 손절가를 어떻게 바꿔야 하는지** 계산해 줍니다.")
            
            sim_c1, sim_c2 = st.columns(2)
            with sim_c1:
                st.markdown("**🔹 손익비(RR)를 올리고 싶다면?**")
                sim_rr = st.slider("목표 손익비 조절", min_value=1.0, max_value=10.0, value=float(round(rr, 1)), step=0.5)
                
                # RR 변경 시 새로운 손절폭과 레버리지 계산
                new_loss_dist = profit_dist / sim_rr
                new_stop = entry_price - new_loss_dist if position == "Long" else entry_price + new_loss_dist
                new_loss_pct = new_loss_dist / entry_price
                new_req_lev = target_risk / (margin * new_loss_pct)
                
                st.info(f"손익비를 **1 : {sim_rr}** 로 가져가려면:\n\n"
                        f"👉 손절가를 **{new_stop:.2f}** 로 타이트하게 올리세요.\n"
                        f"👉 그러면 잃는 금액(-{target_risk} 달러)을 유지하기 위해 레버리지를 **{new_req_lev:.1f}x** 로 올려야 합니다.")

            with sim_c2:
                st.markdown("**🔹 레버리지를 올리고 싶다면?**")
                sim_lev = st.slider("레버리지 직접 조절", min_value=1, max_value=100, value=int(req_lev) if req_lev>1 else 1, step=1)
                
                # 레버리지 변경 시 새로운 손절폭과 RR 계산
                sim_loss_pct = target_risk / (margin * sim_lev)
                sim_loss_dist = sim_loss_pct * entry_price
                sim_stop = entry_price - sim_loss_dist if position == "Long" else entry_price + sim_loss_dist
                sim_rr_val = profit_dist / sim_loss_dist if sim_loss_dist > 0 else 0
                
                st.success(f"레버리지를 **{sim_lev}x** 로 설정하려면:\n\n"
                         f"👉 손절가를 **{sim_stop:.2f}** 로 변경해야 합니다.\n"
                         f"👉 이때 손익비는 **1 : {sim_rr_val:.2f}** 로 변동됩니다.")

            # --- 최종 저장 파트 ---
            st.divider()
            st.subheader("3. 최종 진입 기록")
            st.write("위 시뮬레이션을 참고하여 최종적으로 진입할 레버리지를 기입하고 저장하세요.")
            
            final_lev = st.number_input("최종 확정 레버리지", min_value=1, value=max(1, int(req_lev)), step=1)
            
            if st.button("이 타점으로 진입 기록 저장", type="primary"):
                trade_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                
                trade_data = (
                    trade_id, "진행중", date_str, ticker, position, final_lev, float(margin),
                    float(entry_price), float(target_price), float(stop_loss), reason,
                    0.0, 0.0, "-", "-"
                )
                insert_trade(trade_data)
                st.success(f"저장 완료! (레버리지 {final_lev}x, 마진 {margin} USDT)")
                st.rerun()

        else:
            st.warning("⚠️ 진입가, 목표가, 손절가의 방향이 잘못되었습니다. (예: 롱 포지션인데 목표가가 진입가보다 낮음)")

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
            exit_price = st.number_input("실제 청산가", min_value=0.0, format="%.2f")
            realized_pnl = 0.0
            result = "-"
            
            if exit_price > 0:
                if t_pos == "Long":
                    realized_pnl = t_mar * t_lev * (exit_price - t_entry) / t_entry
                else: 
                    realized_pnl = t_mar * t_lev * (t_entry - exit_price) / t_entry
                
                if realized_pnl > 0: result = "Win"
                elif realized_pnl < 0: result = "Loss"
                else: result = "Draw"
                
                st.info(f"**자동 계산 손익:** {realized_pnl:.2f} USDT\n\n**판정 결과:** {result}")
                
        with col2:
            review = st.text_area("매매 복기", placeholder="계획대로 매매했는지 복기하세요.")
            
        if st.button("청산 완료 및 저장", type="primary"):
            if exit_price > 0:
                update_trade_exit(selected_id, exit_price, realized_pnl, result, review)
                st.success("청산 완료!")
                st.rerun()

# ==========================================
# 탭 3: 대시보드
# ==========================================
with tab3:
    st.subheader("매매 성과 대시보드")
    closed_trades = df[df["status"] == "종료"].copy()
    
    if not closed_trades.empty:
        total_trades = len(closed_trades)
        wins = len(closed_trades[closed_trades["result"] == "Win"])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = closed_trades["pnl"].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 매매 횟수", f"{total_trades}회")
        col2.metric("종합 승률", f"{win_rate:.1f}%")
        col3.metric("누적 손익", f"{total_pnl:,.2f} USDT")
        
        st.divider()
        st.subheader("📉 자산 누적 수익 곡선")
        closed_trades["date"] = pd.to_datetime(closed_trades["date"])
        chart_df = closed_trades.sort_values(by="date").reset_index(drop=True)
        chart_df["Cumulative_PnL"] = chart_df["pnl"].cumsum()
        st.line_chart(chart_df.set_index("date")[["Cumulative_PnL"]], use_container_width=True)
        
    st.divider()
    st.dataframe(df, use_container_width=True, hide_index=True)
