# -*- coding: utf-8 -*-
import asyncio
import logging
from datetime import datetime
import pytz
from config import Config
from news_scanner import NewsScanner
from price_scanner import PriceScanner
from social_scanner import SocialScanner
from kr_stock_scanner import KRStockScanner
from ai_analyzer import AIAnalyzer
from telegram_bot import TelegramBot

# === 🆕 고급 기능 ===
from insider_scanner import InsiderScanner
from short_squeeze_scanner import ShortSqueezeScanner
from whale_scanner import WhaleScanner
from validator import Validator
from performance_tracker import PerformanceTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GlobalStockAlertSystem:
    def __init__(self):
        try:
            self.config = Config()
            self.telegram = TelegramBot(self.config.TELEGRAM_TOKEN, self.config.TELEGRAM_CHAT_ID)
            self.ai = AIAnalyzer(self.config.GEMINI_API_KEY)
            
            # 기본 스캐너
            self.us_news = NewsScanner(self.config.FINNHUB_API_KEY)
            self.us_price = PriceScanner(self.config.ALPHA_VANTAGE_KEY)
            self.us_social = SocialScanner()
            self.kr_scanner = KRStockScanner(self.telegram, self.ai)
            
            # 🆕 고급 스캐너
            self.insider = InsiderScanner()
            self.short_squeeze = ShortSqueezeScanner()
            self.whale = WhaleScanner()
            
            # 🆕 검증기 & 백테스팅
            self.validator = Validator()
            self.tracker = PerformanceTracker()
            
            self.alerted_stocks = {}
            self.alert_cooldown = 14400  # 4시간
            
            logger.info("✅ 10억 만들기 시스템 초기화 완료")
            logger.info("   ✓ 내부자 거래 (Form 4)")
            logger.info("   ✓ 숏스퀴즈 감지 (Finviz)")
            logger.info("   ✓ 고래 추적 (13D/G)")
            logger.info("   ✓ 옵션/다크풀 검증 (yfinance)")
            logger.info("   ✓ 자동 백테스팅")
            
        except Exception as e:
            logger.critical(f"❌ 초기화 실패: {e}")
            raise
    
    async def send_error_alert(self, error):
        """오류 텔레그램 알림"""
        try:
            logger.error(f"오류 발생: {error}")
        except Exception as e:
            logger.critical(f"오류 알림 실패: {e}")
    
    def is_us_market_hours(self):
        try:
            ny_tz = pytz.timezone('America/New_York')
            now = datetime.now(ny_tz)
            if now.weekday() >= 5: return False
            market_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
            market_end = now.replace(hour=20, minute=0, second=0, microsecond=0)
            return market_start <= now <= market_end
        except Exception as e:
            logger.error(f"미국 시간 체크 오류: {e}")
            return True
    
    def is_kr_market_hours(self):
        try:
            kr_tz = pytz.timezone('Asia/Seoul')
            now = datetime.now(kr_tz)
            if now.weekday() >= 5: return False
            from datetime import time
            market_start = time(9, 0)
            market_end = time(15, 30)
            current_time = now.time()
            return market_start <= current_time <= market_end
        except Exception as e:
            logger.error(f"한국 시간 체크 오류: {e}")
            return True
    
    def should_alert(self, symbol, market):
        """중복 알림 방지"""
        now = datetime.now()
        alert_key = f"{market}_{symbol}"
        if alert_key in self.alerted_stocks:
            last_alert = self.alerted_stocks[alert_key]
            if (now - last_alert).total_seconds() < self.alert_cooldown:
                return False
        self.alerted_stocks[alert_key] = now
        return True
    
    async def process_alert(self, stock_data):
        """알림 처리 (AI 분석 + 옵션/다크풀 검증)"""
        try:
            symbol = stock_data.get('symbol', 'UNKNOWN')
            market = stock_data.get('market', 'US')
            trigger_type = stock_data.get('trigger_type', '')
            
            # 중복 체크
            if not self.should_alert(symbol, market):
                logger.info(f"⏭️ {symbol} 쿨다운 중")
                return
            
            # === 🆕 2차 검증 (미국 주식만) ===
            if market == 'US' and symbol != 'US' and symbol != 'UNKNOWN':
                logger.info(f"🔍 {symbol} 2차 검증 중...")
                
                validation = await self.validator.validate(symbol)
                
                if validation['valid']:
                    # 검증 통과 시 트리거 메시지 보강
                    details = ' | '.join(validation['details'])
                    stock_data['trigger_reason'] = f"{stock_data.get('trigger_reason', '')}\n{details}"
                    logger.info(f"✅ {symbol} 검증 통과: {details}")
            
            # API 보호 대기
            await asyncio.sleep(5)
            logger.info(f"🔍 {symbol} AI 분석 진입...")
            
            # AI 분석
            analysis = await self.ai.analyze_opportunity(stock_data)
            
            # 점수 필터링 (고급 신호는 낮은 점수도 허용)
            high_quality_triggers = [
                'whale_alert', 'insider_trading', 'short_squeeze',
                'news', 'news_sentiment'
            ]
            
            min_score = 4 if trigger_type in high_quality_triggers or symbol == 'KR_NEWS' else self.config.MIN_AI_SCORE
            
            # priority 가산점 적용
            ai_score = analysis['score']
            priority = stock_data.get('priority', 0)
            
            if priority > 0:
                logger.info(f"📈 {symbol} 우선순위 가산 (+{priority}점)")
                ai_score = min(10, ai_score + (priority * 0.3))  # 최대 10점
            
            if ai_score < min_score:
                logger.info(f"🗑️ {symbol} 점수 미달 ({ai_score:.1f} < {min_score})")
                return
            
            # 백테스팅 기록
            await self.tracker.log_alert(stock_data, analysis)
            
            # 메시지 포맷팅
            message = self.format_alert_message(stock_data, analysis)
            
            # 전송
            await self.telegram.send_message(message)
            
            logger.info(f"✅ {symbol} 알림 전송 완료 (점수: {ai_score:.1f}/10)")
            
        except Exception as e:
            logger.error(f"알림 처리 오류 ({stock_data.get('symbol', 'UNKNOWN')}): {e}")
    
    def format_alert_message(self, stock, analysis):
        """알림 메시지 포맷"""
        market = stock.get('market', 'US')
        market_emoji = "🇰🇷" if market == 'KR' else "🇺🇸"
        
        if analysis['score'] >= 9: urgency = "🚨 **텐배거 가능성** 🚨"
        elif analysis['score'] >= 8: urgency = "⚠️ **HIGH PRIORITY** ⚠️"
        else: urgency = "📢 **OPPORTUNITY** 📢"
        
        msg = f"{urgency}\n\n"
        msg += f"{market_emoji} **AI 점수: {analysis['score']}/10**\n\n"
        
        if market == 'KR':
            name = stock.get('name', stock.get('symbol'))
            msg += f"**{name}**\n"
            if stock.get('price'): msg += f"현재가: {stock.get('price', 0):,}원\n"
        else:
            msg += f"**${stock['symbol']}**\n"
            if stock.get('price'): msg += f"현재가: ${stock.get('price', 0):.2f}\n"
        
        if stock.get('change_percent'):
            msg += f"변화: **{stock.get('change_percent', 0):+.2f}%**\n"
        
        if stock.get('volume', 0) > 0:
            msg += f"거래량: {stock['volume']:,}\n"
        
        msg += f"\n**트리거:** {stock.get('trigger_reason', '알 수 없음')}\n\n"
        
        msg += f"**🤖 AI 분석**\n"
        msg += f"_{analysis['summary']}_\n\n"
        
        # 전략 섹션
        if stock.get('price', 0) > 0 and analysis.get('target_price', 0) > 0:
            msg += f"**📈 전략**\n"
            if market == 'KR':
                msg += f"진입: {int(analysis['entry_price']):,}원\n"
                msg += f"목표: {int(analysis['target_price']):,}원 **(+{analysis['upside']:.0f}%)**\n"
                msg += f"손절: {int(analysis['stop_loss']):,}원 (-{analysis['risk']:.0f}%)\n\n"
            else:
                msg += f"진입: ${analysis['entry_price']:.2f}\n"
                msg += f"목표: ${analysis['target_price']:.2f} **(+{analysis['upside']:.0f}%)**\n"
                msg += f"손절: ${analysis['stop_loss']:.2f} (-{analysis['risk']:.0f}%)\n\n"
        
        msg += f"**⚠️ 리스크:** {analysis['risk_level']}\n"
        msg += f"**💰 권장비중:** {analysis['position_size']}%\n\n"
        
        news_url = stock.get('news_url') or stock.get('url')
        if news_url:
            msg += f"[📰 뉴스 원문 보기]({news_url})\n\n"
        
        msg += f"_{analysis['reasoning']}_\n\n"
        msg += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return msg
    
    async def scan_us_stocks(self):
        """미국 주식 스캔"""
        if not self.is_us_market_hours(): return []
        alerts = []
        try:
            # === 기본 스캔 + 고급 스캔 통합 ===
            results = await asyncio.gather(
                self.us_news.scan(),
                self.us_price.scan(),
                self.us_social.scan(),
                self.insider.scan(),
                self.short_squeeze.scan(),
                self.whale.scan(),
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"스캐너 오류: {result}")
                    continue
                if result:
                    for alert in result: alert['market'] = 'US'
                    alerts.extend(result)
            
            if alerts: 
                logger.info(f"🇺🇸 미국: {len(alerts)}개 발견")
                
        except Exception as e:
            await self.send_error_alert(f"미국 스캔 오류: {e}")
        
        return alerts
    
    async def scan_kr_stocks(self):
        """한국 주식 스캔"""
        if not self.is_kr_market_hours(): return []
        alerts = []
        try:
            alerts = await self.kr_scanner.scan()
            if alerts: 
                logger.info(f"🇰🇷 한국: {len(alerts)}개 발견")
        except Exception as e:
            await self.send_error_alert(f"한국 스캔 오류: {e}")
        return alerts
    
    async def run(self):
        logger.info("🚀 10억 만들기 글로벌 주식 알림 시스템 시작")
        
        try:
            start_msg = "✅ **10억 만들기 시스템 가동**\n\n"
            start_msg += "🔧 탑재 기능:\n"
            start_msg += "✓ 내부자 거래 추적 (Form 4)\n"
            start_msg += "✓ 숏스퀴즈 감지 (Finviz)\n"
            start_msg += "✓ 고래 추적 (13D/G)\n"
            start_msg += "✓ 옵션/다크풀 검증\n"
            start_msg += "✓ 자동 백테스팅\n\n"
            start_msg += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await self.telegram.send_message(start_msg)
        except Exception as e: 
            logger.error(f"시작 메시지 전송 실패: {e}")
        
        scan_interval = 30
        error_count = 0
        max_errors = 10
        
        while True:
            try:
                us_alerts, kr_alerts = await asyncio.gather(
                    self.scan_us_stocks(),
                    self.scan_kr_stocks()
                )
                
                all_alerts = us_alerts + kr_alerts
                
                if all_alerts:
                    logger.info(f"📬 총 {len(all_alerts)}개 알림 처리 중")
                    
                    for alert in all_alerts:
                        await self.process_alert(alert)
                        await asyncio.sleep(2)
                
                await asyncio.sleep(scan_interval)
                error_count = 0
                
            except KeyboardInterrupt:
                logger.info("⛔ 사용자 종료")
                break
                
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 메인 루프 오류 ({error_count}/{max_errors}): {e}")
                await self.send_error_alert(f"메인 루프 오류: {e}")
                
                if error_count >= max_errors:
                    await self.telegram.send_message("🚨 **시스템 중단**\n\n연속 오류 발생")
                    break
                
                await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        system = GlobalStockAlertSystem()
        asyncio.run(system.run())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
