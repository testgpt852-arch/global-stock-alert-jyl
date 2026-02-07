import aiohttp
import logging

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        
    async def send_message(self, text, parse_mode='Markdown'):
        """텔레그램 메시지 전송"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=10) as response:
                    if response.status == 200:
                        logger.info("✅ Telegram message sent")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Telegram error {response.status}: {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    async def send_photo(self, photo_url, caption=""):
        """이미지 전송 (차트 등)"""
        try:
            url = f"{self.base_url}/sendPhoto"
            
            data = {
                'chat_id': self.chat_id,
                'photo': photo_url,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=15) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            return False