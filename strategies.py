"""
Strateji Sınıfları
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from config import (
    CMO_OVERBOUGHT, CMO_OVERSOLD, 
    STOCH_OVERBOUGHT, STOCH_OVERSOLD,
    RSI_OVERBOUGHT, RSI_OVERSOLD,
    STOCH_RSI_OVERBOUGHT, STOCH_RSI_OVERSOLD,
    WILLIAMS_R_OVERBOUGHT, WILLIAMS_R_OVERSOLD,
    FISHER_BULLISH_THRESHOLD, FISHER_BEARISH_THRESHOLD,
    MINIMUM_VOTE_THRESHOLD
)
from indicators import ChandeMomentumOscillator, StochasticOscillator, RelativeStrengthIndex, MACD, StochasticRSI, WilliamsR, FisherTransform, CoralTrend


class IStrategy(ABC):
    """Strateji interface - Tüm stratejiler bunu implement etmeli"""

    @abstractmethod
    def analyze(self, indicator_values: List[float], klines: List[List]) -> str:
        """Sinyal analizi yap: BUY, SELL veya NEUTRAL döner"""
        pass

class MajorityVoteStrategy(IStrategy):
    """8 İndikatör Majority Vote (Çoğunluk Oylaması) Stratejisi
    
    İndikatörler: CMO, Stochastic, RSI, MACD, Stochastic RSI, Williams %R, Fisher Transform, Coral Trend
    
    Sinyal mantığı:
    - Her indikatör için BUY/SELL/NEUTRAL oylaması yapılır
    - BUY: En az MINIMUM_VOTE_THRESHOLD (4) indikatör BUY sinyali verirse
    - SELL: En az MINIMUM_VOTE_THRESHOLD (4) indikatör SELL sinyali verirse  
    - NEUTRAL: Yukarıdaki koşullar sağlanmazsa
    
    Örnek: 5 BUY, 1 SELL, 2 NEUTRAL → BUY sinyali (5 ≥ 4)
    """

    def __init__(
        self, 
        cmo_indicator: ChandeMomentumOscillator,
        stoch_indicator: StochasticOscillator,
        rsi_indicator: RelativeStrengthIndex,
        macd_indicator: MACD,
        stoch_rsi_indicator: StochasticRSI,
        williams_r_indicator: WilliamsR,
        fisher_indicator: FisherTransform,
        coral_indicator: CoralTrend
    ):
        self.cmo = cmo_indicator
        self.stoch = stoch_indicator
        self.rsi = rsi_indicator
        self.macd = macd_indicator
        self.stoch_rsi = stoch_rsi_indicator
        self.williams_r = williams_r_indicator
        self.fisher = fisher_indicator
        self.coral = coral_indicator

    def _get_individual_signals(self, klines: List[List]) -> Dict[str, str]:
        """Her indikatör için bireysel BUY/SELL/NEUTRAL sinyali hesapla"""
        signals = {}
        curr_idx = -1
        
        # CMO Sinyali
        cmo_values = self.cmo.calculate(klines)
        if cmo_values["cmo"][curr_idx] is not None:
            cmo_val = cmo_values["cmo"][curr_idx]
            if cmo_val < CMO_OVERSOLD:
                signals["cmo"] = "BUY"
            elif cmo_val > CMO_OVERBOUGHT:
                signals["cmo"] = "SELL"
            else:
                signals["cmo"] = "NEUTRAL"
        else:
            signals["cmo"] = "NEUTRAL"
            
        # Stochastic Sinyali
        stoch_values = self.stoch.calculate(klines)
        if stoch_values["stoch_k"][curr_idx] is not None:
            stoch_k = stoch_values["stoch_k"][curr_idx]
            if stoch_k < STOCH_OVERSOLD:
                signals["stoch"] = "BUY"
            elif stoch_k > STOCH_OVERBOUGHT:
                signals["stoch"] = "SELL"
            else:
                signals["stoch"] = "NEUTRAL"
        else:
            signals["stoch"] = "NEUTRAL"
            
        # RSI Sinyali
        rsi_values = self.rsi.calculate(klines)
        if rsi_values["rsi"][curr_idx] is not None:
            rsi_val = rsi_values["rsi"][curr_idx]
            if rsi_val < RSI_OVERSOLD:
                signals["rsi"] = "BUY"
            elif rsi_val > RSI_OVERBOUGHT:
                signals["rsi"] = "SELL"
            else:
                signals["rsi"] = "NEUTRAL"
        else:
            signals["rsi"] = "NEUTRAL"
            
        # MACD Sinyali
        macd_values = self.macd.calculate(klines)
        if (macd_values["macd"][curr_idx] is not None and 
            macd_values["signal"][curr_idx] is not None):
            macd_line = macd_values["macd"][curr_idx]
            macd_signal = macd_values["signal"][curr_idx]
            if macd_line > macd_signal:
                signals["macd"] = "BUY"
            elif macd_line < macd_signal:
                signals["macd"] = "SELL"
            else:
                signals["macd"] = "NEUTRAL"
        else:
            signals["macd"] = "NEUTRAL"
            
        # Stochastic RSI Sinyali
        stoch_rsi_values = self.stoch_rsi.calculate(klines)
        if stoch_rsi_values["stoch_rsi_k"][curr_idx] is not None:
            stoch_rsi_k = stoch_rsi_values["stoch_rsi_k"][curr_idx]
            if stoch_rsi_k < STOCH_RSI_OVERSOLD:
                signals["stoch_rsi"] = "BUY"
            elif stoch_rsi_k > STOCH_RSI_OVERBOUGHT:
                signals["stoch_rsi"] = "SELL"
            else:
                signals["stoch_rsi"] = "NEUTRAL"
        else:
            signals["stoch_rsi"] = "NEUTRAL"
            
        # Williams %R Sinyali
        williams_r_values = self.williams_r.calculate(klines)
        if williams_r_values["williams_r"][curr_idx] is not None:
            williams_r_val = williams_r_values["williams_r"][curr_idx]
            if williams_r_val < WILLIAMS_R_OVERSOLD:
                signals["williams_r"] = "BUY"
            elif williams_r_val > WILLIAMS_R_OVERBOUGHT:
                signals["williams_r"] = "SELL"
            else:
                signals["williams_r"] = "NEUTRAL"
        else:
            signals["williams_r"] = "NEUTRAL"
            
        # Fisher Transform Sinyali
        fisher_values = self.fisher.calculate(klines)
        if (fisher_values["fisher"][curr_idx] is not None and 
            fisher_values["trigger"][curr_idx] is not None):
            fisher_val = fisher_values["fisher"][curr_idx]
            fisher_trigger = fisher_values["trigger"][curr_idx]
            if fisher_val > fisher_trigger and fisher_val > FISHER_BEARISH_THRESHOLD:
                signals["fisher"] = "BUY"
            elif fisher_val < fisher_trigger and fisher_val < FISHER_BULLISH_THRESHOLD:
                signals["fisher"] = "SELL"
            else:
                signals["fisher"] = "NEUTRAL"
        else:
            signals["fisher"] = "NEUTRAL"
            
        # Coral Trend Sinyali
        coral_values = self.coral.calculate(klines)
        if coral_values["trend"][curr_idx] is not None:
            coral_trend = coral_values["trend"][curr_idx]
            if coral_trend == 1:
                signals["coral"] = "BUY"
            elif coral_trend == -1:
                signals["coral"] = "SELL"
            else:
                signals["coral"] = "NEUTRAL"
        else:
            signals["coral"] = "NEUTRAL"
            
        return signals

    def analyze(self, indicator_values: List[float], klines: List[List]) -> Tuple[str, Dict[str, Any]]:
        # Tüm indikatörleri hesapla
        cmo_values = self.cmo.calculate(klines)
        stoch_values = self.stoch.calculate(klines)
        rsi_values = self.rsi.calculate(klines)
        macd_values = self.macd.calculate(klines)
        stoch_rsi_values = self.stoch_rsi.calculate(klines)
        williams_r_values = self.williams_r.calculate(klines)
        fisher_values = self.fisher.calculate(klines)
        coral_values = self.coral.calculate(klines)
        
        # Bireysel sinyalleri al
        individual_signals = self._get_individual_signals(klines)
        
        # Oyları say
        buy_votes = sum(1 for signal in individual_signals.values() if signal == "BUY")
        sell_votes = sum(1 for signal in individual_signals.values() if signal == "SELL")
        neutral_votes = sum(1 for signal in individual_signals.values() if signal == "NEUTRAL")
        
        # Majority vote ile karar ver
        if buy_votes >= MINIMUM_VOTE_THRESHOLD:
            final_signal = "BUY"
        elif sell_votes >= MINIMUM_VOTE_THRESHOLD:
            final_signal = "SELL"
        else:
            final_signal = "NEUTRAL"

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
                "stoch_rsi_d": stoch_rsi_values["stoch_rsi_d"],
                "williams_r": williams_r_values,
                "fisher": fisher_values["fisher"],
                "fisher_trigger": fisher_values["trigger"],
                "coral": coral_values["coral"],
                "coral_trend": coral_values["trend"]
            },
            "vote_breakdown": {
                "individual_signals": individual_signals,
                "buy_votes": buy_votes,
                "sell_votes": sell_votes,
                "neutral_votes": neutral_votes,
                "threshold": MINIMUM_VOTE_THRESHOLD,
                "final_signal": final_signal
            }
        }
        return final_signal, context