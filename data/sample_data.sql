-- ═══════════════════════════════════════════
-- StockCall Tracker — Sample Data
-- Run: sqlite3 stockcall.db < sample_data.sql
-- ═══════════════════════════════════════════

-- Sample stock calls
INSERT INTO stock_calls (broker_id, broker_name, call_date, call_time, stock, exchange, action, cmp, entry_price, target1, target2, stoploss, support, resistance, duration, call_type, status, original_msg, confidence)
VALUES
(1,'TradeBulls Securities','2025-04-01','09:32','TATASTEEL','NSE','BUY',202,202,236,NULL,185,211,240,'2-3 Days','Swing','Target Hit','TATA STEEL\nCMP 202\nTARGET 236\nSUPPORT 211\nDURATION 2-3 DAYS','High'),
(2,'HDFC Securities','2025-04-02','10:15','INFY','NSE','BUY',1780,1780,1820,NULL,1710,1750,1850,'1 Week','Swing','Target Hit','ACCUMULATE INFY\nTARGET 1820\nSL 1710\nTIME 1 WEEK','High'),
(3,'Angel One Signals','2025-04-02','11:05','RELIANCE','NSE','BUY',1445,1450,1510,1540,1420,1430,1560,'Intraday','Intraday','Partial Hit','BUY RELIANCE ABOVE 1450\nTARGET 1510 / 1540\nSTOPLOSS 1420\nINTRADAY','Medium'),
(4,'Zerodha Varsity','2025-04-03','09:50','HDFCBANK','NSE','BUY',1625,1625,1680,NULL,1590,1610,1700,'3-5 Days','Swing','Target Hit','BUY HDFCBANK CMP 1625\nTGT 1680\nSL 1590','High'),
(5,'Motilal Oswal','2025-04-05','10:30','TCS','NSE','SELL',3950,3950,3880,NULL,4010,3870,4020,'2 Days','Swing','SL Hit','SELL TCS @3950\nTARGET 3880\nSL 4010','Medium'),
(1,'TradeBulls Securities','2025-04-06','09:15','SBIN','NSE','BUY',798,800,840,860,775,790,850,'1 Week','Swing','Target Hit','BUY SBI\nCMP 798\nTGT1 840 TGT2 860\nSL 775','High'),
(2,'HDFC Securities','2025-04-07','11:20','WIPRO','NSE','BUY',468,470,495,NULL,455,460,500,'5-7 Days','Swing','Expired','WIPRO BUY ABOVE 470\nTARGET 495\nSL 455\n5-7 DAYS','Medium'),
(4,'Zerodha Varsity','2025-04-08','10:00','ICICIBANK','NSE','BUY',1102,1105,1145,NULL,1075,1090,1160,'Intraday','Intraday','Target Hit','ICICI BANK BUY 1105\nTGT 1145\nSL 1075\nINTRADAY','High'),
(3,'Angel One Signals','2025-04-09','09:45','BAJFINANCE','NSE','BUY',7200,7220,7450,NULL,7050,7100,7500,'3 Days','Swing','SL Hit','BUY BAJFINANCE\nCMP 7200 ENTRY 7220\nTARGET 7450\nSL 7050','Medium'),
(5,'Motilal Oswal','2025-04-10','10:45','MARUTI','NSE','BUY',12400,12400,12800,NULL,12100,12200,13000,'1-2 Weeks','Positional','Pending','MARUTI ACCUMULATE\nTGT 12800\nSL 12100\n1-2 WEEKS','High'),
(1,'TradeBulls Securities','2025-04-12','09:30','SUNPHARMA','NSE','BUY',1560,1560,1620,1660,1510,1540,1680,'1 Week','Swing','Target Hit','SUNPHARMA BUY\nCMP 1560\nTGT1 1620 TGT2 1660\nSL 1510\n1 WEEK','High'),
(2,'HDFC Securities','2025-04-14','10:00','NTPC','NSE','BUY',362,365,390,NULL,348,355,400,'2 Weeks','Positional','Target Hit','ACCUMULATE NTPC\nCMP 362 ENTRY 365\nTGT 390\nSL 348','Medium'),
(4,'Zerodha Varsity','2025-04-15','09:45','AXISBANK','NSE','BUY',1148,1150,1195,1220,1112,1130,1240,'3-5 Days','Swing','Partial Hit','AXIS BANK BUY\n1150 TARGET 1195/1220\nSL 1112','High'),
(3,'Angel One Signals','2025-04-16','11:00','DRREDDY','NSE','BUY',6200,6210,6420,NULL,6050,6100,6500,'1 Week','Swing','SL Hit','BUY DR REDDY\nCMP 6200\nTGT 6420\nSL 6050','Low'),
(5,'Motilal Oswal','2025-04-17','09:20','ITC','NSE','BUY',448,450,475,490,432,440,500,'2 Weeks','Swing','Target Hit','ITC BUY ON DIPS\nCMP 448 ENTRY 450\nTGT1 475 TGT2 490\nSL 432','High');

-- Sample outcomes
INSERT INTO call_outcomes (call_id, exit_price, exit_date, pnl_pct, holding_days)
VALUES
(1, 236,   '2025-04-04', 16.8,  3),
(2, 1820,  '2025-04-09', 2.2,   5),
(3, 1510,  '2025-04-02', 4.1,   0),
(4, 1680,  '2025-04-07', 3.4,   4),
(5, 4010,  '2025-04-06', -1.5,  1),
(6, 840,   '2025-04-12', 5.0,   6),
(7, 468,   '2025-04-14', -0.4,  7),
(8, 1145,  '2025-04-08', 3.6,   0),
(9, 7050,  '2025-04-11', -2.4,  2),
(11,1620,  '2025-04-18', 3.8,   6),
(12,390,   '2025-04-25', 6.8,   11),
(13,1195,  '2025-04-19', 3.9,   4),
(14,6050,  '2025-04-20', -2.6,  4),
(15,475,   '2025-04-28', 5.6,   11);
