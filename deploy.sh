#!/bin/bash

# Bot Multi Gold VPS Deployment Script
# Dosyaları /opt/bot_multi_gold/ dizinine kopyalar ve servisi başlatır

echo "🤖 Bot Multi Gold - Deployment Script"
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
BOT_DIR="/opt/bot_multi_gold"
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
cp -v bot-multi-gold.service /etc/systemd/system/

# Servis dosyasına doğru izinleri ver
echo "🔐 Servis dosyası izinleri ayarlanıyor..."
chmod 644 /etc/systemd/system/bot-multi-gold.service

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
systemctl stop bot-multi-gold.service 2>/dev/null || true

# Servisi etkinleştir (sistem başlangıcında otomatik başlasın)
echo "✅ Bot Multi Gold servisi etkinleştiriliyor..."
systemctl enable bot-multi-gold.service

# Servisi başlat
echo "🚀 Bot Multi Gold servisi başlatılıyor..."
systemctl start bot-multi-gold.service

# Servis durumunu kontrol et
echo "📊 Servis durumu kontrol ediliyor..."
sleep 3

if systemctl is-active --quiet bot-multi-gold.service; then
    echo ""
    echo "✅ ✅ ✅ Bot Multi Gold başarıyla çalışıyor! ✅ ✅ ✅"
    echo ""
    echo "📋 Yararlı komutlar:"
    echo "   Durum kontrol:          sudo systemctl status bot-multi-gold"
    echo "   Canlı loglar:           sudo journalctl -u bot-multi-gold -f"
    echo "   Son 50 satır log:       sudo journalctl -u bot-multi-gold -n 50"
    echo "   Servisi durdur:         sudo systemctl stop bot-multi-gold"
    echo "   Servisi başlat:         sudo systemctl start bot-multi-gold"
    echo "   Servisi yeniden başlat: sudo systemctl restart bot-multi-gold"
    echo ""
    echo "📂 Bot dosyaları: $BOT_DIR"
    echo "📝 Konfigürasyon: $BOT_DIR/config.py"
    echo "🔐 Credentials: $BOT_DIR/config.env"
    echo ""
    echo "💡 Telegram'da '🤖 BOT BAŞLATILDI' mesajını kontrol edin!"
else
    echo ""
    echo "❌ ❌ ❌ Bot Multi Gold başlatılamadı! ❌ ❌ ❌"
    echo ""
    echo "🔍 Hata ayıklama:"
    echo "   1. Servis durumu: sudo systemctl status bot-multi-gold"
    echo "   2. Detaylı loglar: sudo journalctl -u bot-multi-gold -n 100"
    echo "   3. config.env kontrolü: cat $BOT_DIR/config.env"
    echo "   4. Manuel test: cd $BOT_DIR && python3 main.py"
fi

echo ""
echo "🎉 Deployment tamamlandı!"
echo ""
