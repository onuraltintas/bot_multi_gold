# CMO Trading Bot - XAUUSD (Forex Gold)

Twelve Data API kullanarak Forex Gold (XAUUSD) için 8 indikatör ile otomatik trading sinyalleri üreten bot.

## 🎯 Özellikler

- **Instrument**: XAUUSD (Forex Gold)
- **Zaman Dilimleri**: 1m, 5m, 15m, 1h, 4h (5 timeframe)
- **İndikatörler** (8 adet):
  - CMO (Chande Momentum Oscillator)
  - Stochastic Oscillator
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Stochastic RSI
  - Williams %R
  - Fisher Transform
  - Coral Trend
- **Strateji**: MajorityVote (minimum 4/8 indikatör aynı yönde sinyal vermeli)
- **Analiz Yöntemi**: Her mum kapanışında
- **Veri Kaynağı**: Twelve Data API (Real-time forex data, 3 API key ile 2400 req/day)
- **Bildirim**: Telegram
- **Mimari**: OOP - Modüler yapı (7 dosya)
- **Deployment**: Linux VPS uyumlu

## 📊 Sinyal Mantığı

Bot **MajorityVote Stratejisi** kullanır:
- **8 İndikatör** analiz edilir (CMO, Stochastic, RSI, MACD, Stochastic RSI, Williams %R, Fisher Transform, Coral Trend)
- **Minimum 4 indikatör** aynı yönde sinyal vermelidir
- **BUY**: En az 4 indikatör BUY sinyali verdiğinde
- **SELL**: En az 4 indikatör SELL sinyali verdiğinde
- **NEUTRAL**: Yeterli konsensüs yoksa

Her indikatör kendi parametreleri ile ayrı ayrı değerlendirilir ve oy verir.

## 🔧 Kurulum

### Gereksinimler

1. **Python 3.8+**

2. **Twelve Data API Key** (Ücretsiz)
   - [Twelve Data](https://twelvedata.com/pricing) üzerinden ücretsiz hesap açın
   - Free tier: 800 requests/day, real-time forex data
   - API key'i alın (dakikalar içinde hazır)

3. **Telegram Bot Token** (Bildirimler için)

### Kurulum Adımları

1. **Repository'yi klonlayın:**
```bash
git clone <repo-url>
cd bot_multi_envV3
```

2. **Python paketlerini yükleyin:**
```bash
pip install -r requirements.txt
```

3. **Konfigürasyon dosyasını oluşturun:**
```bash
cp config.env.template config.env
nano config.env
```

4. **config.env dosyasını düzenleyin:**
```env
# Twelve Data API Key
TWELVE_DATA_API_KEY=your_api_key_here

# Telegram Bilgileri
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### API Key Alma (Ücretsiz)

1. [Twelve Data](https://twelvedata.com/pricing) sitesine gidin
2. "Start for Free" ile ücretsiz hesap açın
3. Dashboard'dan API key'inizi kopyalayın
4. `config.env` dosyasına yapıştırın

**Free Tier Özellikleri:**
- 800 requests/day (5 timeframe × ~160 = her 9 dakikada bir kontrol)
- Real-time forex data (XAUUSD dahil)
- Limit yok, kredi kartı gerektirmez

## 📁 Proje Yapısı

```
bot_multi_envV3/
├── main.py              - Ana giriş noktası, event loop
├── config.py            - Konfigürasyon ve sabitler
├── indicators.py        - CMO indikatör sınıfı
├── strategies.py        - Sinyal stratejileri (CMOStrategy)
├── core.py              - TwelveDataClient, TimeframeScheduler, SignalTracker, TelegramNotifier
├── analyzer.py          - CryptoAnalyzer (orchestrator)
├── message_builders.py  - Telegram mesaj formatları
├── config.env           - Credentials (GİT'E EKLEMEYİN!)
├── config.env.template  - Örnek konfigürasyon şablonu
├── requirements.txt     - Python bağımlılıkları
└── README.md            - Bu dosya
```

## 🚀 Çalıştırma

### Botu Başlat

```bash
python3 main.py
```

Bot başlatıldığında:
1. Twelve Data API bağlantısı test edilir
2. Tüm timeframe'ler için scheduler başlatılır
3. Telegram'a başlangıç mesajı gönderilir
4. Her mum kapanışında otomatik analiz yapılır

### Log Dosyası

Bot çalışma logları `cmo_bot_xauusd.log` dosyasına kaydedilir:
```bash
tail -f cmo_bot_xauusd.log
```

## 🖥️ Linux VPS'te Çalıştırma

Bot tamamen API tabanlı olduğu için **Linux VPS'te sorunsuz çalışır**!
- Kurulum ve yönetim çok daha kolay
- Stabil ve güvenilir

**Linux VPS kullanmak isterseniz:**
- Wine ile MT5 kurulumu gerekli (karmaşık ve hatalı olabilir)
- X11 display emülasyonu gerekli
- Performans sorunları olabilir
- **Tavsiye edilmez!**

### Windows VPS Kurulumu (Önerilen)

#### 1. Windows VPS Alın
- Vultr, DigitalOcean, AWS, Azure veya Hetzner'den Windows Server VPS
- Minimum: 2 CPU, 4GB RAM
- Windows Server 2019 veya 2022

#### 2. RDP ile Bağlanın
```bash
# Linux/Mac'ten
rdesktop YOUR_VPS_IP -u Administrator

# Windows'tan
mstsc.exe  # Remote Desktop Connection
```

#### 3. VPS'te MT5 Kurun
1. **MT5 İndir ve Kur:**
   - Tarayıcıda: https://www.metatrader5.com/en/download
   - MT5 setup'ı indirin ve kurun
### VPS Kurulum Adımları

1. **VPS'e Bağlanın (SSH)**
   ```bash
   ssh user@your-vps-ip
   ```

2. **Python 3.8+ ve pip yükleyin:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git -y
   ```

3. **Bot dosyalarını kopyalayın:**
   ```bash
   cd ~
   # Git ile:
   git clone <your-repo-url> bot_multi_envV3
   
   # Veya FileZilla/SCP ile dosyaları upload edin
   ```

4. **Virtual environment oluşturun (opsiyonel ama önerilen):**
   ```bash
   cd bot_multi_envV3
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Python paketlerini yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

6. **config.env dosyasını düzenleyin:**
   ```bash
   cp config.env.template config.env
   nano config.env
   ```
   
   Credentials'ları girin:
   ```env
   TWELVE_DATA_API_KEY=your_api_key_here
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

7. **Botu test edin:**
   ```bash
   python3 main.py
   ```

   Log'larda şunu görmelisiniz:
   ```
   INFO - Twelve Data client initialized (800 req/day free tier)
   INFO - Scheduler initialization completed
   INFO - Startup message sent to Telegram
   ```

8. **Arka planda çalıştırın:**

**Seçenek A: systemd service (Önerilen)**

```bash
sudo nano /etc/systemd/system/cmo-bot.service
```

Şu içeriği yapıştırın:
```ini
[Unit]
Description=CMO Trading Bot - XAUUSD
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/bot_multi_envV3
ExecStart=/home/your_username/bot_multi_envV3/venv/bin/python3 /home/your_username/bot_multi_envV3/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Servisi başlatın:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cmo-bot
sudo systemctl start cmo-bot

# Durum kontrol
sudo systemctl status cmo-bot

# Log'ları izle
sudo journalctl -u cmo-bot -f
```

**Seçenek B: screen ile**

```bash
# Screen başlat
screen -S cmo_bot

# Botu çalıştır
python3 main.py

# Detach (Ctrl+A sonra D)

# Tekrar attach olmak için
screen -r cmo_bot
```

**Seçenek C: nohup ile**

```bash
nohup python3 main.py > bot.log 2>&1 &

# Process ID'yi kaydet
echo $! > bot.pid

# Durdurma
kill $(cat bot.pid)
```

### VPS Güvenliği

```bash
# Windows Firewall
# Sadece RDP (3389) ve gerekli portları açık tutun

# Linux Firewall (ufw)
sudo ufw enable
sudo ufw allow 22/tcp  # SSH
sudo ufw allow from YOUR_IP  # Sadece sizin IP'niz
```

### VPS Maliyeti

**Windows VPS (Önerilen):**
- Vultr: $12-18/ay (2 CPU, 4GB RAM)
- DigitalOcean: $24/ay
- Contabo: €10-15/ay

**Linux VPS (Wine ile):**
- Daha ucuz ama sorunlu
- €5-10/ay
- Tavsiye edilmez

## ⚠️ Önemli Notlar

## ⚙️ Konfigürasyon

### config.py Dosyası

Bot ayarlarını değiştirmek için `config.py` dosyasını düzenleyin:

```python
# Trading Konfigürasyonu
TARGET_SYMBOL = "XAUUSD"
TIMEFRAMES = ["3m", "5m", "15m", "1h", "4h"]

# İndikatör Parametreleri
CMO_LENGTH = 14
CMO_OVERBOUGHT = 50
CMO_OVERSOLD = -50
```

Değişiklikten sonra botu yeniden başlatın:
```bash
# systemd ile
sudo systemctl restart cmo-bot

# veya manuel çalıştırıyorsanız
# Ctrl+C ile durdurup tekrar çalıştırın
python3 main.py
```

## 📱 Telegram Mesaj Formatı

### Sinyal Mesajları
```
📊 Kısa Vade Analiz - XAUUSD
🕒 30.10.2025 15:05:00 (TR)
💰 Fiyat: $2654.30

🔥 15 Dakika: 🟢 BUY
   └─ CMO: -65.3

⏰ 1 Saat: ⚪ NEUTRAL
   └─ CMO: 12.5
```

### Uzun Vadeli Sinyaller (4h)
```
💃💃💃 ============================== 💃💃💃
🚨 UZUN VADELİ SİNYAL - XAUUSD 🚨
💃💃💃 ============================== 💃💃💃

🕒 30.10.2025 16:00:00 (TR)
💰 Fiyat: $2654.30

📈 4 Saat: 🟢🟢 BUY 🟢🟢
   └─ CMO: -72.5

💃💃💃 ============================== 💃💃💃
```

## 🔍 Sorun Giderme

### Bot Çalışmıyor?

```bash
# 1. Servis durumunu kontrol et (systemd kullanıyorsanız)
sudo systemctl status cmo-bot

# 2. Son 50 satır log
sudo journalctl -u cmo-bot -n 50

# 3. Canlı log takibi
sudo journalctl -u cmo-bot -f

# 4. Bot loglarını kontrol et
tail -f cmo_bot_xauusd.log

# 5. config.env dosyasını kontrol et
cat config.env
```

### API Hataları?

1. **API Key kontrolü:**
   ```bash
   # config.env'de API key'in doğru olduğundan emin olun
   grep TWELVE_DATA_API_KEY config.env
   ```

2. **Rate limit aşıldı mı?**
   - Free tier: 800 requests/day
   - Log'da "rate limit exceeded" hatası varsa:
     - API key'i yükseltin veya
     - Timeframe sayısını azaltın veya
     - Kontrol aralığını uzatın

3. **İnternet bağlantısı:**
   ```bash
   # API'ye erişimi test et
   curl "https://api.twelvedata.com/time_series?symbol=XAUUSD&interval=1h&apikey=demo&outputsize=5"
   ```
   ```bash
      # Twelve Data paketi yüklü mü?
   python3 -c "import twelvedata; print(twelvedata.__version__)"
   ```

4. **Log kontrolü:**
   ```bash
   tail -f cmo_bot_xauusd.log
   ```
   
   Görmek istediğiniz:
   ```
   INFO - Twelve Data client initialized (800 req/day free tier)
   INFO - Scheduler initialization completed
   ```

### Telegram Mesajı Gelmiyor?

1. **Bot token kontrolü:**
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

2. **Chat ID kontrolü:**
   - Bota `/start` mesajı gönderin
   - `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` adresini ziyaret edin
   - `chat.id` değerini kopyalayın

## 🏗️ Geliştirme

### Yeni İndikatör Eklemek

1. `indicators.py` dosyasına yeni sınıf ekleyin:
```python
class NewIndicator(IIndicator):
    def calculate(self, klines: List[List]) -> Dict:
        # Hesaplama mantığı
        pass
```

2. `strategies.py` dosyasında stratejinizi güncelleyin

3. `main.py` dosyasında yeni indikatörü initialize edin

### Test Etmek

```bash
# Syntax kontrolü
python3 -m py_compile main.py config.py indicators.py strategies.py core.py analyzer.py

# Manuel çalıştırma (log'ları görmek için)
python3 main.py
```

## 🔒 Güvenlik

- ⚠️ `config.env` dosyasını **asla** Git'e eklemeyin
- 🔐 API key'inizi güvenli tutun
- 📝 Log dosyalarını düzenli kontrol edin
- 🔄 Sistem güncellemelerini düzenli yapın

## 📊 Performans

- **API Kullanımı**: 800 requests/day limit (free tier)
- **Kontrol Sıklığı**: Her 9 dakikada bir (5 timeframe için)
- **RAM Kullanımı**: ~30-50 MB
- **CPU Kullanımı**: Minimal (analiz sırasında %2-5)
- **Disk Kullanımı**: Log dosyaları için ~5-20 MB/gün

## 🤝 Katkıda Bulunma

1. Projeyi fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'i push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📝 Changelog

### v3.0.0 (2025-10-30)
- ✨ **Twelve Data API entegrasyonu** (MT5 yerine)
- ✅ Linux VPS desteği (tam uyumlu)
- 🌐 Real-time Forex data (XAUUSD)
- 🆓 800 requests/day free tier
- 📝 API tabanlı mimari
- 🔄 Daha stabil veri akışı

### v2.0.0 (2025-09-29)
- ✨ Modüler mimari (6 dosyaya ayrıldı)
- ✨ Her mum kapanışında analiz
- ✨ CMO indikatörü implementasyonu
- ✨ 5 farklı timeframe desteği
- 📝 Kapsamlı dokümantasyon

### v1.0.0 (Initial)
- ⚡ Temel sinyal sistemi
- 📱 Telegram bildirimleri

## 📄 Lisans

Bu proje kişisel kullanım içindir.

## ⚠️ Sorumluluk Reddi

Bu bot yalnızca bilgilendirme amaçlıdır. Finansal tavsiye değildir. Forex ticareti yüksek risk içerir. Kendi riskiniz altında kullanın.
   ```

4. **Log kontrolü:**
   ```bash
   tail -f cmo_bot_xauusd.log
   ```
   
   Görmek istediğiniz:
   ```
   INFO - MT5 connected: 12345678 @ BrokerName-Server
   ```

### Telegram Mesajı Gelmiyor?

1. **Bot token kontrolü:**
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

2. **Chat ID kontrolü:**
   - Bota `/start` mesajı gönderin
   - `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` adresini ziyaret edin
   - `chat.id` değerini kopyalayın

### Symbol Hatası (XAUUSD bulunamadı)?

1. **MT5'te symbol kontrolü:**
   - Market Watch penceresini açın (Ctrl+M)
   - "XAUUSD" veya "GOLD" aratın
   - Symbol adını broker'ınıza göre ayarlayın (örn: "XAUUSDm", "GOLD", vb.)

2. **config.py'de symbol güncelleme:**
   ```python
   TARGET_SYMBOL = "XAUUSD"  # Broker'ınıza göre ayarlayın
   ```

## 🏗️ Geliştirme

### Yeni İndikatör Eklemek

1. `indicators.py` dosyasına yeni sınıf ekleyin:
```python
class NewIndicator(IIndicator):
    def calculate(self, klines: List[List]) -> Dict:
        # Hesaplama mantığı
        pass
```

2. `strategies.py` dosyasında stratejinizi güncelleyin

3. `main.py` dosyasında yeni indikatörü initialize edin

### Test Etmek

```bash
# Syntax kontrolü
python3 -m py_compile main.py config.py indicators.py strategies.py core.py analyzer.py

# Manuel çalıştırma (log'ları görmek için)
python3 main.py
```

## 🔒 Güvenlik

- ⚠️ `config.env` dosyasını **asla** Git'e eklemeyin
- 🔐 MT5 şifrenizi güvenli tutun
- � Log dosyalarını düzenli kontrol edin
- 🔄 Sistem güncellemelerini düzenli yapın

## 📊 Performans

- **MT5 API Kullanımı**: Her timeframe için mum kapanışında veri çekimi
- **RAM Kullanımı**: ~50-100 MB
- **CPU Kullanımı**: Minimal (analiz sırasında %5-10)

## 📄 Lisans

Bu proje kişisel kullanım içindir.
- **Disk Kullanımı**: Log dosyaları için ~10-50 MB/gün

## 🤝 Katkıda Bulunma

1. Projeyi fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'i push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📝 Changelog

### v2.0.0 (2025-09-29)
- ✨ Modüler mimari (6 dosyaya ayrıldı)
- ✨ Her mum kapanışında analiz (TradingView senkronize)
- ✨ Otomatik scheduler senkronizasyonu
- ✨ EMA ve DMI indikatörleri eklendi
- ✨ 5 farklı timeframe desteği
- ✨ Uzun vadeli sinyaller için özel mesaj formatı
- 🐛 ADX hesaplama düzeltildi
- 📝 Kapsamlı dokümantasyon

### v1.0.0 (Initial)
- ⚡ Temel CCI sinyal sistemi
- 📱 Telegram bildirimleri

## 📄 Lisans

Bu proje kişisel kullanım içindir.

## ⚠️ Sorumluluk Reddi

Bu bot yalnızca bilgilendirme amaçlıdır. Finansal tavsiye değildir. Kripto para ticareti yüksek risk içerir. Kendi riskiniz altında kullanın.