"""Mesaj oluşturucu sınıflar (Short / Long Term)

Davranış Koruma Notu:
- Çıktı formatı mevcut Analyzer içindeki mesajlarla aynı mantığı korur.
- Sadece string üretim sorumluluğu bu dosyaya taşınmıştır.
"""
from datetime import datetime
import pytz
import time
from typing import Dict, Optional
try:
    from config import (
        ADVANCED_BIAS_ENABLED,
        CCI_ZONE_EXTREME_POSITIVE,
        CCI_ZONE_POSITIVE,
        CCI_ZONE_MID_POSITIVE,
        CCI_ZONE_MID_NEGATIVE,
        CCI_ZONE_NEGATIVE,
        CCI_ZONE_EXTREME_NEGATIVE,
    )
except ImportError:  # fallback safety
    ADVANCED_BIAS_ENABLED = False
    # Sensible internal defaults if config import fails
    CCI_ZONE_EXTREME_POSITIVE = 200
    CCI_ZONE_POSITIVE = 100
    CCI_ZONE_MID_POSITIVE = 30
    CCI_ZONE_MID_NEGATIVE = -30
    CCI_ZONE_NEGATIVE = -100
    CCI_ZONE_EXTREME_NEGATIVE = -200


def _format_ema_trend(price: float, ema_13: float, ema_21: float, ema_55: float) -> str:
    if price > ema_13 and price > ema_21 and price > ema_55:
        return "Pozitif 📈"
    if price < ema_13 and price < ema_21 and price < ema_55:
        return "Negatif 📉"
    return "Nötr ➡️"


def _format_wavetrend(indicators: Dict) -> str:
    if 'wt1' not in indicators or 'wt2' not in indicators:
        return ""
    wt1 = indicators['wt1']
    wt2 = indicators['wt2']
    wt_cross_up = indicators.get('wt_cross_up', False)
    wt_cross_down = indicators.get('wt_cross_down', False)
    wt_status = ""
    if wt_cross_down and wt2 > 60:
        wt_status = " 🔴 CROSS DOWN - SELL!"
    elif wt_cross_up and wt2 < -60:
        wt_status = " 🟢 CROSS UP - BUY!"
    elif wt_cross_up:
        wt_status = " 🟢 CROSS UP"
    elif wt_cross_down:
        wt_status = " 🔴 CROSS DOWN"

    if wt1 > 60:
        wt_level = " (Aşırı Alım)"
    elif wt1 < -60:
        wt_level = " (Aşırı Satım)"
    else:
        wt_level = ""
    return f"WT: {wt1:.1f} / {wt2:.1f}{wt_status}{wt_level}"


def _format_rsi(indicators: Dict) -> str:
    rsi = indicators.get('rsi')
    if rsi is None:
        return ""
    status = ""
    if rsi < 15:
        status = " (🟢 BUY için uygun)"
    elif rsi > 85:
        status = " (🔴 SELL için uygun)"
    return f"RSI: {rsi:.1f}{status}"


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


def _format_dmi(indicators: Dict) -> str:
    if not all(k in indicators for k in ['plus_di', 'minus_di', 'adx']):
        return ""
    return f"DMI: +DI {indicators['plus_di']:.1f} | -DI {indicators['minus_di']:.1f} | ADX {indicators['adx']:.1f}"


def _cci_zone_comment(cci_value: float) -> str:
    """CCI değeri için kısa bölge/uyarı etiketi döner.

    Eşik mantığı:
      > +200  : Aşırı Pozitif (Agresif Pozitif Bölge)
      +100..200: Pozitif Bölge (Olası Dönüş Riski Artıyor)
      +30..+100: Ilımlı Pozitif
      -30..+30 : Nötr Konsolidasyon
      -100..-30: Ilımlı Negatif
      -200..-100: Negatif Bölge (Potansiyel Tepki Alanı)
      < -200  : Aşırı Negatif (Agresif Negatif Bölge)
    """
    c = cci_value
    if c > CCI_ZONE_EXTREME_POSITIVE:
        return "Aşırı Pozitif ⚠️"
    if c > CCI_ZONE_POSITIVE:
        return "Pozitif Bölge"
    if c > CCI_ZONE_MID_POSITIVE:
        return "Ilımlı Pozitif"
    if c >= CCI_ZONE_MID_NEGATIVE:
        return "Nötr"
    if c >= CCI_ZONE_NEGATIVE:
        return "Ilımlı Negatif"
    if c >= CCI_ZONE_EXTREME_NEGATIVE:
        return "Negatif Bölge 🎯"
    return "Aşırı Negatif ⚠️"


def _interpret_dmi(indicators: Dict) -> str:
    """ADX gücü ve DMI dominansı yorumlar.

    Eşikler (piyasa genel pratikleri + basitleştirilmiş):
      - ADX < 15: Zayıf trend
      - 15 ≤ ADX < 25: Oluşum / belirsiz
      - 25 ≤ ADX < 35: Orta güçte trend
      - 35 ≤ ADX < 50: Güçlü trend
      - ADX ≥ 50: Çok güçlü (yorulma riski)

    Dominans:
      - +DI -DI'dan en az 2 puan yüksekse: Boğa dominansı
      - -DI +DI'dan en az 2 puan yüksekse: Ayı dominansı
      - Aksi halde Kararsız
    """
    if not all(k in indicators for k in ['plus_di', 'minus_di', 'adx']):
        return ""
    plus_di = indicators['plus_di']
    minus_di = indicators['minus_di']
    adx = indicators['adx']

    # ADX güç etiketi
    if adx < 15:
        adx_tag = "Zayıf"
    elif adx < 25:
        adx_tag = "Oluşuyor"
    elif adx < 35:
        adx_tag = "Orta"
    elif adx < 50:
        adx_tag = "Güçlü"
    else:
        adx_tag = "Çok Güçlü ⚠️"

    # Dominans
    if plus_di - minus_di >= 2:
        dom = "Boğa"
    elif minus_di - plus_di >= 2:
        dom = "Ayı"
    else:
        dom = "Kararsız"

    return f"Trend: {adx_tag} | Dominans: {dom}"


def _compute_bias(signal: str, indicators: Dict) -> Optional[str]:
    """CCI sinyali + EMA trend + DMI dominansı üzerinden birleşik bias.
    Bu sadece yorumlayıcıdır; asıl sinyal CCI kalır.
    Dönüş: (emoji + kısa özet)
    """
    if signal not in ("BUY", "SELL"):
        return None
    # EMA trend
    ema_bias = None
    if {'ema_13','ema_21','ema_55'} <= indicators.keys():
        price = indicators.get('price_for_trend') or indicators.get('close') or indicators.get('price')
        # Fiyat bilgisi yoksa ema bias hesaplamayı atla
        ema_13, ema_21, ema_55 = indicators['ema_13'], indicators['ema_21'], indicators['ema_55']
        if price is not None:
            if price > ema_13 and price > ema_21 and price > ema_55:
                ema_bias = 'Boğa'
            elif price < ema_13 and price < ema_21 and price < ema_55:
                ema_bias = 'Ayı'
            else:
                ema_bias = 'Nötr'

    # DMI dominansı
    dmi_dom = None
    if all(k in indicators for k in ['plus_di','minus_di','adx']):
        plus_di = indicators['plus_di']
        minus_di = indicators['minus_di']
        if plus_di - minus_di >= 2:
            dmi_dom = 'Boğa'
        elif minus_di - plus_di >= 2:
            dmi_dom = 'Ayı'
        else:
            dmi_dom = 'Kararsız'

    votes = []
    # CCI sinyalinin yönü
    votes.append('Boğa' if signal == 'BUY' else 'Ayı')
    if ema_bias:
        votes.append(ema_bias)
    if dmi_dom:
        votes.append(dmi_dom)

    # Skorla: Boğa +1, Ayı -1, Kararsız 0, Nötr 0
    score = 0
    for v in votes:
        if v == 'Boğa':
            score += 1
        elif v == 'Ayı':
            score -= 1

    if score >= 2:
        summary = "Güçlü Boğa Bias"
        emoji = "🟢"
    elif score == 1:
        summary = "Hafif Boğa Bias"
        emoji = "🟢"
    elif score == 0:
        summary = "Karışık"
        emoji = "⚪"
    elif score == -1:
        summary = "Hafif Ayı Bias"
        emoji = "🔴"
    else:  # score <= -2
        summary = "Güçlü Ayı Bias"
        emoji = "🔴"

    detail = ",".join(votes)
    return f"{emoji} Birleşik Bias: {summary} ({detail})"


def _format_td_sequential(indicators: Dict) -> str:
    """TD Sequential değerlerini yorumla ve formatla.

    Returns:
        Boş string veya TD Sequential satırı
    """
    if 'td_up' not in indicators or 'td_down' not in indicators:
        return ""

    td_up = int(indicators.get('td_up', 0))
    td_down = int(indicators.get('td_down', 0))

    # TD Sequential 9 sinyalleri (en güçlü)
    if td_down == 9:
        return "TD Sequential: 🚀 LONG (9/9) - Momentum tükendi!"
    if td_up == 9:
        return "TD Sequential: ☂️ SHORT (9/9) - Momentum tükendi!"

    # TD Sequential 7-8 uyarıları
    if td_down == 8:
        return f"TD Sequential: ⚠️ ({td_down}/9) - 🚀 LONG yakın"
    if td_down == 7:
        return f"TD Sequential: ({td_down}/9) - 🚀 LONG uyarısı"

    if td_up == 8:
        return f"TD Sequential: ⚠️ ({td_up}/9) - ☂️ SHORT yakın"
    if td_up == 7:
        return f"TD Sequential: ({td_up}/9) - ☂️ SHORT uyarısı"

    # 1-6 arası sadece değeri göster
    if td_down > 0:
        return f"TD Sequential: ⬇️ ({td_down}/9) Bearish count"
    if td_up > 0:
        return f"TD Sequential: ⬆️ ({td_up}/9) Bullish count"

    return ""


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
    """15m & 1h batch mesajı oluşturur"""

    TIMEFRAME_INFO = {
        "15m": {"emoji": "🔥", "name": "15 Dakika"},
        "1h": {"emoji": "⏰", "name": "1 Saat"}
    }

    def build(self, symbol: str, price: float, results: Dict, tracker) -> Optional[str]:
        # Aktif result yoksa mesaj üretme
        first_active = next((r for r in results.values() if r is not None), None)
        if not first_active:
            return None

        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)
        message = f"*🚨 📊 Kısa Vade Analiz - {symbol} 📊 🚨*\n"
        message += f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n"
        message += f"💰 Fiyat: ${price:.4f}\n\n"

        for timeframe in ["15m", "1h"]:
            tf_info = self.TIMEFRAME_INFO[timeframe]
            result = results.get(timeframe)
            if result and result['signal'] != "NEUTRAL":
                signal_type = result['signal']
                indicators = result['indicators']
                if signal_type == "BUY":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🟢🟢 *BUY* 🟢🟢\n"
                elif signal_type == "SELL":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🔴🔴 *SELL* 🔴🔴\n"
                cmo_line = _format_cmo(indicators)
                if cmo_line:
                    message += f"   └─ {cmo_line}\n"
            else:
                last_signal, last_ts = tracker.get_last_signal(symbol, timeframe)
                if last_signal != "NEUTRAL" and last_ts:
                    time_ago = _format_time_ago(last_ts)
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Son {'ALIM' if last_signal=='BUY' else 'SATIM'}: {time_ago}\n"
                else:
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Henüz sinyal yok\n"
            if timeframe == "15m":
                message += "\n"
        return message


class LongTermMessageBuilder:
    """4h & 1d batch mesajı oluşturur"""

    TIMEFRAME_INFO = {
        "4h": {"emoji": "📈", "name": "4 Saat"},
        "1d": {"emoji": "🎯", "name": "1 Gün"}
    }

    def build(self, symbol: str, price: float, results: Dict, tracker) -> Optional[str]:
        first_active = next((r for r in results.values() if r is not None), None)
        if not first_active:
            return None
        turkey_tz = pytz.timezone('Europe/Istanbul')
        turkey_time = datetime.now(turkey_tz)

        header = "💃💃💃 " + "="*30 + " 💃💃💃"
        message = f"{header}\n"
        message += f"*🚨 UZUN VADELİ ANALİZ - {symbol} 🚨*\n"
        message += f"{header}\n\n"
        message += f"🕒 {turkey_time.strftime('%d.%m.%Y %H:%M:%S')} (TR)\n"
        message += f"💰 Fiyat: ${price:.4f}\n\n"

        for timeframe in ["4h", "1d"]:
            tf_info = self.TIMEFRAME_INFO[timeframe]
            result = results.get(timeframe)
            if result and result['signal'] != "NEUTRAL":
                signal_type = result['signal']
                indicators = result['indicators']
                if signal_type == "BUY":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🟢🟢 *BUY* 🟢🟢\n"
                elif signal_type == "SELL":
                    message += f"{tf_info['emoji']} {tf_info['name']}: 🔴🔴 *SELL* 🔴🔴\n"
                cmo_line = _format_cmo(indicators)
                if cmo_line:
                    message += f"   └─ {cmo_line}\n"
            else:
                last_signal, last_ts = tracker.get_last_signal(symbol, timeframe)
                if last_signal != "NEUTRAL" and last_ts:
                    time_ago = _format_time_ago(last_ts)
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Son {'ALIM' if last_signal=='BUY' else 'SATIM'}: {time_ago}\n"
                else:
                    message += f"{tf_info['emoji']} {tf_info['name']}: ⚪ Henüz sinyal yok\n"
            if timeframe == "4h":
                message += "\n"
        message += f"\n{header}"
        return message
