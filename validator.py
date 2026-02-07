# -*- coding: utf-8 -*-
import yfinance as yf
import asyncio
import logging
from statistics import mean, stdev

logger = logging.getLogger(__name__)

class Validator:
    """1차 포착 종목을 옵션/다크풀로 2차 검증"""
    
    def __init__(self):
        pass
    
    async def validate(self, symbol):
        """옵션 + 다크풀 통합 검증"""
        try:
            # 비동기 래핑 (yfinance는 동기식)
            result = await asyncio.to_thread(self._sync_validate, symbol)
            return result
        except Exception as e:
            logger.error(f"검증 오류 ({symbol}): {e}")
            return {'valid': False}
    
    def _sync_validate(self, symbol):
        """동기식 검증 로직"""
        findings = {
            'valid': False,
            'options_signal': False,
            'dark_pool_signal': False,
            'block_trade_signal': False,
            'details': []
        }
        
        try:
            ticker = yf.Ticker(symbol)
            
            # === 1. 옵션 이상 징후 ===
            options_check = self._check_options(ticker)
            if options_check:
                findings['options_signal'] = True
                findings['details'].append(options_check)
            
            # === 2. 다크풀 + Block Trade ===
            dark_pool_check = self._check_dark_pool(ticker)
            if dark_pool_check:
                findings['dark_pool_signal'] = True
                findings['details'].append(dark_pool_check)
            
            # 하나라도 양성이면 valid
            if findings['options_signal'] or findings['dark_pool_signal']:
                findings['valid'] = True
            
        except Exception as e:
            logger.debug(f"{symbol} 검증 실패: {e}")
        
        return findings
    
    def _check_options(self, ticker):
        """옵션 거래량 폭발 체크"""
        try:
            # 가장 가까운 만기일 선택
            dates = ticker.options
            if not dates:
                return None
            
            nearest_date = dates[0]  # 가장 가까운 만기
            
            # 옵션 체인 가져오기
            opt_chain = ticker.option_chain(nearest_date)
            calls = opt_chain.calls
            
            if calls.empty:
                return None
            
            # Call 옵션 거래량 분석
            avg_volume = calls['volume'].mean()
            max_volume = calls['volume'].max()
            
            # 최대 거래량이 평균의 5배 이상 = 이상 징후
            if max_volume > avg_volume * 5 and max_volume > 1000:
                return f"💰 옵션 폭발 (Call 거래량 {int(max_volume):,})"
            
        except Exception:
            pass
        
        return None
    
    def _check_dark_pool(self, ticker):
        """다크풀/Block Trade 추정"""
        try:
            # 최근 10일 데이터
            hist = ticker.history(period='10d', interval='1d')
            
            if hist.empty or len(hist) < 5:
                return None
            
            # 최근 5일 평균 거래량
            volumes = hist['Volume'].values
            avg_volume = mean(volumes[:-1])  # 오늘 제외
            
            # 표준편차 계산
            try:
                std_volume = stdev(volumes[:-1])
            except:
                std_volume = avg_volume * 0.2  # 기본값
            
            # 오늘 거래량
            today_volume = volumes[-1]
            
            # 가격 변동성
            prices = hist['Close'].values
            price_change_pct = abs((prices[-1] - prices[-2]) / prices[-2]) * 100
            
            # === Gemini 제안: 3-Sigma 통계적 접근 ===
            # 거래량이 평균 + 3*표준편차 이상 = 99.7% 확률의 이상치
            threshold_3sigma = avg_volume + (3 * std_volume)
            
            # 조건: 거래량 폭발 + 가격 변화 미미
            if today_volume > threshold_3sigma and price_change_pct < 2.0:
                return f"🛡️ 다크풀 의심 (거래량 {today_volume/1000000:.1f}M, 가격 변화 {price_change_pct:.1f}%)"
            
            # Block Trade 체크 (거래량 3배 이상)
            if today_volume > avg_volume * 3 and price_change_pct < 3.0:
                return f"🐋 Block Trade 감지 (거래량 {int(today_volume/avg_volume)}배)"
            
        except Exception:
            pass
        
        return None
