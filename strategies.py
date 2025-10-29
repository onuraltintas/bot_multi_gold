"""
Strateji Sınıfları
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from config import (
    CMO_OVERBOUGHT, CMO_OVERSOLD, 
    STOCH_OVERBOUGHT, STOCH_OVERSOLD,
    RSI_OVERBOUGHT, RSI_OVERSOLD,
    STOCH_RSI_OVERBOUGHT, STOCH_RSI_OVERSOLD
)
from indicators import ChandeMomentumOscillator, StochasticOscillator, RelativeStrengthIndex, MACD, StochasticRSI


class IStrategy(ABC):
    """Strateji interface - Tüm stratejiler bunu implement etmeli"""

    @abstractmethod
    def analyze(self, indicator_values: List[float], klines: List[List]) -> str:
        """Sinyal analizi yap: BUY, SELL veya NEUTRAL döner"""
        pass


class CMOStrategy(IStrategy):
    """CMO (Chande Momentum Oscillator) tabanlı basit strateji
    
    Sinyal mantığı:
    - CMO < -50: Aşırı satım bölgesi, potansiyel BUY
    - CMO > +50: Aşırı alım bölgesi, potansiyel SELL
    - Diğer durumlar: NEUTRAL
    """

    def __init__(self, cmo_indicator: ChandeMomentumOscillator):
        self.cmo = cmo_indicator

    def analyze(self, indicator_values: List[float], klines: List[List]) -> str:
        # indicator_values burada kullanılmıyor, direkt klines'dan hesaplıyoruz
        return "NEUTRAL"  # Basit placeholder

    def analyze_with_context(self, klines: List[List]) -> Tuple[str, Dict[str, Any]]:
        """CMO hesapla ve sinyal + context döndür"""
        cmo_values = self.cmo.calculate(klines)
        
        # Son kapanmış mumu kullan (aktif mum hariç)
        curr_idx = len(cmo_values["cmo"]) - 2
        
        if curr_idx < 0 or cmo_values["cmo"][curr_idx] is None:
            signal = "NEUTRAL"
        else:
            cmo_val = cmo_values["cmo"][curr_idx]
            
            if cmo_val < CMO_OVERSOLD:
                signal = "BUY"
            elif cmo_val > CMO_OVERBOUGHT:
                signal = "SELL"
            else:
                signal = "NEUTRAL"

        context: Dict[str, Any] = {
            "indicators": {
                "cmo": cmo_values
            }
        }
        return signal, context


class CMOStochasticStrategy(IStrategy):
    """CMO + Stochastic kombinasyonu ile sinyal üretimi
    
    Sinyal mantığı:
    - BUY: CMO < oversold VE Stochastic %K < 20
    - SELL: CMO > overbought VE Stochastic %K > 80
    - NEUTRAL: Diğer durumlar
    """

    def __init__(self, cmo_indicator: ChandeMomentumOscillator, stoch_indicator: StochasticOscillator):
        self.cmo = cmo_indicator
        self.stoch = stoch_indicator

    def analyze(self, indicator_values: List[float], klines: List[List]) -> str:
        return "NEUTRAL"  # Placeholder

    def analyze_with_context(self, klines: List[List]) -> Tuple[str, Dict[str, Any]]:
        """CMO ve Stochastic hesapla, sinyal + context döndür"""
        cmo_values = self.cmo.calculate(klines)
        stoch_values = self.stoch.calculate(klines)
        
        # Son kapanmış mumu kullan (aktif mum hariç)
        curr_idx = len(cmo_values["cmo"]) - 2
        
        signal = "NEUTRAL"
        
        if curr_idx < 0:
            pass
        elif cmo_values["cmo"][curr_idx] is None or stoch_values["stoch_k"][curr_idx] is None:
            pass
        else:
            cmo_val = cmo_values["cmo"][curr_idx]
            stoch_k = stoch_values["stoch_k"][curr_idx]
            stoch_d = stoch_values["stoch_d"][curr_idx]
            
            # BUY sinyali: Hem CMO hem Stochastic oversold
            if cmo_val < CMO_OVERSOLD and stoch_k < STOCH_OVERSOLD:
                signal = "BUY"
            # SELL sinyali: Hem CMO hem Stochastic overbought
            elif cmo_val > CMO_OVERBOUGHT and stoch_k > STOCH_OVERBOUGHT:
                signal = "SELL"

        context: Dict[str, Any] = {
            "indicators": {
                "cmo": cmo_values,
                "stoch_k": stoch_values["stoch_k"],
                "stoch_d": stoch_values["stoch_d"]
            }
        }
        return signal, context


class CMOStochasticRSIStrategy(IStrategy):
    """CMO + Stochastic + RSI tabanlı üçlü onaylı strateji
    
    Sinyal mantığı:
    - BUY: CMO < oversold VE Stoch K < oversold VE RSI < oversold
    - SELL: CMO > overbought VE Stoch K > overbought VE RSI > overbought
    - Üç indikatör de aynı yönde sinyal verdiğinde işlem yapılır
    """

    def __init__(
        self, 
        cmo_indicator: ChandeMomentumOscillator,
        stoch_indicator: StochasticOscillator,
        rsi_indicator: RelativeStrengthIndex
    ):
        self.cmo = cmo_indicator
        self.stoch = stoch_indicator
        self.rsi = rsi_indicator

    def analyze(self, indicator_values: List[float], klines: List[List]) -> Tuple[str, Dict[str, Any]]:
        signal = "NEUTRAL"
        
        # Tüm indikatörleri hesapla
        cmo_values = self.cmo.calculate(klines)
        stoch_values = self.stoch.calculate(klines)
        rsi_values = self.rsi.calculate(klines)
        
        curr_idx = -1
        
        # Eğer herhangi biri None ise sinyal yok
        if cmo_values["cmo"][curr_idx] is None or \
           stoch_values["stoch_k"][curr_idx] is None or \
           rsi_values["rsi"][curr_idx] is None:
            pass
        else:
            cmo_val = cmo_values["cmo"][curr_idx]
            stoch_k = stoch_values["stoch_k"][curr_idx]
            stoch_d = stoch_values["stoch_d"][curr_idx]
            rsi_val = rsi_values["rsi"][curr_idx]
            
            # BUY sinyali: Her üç indikatör de oversold
            if (cmo_val < CMO_OVERSOLD and 
                stoch_k < STOCH_OVERSOLD and 
                rsi_val < RSI_OVERSOLD):
                signal = "BUY"
            # SELL sinyali: Her üç indikatör de overbought
            elif (cmo_val > CMO_OVERBOUGHT and 
                  stoch_k > STOCH_OVERBOUGHT and 
                  rsi_val > RSI_OVERBOUGHT):
                signal = "SELL"

        context: Dict[str, Any] = {
            "indicators": {
                "cmo": cmo_values,
                "stoch_k": stoch_values["stoch_k"],
                "stoch_d": stoch_values["stoch_d"],
                "rsi": rsi_values
            }
        }
        return signal, context


class CMOStochasticRSIMACDStrategy(IStrategy):
    """CMO + Stochastic + RSI + MACD tabanlı dörtlü onaylı strateji
    
    Sinyal mantığı:
    - BUY: CMO < oversold VE Stoch K < oversold VE RSI < oversold VE MACD > Signal (bullish cross)
    - SELL: CMO > overbought VE Stoch K > overbought VE RSI > overbought VE MACD < Signal (bearish cross)
    - Dört indikatör de aynı yönde sinyal verdiğinde işlem yapılır
    """

    def __init__(
        self, 
        cmo_indicator: ChandeMomentumOscillator,
        stoch_indicator: StochasticOscillator,
        rsi_indicator: RelativeStrengthIndex,
        macd_indicator: MACD
    ):
        self.cmo = cmo_indicator
        self.stoch = stoch_indicator
        self.rsi = rsi_indicator
        self.macd = macd_indicator

    def analyze(self, indicator_values: List[float], klines: List[List]) -> Tuple[str, Dict[str, Any]]:
        signal = "NEUTRAL"
        
        # Tüm indikatörleri hesapla
        cmo_values = self.cmo.calculate(klines)
        stoch_values = self.stoch.calculate(klines)
        rsi_values = self.rsi.calculate(klines)
        macd_values = self.macd.calculate(klines)
        
        curr_idx = -1
        
        # Eğer herhangi biri None ise sinyal yok
        if (cmo_values["cmo"][curr_idx] is None or 
            stoch_values["stoch_k"][curr_idx] is None or 
            rsi_values["rsi"][curr_idx] is None or
            macd_values["macd"][curr_idx] is None or
            macd_values["signal"][curr_idx] is None):
            pass
        else:
            cmo_val = cmo_values["cmo"][curr_idx]
            stoch_k = stoch_values["stoch_k"][curr_idx]
            stoch_d = stoch_values["stoch_d"][curr_idx]
            rsi_val = rsi_values["rsi"][curr_idx]
            macd_line = macd_values["macd"][curr_idx]
            macd_signal = macd_values["signal"][curr_idx]
            macd_histogram = macd_values["histogram"][curr_idx]
            
            # BUY sinyali: Tüm indikatörler oversold + MACD bullish
            if (cmo_val < CMO_OVERSOLD and 
                stoch_k < STOCH_OVERSOLD and 
                rsi_val < RSI_OVERSOLD and
                macd_line > macd_signal):  # MACD üstte (bullish)
                signal = "BUY"
            # SELL sinyali: Tüm indikatörler overbought + MACD bearish
            elif (cmo_val > CMO_OVERBOUGHT and 
                  stoch_k > STOCH_OVERBOUGHT and 
                  rsi_val > RSI_OVERBOUGHT and
                  macd_line < macd_signal):  # MACD altta (bearish)
                signal = "SELL"

        context: Dict[str, Any] = {
            "indicators": {
                "cmo": cmo_values,
                "stoch_k": stoch_values["stoch_k"],
                "stoch_d": stoch_values["stoch_d"],
                "rsi": rsi_values,
                "macd": macd_values["macd"],
                "macd_signal": macd_values["signal"],
                "macd_histogram": macd_values["histogram"]
            }
        }
        return signal, context


class AllIndicatorsStrategy(IStrategy):
    """CMO + Stochastic + RSI + MACD + Stochastic RSI - Beşli kombinasyon
    
    Sinyal mantığı:
    - BUY: CMO < oversold VE Stoch K < oversold VE RSI < oversold VE 
           MACD > Signal VE Stoch RSI K < oversold
    - SELL: CMO > overbought VE Stoch K > overbought VE RSI > overbought VE 
            MACD < Signal VE Stoch RSI K > overbought
    - Tüm indikatörler aynı yönde sinyal verdiğinde işlem yapılır
    """

    def __init__(
        self, 
        cmo_indicator: ChandeMomentumOscillator,
        stoch_indicator: StochasticOscillator,
        rsi_indicator: RelativeStrengthIndex,
        macd_indicator: MACD,
        stoch_rsi_indicator: StochasticRSI
    ):
        self.cmo = cmo_indicator
        self.stoch = stoch_indicator
        self.rsi = rsi_indicator
        self.macd = macd_indicator
        self.stoch_rsi = stoch_rsi_indicator

    def analyze(self, indicator_values: List[float], klines: List[List]) -> Tuple[str, Dict[str, Any]]:
        signal = "NEUTRAL"
        
        # Tüm indikatörleri hesapla
        cmo_values = self.cmo.calculate(klines)
        stoch_values = self.stoch.calculate(klines)
        rsi_values = self.rsi.calculate(klines)
        macd_values = self.macd.calculate(klines)
        stoch_rsi_values = self.stoch_rsi.calculate(klines)
        
        curr_idx = -1
        
        # Eğer herhangi biri None ise sinyal yok
        if (cmo_values["cmo"][curr_idx] is None or 
            stoch_values["stoch_k"][curr_idx] is None or 
            rsi_values["rsi"][curr_idx] is None or
            macd_values["macd"][curr_idx] is None or
            macd_values["signal"][curr_idx] is None or
            stoch_rsi_values["stoch_rsi_k"][curr_idx] is None):
            pass
        else:
            cmo_val = cmo_values["cmo"][curr_idx]
            stoch_k = stoch_values["stoch_k"][curr_idx]
            stoch_d = stoch_values["stoch_d"][curr_idx]
            rsi_val = rsi_values["rsi"][curr_idx]
            macd_line = macd_values["macd"][curr_idx]
            macd_signal = macd_values["signal"][curr_idx]
            macd_histogram = macd_values["histogram"][curr_idx]
            stoch_rsi_k = stoch_rsi_values["stoch_rsi_k"][curr_idx]
            stoch_rsi_d = stoch_rsi_values["stoch_rsi_d"][curr_idx]
            
            # BUY sinyali: Tüm indikatörler oversold/bullish
            if (cmo_val < CMO_OVERSOLD and 
                stoch_k < STOCH_OVERSOLD and 
                rsi_val < RSI_OVERSOLD and
                macd_line > macd_signal and
                stoch_rsi_k < STOCH_RSI_OVERSOLD):
                signal = "BUY"
            # SELL sinyali: Tüm indikatörler overbought/bearish
            elif (cmo_val > CMO_OVERBOUGHT and 
                  stoch_k > STOCH_OVERBOUGHT and 
                  rsi_val > RSI_OVERBOUGHT and
                  macd_line < macd_signal and
                  stoch_rsi_k > STOCH_RSI_OVERBOUGHT):
                signal = "SELL"

        context: Dict[str, Any] = {
            "indicators": {
                "cmo": cmo_values,
                "stoch_k": stoch_values["stoch_k"],
                "stoch_d": stoch_values["stoch_d"],
                "rsi": rsi_values,
                "macd": macd_values["macd"],
                "macd_signal": macd_values["signal"],
                "macd_histogram": macd_values["histogram"],
                "stoch_rsi_k": stoch_rsi_values["stoch_rsi_k"],
                "stoch_rsi_d": stoch_rsi_values["stoch_rsi_d"]
            }
        }
        return signal, context