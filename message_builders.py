"""Mesaj oluşturucu sınıflar (Short / Long Term)

Davranış Koruma Notu:
- Çıktı formatı mevcut Analyzer içindeki mesajlarla aynı mantığı korur.
- Sadece string üretim sorumluluğu bu dosyaya taşınmıştır.
"""
from datetime import datetime
import pytz
import time
from typing import Dict, Optional



def _format_cmo(indicators: Dict) -> str:
    """Chande Momentum Oscillator formatlayıcı"""
    cmo = indicators.get('cmo')
    if cmo is None:
        return ""
    status = ""
    if cmo > 50:
        status = " 🔴 Aşırı Alım"
    elif cmo < -50:
        status = " 🟢 Aşırı Satım"
    elif cmo > 0:
        status = " ↗️ Pozitif Momentum"
    elif cmo < 0:
        status = " ↘️ Negatif Momentum"
    return f"CMO: {cmo:.1f}{status}"


def _format_williams_r(indicators: Dict) -> str:
    """Williams %R formatlayıcı"""
    williams_r = indicators.get('williams_r')
    if williams_r is None:
        return ""
    status = ""
    if williams_r > -20:
        status = " 🔴 Aşırı Alım"
    elif williams_r < -80:
        status = " 🟢 Aşırı Satım"
    elif williams_r > -50:
        status = " ↗️ Güçlü"
    elif williams_r < -50:
        status = " ↘️ Zayıf"
    return f"Williams %R: {williams_r:.1f}{status}"


def _format_fisher(indicators: Dict) -> str:
    """Fisher Transform formatlayıcı"""
    fisher = indicators.get('fisher')
    trigger = indicators.get('fisher_trigger')
    if fisher is None or trigger is None:
        return ""
    
    # Cross durumu
    cross_status = ""
    if fisher > trigger:
        if fisher > 1.5:
            cross_status = " 🟢 GÜÇLÜ BUY"
        else:
            cross_status = " ↗️ Bullish"
    elif fisher < trigger:
        if fisher < -1.5:
            cross_status = " 🔴 GÜÇLÜ SELL"
        else:
            cross_status = " ↘️ Bearish"
    
    # Extreme seviye uyarısı
    if abs(fisher) > 2.5:
        cross_status += " (⚠️ Extreme)"
    
    return f"Fisher: {fisher:.2f} / Trigger: {trigger:.2f}{cross_status}"


def _format_coral(indicators: Dict) -> str:
    """Coral Trend formatlayıcı"""
    coral = indicators.get('coral')
    trend = indicators.get('coral_trend')
    if coral is None or trend is None:
        return ""
    
    # Trend durumu
    if trend == 1:
        trend_status = " 🟢 Bullish Trend"
    elif trend == -1:
        trend_status = " 🔴 Bearish Trend"
    else:
        trend_status = " ⚪ Neutral"
    
    return f"Coral: {coral:.2f}{trend_status}"


def _format_vote_breakdown(indicators: Dict) -> str:
    """MajorityVoteStrategy için oylama detaylarını formatla"""
    vote_info = indicators.get('vote_breakdown')
    if not vote_info:
        return ""
    
    individual_signals = vote_info.get('individual_signals', {})
    buy_votes = vote_info.get('buy_votes', 0)
    sell_votes = vote_info.get('sell_votes', 0) 
    neutral_votes = vote_info.get('neutral_votes', 0)
    threshold = vote_info.get('threshold', 4)
    
    # Oylama özeti
    vote_summary = f"📊 Oylama: {buy_votes}🟢 {sell_votes}🔴 {neutral_votes}⚪ (Min: {threshold})"
    
    # Bireysel sinyaller (değerlerle birlikte, alt alta)
    signal_lines = []
    signal_emojis = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "⚪"}
    
    curr_idx = -1  # Son kapanmış mum
    
    # İndikatör sırası (görsel düzen için)
    indicator_order = ["cmo", "stoch", "rsi", "macd", "stoch_rsi", "williams_r", "fisher", "coral"]
    
    for indicator in indicator_order:
        if indicator not in individual_signals:
            continue
            
        signal = individual_signals[indicator]
        emoji = signal_emojis.get(signal, "❓")
        value_str = ""
        
        # Her indikatör için değer çek
        if indicator == "cmo" and indicators.get('cmo'):
            val = indicators['cmo']['cmo'][curr_idx] if indicators['cmo']['cmo'][curr_idx] is not None else 0
            value_str = f"{val:.1f}"
        elif indicator == "stoch" and indicators.get('stoch_k'):
            val = indicators['stoch_k'][curr_idx] if indicators['stoch_k'][curr_idx] is not None else 0
            value_str = f"{val:.1f}"
        elif indicator == "rsi" and indicators.get('rsi'):
            val = indicators['rsi']['rsi'][curr_idx] if indicators['rsi']['rsi'][curr_idx] is not None else 0
            value_str = f"{val:.1f}"
        elif indicator == "macd" and indicators.get('macd'):
            macd_val = indicators['macd'][curr_idx] if indicators['macd'][curr_idx] is not None else 0
            signal_val = indicators.get('macd_signal', [0])[curr_idx] if indicators.get('macd_signal', [0])[curr_idx] is not None else 0
            cross_symbol = ">" if macd_val > signal_val else "<"
            value_str = f"{macd_val:.3f} {cross_symbol} {signal_val:.3f}"
        elif indicator == "stoch_rsi" and indicators.get('stoch_rsi_k'):
            val = indicators['stoch_rsi_k'][curr_idx] if indicators['stoch_rsi_k'][curr_idx] is not None else 0
            value_str = f"{val:.1f}"
        elif indicator == "williams_r" and indicators.get('williams_r'):
            val = indicators['williams_r']['williams_r'][curr_idx] if indicators['williams_r']['williams_r'][curr_idx] is not None else 0
            value_str = f"{val:.1f}"
        elif indicator == "fisher" and indicators.get('fisher'):
            fisher_val = indicators['fisher'][curr_idx] if indicators['fisher'][curr_idx] is not None else 0
            trigger_val = indicators.get('fisher_trigger', [0])[curr_idx] if indicators.get('fisher_trigger', [0])[curr_idx] is not None else 0
            value_str = f"{fisher_val:.2f} / {trigger_val:.2f}"
        elif indicator == "coral" and indicators.get('coral_trend'):
            trend_val = indicators['coral_trend'][curr_idx] if indicators['coral_trend'][curr_idx] is not None else 0
            trend_text = "Bullish ↗️" if trend_val == 1 else "Bearish ↘️" if trend_val == -1 else "Neutral →"
            value_str = trend_text
        
        # İndikatör adı ve değer (hizalı format)
        indicator_names = {
            "cmo": "CMO", "stoch": "Stochastic", "rsi": "RSI", "macd": "MACD",
            "stoch_rsi": "Stoch RSI", "williams_r": "Williams %R", "fisher": "Fisher", "coral": "Coral Trend"
        }
        name = indicator_names.get(indicator, indicator.upper())
        signal_lines.append(f"   ├─ {emoji} {name:<12}: {value_str}")
    
    # Son satır için farklı karakter
    if signal_lines:
        signal_lines[-1] = signal_lines[-1].replace("├─", "└─")
    
    details_block = "\n".join(signal_lines)
    
    return f"{vote_summary}\n{details_block}"


def _format_time_ago(timestamp: int) -> str:
    now = int(time.time())
    diff = now - timestamp
    if diff < 3600:
        minutes = max(1, diff // 60)
        return f"{minutes} dk önce"
    if diff < 86400:
        hours = diff // 3600
        return f"{hours} saat önce"
    days = diff // 86400
    return f"{days} gün önce"


class ShortTermMessageBuilder:
    """1m, 5m, 15m & 1h batch mesajı oluşturur"""

    TIMEFRAME_INFO = {
        "1m": {"emoji": "⚡⚡", "name": "1 Dakika"},
        "5m": {"emoji": "⚡", "name": "5 Dakika"},
        "15m": {"emoji": "🔥", "name": "15 Dakika"},
        "1h": {"emoji": "⏰", "name": "1 Saat"}
    }

    def build(self, symbol: str, price: float, results: Dict, tracker) -> Optional[str]:
        # Aktif result yoksa mesaj üretme
        first_active = next((r for r in results.values() if r is not None), None)
        if not first_active:
            return None
        
        # NET BUY veya NET SELL sinyali var mı kontrol et (threshold'a ulaşmış olmalı)
        # final_signal BUY veya SELL olmalı, NEUTRAL değil
        has_real_signal = any(
            r and r['signal'] in ['BUY', 'SELL']
            for r in results.values() if r is not None
        )
        
        # Sadece NEUTRAL veya None varsa mesaj üretme
        if not has_real_signal:
            return None

        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)
        message = f"*🏆🏆🏆 ✨ Kısa Vade Analiz - {symbol} ✨ 🏆🏆🏆*\n"
        message += f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n"
        message += f"💰 Fiyat: ${price:.4f}\n\n"

        for timeframe in ["1m", "5m", "15m", "1h"]:
            tf_info = self.TIMEFRAME_INFO[timeframe]
            result = results.get(timeframe)
            
            # NEUTRAL olmayan sinyalleri göster
            if result and result['signal'] != "NEUTRAL":
                signal_type = result['signal']
                indicators = result['indicators']
                
                # Sadece BUY ve SELL sinyalleri göster
                if signal_type == "BUY":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🟢🟢 *BUY* 🟢🟢\n"
                elif signal_type == "SELL":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🔴🔴 *SELL* 🔴🔴\n"
                
                # Vote breakdown göster
                vote_line = _format_vote_breakdown(indicators)
                if vote_line:
                    message += f"   {vote_line}\n"
                else:
                    # Fallback: Sadece CMO göster
                    cmo_line = _format_cmo(indicators)
                    if cmo_line:
                        message += f"   └─ {cmo_line}\n"
            else:
                # Result yok veya NEUTRAL ise son sinyal bilgisini göster
                last_signal, last_ts = tracker.get_last_signal(symbol, timeframe)
                if last_signal != "NEUTRAL" and last_ts:
                    time_ago = _format_time_ago(last_ts)
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Son {'ALIM' if last_signal=='BUY' else 'SATIM'}: {time_ago}\n"
                else:
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Henüz analiz yapılmadı\n"
            if timeframe in ["5m", "15m"]:
                message += "\n"
        return message


class LongTermMessageBuilder:
    """4h batch mesajı oluşturur"""

    TIMEFRAME_INFO = {
        "4h": {"emoji": "📈", "name": "4 Saat"}
    }

    def build(self, symbol: str, price: float, results: Dict, tracker) -> Optional[str]:
        first_active = next((r for r in results.values() if r is not None), None)
        if not first_active:
            return None
        
        # NET BUY veya NET SELL sinyali var mı kontrol et (threshold'a ulaşmış olmalı)
        # final_signal BUY veya SELL olmalı, NEUTRAL değil
        has_real_signal = any(
            r and r['signal'] in ['BUY', 'SELL']
            for r in results.values() if r is not None
        )
        
        # Sadece NEUTRAL veya None varsa mesaj üretme
        if not has_real_signal:
            return None
        
        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)

        header = "🏆🏆🏆 " + "="*30 + " 🏆🏆🏆"
        message = f"{header}\n"
        message += f"*🥇🥇🥇 UZUN VADELİ ANALİZ - {symbol} 🥇🥇🥇*\n"
        message += f"{header}\n\n"
        message += f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n"
        message += f"💰 Fiyat: ${price:.4f}\n\n"

        for timeframe in ["4h"]:
            tf_info = self.TIMEFRAME_INFO[timeframe]
            result = results.get(timeframe)
            
            # NEUTRAL olmayan sinyalleri göster
            if result and result['signal'] != "NEUTRAL":
                signal_type = result['signal']
                indicators = result['indicators']
                
                # Sadece BUY ve SELL sinyalleri göster
                if signal_type == "BUY":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🟢🟢 *BUY* 🟢🟢\n"
                elif signal_type == "SELL":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🔴🔴 *SELL* 🔴🔴\n"
                
                # Vote breakdown göster
                vote_line = _format_vote_breakdown(indicators)
                if vote_line:
                    message += f"   {vote_line}\n"
                else:
                    # Fallback: Sadece CMO göster
                    cmo_line = _format_cmo(indicators)
                    if cmo_line:
                        message += f"   └─ {cmo_line}\n"
            else:
                # Gerçekten analiz yapılmamış durumlar
                last_signal, last_ts = tracker.get_last_signal(symbol, timeframe)
                if last_signal != "NEUTRAL" and last_ts:
                    time_ago = _format_time_ago(last_ts)
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Son {'ALIM' if last_signal=='BUY' else 'SATIM'}: {time_ago}\n"
                else:
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Henüz analiz yapılmadı\n"

        message += f"\n{header}"
        return message
