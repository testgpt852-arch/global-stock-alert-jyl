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
            
            # 미국 스캐너
            self.us_news = NewsScanner(self.config.FINNHUB_API_KEY)
            self.us_price = PriceScanner(self.config.ALPHA_VANTAGE_KEY)
            self.us_social = SocialScanner()
            
            # 한국 스캐너
            self.kr_scanner = KRStockScanner(self.telegram, self.ai)
            
            self.alerted_stocks = {}
            self.alert_cooldown = 14400  # 1시간
            
            logger.info("✅ 시스템 초기화 완료")
            
        except Exception as e:
            logger.critical(f"❌ 초기화 실패: {e}")
            raise
    
    async def send_error_alert(self, error):
        """오류 텔레그램 알림"""
        try:
            msg = f"⚠️ **시스템 오류**\n\n```\n{str(error)}\n```\n\n"
            msg += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await self.telegram.send_message(msg)
            logger.error(f"오류 알림 전송: {error}")
        except Exception as e:
            logger.critical(f"오류 알림 실패: {e}")
    
    def is_us_market_hours(self):
        """미국 장시간 체크"""
        try:
            ny_tz = pytz.timezone('America/New_York')
            now = datetime.now(ny_tz)
            
            if now.weekday() >= 5:
                return False
            
            market_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
            market_end = now.replace(hour=20, minute=0, second=0, microsecond=0)
            
            return market_start <= now <= market_end
        except Exception as e:
            logger.error(f"미국 시간 체크 오류: {e}")
            return True
    
    def is_kr_market_hours(self):
        """한국 장시간 체크"""
        try:
            kr_tz = pytz.timezone('Asia/Seoul')
            now = datetime.now(kr_tz)
            
            if now.weekday() >= 5:
                return False
            
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
            if (now - last_alert).seconds < self.alert_cooldown:
                return False
        
        self.alerted_stocks[alert_key] = now
        return True
    
    async def process_alert(self, stock_data):
        """알림 처리"""
        try:
            symbol = stock_data['symbol']
            market = stock_data.get('market', 'US')
            
            if not self.should_alert(symbol, market):
                logger.info(f"⏭️ {symbol} 쿨다운 중")
                return
            
            logger.info(f"🔍 {symbol} 분석 중...")
            
            # AI 분석
            analysis = await self.ai.analyze_opportunity(stock_data)
            
            if analysis['score'] < self.config.MIN_AI_SCORE:
                logger.info(f"⏭️ {symbol} 점수 낮음: {analysis['score']}/10")
                return
            
            # 알림 생성
            message = self.format_alert_message(stock_data, analysis)
            
            # 전송
            await self.telegram.send_message(message)
            
            logger.info(f"✅ {symbol} 알림 전송 (점수: {analysis['score']}/10)")
            
        except Exception as e:
            await self.send_error_alert(f"알림 처리 오류 ({stock_data.get('symbol', 'UNKNOWN')}): {e}")
    
    def format_alert_message(self, stock, analysis):
        """알림 메시지 포맷"""
        market = stock.get('market', 'US')
        market_emoji = "🇰🇷" if market == 'KR' else "🇺🇸"
        
        if analysis['score'] >= 9:
            urgency = "🚨 **텐배거 가능성** 🚨"
        elif analysis['score'] >= 8:
            urgency = "⚠️ **HIGH PRIORITY** ⚠️"
        else:
            urgency = "📢 **OPPORTUNITY** 📢"
        
        msg = f"{urgency}\n\n"
        msg += f"{market_emoji} **AI 점수: {analysis['score']}/10**\n\n"
        
        if market == 'KR':
            msg += f"**{stock.get('name', '')}** ({stock['symbol']})\n"
            msg += f"현재가: {stock['price']:,}원\n"
        else:
            msg += f"**${stock['symbol']}**\n"
            msg += f"현재가: ${stock['price']:.2f}\n"
        
        msg += f"변화: **{stock['change_percent']:+.2f}%**\n"
        
        if stock.get('volume', 0) > 0:
            msg += f"거래량: {stock['volume']:,}\n"
        
        msg += f"\n**트리거:** {stock['trigger_reason']}\n\n"
        
        msg += f"**🤖 AI 분석**\n"
        msg += f"_{analysis['summary']}_\n\n"
        
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
        
        if stock.get('news_url'):
            msg += f"[📰 뉴스보기]({stock['news_url']})\n\n"
        
        msg += f"_{analysis['reasoning']}_\n\n"
        msg += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return msg
    
    async def scan_us_stocks(self):
        """미국 주식 스캔"""
        if not self.is_us_market_hours():
            return []
        
        alerts = []
        try:
            results = await asyncio.gather(
                self.us_news.scan(),
                self.us_price.scan(),
                self.us_social.scan(),
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"미국 스캐너 오류: {result}")
                    continue
                if result:
                    # market 태그 추가
                    for alert in result:
                        alert['market'] = 'US'
                    alerts.extend(result)
            
            if alerts:
                logger.info(f"🇺🇸 미국: {len(alerts)}개 발견")
            
        except Exception as e:
            await self.send_error_alert(f"미국 스캔 오류: {e}")
        
        return alerts
    
    async def scan_kr_stocks(self):
        """한국 주식 스캔"""
        if not self.is_kr_market_hours():
            return []
        
        alerts = []
        try:
            alerts = await self.kr_scanner.scan()
            
            if alerts:
                logger.info(f"🇰🇷 한국: {len(alerts)}개 발견")
            
        except Exception as e:
            await self.send_error_alert(f"한국 스캔 오류: {e}")
        
        return alerts
    
    async def run(self):
        """메인 루프"""
        logger.info("🌍 글로벌 주식 알림 시스템 시작")
        
        try:
            start_msg = "✅ **글로벌 주식 알림 시작**\n\n"
            start_msg += "🇺🇸 미국 주식 모니터링\n"
            start_msg += "🇰🇷 한국 주식 모니터링\n\n"
            start_msg += "⏰ 시작: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n"
            start_msg += "📊 **감지 항목:**\n"
            start_msg += "• 실시간 뉴스\n"
            start_msg += "• 가격 급등/급락\n"
            start_msg += "• 소셜 트렌드\n"
            start_msg += "• AI 자동 분석\n\n"
            start_msg += "💡 중요 알림만 보내드립니다!"
            
            await self.telegram.send_message(start_msg)
            
        except Exception as e:
            logger.error(f"시작 메시지 전송 실패: {e}")
        
        scan_interval = 30
        error_count = 0
        max_errors = 10
        
        while True:
            try:
                # 양쪽 동시 스캔
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
                logger.info("🛑 종료 중...")
                await self.telegram.send_message("⚠️ 시스템 종료됨")
                break
                
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 메인 루프 오류 ({error_count}/{max_errors}): {e}")
                await self.send_error_alert(f"메인 루프 오류: {e}")
                
                if error_count >= max_errors:
                    critical_msg = f"🚨 **시스템 중단**\n\n연속 오류 {max_errors}회\n재시작 필요"
                    await self.telegram.send_message(critical_msg)
                    break
                
                await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        system = GlobalStockAlertSystem()
        asyncio.run(system.run())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")