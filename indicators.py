"""
İndikatör Sınıfları
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class IIndicator(ABC):
    """İndikatör interface - Tüm indikatörler bunu implement etmeli"""

    @abstractmethod
    def calculate(self, klines: List[List]) -> List[float]:
        """İndikatör değerlerini hesapla"""
        pass


class ChandeMomentumOscillator(IIndicator):
    """Chande Momentum Oscillator (CMO)
    
    CMO, fiyat momentumunu ölçer ve -100 ile +100 arasında değer alır.
    Formül: CMO = 100 * ((Sum(Up) - Sum(Down)) / (Sum(Up) + Sum(Down)))
    
    Yorumlama:
    - CMO > +50: Güçlü yukarı momentum (overbought bölgesi)
    - CMO > 0: Pozitif momentum (boğa)
    - CMO < 0: Negatif momentum (ayı)
    - CMO < -50: Güçlü aşağı momentum (oversold bölgesi)
    """
    
    def __init__(self, length: int = 14, use_low: bool = True):
        self.length = length
        self.use_low = use_low
    
    def calculate(self, klines: List[List]) -> Dict[str, List]:
        """CMO değerlerini hesapla
        
        Returns:
            Dict with 'cmo' key containing CMO values
        """
        n = len(klines)
        cmo_values = [None] * n
        
        if n < self.length + 1:
            return {"cmo": cmo_values}
        
        # use_low=True ise low fiyatlarını, False ise close fiyatlarını kullan
        if self.use_low:
            prices = [float(k[3]) for k in klines]  # Low fiyatları (index 3)
        else:
            prices = [float(k[4]) for k in klines]  # Close fiyatları (index 4)
        
        for i in range(self.length, n):
            sum_up = 0.0
            sum_down = 0.0
            
            for j in range(i - self.length + 1, i + 1):
                if j > 0:  # İlk mum için önceki mum yok
                    change = prices[j] - prices[j - 1]
                    if change > 0:
                        sum_up += change
                    elif change < 0:
                        sum_down += abs(change)
            
            total = sum_up + sum_down
            if total != 0:
                cmo_values[i] = 100 * ((sum_up - sum_down) / total)
            else:
                cmo_values[i] = 0.0
        
        return {"cmo": cmo_values}


class StochasticOscillator(IIndicator):
    """Stochastic Oscillator (Stokastik)
    
    Stokastik, fiyatın belirli bir periyottaki high-low aralığındaki konumunu gösterir.
    %K ve %D olmak üzere iki çizgi vardır.
    
    Formül:
    - %K = 100 * ((Close - Lowest Low) / (Highest High - Lowest Low))
    - %D = %K'nın smooth_d periyotlu basit ortalaması
    
    Yorumlama:
    - %K > 80: Aşırı alım bölgesi
    - %K < 20: Aşırı satım bölgesi
    - %K crosses above %D: Alım sinyali
    - %K crosses below %D: Satım sinyali
    """
    
    def __init__(self, period_k: int = 9, smooth_k: int = 3, smooth_d: int = 3):
        """
        Args:
            period_k: %K periyodu (genellikle 14 veya 9)
            smooth_k: %K'yı smooth etmek için kullanılan periyot
            smooth_d: %D'yi hesaplamak için %K'nın smooth periyodu
        """
        self.period_k = period_k
        self.smooth_k = smooth_k
        self.smooth_d = smooth_d
    
    def calculate(self, klines: List[List]) -> Dict[str, List]:
        """Stochastic değerlerini hesapla
        
        Returns:
            Dict with 'stoch_k' and 'stoch_d' keys containing Stochastic values
        """
        n = len(klines)
        stoch_k_raw = [None] * n
        stoch_k_smooth = [None] * n
        stoch_d = [None] * n
        
        if n < self.period_k:
            return {"stoch_k": stoch_k_smooth, "stoch_d": stoch_d}
        
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        closes = [float(k[4]) for k in klines]
        
        # 1. Önce raw %K hesapla
        for i in range(self.period_k - 1, n):
            period_high = max(highs[i - self.period_k + 1:i + 1])
            period_low = min(lows[i - self.period_k + 1:i + 1])
            
            if period_high - period_low != 0:
                stoch_k_raw[i] = 100 * ((closes[i] - period_low) / (period_high - period_low))
            else:
                stoch_k_raw[i] = 50.0
        
        # 2. %K'yı smooth et (smooth_k periyotlu SMA)
        for i in range(self.period_k + self.smooth_k - 2, n):
            valid_k = [stoch_k_raw[j] for j in range(i - self.smooth_k + 1, i + 1) if stoch_k_raw[j] is not None]
            if len(valid_k) == self.smooth_k:
                stoch_k_smooth[i] = sum(valid_k) / self.smooth_k
        
        # 3. %D hesapla (%K'nın smooth_d periyotlu SMA'sı)
        for i in range(self.period_k + self.smooth_k + self.smooth_d - 3, n):
            valid_k = [stoch_k_smooth[j] for j in range(i - self.smooth_d + 1, i + 1) if stoch_k_smooth[j] is not None]
            if len(valid_k) == self.smooth_d:
                stoch_d[i] = sum(valid_k) / self.smooth_d
        
        return {"stoch_k": stoch_k_smooth, "stoch_d": stoch_d}


class RelativeStrengthIndex(IIndicator):
    """Relative Strength Index (RSI) - Standard
    
    RSI, fiyat momentumunu ölçer ve 0 ile 100 arasında değer alır.
    
    Formül:
    1. Price changes'i hesapla
    2. Gains (yukarı hareketler) ve Losses (aşağı hareketler) ayır
    3. Average Gain ve Average Loss hesapla (basit ortalama)
    4. RS = Average Gain / Average Loss
    5. RSI = 100 - (100 / (1 + RS))
    
    Yorumlama:
    - RSI > 70: Aşırı alım bölgesi
    - RSI < 30: Aşırı satım bölgesi
    - RSI > 85: Çok güçlü aşırı alım
    - RSI < 15: Çok güçlü aşırı satım
    """
    
    def __init__(self, length: int = 14):
        """
        Args:
            length: RSI hesaplama periyodu
        """
        self.length = length
    
    def calculate(self, klines: List[List]) -> Dict[str, List]:
        """RSI değerlerini hesapla (Standart RSI - Basit Ortalama)
        
        Returns:
            Dict with 'rsi' key containing RSI values
        """
        n = len(klines)
        rsi_values = [None] * n
        
        if n < self.length + 1:
            return {"rsi": rsi_values}
        
        closes = [float(k[4]) for k in klines]
        
        # RSI hesaplama için rolling window kullan
        for i in range(self.length, n):
            # Son length+1 mumu al (price changes için)
            window_closes = closes[i - self.length:i + 1]
            
            # Price changes
            gains = []
            losses = []
            for j in range(1, len(window_closes)):
                change = window_closes[j] - window_closes[j - 1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            # Average gain/loss (basit ortalama)
            avg_gain = sum(gains) / self.length
            avg_loss = sum(losses) / self.length
            
            # RSI hesapla
            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100 - (100 / (1 + rs))
        
        return {"rsi": rsi_values}


class MACD(IIndicator):
    """MACD (Moving Average Convergence Divergence)
    
    MACD, iki hareketli ortalamanın farkını izleyerek trend ve momentum gösterir.
    
    Bileşenler:
    1. MACD Line: Fast EMA - Slow EMA
    2. Signal Line: MACD Line'ın EMA'sı
    3. Histogram: MACD Line - Signal Line
    
    Formül:
    - MACD = EMA(fast) - EMA(slow)
    - Signal = EMA(MACD, signal_length)
    - Histogram = MACD - Signal
    
    Yorumlama:
    - MACD > Signal: Yükseliş trendi (BUY sinyali)
    - MACD < Signal: Düşüş trendi (SELL sinyali)
    - Histogram > 0: Pozitif momentum
    - Histogram < 0: Negatif momentum
    - Zero-line cross: Trend değişimi
    """
    
    def __init__(self, fast_length: int = 12, slow_length: int = 26, signal_length: int = 9):
        """
        Args:
            fast_length: Hızlı EMA periyodu
            slow_length: Yavaş EMA periyodu
            signal_length: Sinyal hattı EMA periyodu
        """
        self.fast_length = fast_length
        self.slow_length = slow_length
        self.signal_length = signal_length
    
    def _calculate_ema(self, data: List[float], period: int) -> List[float]:
        """EMA hesapla"""
        ema_values = [None] * len(data)
        
        if len(data) < period:
            return ema_values
        
        # İlk EMA değeri SMA olarak başlar
        sma = sum(data[:period]) / period
        ema_values[period - 1] = sma
        
        # Smoothing faktörü
        multiplier = 2 / (period + 1)
        
        # Sonraki EMA değerleri
        for i in range(period, len(data)):
            ema_values[i] = (data[i] - ema_values[i - 1]) * multiplier + ema_values[i - 1]
        
        return ema_values
    
    def calculate(self, klines: List[List]) -> Dict[str, List]:
        """MACD değerlerini hesapla
        
        Returns:
            Dict with 'macd', 'signal', 'histogram' keys
        """
        n = len(klines)
        macd_line = [None] * n
        signal_line = [None] * n
        histogram = [None] * n
        
        if n < self.slow_length:
            return {"macd": macd_line, "signal": signal_line, "histogram": histogram}
        
        # Close fiyatları (source)
        closes = [float(k[4]) for k in klines]
        
        # Fast ve Slow EMA'ları hesapla
        fast_ema = self._calculate_ema(closes, self.fast_length)
        slow_ema = self._calculate_ema(closes, self.slow_length)
        
        # MACD Line = Fast EMA - Slow EMA
        for i in range(n):
            if fast_ema[i] is not None and slow_ema[i] is not None:
                macd_line[i] = fast_ema[i] - slow_ema[i]
        
        # Signal Line = MACD Line'ın EMA'sı
        # None olmayan MACD değerlerini bul
        macd_values_for_signal = []
        macd_start_idx = None
        for i in range(n):
            if macd_line[i] is not None:
                if macd_start_idx is None:
                    macd_start_idx = i
                macd_values_for_signal.append(macd_line[i])
        
        if len(macd_values_for_signal) >= self.signal_length:
            signal_ema = self._calculate_ema(macd_values_for_signal, self.signal_length)
            
            # Signal değerlerini orijinal array'e yerleştir
            for i, sig_val in enumerate(signal_ema):
                if sig_val is not None:
                    signal_line[macd_start_idx + i] = sig_val
        
        # Histogram = MACD - Signal
        for i in range(n):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram[i] = macd_line[i] - signal_line[i]
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }


class StochasticRSI(IIndicator):
    """Stochastic RSI - RSI değerlerinin Stochastic'i
    
    Stochastic RSI, RSI indikatörünün stochastic formülüyle hesaplanmasıdır.
    Hem RSI'ın momentum bilgisini hem de Stochastic'in overbought/oversold
    özelliklerini birleştirir.
    
    Hesaplama:
    1. RSI değerlerini hesapla (length_rsi periyodu ile)
    2. RSI değerlerinin son length_stoch periyodu içindeki en yüksek/düşüğünü bul
    3. Stochastic formülü uygula: (RSI - RSI_min) / (RSI_max - RSI_min) * 100
    4. %K'yı smooth_k periyodu ile düzleştir
    5. %D = %K'nın smooth_d periyodu ile ortalaması
    
    Yorumlama:
    - Stoch RSI > 80: Aşırı alım bölgesi
    - Stoch RSI < 20: Aşırı satım bölgesi
    - %K > %D cross: BUY sinyali
    - %K < %D cross: SELL sinyali
    """
    
    def __init__(
        self, 
        length_rsi: int = 14, 
        length_stoch: int = 14, 
        smooth_k: int = 3, 
        smooth_d: int = 3
    ):
        """
        Args:
            length_rsi: RSI hesaplama periyodu
            length_stoch: Stochastic hesaplama periyodu (RSI değerleri üzerinde)
            smooth_k: %K smooth periyodu
            smooth_d: %D smooth periyodu
        """
        self.length_rsi = length_rsi
        self.length_stoch = length_stoch
        self.smooth_k = smooth_k
        self.smooth_d = smooth_d
        
        # RSI hesaplayıcı
        self.rsi_calculator = RelativeStrengthIndex(length=length_rsi)
    
    def _smooth_values(self, values: List[float], period: int) -> List[float]:
        """Değerleri SMA ile smooth et"""
        smoothed = [None] * len(values)
        
        for i in range(len(values)):
            if values[i] is None:
                continue
                
            # Son 'period' kadar valid değeri topla
            valid_values = []
            for j in range(max(0, i - period + 1), i + 1):
                if values[j] is not None:
                    valid_values.append(values[j])
            
            if len(valid_values) == period:
                smoothed[i] = sum(valid_values) / period
        
        return smoothed
    
    def calculate(self, klines: List[List]) -> Dict[str, List]:
        """Stochastic RSI değerlerini hesapla
        
        Returns:
            Dict with 'stoch_rsi_k', 'stoch_rsi_d' keys
        """
        n = len(klines)
        stoch_rsi_raw = [None] * n
        stoch_rsi_k = [None] * n
        stoch_rsi_d = [None] * n
        
        if n < self.length_rsi + self.length_stoch:
            return {
                "stoch_rsi_k": stoch_rsi_k,
                "stoch_rsi_d": stoch_rsi_d
            }
        
        # 1. RSI değerlerini hesapla
        rsi_result = self.rsi_calculator.calculate(klines)
        rsi_values = rsi_result["rsi"]
        
        # 2. RSI değerleri üzerinde Stochastic hesapla
        for i in range(self.length_stoch - 1, n):
            # Son length_stoch kadar RSI değerini al
            window_rsi = []
            for j in range(i - self.length_stoch + 1, i + 1):
                if rsi_values[j] is not None:
                    window_rsi.append(rsi_values[j])
            
            if len(window_rsi) == self.length_stoch:
                rsi_min = min(window_rsi)
                rsi_max = max(window_rsi)
                
                if rsi_max - rsi_min != 0:
                    # Stochastic formülü
                    stoch_rsi_raw[i] = ((rsi_values[i] - rsi_min) / (rsi_max - rsi_min)) * 100
                else:
                    stoch_rsi_raw[i] = 50.0  # Flat durumda ortada tut
        
        # 3. %K = Stoch RSI'ın smooth_k ile düzleştirilmesi
        stoch_rsi_k = self._smooth_values(stoch_rsi_raw, self.smooth_k)
        
        # 4. %D = %K'nın smooth_d ile düzleştirilmesi
        stoch_rsi_d = self._smooth_values(stoch_rsi_k, self.smooth_d)
        
        return {
            "stoch_rsi_k": stoch_rsi_k,
            "stoch_rsi_d": stoch_rsi_d
        }
