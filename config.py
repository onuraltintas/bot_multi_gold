"""
Konfigürasyon ve Sabitler
"""
import os
from dotenv import load_dotenv

load_dotenv('config.env')

# Telegram Konfigürasyonu
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Trading Konfigürasyonu
TARGET_SYMBOL = "XAU/USD"  # Forex Gold (Twelve Data format: XAU/USD)
TIMEFRAMES = ["5m", "15m", "1h", "4h"]  # 1m kaldırıldı

# Minimum mum sayısı
MIN_KLINES = 100

# Timeframe başına minimum mum sayısı
MIN_KLINES_PER_TIMEFRAME = {
    "5m": 100,
    "15m": 100,
    "1h": 100,
    "4h": 100    
}

# Chande Momentum Oscillator Parametreleri
CMO_LENGTH = 13
CMO_OVERBOUGHT = 62.01  # Sell sinyali (simetrik)
CMO_OVERSOLD = -62.01  # Buy sinyali

# Stochastic Oscillator Parametreleri
STOCH_PERIOD_K = 9  # %K periyodu
STOCH_SMOOTH_K = 3  # %K smooth periyodu
STOCH_SMOOTH_D = 3  # %D smooth periyodu
STOCH_OVERBOUGHT = 85  # Aşırı alım seviyesi
STOCH_OVERSOLD = 15  # Aşırı satım seviyesi

# RSI (Relative Strength Index) Parametreleri
RSI_LENGTH = 4  # RSI periyodu
RSI_OVERBOUGHT = 85  # Aşırı alım seviyesi (Sell sinyali)
RSI_OVERSOLD = 15  # Aşırı satım seviyesi (Buy sinyali)

# MACD (Moving Average Convergence Divergence) Parametreleri
MACD_FAST_LENGTH = 8  # Hızlı EMA periyodu
MACD_SLOW_LENGTH = 13  # Yavaş EMA periyodu
MACD_SIGNAL_LENGTH = 8  # Sinyal hattı periyodu
# Source: close (kapanış fiyatı kullanılacak)

# Stochastic RSI Parametreleri
STOCH_RSI_LENGTH_RSI = 5  # RSI hesaplama periyodu
STOCH_RSI_LENGTH_STOCH = 8  # Stochastic hesaplama periyodu
STOCH_RSI_SMOOTH_K = 3  # %K smooth periyodu
STOCH_RSI_SMOOTH_D = 3  # %D smooth periyodu
STOCH_RSI_OVERBOUGHT = 85  # Aşırı alım seviyesi
STOCH_RSI_OVERSOLD = 15  # Aşırı satım seviyesi

# Williams %R Parametreleri
WILLIAMS_R_LENGTH = 10  # Williams %R periyodu
WILLIAMS_R_OVERBOUGHT = -20  # Aşırı alım seviyesi (Sell sinyali)
WILLIAMS_R_OVERSOLD = -80  # Aşırı satım seviyesi (Buy sinyali)

# Fisher Transform Parametreleri
FISHER_LENGTH = 8  # Fisher Transform periyodu
FISHER_BULLISH_THRESHOLD = 1.5  # Güçlü boğa trendi eşiği
FISHER_BEARISH_THRESHOLD = -1.5  # Güçlü ayı trendi eşiği

# Coral Trend Parametreleri
CORAL_PERIOD = 21  # Coral Trend EMA periyodu
CORAL_MULTIPLIER = 0.4  # ATR çarpanı (0.2-0.6 arası önerilir)

# Strateji Parametreleri - Majority Vote
MINIMUM_VOTE_THRESHOLD = 4  # 8 indikatörden en az kaç tanesi aynı yönde sinyal vermeli (4-8 arası)

# Twelve Data API Konfigürasyonu
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")