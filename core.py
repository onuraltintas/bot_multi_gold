"""
Core Sınıflar - Exchange Client, Scheduler, Tracker, Notifier
"""
import httpx
import time
import logging
import asyncio
from datetime import datetime
import pytz
from typing import List, Tuple, Callable, Awaitable, Any, Optional
from config import MIN_KLINES

logger = logging.getLogger(__name__)


async def async_retry(
    func: Callable[[], Awaitable[Any]],
    *,
    retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    retry_exceptions: tuple = (httpx.RequestError, httpx.TimeoutException),
    on_error: Optional[Callable[[int, Exception], None]] = None,
) -> Any:
    """Basit exponential backoff ile async retry helper.

    Args:
        func: Awaitable döndüren çağrı (parametresiz lambda).
        retries: Toplam deneme sayısı (ilk deneme + ekstra tekrar = retries).
        base_delay: İlk bekleme süresi.
        max_delay: Üst sınır bekleme.
        retry_exceptions: Yakalanacak istisna tipleri.
        on_error: Hata olduğunda çağrılacak callback (attempt, exception).
    Returns:
        func çıktısı ya da son hata raise edilir.
    """
    attempt = 0
    while True:
        try:
            return await func()
        except retry_exceptions as e:  # type: ignore
            attempt += 1
            if attempt > retries:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            if on_error:
                on_error(attempt, e)
            await asyncio.sleep(delay)
        except Exception:
            # Farklı exception tipi ise retry etmeden direkt fırlat
            raise


class ExchangeClient:
    """Exchange API base class - Twelve Data veya başka kaynaklardan veri çekmek için"""

    async def get_klines(self, symbol: str, interval: str, limit: int = 101) -> List[List]:
        """Mum verilerini al - Alt sınıflar implement etmeli"""
        raise NotImplementedError("Subclass must implement get_klines()")

    async def close(self):
        """Client kapatma - Alt sınıflar implement etmeli"""
        pass


class TwelveDataClient(ExchangeClient):
    """Twelve Data API Client - Real-time Forex Gold (XAUUSD) verisi için
    
    Free tier: 800 requests/day, real-time data
    """
    
    # Timeframe mapping: bot -> Twelve Data
    # Supported: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 8h, 1day, 1week, 1month
    TIMEFRAME_MAP = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "45m": "45min",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "8h": "8h",
        "1d": "1day"
    }
    
    def __init__(self, api_key: str):
        """Twelve Data Client initialize
        
        Args:
            api_key: Twelve Data API key
        """
        self.api_key = api_key
        self.base_url = "https://api.twelvedata.com"
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def get_klines(self, symbol: str, interval: str, limit: int = 101) -> List[List]:
        """Twelve Data'dan mum verilerini al ve bot formatına çevir
        
        Returns:
            List[List]: Her mum [open_time, open, high, low, close, volume, close_time, ...]
        """
        # Timeframe çevir
        td_interval = self.TIMEFRAME_MAP.get(interval)
        if td_interval is None:
            logger.error(f"Unsupported timeframe: {interval}")
            return []
        
        # Symbol format: Use as-is (XAU/USD for forex pairs)
        td_symbol = symbol
        
        # API request
        url = f"{self.base_url}/time_series"
        params = {
            "symbol": td_symbol,
            "interval": td_interval,
            "outputsize": limit,
            "apikey": self.api_key,
            "timezone": "UTC",  # UTC timezone kullan
            "format": "JSON"
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Hata kontrolü
            if "status" in data and data["status"] == "error":
                logger.error(f"Twelve Data API error: {data.get('message', 'Unknown error')}")
                return []
            
            if "values" not in data or not data["values"]:
                logger.error(f"No data from Twelve Data for {symbol} {interval}")
                return []
            
            # Twelve Data formatını bot formatına çevir
            # Twelve Data: {"datetime": "2025-01-01 12:00:00", "open": "2000.00", "high": "2001.00", ...}
            # Bot: [open_time_ms, open, high, low, close, volume, close_time_ms, ...]
            klines = []
            timeframe_ms = self._get_timeframe_ms(interval)
            
            for candle in reversed(data["values"]):  # En eskiden en yeniye sırala
                # Datetime'ı parse et (UTC timezone)
                dt_str = candle["datetime"]
                # Format: "2025-01-01 12:00:00" veya "2025-01-01"
                try:
                    if " " in dt_str:
                        # UTC olarak parse et
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                        dt = dt.replace(tzinfo=pytz.UTC)
                    else:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d")
                        dt = dt.replace(tzinfo=pytz.UTC)
                    
                    open_time_ms = int(dt.timestamp() * 1000)
                    close_time_ms = open_time_ms + timeframe_ms
                    
                    klines.append([
                        open_time_ms,
                        float(candle["open"]),
                        float(candle["high"]),
                        float(candle["low"]),
                        float(candle["close"]),
                        float(candle.get("volume", 0)),  # Forex'te volume olmayabilir
                        close_time_ms,
                        0,  # quote_asset_volume (Twelve Data'da yok)
                        0,  # number_of_trades (Twelve Data'da yok)
                        0,  # taker_buy_base (Twelve Data'da yok)
                        0   # taker_buy_quote (Twelve Data'da yok)
                    ])
                except Exception as e:
                    logger.error(f"Error parsing candle datetime '{dt_str}': {e}")
                    continue
            
            return klines
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Twelve Data HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching Twelve Data: {e}")
            return []
    
    def _get_timeframe_ms(self, interval: str) -> int:
        """Timeframe'i milisaniyeye çevir"""
        map_ms = {
            "1m": 60 * 1000,
            "3m": 3 * 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000
        }
        return map_ms.get(interval, 60 * 1000)
    
    async def close(self):
        """HTTP client'ı kapat"""
        await self.client.aclose()
        logger.info("Twelve Data client closed")


class TimeframeScheduler:
    """Her timeframe için mum kapanış zamanlarını takip eder"""

    # Timeframe'leri millisaniyeye çevir
    TIMEFRAME_MS = {
        "1m": 60 * 1000,
        "3m": 3 * 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000
    }

    def __init__(self):
        self.next_candle_close = {}  # timeframe -> timestamp (ms)
        self.initialized = set()
        self.retry_counts = {}  # timeframe -> retry sayısı (timestamp validation için)

    async def initialize(self, symbol: str, timeframe: str, exchange_client):
        """Exchange'den aktif mumun kapanış zamanını al"""
        if timeframe in self.initialized:
            return

        try:
            # Son 2 mumu al
            klines = await exchange_client.get_klines(symbol, timeframe, limit=2)
            if not klines or len(klines) < 1:
                logger.error(f"Could not fetch klines for {symbol} {timeframe}")
                return

            # Aktif mumun close time'ını kullan (1 mum gecikmeyi önle)
            # klines[-1] = Şu an aktif mum (henüz kapanmamış)
            # klines[-1][6] = Bu mumun kapanış zamanı (gelecekteki timestamp)
            current_candle_close = int(klines[-1][6])

            # İlk kontrol bu mumun kapanışında olacak
            self.next_candle_close[timeframe] = current_candle_close
            self.initialized.add(timeframe)

            logger.info(f"Scheduler initialized for {timeframe}: next close at {self._format_timestamp(current_candle_close)}")

        except Exception as e:
            logger.error(f"Error initializing scheduler for {timeframe}: {e}")

    def should_analyze(self, timeframe: str) -> bool:
        """Bu timeframe'in mumu kapandı mı?

        5 saniye buffer ekler - Exchange'in mumu finalize etmesi ve rate limit için.
        Bu, "1 mum geç sinyal" sorununu önler ve API limitlerini korur.
        """
        if timeframe not in self.next_candle_close:
            return False

        current_time = int(time.time() * 1000)
        # 5 saniye buffer: Exchange'in mumu tam finalize etmesi ve rate limit koruması
        candle_close_with_buffer = self.next_candle_close[timeframe] + 5000
        return current_time >= candle_close_with_buffer

    def mark_analyzed(self, timeframe: str):
        """Analiz yapıldı, bir sonraki mum kapanışını ayarla"""
        if timeframe not in self.next_candle_close:
            return

        interval_ms = self.TIMEFRAME_MS.get(timeframe, 60000)
        self.next_candle_close[timeframe] += interval_ms
        # Retry counter'ı sıfırla (yeni mum için baştan başla)
        self.retry_counts[timeframe] = 0
        logger.debug(f"{timeframe} next close: {self._format_timestamp(self.next_candle_close[timeframe])}")

    def get_next_check_time(self) -> float:
        """En yakın mum kapanışına kalan süre (saniye)

        5 saniye buffer dahil - should_analyze() ile senkronize çalışır.

        ⚠️ ÖZEL: Eğer herhangi bir timeframe retry durumundaysa (retry_count > 0),
        10 saniye döndür (rate limit koruması için).
        """
        # 🔥 FIX: Retry durumu kontrolü
        # Eğer herhangi bir timeframe retry modundaysa, 10 saniye döndür (rate limit: 8 req/min)
        for timeframe, retry_count in self.retry_counts.items():
            if retry_count > 0:
                logger.debug(f"Retry mode active for {timeframe} (retry {retry_count}/6), next check in 10 seconds")
                return 10  # Rate limit aşılmaması için 10 saniye bekle

        # Normal flow (retry yoksa)
        if not self.next_candle_close:
            return 60  # Default 60 saniye

        current_time = int(time.time() * 1000)

        # 5 saniye buffer ekle (should_analyze ile aynı)
        # Her timestamp'e 5000ms ekleyerek kontrol et
        next_times = [
            (t + 5000) - current_time
            for t in self.next_candle_close.values()
            if (t + 5000) > current_time
        ]

        if not next_times:
            return 1  # Hemen kontrol et

        return max(1, min(next_times) / 1000)  # En az 1 saniye

    def increment_retry(self, timeframe: str) -> int:
        """Timestamp validation retry sayısını artır ve döndür"""
        if timeframe not in self.retry_counts:
            self.retry_counts[timeframe] = 0
        self.retry_counts[timeframe] += 1
        return self.retry_counts[timeframe]

    def reset_retry(self, timeframe: str):
        """Retry counter'ı sıfırla (başarılı analiz sonrası)"""
        self.retry_counts[timeframe] = 0

    def should_skip_due_to_timeout(self, timeframe: str, max_retries: int = 6) -> bool:
        """60 saniye (6 retry x 10 saniye) geçtiyse True döndür"""
        retry_count = self.retry_counts.get(timeframe, 0)
        return retry_count >= max_retries

    def _format_timestamp(self, timestamp_ms: int) -> str:
        """Timestamp'i okunabilir formata çevir"""
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=pytz.timezone('Europe/Istanbul'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')


class SignalTracker:
    """Sinyal takibi ve tekrar önleme"""

    def __init__(self):
        self.last_signals = {}
        self.signal_timestamps = {}

    def should_send(self, symbol: str, timeframe: str, signal: str, timestamp: int) -> bool:
        """Sinyalin gönderilip gönderilmeyeceğini belirle"""
        key = f"{symbol}_{timeframe}"

        if key not in self.last_signals:
            self.last_signals[key] = "NEUTRAL"
            self.signal_timestamps[key] = 0

        if signal == self.last_signals[key]:
            return False

        self.last_signals[key] = signal
        self.signal_timestamps[key] = timestamp
        return True

    def get_last_signal(self, symbol: str, timeframe: str) -> Tuple[str, int]:
        """Son sinyal ve zamanını döndür"""
        key = f"{symbol}_{timeframe}"
        if key in self.last_signals:
            return self.last_signals[key], self.signal_timestamps[key]
        return "NEUTRAL", 0


class TelegramNotifier:
    """Telegram mesaj gönderme"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_message(self, message: str):
        """Telegram'a mesaj gönder (retry/backoff)."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_notification": False,
        }

        async def _call():
            return await self.client.post(url, json=payload)

        def _on_err(attempt: int, exc: Exception):
            logger.warning(f"Telegram send attempt {attempt} failed: {exc}")

        try:
            response = await async_retry(_call, retries=3, base_delay=0.5, max_delay=3.0, on_error=_on_err)
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
            else:
                logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Final failure sending Telegram message: {e}")

    async def close(self):
        """HTTP client'i kapat"""
        await self.client.aclose()