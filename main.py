#!/usr/bin/env python3
"""
CMO Trading Bot - XAUUSD
CMO indikatörü kullanarak Forex Gold için alım/satım sinyalleri üretir.
Sinyaller Telegram üzerinden gönderilir.
"""
import asyncio
import logging
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TARGET_SYMBOL, TIMEFRAMES,
    CMO_LENGTH, TWELVE_DATA_API_KEY,
    STOCH_PERIOD_K, STOCH_SMOOTH_K, STOCH_SMOOTH_D,
    RSI_LENGTH,
    MACD_FAST_LENGTH, MACD_SLOW_LENGTH, MACD_SIGNAL_LENGTH,
    STOCH_RSI_LENGTH_RSI, STOCH_RSI_LENGTH_STOCH, STOCH_RSI_SMOOTH_K, STOCH_RSI_SMOOTH_D,
    WILLIAMS_R_LENGTH, FISHER_LENGTH, CORAL_PERIOD, CORAL_MULTIPLIER
)
from core import TwelveDataClient, TimeframeScheduler, SignalTracker, TelegramNotifier
from indicators import ChandeMomentumOscillator, StochasticOscillator, RelativeStrengthIndex, MACD, StochasticRSI, WilliamsR, FisherTransform, CoralTrend
from strategies import AllIndicatorsStrategy
from analyzer import CryptoAnalyzer

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cmo_bot_xauusd.log")
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Ana fonksiyon - Botu başlatır ve sürekli döngüde çalıştırır"""

    # Konfigürasyonu kontrol et
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in .env file")
        return
    
    if not TWELVE_DATA_API_KEY:
        logger.error("TWELVE_DATA_API_KEY not found in .env file")
        return

    # Twelve Data Client oluştur
    exchange = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
    logger.info("Twelve Data client initialized (800 req/day free tier)")

    # İndikatörler oluştur
    cmo_indicator = ChandeMomentumOscillator(length=CMO_LENGTH, use_low=True)
    logger.info(f"CMO Indicator initialized with length={CMO_LENGTH}, use_low=True")
    
    stoch_indicator = StochasticOscillator(
        period_k=STOCH_PERIOD_K,
        smooth_k=STOCH_SMOOTH_K,
        smooth_d=STOCH_SMOOTH_D
    )
    logger.info(f"Stochastic Indicator initialized with K={STOCH_PERIOD_K}, smoothK={STOCH_SMOOTH_K}, smoothD={STOCH_SMOOTH_D}")
    
    rsi_indicator = RelativeStrengthIndex(length=RSI_LENGTH)
    logger.info(f"RSI Indicator initialized with length={RSI_LENGTH}")
    
    macd_indicator = MACD(
        fast_length=MACD_FAST_LENGTH,
        slow_length=MACD_SLOW_LENGTH,
        signal_length=MACD_SIGNAL_LENGTH
    )
    logger.info(f"MACD Indicator initialized with fast={MACD_FAST_LENGTH}, slow={MACD_SLOW_LENGTH}, signal={MACD_SIGNAL_LENGTH}")
    
    stoch_rsi_indicator = StochasticRSI(
        length_rsi=STOCH_RSI_LENGTH_RSI,
        length_stoch=STOCH_RSI_LENGTH_STOCH,
        smooth_k=STOCH_RSI_SMOOTH_K,
        smooth_d=STOCH_RSI_SMOOTH_D
    )
    logger.info(f"Stochastic RSI Indicator initialized with lengthRSI={STOCH_RSI_LENGTH_RSI}, lengthStoch={STOCH_RSI_LENGTH_STOCH}, smoothK={STOCH_RSI_SMOOTH_K}, smoothD={STOCH_RSI_SMOOTH_D}")
    
    williams_r_indicator = WilliamsR(length=WILLIAMS_R_LENGTH)
    logger.info(f"Williams %R Indicator initialized with length={WILLIAMS_R_LENGTH}")
    
    fisher_indicator = FisherTransform(length=FISHER_LENGTH)
    logger.info(f"Fisher Transform Indicator initialized with length={FISHER_LENGTH}")
    
    coral_indicator = CoralTrend(period=CORAL_PERIOD, multiplier=CORAL_MULTIPLIER)
    logger.info(f"Coral Trend Indicator initialized with period={CORAL_PERIOD}, multiplier={CORAL_MULTIPLIER}")

    # Strateji oluştur - Tüm indikatörler kombinasyonu (8 indikatör)
    strategy = AllIndicatorsStrategy(
        cmo_indicator=cmo_indicator, 
        stoch_indicator=stoch_indicator,
        rsi_indicator=rsi_indicator,
        macd_indicator=macd_indicator,
        stoch_rsi_indicator=stoch_rsi_indicator,
        williams_r_indicator=williams_r_indicator,
        fisher_indicator=fisher_indicator,
        coral_indicator=coral_indicator
    )

    tracker = SignalTracker()
    notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    scheduler = TimeframeScheduler()

    # Ana analyzer'ı oluştur (Dependency Injection)
    analyzer = CryptoAnalyzer(
        exchange_client=exchange,
        indicator=cmo_indicator,
        strategy=strategy,
        signal_tracker=tracker,
        notifier=notifier,
        scheduler=scheduler,
        symbol=TARGET_SYMBOL
    )

    try:
        # Scheduler'ı başlat (1m hariç, çünkü 5m ile birlikte analiz edilecek)
        logger.info("Initializing scheduler for all timeframes...")
        for timeframe in TIMEFRAMES:
            if timeframe == "1m":
                continue  # 1m için scheduler yok, 5m kapandığında analiz edilecek
            await scheduler.initialize(TARGET_SYMBOL, timeframe, exchange)
        logger.info("Scheduler initialization completed")

        # Başlangıç mesajı gönder
        from datetime import datetime
        import pytz
        turkey_tz = pytz.timezone('Europe/Istanbul')
        start_time = datetime.now(turkey_tz)

        startup_message = (
            "🤖 *BOT BAŞLATILDI*\n"
            f"🕒 {start_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n\n"
            f"📊 Sembol: *{TARGET_SYMBOL}*\n"
            f"🖥 Platform: *Twelve Data API*\n"
            f"⏰ Timeframes: {' | '.join(TIMEFRAMES)}\n"
            f"📈 İndikatör: *CMO({CMO_LENGTH})*\n\n"
            "✅ Sinyaller bekleniyor..."
        )
        await notifier.send_message(startup_message)
        logger.info("Startup message sent to Telegram")

        # Sonsuz analiz döngüsü - her timeframe için mum kapanışlarını kontrol et
        while True:
            # Tüm timeframe'leri kontrol et
            ready_timeframes = []
            for timeframe in TIMEFRAMES:
                if scheduler.should_analyze(timeframe):
                    ready_timeframes.append(timeframe)
                    logger.info(f"Candle closed for {timeframe}")

            # Hazır timeframe'ler varsa analiz et
            if ready_timeframes:
                logger.info(f"Analyzing timeframes: {ready_timeframes}")
                
                # Kısa ve uzun vadeli timeframe'leri ayır
                short_term = [tf for tf in ready_timeframes if tf in ["3m", "5m", "15m", "1h"]]
                long_term = [tf for tf in ready_timeframes if tf in ["4h", "1d"]]
                
                # Kısa vadeli analiz
                if short_term:
                    successfully_analyzed = await analyzer.analyze_short_term_batch(short_term)
                    for timeframe in successfully_analyzed:
                        scheduler.mark_analyzed(timeframe)
                        logger.debug(f"Marked {timeframe} as analyzed")
                
                # Uzun vadeli analiz
                if long_term:
                    successfully_analyzed = await analyzer.analyze_long_term_batch(long_term)
                    for timeframe in successfully_analyzed:
                        scheduler.mark_analyzed(timeframe)
                        logger.debug(f"Marked {timeframe} as analyzed")

            # En yakın mum kapanışına kadar bekle
            wait_time = scheduler.get_next_check_time()
            logger.debug(f"Next check in {wait_time:.1f} seconds")
            await asyncio.sleep(wait_time)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await notifier.send_message(f"❌ *Bot Error*\n{str(e)}\nBot has stopped.")
    finally:
        await exchange.close()
        await notifier.close()


if __name__ == "__main__":
    asyncio.run(main())