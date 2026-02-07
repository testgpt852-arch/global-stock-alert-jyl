# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime, timedelta
import logging
import yfinance as yf
import asyncio

logger = logging.getLogger(__name__)

class PerformanceTracker:
    def __init__(self):
        self.history_file = '/mnt/user-data/outputs/alert_history.jsonl'
        
        # 파일 없으면 생성
        if not os.path.exists(self.history_file):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            open(self.history_file, 'a').close()
    
    async def log_alert(self, stock_data, analysis):
        """알림 발송 시 기록"""
        try:
            record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': stock_data.get('symbol', 'UNKNOWN'),
                'price_at_alert': stock_data.get('price', 0),
                'ai_score': analysis.get('score', 0),
                'trigger_type': stock_data.get('trigger_type', ''),
                'trigger_reason': stock_data.get('trigger_reason', ''),
                'target_price': analysis.get('target_price', 0),
                'upside': analysis.get('upside', 0),
                'market': stock_data.get('market', 'US')
            }
            
            # JSONL 형식으로 추가 (한 줄씩)
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            logger.debug(f"📊 백테스팅 기록: {stock_data.get('symbol')}")
            
        except Exception as e:
            logger.error(f"성과 로그 실패: {e}")
    
    async def backtest(self, days=7):
        """과거 알림 성과 분석"""
        try:
            if not os.path.exists(self.history_file):
                return "백테스팅 데이터 없음"
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
                records = [json.loads(line) for line in f if line.strip()]
            
            if not records:
                return "백테스팅 데이터 없음"
            
            # N일 지난 알림들만
            cutoff = datetime.now() - timedelta(days=days)
            old_records = []
            
            for record in records:
                try:
                    alert_time = datetime.fromisoformat(record['timestamp'])
                    if alert_time < cutoff:
                        old_records.append(record)
                except:
                    continue
            
            if not old_records:
                return f"최근 {days}일 이내 알림만 존재 (백테스팅 대기 중)"
            
            # 실제 성과 측정
            results = []
            
            for record in old_records[:50]:  # 최근 50개만 (API 제한)
                try:
                    symbol = record['symbol']
                    
                    # 한국 종목은 스킵 (yfinance 한계)
                    if record.get('market') == 'KR':
                        continue
                    
                    price_then = record.get('price_at_alert', 0)
                    if price_then == 0:
                        continue
                    
                    # 현재 가격 조회
                    actual_gain = await asyncio.to_thread(
                        self._get_current_price,
                        symbol,
                        price_then
                    )
                    
                    if actual_gain is not None:
                        results.append({
                            'symbol': symbol,
                            'ai_score': record.get('ai_score', 0),
                            'predicted_upside': record.get('upside', 0),
                            'actual_gain': actual_gain,
                            'success': actual_gain > 20  # 20% 이상 = 성공
                        })
                        
                except Exception:
                    continue
            
            if not results:
                return "측정 가능한 데이터 없음"
            
            # 통계 계산
            total = len(results)
            success_count = sum(1 for r in results if r['success'])
            success_rate = (success_count / total) * 100 if total > 0 else 0
            
            avg_gain = sum(r['actual_gain'] for r in results) / total if total > 0 else 0
            
            # AI 점수별 정확도
            high_score = [r for r in results if r['ai_score'] >= 8]
            high_score_success = sum(1 for r in high_score if r['success'])
            high_score_rate = (high_score_success / len(high_score)) * 100 if high_score else 0
            
            report = f"""
📊 백테스팅 결과 ({days}일 전 알림)

총 알림: {total}개
성공 (20%+ 상승): {success_count}개
성공률: {success_rate:.1f}%
평균 수익률: {avg_gain:+.1f}%

고점수(8+) 알림: {len(high_score)}개
고점수 성공률: {high_score_rate:.1f}%
"""
            
            return report
            
        except Exception as e:
            logger.error(f"백테스팅 오류: {e}")
            return f"백테스팅 오류: {e}"
    
    def _get_current_price(self, symbol, price_then):
        """현재 가격 조회 및 수익률 계산"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d')
            
            if hist.empty:
                return None
            
            price_now = hist['Close'].iloc[-1]
            gain_pct = ((price_now - price_then) / price_then) * 100
            
            return gain_pct
            
        except Exception:
            return None
