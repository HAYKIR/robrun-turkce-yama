# Rob Run Türkçe Yama

Rob Run (Steam) için açık kaynak, topluluk yapımı Türkçe yama.

- 4.771 satırlık arayüz, ipucu (Kodeks), eğitim, hapishane ve ayar metinleri Türkçe
- Ana fontlara gerçek `ğ Ğ ş Ş ı İ` harfleri eklenir
- Oyun güncellense bile aracı tekrar çalıştırınca yeni sürüme kendini uyarlar
- Kodun tamamı bu depoda, tek dosya: [`robrun_tr.py`](robrun_tr.py)

> [!WARNING]
> Bu resmi bir yama değildir ve geliştirici Kefir ile bir bağlantısı yoktur. Oyun klasöründeki dosyalar değiştirilmez, ama oyunun yüklediği içerik değişir. Easy Anti-Cheat veya geliştiricinin bunu nasıl değerlendireceği **garanti edilemez**. Kullanım riski size aittir.

## Kurulum

**Gerekenler:** Windows, Steam'de kurulu Rob Run, [Python 3.9 veya üstü](https://www.python.org/downloads/) (kurarken **"Add python.exe to PATH"** kutusunu işaretleyin).

1. Bu sayfada **Code → Download ZIP** ile depoyu indirin ve bir klasöre çıkarın.
2. `Kur_ve_Baslat.bat` dosyasına çift tıklayın.
   - İlk çalıştırmada gerekli kütüphane (`UnityPy`) klasör içindeki `.venv` ortamına kurulur.
   - Ardından yama kurulur ve oyun Steam üzerinden açılır.
3. Sonraki girişlerde oyunu doğrudan Steam'den açabilirsiniz.

**Oyuna güncelleme gelince:** `Kur_ve_Baslat.bat` dosyasını bir kez daha çalıştırın.

**Kaldırmak için:** `Kaldir.bat` dosyasına çift tıklayın. Oyun İngilizce açılır.

### Komut satırından

```bat
pip install -r requirements.txt
python robrun_tr.py               :: kur ve oyunu başlat
python robrun_tr.py --no-launch   :: sadece kur
python robrun_tr.py --uninstall   :: kaldır
python robrun_tr.py --game-dir "E:\SteamLibrary\steamapps\common\Rob Run"
python robrun_tr.py --force       :: paketleri baştan üret
```

## Nasıl çalışıyor?

Oyun, Unity Addressables sistemini kullanıyor. Oyunun kendi `settings.json` dosyası, ana katalog için bir **önbellek konumu** tanımlıyor:

```
%USERPROFILE%\AppData\LocalLow\Kefir\ROB RUN\com.unity.addressables\catalog_<TARİH>.hash
```

Bu konumda oyunun güncel hash değeriyle eşleşen bir katalog varsa, Unity oyun klasöründeki katalog yerine onu yükler. Araç şunları yapar:

1. Steam kütüphanelerinde oyunu bulur.
2. `settings.json` dosyasından güncel katalog adını, `StandaloneWindows64` klasöründen hash değerini okur.
3. **Oyunun kendi** İngilizce dil paketini okur ve `data/master_tr.json` içindeki çevirileri yazarak Türkçe paketi **sizin bilgisayarınızda** üretir.
4. **Oyunun kendi** font paketini okur ve mevcut harf parçalarından `Ş ş Ğ ğ İ ı` harflerini oluşturur. Font düzeni değişmişse bu adım atlanır, Türkçe harfler en yakın harfe (`ş → s` gibi) eşlenir.
5. Güncel kataloğun bir kopyasında sadece bu iki paketin adresini değiştirir ve önbellek klasörüne yazar.

Oyun dosyası dağıtılmaz. Depoda sadece kaynak kod ve çeviri metinleri bulunur.

### Ne yapmaz

- İnternete bağlanmaz, veri göndermez.
- Driver veya servis kurmaz, yönetici izni istemez.
- Oyun belleğine müdahale etmez, DLL enjekte etmez.
- Oyun klasörüne dosya eklemez. (Eski sürümlerin bıraktığı yama dosyalarını temizler.)

## Bilinen sınırlar

- Güncellemeyle oyuna yeni metin eklenirse, `master_tr.json` güncellenene kadar o satırlar İngilizce görünür.
- Konturlu (Outline) ve tırnaklı (Serif) yardımcı fontlarda `ğ ş ı` harfleri `g s i` olarak görünür.
- Geliştirici önbellek sistemini kapatır veya katalog yapısını değiştirirse araç hata verir ve hiçbir şey yazmaz.

## Sorun giderme

| Sorun | Çözüm |
|---|---|
| `Python bulunamadı` | Python'u kurun, kurulumda "Add to PATH" seçeneğini işaretleyin. |
| `Rob Run kurulumu bulunamadı` | `python robrun_tr.py --game-dir "OYUN_KLASÖRÜ"` ile klasörü belirtin. |
| Oyun hâlâ İngilizce | `Kur_ve_Baslat.bat` dosyasını tekrar çalıştırın. Olmazsa `--force` ekleyin. |
| Oyun açılmıyor veya bozuk görünüyor | `Kaldir.bat`, ardından Steam → Rob Run → Özellikler → Yüklü Dosyalar → **Dosya bütünlüğünü doğrula**. |

## Çeviriye katkı

Çeviriler [`data/master_tr.json`](data/master_tr.json) dosyasında `"Tablo::anahtar": "Türkçe metin"` biçiminde durur. Düzeltme yaparken şunlara dokunmayın:

- `{0}`, `{1:time:}`, `{0:plural:...}`, `{0:cond:...}` gibi yer tutucular (`plural`, `cond`, `choose` kelimeleri çevrilmez),
- `<color=...>`, `</color>`, `<link=...>`, `<nobr>` gibi etiketler.

## Lisans

Kaynak kod MIT lisansı ile yayınlanır, ayrıntılar [`LICENSE`](LICENSE) dosyasında. Rob Run ve tüm oyun içerikleri Kefir'e aittir.
