#!/bin/bash

# CCI Trading Bot VPS Deployment Script
# Dosyaları /opt/bot_multi/ dizinine kopyalar ve servisi başlatır

echo "🤖 CCI Trading Bot - Deployment Script"
echo "=================================================="

# Root olarak çalıştırılıp çalıştırılmadığını kontrol et
if [ "$EUID" -ne 0 ]; then
    echo "❌ Bu script root olarak çalıştırılmalı (sudo ./deploy.sh)"
    exit 1
fi

# Mevcut dizini al
CURRENT_DIR="$(pwd)"
echo "📂 Kaynak dizin: $CURRENT_DIR"

# Hedef bot dizini
BOT_DIR="/opt/bot_multi"
echo "📁 Hedef dizin: $BOT_DIR"

# Bot dizinini oluştur
echo "📁 Bot dizini oluşturuluyor..."
mkdir -p $BOT_DIR

# Dosyaları kopyala
echo "📄 Bot dosyaları kopyalanıyor..."
cp -v main.py $BOT_DIR/
cp -v config.py $BOT_DIR/
cp -v indicators.py $BOT_DIR/
cp -v strategies.py $BOT_DIR/
cp -v core.py $BOT_DIR/
cp -v analyzer.py $BOT_DIR/
cp -v message_builders.py $BOT_DIR/
cp -v config.env $BOT_DIR/
cp -v requirements.txt $BOT_DIR/
cp -v README.md $BOT_DIR/

echo "✅ Dosyalar kopyalandı"

# Servis dosyasını kopyala
echo "⚙️  Systemd servis dosyası kopyalanıyor..."
cp -v cci-bot.service /etc/systemd/system/

# Servis dosyasına doğru izinleri ver
echo "🔐 Servis dosyası izinleri ayarlanıyor..."
chmod 644 /etc/systemd/system/cci-bot.service

# Bot dosyalarına doğru izinleri ver
echo "🔐 Bot dosyası izinleri ayarlanıyor..."
chmod +x $BOT_DIR/main.py
chown -R root:root $BOT_DIR

# config.env dosyasını kontrol et
echo "🔍 config.env dosyası kontrol ediliyor..."
if [ ! -f "$BOT_DIR/config.env" ]; then
    echo "⚠️  UYARI: config.env dosyası bulunamadı!"
    echo "   Lütfen $BOT_DIR/config.env dosyasını kontrol edin"
else
    echo "✅ config.env dosyası mevcut"
fi

# Systemd'yi yeniden yükle
echo "🔄 Systemd servisleri yeniden yükleniyor..."
systemctl daemon-reload

# Eski servisi durdur (hata vermesi önemli değil)
echo "🛑 Eski servis durduruluyor (varsa)..."
systemctl stop cci-bot.service 2>/dev/null || true

# Servisi etkinleştir (sistem başlangıcında otomatik başlasın)
echo "✅ CCI Bot servisi etkinleştiriliyor..."
systemctl enable cci-bot.service

# Servisi başlat
echo "🚀 CCI Bot servisi başlatılıyor..."
systemctl start cci-bot.service

# Servis durumunu kontrol et
echo "📊 Servis durumu kontrol ediliyor..."
sleep 3

if systemctl is-active --quiet cci-bot.service; then
    echo ""
    echo "✅ ✅ ✅ CCI Bot başarıyla çalışıyor! ✅ ✅ ✅"
    echo ""
    echo "📋 Yararlı komutlar:"
    echo "   Durum kontrol:          sudo systemctl status cci-bot"
    echo "   Canlı loglar:           sudo journalctl -u cci-bot -f"
    echo "   Son 50 satır log:       sudo journalctl -u cci-bot -n 50"
    echo "   Servisi durdur:         sudo systemctl stop cci-bot"
    echo "   Servisi başlat:         sudo systemctl start cci-bot"
    echo "   Servisi yeniden başlat: sudo systemctl restart cci-bot"
    echo ""
    echo "📂 Bot dosyaları: $BOT_DIR"
    echo "📝 Konfigürasyon: $BOT_DIR/config.py"
    echo "🔐 Credentials: $BOT_DIR/config.env"
    echo ""
    echo "💡 Telegram'da '🤖 BOT BAŞLATILDI' mesajını kontrol edin!"
else
    echo ""
    echo "❌ ❌ ❌ CCI Bot başlatılamadı! ❌ ❌ ❌"
    echo ""
    echo "🔍 Hata ayıklama:"
    echo "   1. Servis durumu: sudo systemctl status cci-bot"
    echo "   2. Detaylı loglar: sudo journalctl -u cci-bot -n 100"
    echo "   3. config.env kontrolü: cat $BOT_DIR/config.env"
    echo "   4. Manuel test: cd $BOT_DIR && python3 main.py"
fi

echo ""
echo "🎉 Deployment tamamlandı!"
echo ""
