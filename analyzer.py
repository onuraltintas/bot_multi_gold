"""
CryptoAnalyzer - Ana Orkestrasyon Sınıfı
"""
import time
import logging
from datetime import datetime
import pytz
from typing import Dict, Optional, List
from config import TARGET_SYMBOL, MIN_KLINES, MIN_KLINES_PER_TIMEFRAME, TIMEFRAMES
from indicators import IIndicator
from strategies import IStrategy
from core import ExchangeClient, SignalTracker, TelegramNotifier
from message_builders import ShortTermMessageBuilder, LongTermMessageBuilder

logger = logging.getLogger(__name__)


class CryptoAnalyzer:
    """Ana orkestrasyon sınıfı - Tüm componentleri koordine eder"""

    def __init__(self,
                 exchange_client: ExchangeClient,
                 indicator: IIndicator,
                 strategy: IStrategy,
                 signal_tracker: SignalTracker,
                 notifier: TelegramNotifier,
                 scheduler=None,
                 symbol: str = TARGET_SYMBOL):
        self.exchange = exchange_client
        self.indicator = indicator
        self.strategy = strategy
        self.tracker = signal_tracker
        self.notifier = notifier
        self.scheduler = scheduler
        self.symbol = symbol
        # Yeni builder bileşenleri
        self._short_builder = ShortTermMessageBuilder()
        self._long_builder = LongTermMessageBuilder()

    async def analyze_timeframe(self, timeframe: str) -> Optional[Dict]:
        """Belirli bir timeframe için analiz yap"""
        klines = await self.exchange.get_klines(self.symbol, timeframe)

        # Minimum mum kontrolü (TradingView uyumlu)
        # API aktif mumu da döndürür, bu yüzden min+1 gerekli
        # Örn: 100 kapanmış mum + 1 aktif = 101 mum gerekir
        min_required = MIN_KLINES_PER_TIMEFRAME.get(timeframe, MIN_KLINES)

        # En az min_required + 1 mum olmalı (aktif mum dahil)
        if not klines or len(klines) < min_required + 1:
            logger.warning(
                f"Insufficient data for {self.symbol} {timeframe}: "
                f"got {len(klines) if klines else 0}, need {min_required + 1}"
            )
            return None

        # Stratejiyi çağır ve sinyal al
        indicator_values = self.indicator.calculate(klines)
        signal = self.strategy.analyze(indicator_values, klines)

        # Sinyal bilgilerini hazırla
        # SON KAPANMIŞ MUMU KULLAN (aktif mum hariç) - TradingView senkronizasyonu için
        closes = [float(k[4]) for k in klines]
        curr_idx = len(klines) - 2  # Son kapanmış mum

        # Data validation kontrolü
        # Aldığımız son kapanmış mumun close_time'ını kontrol et
        last_completed_candle_close_time = int(klines[curr_idx][6])  # close_time (ms)

        # Scheduler varsa, beklenen close time ile karşılaştır
        if self.scheduler and hasattr(self.scheduler, 'next_candle_close'):
            expected_close_time = self.scheduler.next_candle_close.get(timeframe)
            if expected_close_time:
                # Son kapanmış mum, beklenen mumdan ESKİ mi?
                if last_completed_candle_close_time < expected_close_time:
                    # Retry counter'ı artır
                    retry_count = self.scheduler.increment_retry(timeframe)

                    # 60 saniye (6 retry x 10 saniye) geçti mi?
                    if self.scheduler.should_skip_due_to_timeout(timeframe):
                        logger.error(
                            f"{timeframe}: Data TIMEOUT after 6 retries (60 seconds)! "
                            f"Expected close: {expected_close_time}, "
                            f"Got: {last_completed_candle_close_time}. "
                            f"Skipping this candle permanently and moving to next."
                        )
                        # Scheduler'ı güncelle (bir sonraki mumu bekle)
                        self.scheduler.mark_analyzed(timeframe)
                        return None  # Analiz yok (mum atlandı)

                    logger.warning(
                        f"{timeframe}: Data not yet updated (retry {retry_count}/6). "
                        f"Expected close: {expected_close_time}, "
                        f"Got: {last_completed_candle_close_time} "
                        f"(diff: {(expected_close_time - last_completed_candle_close_time) / 1000:.1f}s). "
                        f"Will retry on next loop cycle..."
                    )
                    return None  # Bu iterasyonu atla, bir sonraki döngüde tekrar dene
                else:
                    # Timestamp validation başarılı, retry counter'ı sıfırla
                    self.scheduler.reset_retry(timeframe)

        timestamp = int(klines[curr_idx][0]) // 1000

        # NEUTRAL durumlar için loglama
        if signal == "NEUTRAL":
            # indicator_values dictionary'den değerleri al (arrays)
            indicators_raw = indicator_values if isinstance(indicator_values, dict) else {}
            
            # curr_idx ile son değerleri al
            indicators_data = {}
            for key, value in indicators_raw.items():
                if isinstance(value, list) and len(value) > curr_idx:
                    indicators_data[key] = value[curr_idx]

            # NEUTRAL durumlar için log
            log_parts = [
                f"⚪ {timeframe} | NEUTRAL",
                f"Price: ${closes[curr_idx]:.4f}",
            ]
            
            if 'cmo' in indicators_data and indicators_data['cmo'] is not None:
                log_parts.append(f"CMO: {indicators_data['cmo']:.1f}")
            if 'stoch_k' in indicators_data and indicators_data['stoch_k'] is not None:
                log_parts.append(f"Stoch K: {indicators_data['stoch_k']:.1f}")
            if 'rsi' in indicators_data and indicators_data['rsi'] is not None:
                log_parts.append(f"RSI: {indicators_data['rsi']:.1f}")
            if 'macd' in indicators_data and 'macd_signal' in indicators_data:
                if indicators_data['macd'] is not None and indicators_data['macd_signal'] is not None:
                    log_parts.append(f"MACD: {indicators_data['macd']:.4f}/{indicators_data['macd_signal']:.4f}")
            if 'stoch_rsi_k' in indicators_data and indicators_data['stoch_rsi_k'] is not None:
                log_parts.append(f"StochRSI K: {indicators_data['stoch_rsi_k']:.1f}")

            logger.info(" | ".join(log_parts))

            # ✅ FIX: NEUTRAL durumunda da result döndür (scheduler güncellemesi için)
            return {
                "symbol": self.symbol,
                "timeframe": timeframe,
                "signal": "NEUTRAL",
                "price": closes[curr_idx],
                "timestamp": timestamp,
                "indicators": indicators_data
            }

        # Sinyali tracker'a kaydet (mesaj gönderme kontrolü için değil, sadece "son sinyal" bilgisi için)
        self.tracker.last_signals[f"{self.symbol}_{timeframe}"] = signal
        self.tracker.signal_timestamps[f"{self.symbol}_{timeframe}"] = timestamp

        # İndikatör değerlerini hazırla (mesajda göstermek için)
        indicators_raw = indicator_values if isinstance(indicator_values, dict) else {}
        
        # curr_idx ile son değerleri al
        indicators_data = {}
        for key, value in indicators_raw.items():
            if isinstance(value, list) and len(value) > curr_idx:
                indicators_data[key] = value[curr_idx]

        # Detaylı sinyal + indikatör logu
        log_parts = [
            f"🎯 {timeframe} | {signal}",
            f"Price: ${closes[curr_idx]:.4f}",
        ]
        
        if 'cmo' in indicators_data and indicators_data['cmo'] is not None:
            log_parts.append(f"CMO: {indicators_data['cmo']:.1f}")
        if 'stoch_k' in indicators_data and indicators_data['stoch_k'] is not None:
            log_parts.append(f"Stoch K: {indicators_data['stoch_k']:.1f}")
        if 'rsi' in indicators_data and indicators_data['rsi'] is not None:
            log_parts.append(f"RSI: {indicators_data['rsi']:.1f}")
        if 'macd' in indicators_data and 'macd_signal' in indicators_data:
            if indicators_data['macd'] is not None and indicators_data['macd_signal'] is not None:
                log_parts.append(f"MACD: {indicators_data['macd']:.4f}/{indicators_data['macd_signal']:.4f}")
        if 'stoch_rsi_k' in indicators_data and indicators_data['stoch_rsi_k'] is not None:
            log_parts.append(f"StochRSI K: {indicators_data['stoch_rsi_k']:.1f}")

        logger.info(" | ".join(log_parts))

        return {
            "symbol": self.symbol,
            "timeframe": timeframe,
            "signal": signal,
            "price": closes[curr_idx],
            "timestamp": timestamp,
            "indicators": indicators_data
        }

    async def analyze_short_term_batch(self, timeframes: List[str]) -> List[str]:
        """Kısa vadeli timeframe'leri toplu analiz et (1m, 5m, 15m, 1h)

        Args:
            timeframes: Analiz edilecek timeframe'ler (örn: ["1m", "5m", "15m", "1h"])

        Returns:
            Başarıyla analiz edilen timeframe'lerin listesi
        """
        successfully_analyzed = []
        try:
            # Her timeframe için analiz sonuçlarını topla
            results = {}

            for timeframe in ["1m", "5m", "15m", "1h"]:  # Tüm kısa vadeli timeframe'leri kontrol et
                if timeframe in timeframes:
                    # Bu timeframe mum kapandı, analiz et
                    result = await self.analyze_timeframe(timeframe)
                    if result:
                        results[timeframe] = result
                        successfully_analyzed.append(timeframe)  # ✅ BAŞARILI
                        # Log zaten analyze_timeframe içinde yapılıyor
                else:
                    # Bu timeframe mum kapanmadı, sadece son sinyali al
                    # Boş result olarak ekle (mesajda "son sinyal" gösterilecek)
                    results[timeframe] = None
                    logger.debug(f"{timeframe}: not closed, will show last signal")

            # En az bir timeframe'de sinyal var mı kontrol et
            has_signal = any(
                result and result['signal'] != "NEUTRAL"
                for result in results.values() if result is not None
            )

            if has_signal:
                # En az birinde sinyal var, mesaj gönder
                logger.info(f"Short-term batch has signals, sending message")
                await self._send_short_term_batch_message(results)
            else:
                # Hiçbirinde sinyal yok, sessiz
                logger.debug(f"Short-term batch: no signals, skipping message")

        except Exception as e:
            logger.error(f"Error analyzing short-term batch: {e}", exc_info=True)

        return successfully_analyzed

    async def analyze_long_term_batch(self, timeframes: List[str]) -> List[str]:
        """Uzun vadeli timeframe'leri toplu analiz et (4h)

        Args:
            timeframes: Analiz edilecek timeframe'ler (örn: ["4h"])

        Returns:
            Başarıyla analiz edilen timeframe'lerin listesi
        """
        successfully_analyzed = []
        try:
            # Her timeframe için analiz sonuçlarını topla
            results = {}

            for timeframe in ["4h"]:  # Uzun vade timeframe'ini kontrol et
                if timeframe in timeframes:
                    # Bu timeframe mum kapandı, analiz et
                    # Önce yetersiz veri kontrolü
                    klines = await self.exchange.get_klines(self.symbol, timeframe)
                    min_required = MIN_KLINES_PER_TIMEFRAME.get(timeframe, MIN_KLINES)

                    if not klines or len(klines) < min_required + 1:
                        logger.warning(
                            f"Insufficient data for {self.symbol} {timeframe}: "
                            f"got {len(klines) if klines else 0}, need {min_required}"
                        )
                        await self._send_insufficient_data_message(timeframe, len(klines) if klines else 0)
                        results[timeframe] = None
                        continue

                    result = await self.analyze_timeframe(timeframe)
                    if result:
                        results[timeframe] = result
                        successfully_analyzed.append(timeframe)  # ✅ BAŞARILI
                        # Log zaten analyze_timeframe içinde yapılıyor
                else:
                    # Bu timeframe mum kapanmadı, sadece son sinyali al
                    results[timeframe] = None
                    logger.debug(f"{timeframe}: not closed, will show last signal")

            # En az bir timeframe'de sinyal var mı kontrol et
            has_signal = any(
                result and result['signal'] != "NEUTRAL"
                for result in results.values() if result is not None
            )

            if has_signal:
                # En az birinde sinyal var, mesaj gönder
                logger.info(f"Long-term batch has signals, sending message")
                await self._send_long_term_batch_message(results)
            else:
                # Hiçbirinde sinyal yok, sessiz
                logger.debug(f"Long-term batch: no signals, skipping message")

        except Exception as e:
            logger.error(f"Error analyzing long-term batch: {e}", exc_info=True)

        return successfully_analyzed

    async def run_analysis(self):
        """Tüm timeframe'ler için analiz çalıştır (eski metod - geriye dönük uyumluluk)"""
        short_term_signals = {}  # 1m, 5m, 15m, 1h
        long_term_signals = {}   # 4h

        for timeframe in TIMEFRAMES:
            try:
                result = await self.analyze_timeframe(timeframe)
                if result:
                    # Uzun vadeli ve kısa vadeli sinyalleri ayır
                    if timeframe in ["4h"]:
                        long_term_signals[timeframe] = result
                    else:
                        short_term_signals[timeframe] = result
                    logger.info(f"{timeframe}: {result['signal']} signal detected")
                else:
                    logger.info(f"{timeframe}: No signal generated")
            except Exception as e:
                logger.error(f"Error analyzing {timeframe}: {e}")
                continue

        # Kısa vadeli sinyaller için normal mesaj
        if short_term_signals:
            await self._send_short_term_message(short_term_signals)

        # Uzun vadeli sinyaller için özel mesaj (ayrı)
        if long_term_signals:
            await self._send_long_term_message(long_term_signals)

        if not short_term_signals and not long_term_signals:
            logger.info("No signals generated on any timeframe")

    async def _send_short_term_batch_message(self, results: Dict):
        first_active_result = next((r for r in results.values() if r is not None), None)
        if not first_active_result:
            logger.warning("No active results in batch, skipping message")
            return
        symbol = first_active_result['symbol']
        price = first_active_result['price']
        message = self._short_builder.build(symbol, price, results, self.tracker)
        if message:
            await self.notifier.send_message(message)
            logger.info("Short-term batch message sent")

# Placeholder fonksiyonu artık gereksiz (time-ago builder içinde hesaplanıyor)

    async def _send_short_term_message(self, signals: Dict):
        """Kısa vadeli (1m, 5m, 15m, 1h) sinyal mesajı - GOLD"""
        timeframe_info = {
            "1m": {"emoji": "⚡⚡", "name": "1 Dakika"},
            "5m": {"emoji": "🔸", "name": "5 Dakika"},
            "15m": {"emoji": "�", "name": "15 Dakika"},
            "1h": {"emoji": "⏰", "name": "1 Saat"}
        }

        first_signal = list(signals.values())[0]
        symbol = first_signal['symbol']
        price = first_signal['price']

        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)

        message = f"*🥇🥇🥇🥇🥇 GOLD ALTIN SİNYALİ 🥇🥇🥇🥇🥇*\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 Sembol: *{symbol}*\n"
        message += f"� Fiyat: *${price:.2f}*\n"
        message += f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        short_timeframes = ["5m", "15m", "1h"]
        for timeframe in short_timeframes:
            tf_info = timeframe_info.get(timeframe)
            if not tf_info:
                continue

            if timeframe in signals:
                signal_data = signals[timeframe]
                signal_type = signal_data['signal']
                indicators = signal_data['indicators']

                if signal_type == "BUY":
                    message += f"{tf_info['emoji']} *{tf_info['name']}*\n"
                    message += f"   🟢 *LONG (BUY)* 🟢\n"
                elif signal_type == "SELL":
                    message += f"{tf_info['emoji']} *{tf_info['name']}*\n"
                    message += f"   🔴 *SHORT (SELL)* 🔴\n"

                # CMO değeri
                cmo = indicators.get('cmo')
                if cmo is not None:
                    message += f"   └─ CMO(13): {cmo:.2f}\n"
                
                # Stochastic değerleri
                stoch_k = indicators.get('stoch_k')
                stoch_d = indicators.get('stoch_d')
                if stoch_k is not None and stoch_d is not None:
                    message += f"   └─ Stoch(9,3,3): K={stoch_k:.2f} D={stoch_d:.2f}\n"
                
                # RSI değeri
                rsi = indicators.get('rsi')
                if rsi is not None:
                    message += f"   └─ RSI(4): {rsi:.2f}\n"
                
                # MACD değerleri
                macd = indicators.get('macd')
                macd_signal = indicators.get('macd_signal')
                macd_histogram = indicators.get('macd_histogram')
                if macd is not None and macd_signal is not None:
                    message += f"   └─ MACD(8,13,8): {macd:.4f} / {macd_signal:.4f}\n"
                    if macd_histogram is not None:
                        hist_symbol = "📈" if macd_histogram > 0 else "📉"
                        message += f"   └─ Histogram: {macd_histogram:.4f} {hist_symbol}\n"
                
                # Stochastic RSI değerleri
                stoch_rsi_k = indicators.get('stoch_rsi_k')
                stoch_rsi_d = indicators.get('stoch_rsi_d')
                if stoch_rsi_k is not None and stoch_rsi_d is not None:
                    message += f"   └─ StochRSI(5,8,3,3): K={stoch_rsi_k:.2f} D={stoch_rsi_d:.2f}\n"

                # EMA Trend bilgisi
                if 'ema_13' in indicators and 'ema_21' in indicators and 'ema_55' in indicators:
                    ema_13 = indicators['ema_13']
                    ema_21 = indicators['ema_21']
                    ema_55 = indicators['ema_55']
                    current_price = signal_data['price']

                    if current_price > ema_13 and current_price > ema_21 and current_price > ema_55:
                        message += f"   └─ EMA Trend: Pozitif 📈\n"
                    elif current_price < ema_13 and current_price < ema_21 and current_price < ema_55:
                        message += f"   └─ EMA Trend: Negatif 📉\n"
                    else:
                        message += f"   └─ EMA Trend: Nötr ➡️\n"

                # WaveTrend bilgisi
                if 'wt1' in indicators and 'wt2' in indicators:
                    wt1 = indicators['wt1']
                    wt2 = indicators['wt2']
                    wt_cross_up = indicators.get('wt_cross_up', False)
                    wt_cross_down = indicators.get('wt_cross_down', False)

                    # Cross durumu ve sinyal
                    wt_status = ""
                    if wt_cross_down and wt2 > 60:
                        # 60 üstünde cross down = SELL
                        wt_status = " 🔴 CROSS DOWN - SELL!"
                    elif wt_cross_up and wt2 < -60:
                        # -60 altında cross up = BUY
                        wt_status = " 🟢 CROSS UP - BUY!"
                    elif wt_cross_up:
                        wt_status = " 🟢 CROSS UP"
                    elif wt_cross_down:
                        wt_status = " 🔴 CROSS DOWN"

                    # WT1 seviye kontrolü
                    if wt1 > 60:
                        wt_level = " (Aşırı Alım)"
                    elif wt1 < -60:
                        wt_level = " (Aşırı Satım)"
                    else:
                        wt_level = ""

                    message += f"   └─ WT: {wt1:.1f} / {wt2:.1f}{wt_status}{wt_level}\n"

                if 'rsi' in indicators and 'rsi_signal' in indicators:
                    rsi_val = indicators['rsi']
                    rsi_status = ""
                    if rsi_val < 15:
                        rsi_status = " (🟢 BUY için uygun)"
                    elif rsi_val > 85:
                        rsi_status = " (🔴 SELL için uygun)"
                    message += f"   └─ RSI: {rsi_val:.1f}{rsi_status}\n"

                # DMI bilgisi
                if 'plus_di' in indicators and 'minus_di' in indicators and 'adx' in indicators:
                    plus_di = indicators['plus_di']
                    minus_di = indicators['minus_di']
                    adx = indicators['adx']
                    message += f"   └─ DMI: +DI {plus_di:.1f} | -DI {minus_di:.1f} | ADX {adx:.1f}\n"

        await self.notifier.send_message(message)
        logger.info(f"Short-term message sent: {len(signals)} signals detected")

    async def _send_long_term_batch_message(self, results: Dict):
        first_active_result = next((r for r in results.values() if r is not None), None)
        if not first_active_result:
            logger.warning("No active results in long-term batch, skipping message")
            return
        symbol = first_active_result['symbol']
        price = first_active_result['price']
        message = self._long_builder.build(symbol, price, results, self.tracker)
        if message:
            await self.notifier.send_message(message)
            logger.info("Long-term batch message sent")

    async def _send_long_term_message(self, signals: Dict):
        """Uzun vadeli (4h) analiz mesajı - GOLD"""
        timeframe_info = {
            "4h": {"emoji": "�", "name": "4 Saat"}
        }

        first_signal = list(signals.values())[0]
        symbol = first_signal['symbol']
        price = first_signal['price']

        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)

        # ÖZEL FORMAT - Dikkat çekici GOLD mesajı
        message = "🥇"*10 + "\n"
        message += f"*⚡ GOLD UZUN VADELİ SİNYAL ⚡*\n"
        message += "🥇"*10 + "\n\n"
        message += f"📊 Sembol: *{symbol}*\n"
        message += f"� Fiyat: *${price:.2f}*\n"
        message += f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        # 4h timeframe göster
        long_timeframes = ["4h"]
        for timeframe in long_timeframes:
            tf_info = timeframe_info.get(timeframe)
            if not tf_info:
                continue

            if timeframe in signals:
                signal_data = signals[timeframe]
                signal_type = signal_data['signal']
                indicators = signal_data['indicators']

                if signal_type == "BUY":
                    message += f"{tf_info['emoji']} *{tf_info['name']}*\n"
                    message += f"   🟢 *UZUN VADELİ LONG* 🟢\n"
                elif signal_type == "SELL":
                    message += f"{tf_info['emoji']} *{tf_info['name']}*\n"
                    message += f"   🔴 *UZUN VADELİ SHORT* 🔴\n"

                # CMO değeri
                cmo = indicators.get('cmo')
                if cmo is not None:
                    message += f"   └─ CMO(13): {cmo:.2f}\n"
                
                # Stochastic değerleri
                stoch_k = indicators.get('stoch_k')
                stoch_d = indicators.get('stoch_d')
                if stoch_k is not None and stoch_d is not None:
                    message += f"   └─ Stoch(9,3,3): K={stoch_k:.2f} D={stoch_d:.2f}\n"
                
                # RSI değeri
                rsi = indicators.get('rsi')
                if rsi is not None:
                    message += f"   └─ RSI(4): {rsi:.2f}\n"
                
                # MACD değerleri
                macd = indicators.get('macd')
                macd_signal = indicators.get('macd_signal')
                macd_histogram = indicators.get('macd_histogram')
                if macd is not None and macd_signal is not None:
                    message += f"   └─ MACD(8,13,8): {macd:.4f} / {macd_signal:.4f}\n"
                    if macd_histogram is not None:
                        hist_symbol = "📈" if macd_histogram > 0 else "📉"
                        message += f"   └─ Histogram: {macd_histogram:.4f} {hist_symbol}\n"
                
                # Stochastic RSI değerleri
                stoch_rsi_k = indicators.get('stoch_rsi_k')
                stoch_rsi_d = indicators.get('stoch_rsi_d')
                if stoch_rsi_k is not None and stoch_rsi_d is not None:
                    message += f"   └─ StochRSI(5,8,3,3): K={stoch_rsi_k:.2f} D={stoch_rsi_d:.2f}\n"

                # EMA Trend bilgisi
                if 'ema_13' in indicators and 'ema_21' in indicators and 'ema_55' in indicators:
                    ema_13 = indicators['ema_13']
                    ema_21 = indicators['ema_21']
                    ema_55 = indicators['ema_55']
                    current_price = signal_data['price']

                    if current_price > ema_13 and current_price > ema_21 and current_price > ema_55:
                        message += f"   └─ EMA Trend: Pozitif 📈\n"
                    elif current_price < ema_13 and current_price < ema_21 and current_price < ema_55:
                        message += f"   └─ EMA Trend: Negatif 📉\n"
                    else:
                        message += f"   └─ EMA Trend: Nötr ➡️\n"

                # WaveTrend bilgisi
                if 'wt1' in indicators and 'wt2' in indicators:
                    wt1 = indicators['wt1']
                    wt2 = indicators['wt2']
                    wt_cross_up = indicators.get('wt_cross_up', False)
                    wt_cross_down = indicators.get('wt_cross_down', False)

                    # Cross durumu ve sinyal
                    wt_status = ""
                    if wt_cross_down and wt2 > 60:
                        # 60 üstünde cross down = SELL
                        wt_status = " 🔴 CROSS DOWN - SELL!"
                    elif wt_cross_up and wt2 < -60:
                        # -60 altında cross up = BUY
                        wt_status = " 🟢 CROSS UP - BUY!"
                    elif wt_cross_up:
                        wt_status = " 🟢 CROSS UP"
                    elif wt_cross_down:
                        wt_status = " 🔴 CROSS DOWN"

                    # WT1 seviye kontrolü
                    if wt1 > 60:
                        wt_level = " (Aşırı Alım)"
                    elif wt1 < -60:
                        wt_level = " (Aşırı Satım)"
                    else:
                        wt_level = ""

                    message += f"   └─ WT: {wt1:.1f} / {wt2:.1f}{wt_status}{wt_level}\n"

                if 'rsi' in indicators and 'rsi_signal' in indicators:
                    rsi_val = indicators['rsi']
                    rsi_status = ""
                    if rsi_val < 15:
                        rsi_status = " (🟢 BUY için uygun)"
                    elif rsi_val > 85:
                        rsi_status = " (🔴 SELL için uygun)"
                    message += f"   └─ RSI: {rsi_val:.1f}{rsi_status}\n"

                # DMI bilgisi
                if 'plus_di' in indicators and 'minus_di' in indicators and 'adx' in indicators:
                    plus_di = indicators['plus_di']
                    minus_di = indicators['minus_di']
                    adx = indicators['adx']
                    message += f"   └─ DMI: +DI {plus_di:.1f} | -DI {minus_di:.1f} | ADX {adx:.1f}\n"

        message += "\n💃💃💃 " + "="*30 + " 💃💃💃"

        await self.notifier.send_message(message)
        logger.info(f"Long-term message sent: {len(signals)} signals detected")

    def _format_time_ago(self, timestamp: int) -> str:
        """Zamanı 'X saat önce' formatına çevir"""
        now = int(time.time())
        diff = now - timestamp

        if diff < 3600:
            minutes = max(1, diff // 60)
            return f"{minutes} dk önce"
        elif diff < 86400:
            hours = diff // 3600
            return f"{hours} saat önce"
        else:
            days = diff // 86400
            return f"{days} gün önce"

    async def _send_neutral_message(self, results: Dict, is_long_term: bool = False):
        """NEUTRAL sinyal durumunda test mesajı gönder (mum kapanış testi için)

        Args:
            results: Timeframe sonuçları (result_dict or None)
            is_long_term: Uzun vadeli mi (4h) yoksa kısa vadeli mi (5m, 15m, 1h)
        """
        if is_long_term:
            timeframes = ["4h"]
            timeframe_info = {
                "4h": {"emoji": "📈", "name": "4 Saat"},

            }
            title = "UZUN VADELİ"
        else:
            timeframes = ["15m", "1h"]
            timeframe_info = {
                "15m": {"emoji": "🔥", "name": "15 Dakika"},
                "1h": {"emoji": "⏰", "name": "1 Saat"}
            }
            title = "KISA VADELİ"

        # Fiyat bilgisi için aktif result al
        first_active_result = next((r for r in results.values() if r is not None), None)
        if not first_active_result:
            logger.warning("No active results for neutral message")
            return

        symbol = first_active_result['symbol']
        price = first_active_result['price']

        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)

        message = f"⚪ *TEST: {title} NEUTRAL Analiz*\n"
        message += f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n"
        message += f"💰 Fiyat: ${price:.4f}\n\n"

        # Her timeframe için mum kapanış bilgisi
        for timeframe in timeframes:
            tf_info = timeframe_info[timeframe]
            result = results.get(timeframe)

            if result:
                message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ MUM KAPANDI - NEUTRAL\n"
            else:
                message += f"{tf_info['emoji']} {tf_info['name']}: Mum kapanmadı\n"

        message += f"\n⚠️ Test mesajı - Mum kapanış kontrolü"

        await self.notifier.send_message(message)
        logger.info(f"NEUTRAL test message sent for {title}")

    async def _send_insufficient_data_message(self, timeframe: str, data_count: int):
        """Yetersiz veri durumu için uyarı mesajı"""
        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)

        min_required = MIN_KLINES_PER_TIMEFRAME.get(timeframe, MIN_KLINES)

        message = (
            f"⚠️ *{timeframe} Analiz Uyarısı*\n"
            f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n\n"
            f"Yetersiz veri: {data_count} mum\n"
            f"Gerekli: {min_required} mum\n\n"
            f"{self.symbol} {timeframe} grafiği için henüz yeterli geçmiş veri yok. "
            f"Bot çalışmaya devam ediyor, veri biriktikçe analiz başlayacak."
        )

        await self.notifier.send_message(message)
        logger.warning(f"{timeframe} insufficient data message sent")