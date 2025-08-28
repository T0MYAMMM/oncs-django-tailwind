import logging
import requests
import json
import time
from typing import Any
import psycopg2.extras
import threading
from kafka import KafkaProducer

from database.connect import get_connection
from database.crud import onm_urls_update_url_status, onm_urls_fetch_pending, onm_urls_get_running_count, onm_urls_update_running_to_pending
from kafka_clients.crawler_producer import json_serializer
from variables import PRODUCTION_SERVER_1, PRODUCTION_SERVER_2, PRODUCTION_SERVER_3

from crawlers.utils.zyteAPI import request_article
from database.crud import extract_source_name, onm_urls_update_url_status
#from kafka_clients.scraper_producer import send_content
from scrapers.zyte.base_scraper import BaseScraper
from scrapers.zyte.fetch_dateformat import get_okezone_published_date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from kafka import KafkaProducer

def json_serializer(data):
    return json.dumps(data).encode("utf-8")

def on_send_success(record_metadata):
    print(f"Message sent successfully!")
    print(f"Topic: {record_metadata.topic}")
    print(f"Partition: {record_metadata.partition}")
    print(f"Offset: {record_metadata.offset}\n")

def on_send_error(excp):
    print(f"An error occurred while sending data to Kafka: {excp}\n")

def send_content(data, producer):
    try:
        print(f"\nSending Content to Kafka: {data['link']} - {data['title']}\n")
        producer.send('onm-contents', data).add_callback(on_send_success).add_errback(on_send_error)
        print(f"Successfully add content to onm-contents")
        producer.flush()
        
    except Exception as e:
        print(f"An error occurred while sending data to Kafka: {e}")

headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
        'Sec-Ch-Ua': '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
    }

class BaseScraper():
    name = 'base'
    start_urls = []
    fetch_url_thread = None
    thread_pool = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn = get_connection()
        self.conn.autocommit = True
        self.cursor = self.conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        self.producer = KafkaProducer(
            bootstrap_servers = [PRODUCTION_SERVER_1, PRODUCTION_SERVER_2, PRODUCTION_SERVER_3],
            value_serializer = json_serializer
        )
    
    def process_url(self, url, cursor):
        raise NotImplementedError("Subclasses must implement the 'process_url' method.")

    def closed(self):
        self.cursor.close()
        self.conn.close()
        print(f'Scraper closed. \n\n')

class ZyteScraper(BaseScraper):
    name = 'zyte'

    def process_url(self, url, datepub=None, fetch_dateformat=False, manual=False):
        try:
            if not manual:
                start_time = time.time()
                sourceName = extract_source_name(url)

                article = request_article(url) 
                title = article.get('headline', [])
                articleBody = article.get('articleBody', [])
                datePublishedRaw = article.get('datePublishedRaw', [])

                if datepub is not None:
                    datePublishedRaw = datepub
                elif fetch_dateformat:
                    datePublishedRaw = get_okezone_published_date(url)
                else:
                    datePublishedRaw = article.get('datePublishedRaw', [])  
                    
                authors = article.get('authors', {})
                images = article.get('images', {})
                language = article.get('inLanguage', {})
                author_names = [author.get('name') for author in authors]
                image_urls = [image.get('url') for image in images]

                from datetime import datetime, timedelta, timezone
                
                if sourceName == 'mistar.id':
                    _, tanggal_waktu = datePublishedRaw.split(", ", 1)
                    dt = datetime.strptime(tanggal_waktu, "%d %B %Y %H.%M")
                    datePublishedStr = dt.replace(tzinfo=timezone(timedelta(hours=7)))
                    datePublishedRaw = datePublishedStr.isoformat()
                
                
                article_data = {
                    "source_name" : sourceName,
                    "title": title,
                    "description" : "",
                    "body": articleBody,
                    "date_published": datePublishedRaw, #"2025-01-08", #7"2024-12-02T19:13:00", #6 "2024-12-02T22:20:42+07:00", #5 "2024-12-02T21:21:00+07:00", #3 "2024-12-02T11:45:21+00:00",#2 "2024-12-02T18:29:38+07:00", #datePublishedRaw,
                    "author_list" : author_names,
                    "images": image_urls,
                    "link": url,
                    "language": language
                    }
            else:   
                if datepub is not None:
                    datePublishedRaw = datepub
                else:
                    datePublishedRaw = ""

                article_data = {
                    "source_name": extract_source_name(url),
                    "title": "Mobil Bekas Kian Diminati, OLXmobbi Tawarkan Solusi Jual-Beli yang Praktis dan Aman",
                    "description": 'Astra Financial Talk: "Tukar Mobil Lama, Langsung Bawa Pulang yang Baru di GIIAS 2025" bersama OLXmobbi, Gaikindo dan Astra Financial. (Foto: Ubaidillah/SWA)',
                    "body": """
Saat ini, minat masyarakat Indonesia terhadap mobil bekas terus meningkat. Baik pembeli mobil pertama maupun mereka yang ingin meng-upgrade kendaraan lamanya, sama-sama menjadikan mobil bekas sebagai pilihan utama.

Sepanjang 2024, penjualan mobil bekas di Indonesia diperkirakan melampaui 1,8 juta unit. Angka ini jauh melampaui penjualan mobil baru yang tercatat hanya 865.723 unit secara wholesales pada tahun yang sama.

Tren ini juga tercermin dalam pertumbuhan pembiayaan kendaraan bekas. Otoritas Jasa Keuangan (OJK) mencatat bahwa pada lima bulan pertama 2025 (Januari–Mei), pembiayaan kendaraan bekas tumbuh 10% secara tahunan (year-on-year/yoy) menjadi Rp118 triliun. Nilai ini menyumbang 22% dari total pembiayaan yang disalurkan perusahaan multifinance di Indonesia.

Sejalan dengan pertumbuhan itu, Astra Financial mencatatkan peningkatan penyaluran pembiayaan mobil bekas melalui Astra Credit Companies (ACC) dan Toyota Astra Financial Services (TAF) sebesar Rp8,15 triliun, atau naik 15% secara yoy pada periode Januari–Juni 2025.

Kemudahan dalam membeli mobil bekas juga meningkat berkat dukungan teknologi. Kekhawatiran terhadap kondisi mobil bisa ditekan, karena makin banyak perusahaan tepercaya yang menjual mobil bekas dalam kondisi baik, harga terjangkau, serta didukung sistem pembiayaan yang fleksibel. Faktor-faktor ini semakin meningkatkan minat masyarakat terhadap mobil bekas.

“Dulu, jual beli mobil bekas seringkali seperti beli kucing dalam karung. Sekarang prosesnya jauh lebih aman, transparan, dan sistematis,” ujar Kukuh Kumara, Sekretaris Umum Gaikindo, dalam acara Astra Financial Talk di GIIAS 2025, Selasa (29/7/2025).

Salah satu perusahaan yang menyediakan layanan jual beli mobil bekas adalah OLXmobbi. Sebagai bagian dari Grup Astra, OLXmobbi memiliki reputasi yang kuat. Perusahaan ini mengintegrasikan layanan jual beli secara online dan offline berbasis teknologi, sekaligus menjadi solusi menyeluruh dalam ekosistem pasar mobil bekas.

Saat ini, OLXmobbi memiliki 30 Store & Inspection Center yang tersebar di 10 kota besar, termasuk Jabodetabek, Bandung, Semarang, Surabaya, Malang, Denpasar, Pekanbaru, Palembang, Balikpapan, dan Medan. Proses inspeksi pun dilakukan secara cepat dan menyeluruh, hanya dalam waktu sekitar 60 menit.

“Biasanya orang bingung mau dikemanakan mobil lamanya saat ingin ganti ke mobil baru. Sekarang, cukup datang ke booth OLXmobbi di GIIAS 2025, lakukan inspeksi gratis sekitar 45 menit, dan setelah deal, uang bisa langsung ditransfer dalam waktu 60 menit,” jelas Agung Iskandar, COO & Director OLXmobbi.

Menurut Agung, kendala utama masyarakat saat ingin mengganti mobil lama dengan yang baru adalah soal waktu. Banyak orang kesulitan karena tempat parkir terbatas. Mobil lama belum sempat dijual, tapi mobil baru sudah datang, atau sebaliknya, mobil lama sudah dijual tapi harus menunggu pengiriman mobil baru.

“Kami sudah punya sedikit fleksibilitas yang sengaja dibuat khusus untuk konsumen-konsumen yang mau tukar tambah dari bekas ke baru di GIIAS. Waktu serah terimanya pun disesuaikan, mobil bekasnya baru kami ambil kalau mobil baru sudah datang. Jadi timing-nya itu pas sekali,” ujarnya.
Proses serupa juga berlaku di luar ajang GIIAS. Pelanggan bisa menjadwalkan inspeksi gratis secara online. Inspeksi kemudian dilakukan oleh tim ahli OLXmobbi, baik di Store maupun lewat layanan Home Inspection, dengan durasi sekitar 60 menit.

“Untuk mengetahui estimasi harga jual mobil lama, masyarakat juga bisa melihatnya di OLXmobbi. Tinggal isi data, dan ini gratis,” tambah Agung.

Tidak hanya menawarkan kemudahan dalam menjual mobil bekas, OLXmobbi juga mempermudah proses pembelian. Hanya dengan tiga langkah — pilih mobilnya, tentukan jadwal test drive, dan lanjutkan ke pembayaran jika cocok — konsumen bisa membawa pulang mobil bekas idaman. Saat ini, tersedia lebih dari 2.000 pilihan mobil bekas di OLXmobbi.

Hal yang Mempengaruhi Harga Mobil Bekas
Kondisi mobil: OLXmobbi melakukan inspeksi menyeluruh pada 188 titik kendaraan, termasuk mesin, transmisi, rangka, eksterior, interior, kaki-kaki, hingga suspensi. Semakin baik kondisinya, semakin besar kemungkinan mendapatkan harga terbaik.

Kebersihan kendaraan: Pastikan kendaraan dalam keadaan bersih sebelum dijual. Ini akan membantu inspektor menilai mobil dengan lebih objektif. “Kalau kotor, kita mungkin lihatnya berbeda, kelihatan ada baret padahal tidak ada,” ujar Agung.

Aksesori tambahan: Mobil dengan kondisi standar seperti saat pertama dibeli cenderung memiliki harga jual lebih tinggi. Aksesori tambahan yang berlebihan bisa menurunkan nilai jual.

Dokumen service berkala: Dokumen servis rutin sering dilupakan, padahal bisa menjadi nila   i tambah. Jika tersedia, tunjukkan dokumen tersebut untuk meningkatkan harga jual.

Surat-surat atau dokumen kendaraan: Mobil itu, dokumennya itu bukan sebatas STNK dan BPKB, tapi ada juga tambahan lainnya seperti buku manual, buku service dan termasuk faktur. “Seringnya orang Indonesia itu kehilangan buku service yang hilang atau nggak dirawat, buku manualnya entah dimana, yang paling sering faktur, itu hilang. Lalu kunci serep juga jangan lupa,” ungkapnya.

Tren pertumbuhan mobil bekas di Indonesia tidak hanya menunjukkan pergeseran preferensi konsumen, tetapi juga menandai transformasi ekosistem otomotif yang semakin terintegrasi dengan teknologi dan layanan yang user-friendly.

Dengan hadirnya platform seperti OLXmobbi yang menawarkan proses transparan, cepat, dan terpercaya, jual beli mobil bekas kini bukan lagi aktivitas yang merepotkan.

Di tengah tantangan ruang, waktu, dan kebutuhan mobilitas yang dinamis, solusi seperti ini menjadi jawaban atas kebutuhan masyarakat urban yang menginginkan kepraktisan tanpa mengorbankan kualitas. (*)
""",
                    "date_published": "2025-07-3122:00:00+07:00",
                    "author_list": ["M. Ubaidillah", "Teguh Sri Pambudi"],
                    "images": [
                        "https://storage.googleapis.com/swafiles/images/2025/07/312051/1753969887_57337dbdb61fbcb13f6e.jpeg"
                        ],
                    "link": "https://swa.co.id/read/462229/mobil-bekas-kian-diminati-olxmobbi-tawarkan-solusi-jual-beli-yang-praktis-dan-aman",
                    "language": "id"
                }
            
            
            print(article_data)
            #return None
            
            if self.cursor is not None:
                if article_data['title'] != '' and article_data['date_published'] != '': 
                    #send_content(article_data, self.producer)
                    #onm_urls_update_url_status(url, 'success', cursor)    
                    #scrape_time = time.time() - start_time
                    print(f"\n\n[SUCCESS] Scrape completed.\n\n")

                else:
                    print(f"[Error] Article title is empty or invalid.")
                    #onm_urls_update_url_status(url, 'error', self.cursor)  
            else:
                print(article_data['link'], article_data['title'])
            
        except Exception as e:
            print(f"Error processing URL '{url}': {e}")
            #onm_urls_update_url_status(url, 'error', self.cursor)   


if __name__ == "__main__":
    scraper = ZyteScraper()
    # Daftar URL dalam list Python

    links = [
        #"https://andreaautopage.com/home/read/B4O6LrA1d28KF9X/OLXmobbi_Dijamin_Customernya_Aman_dan_Nyaman",
        "https://dapurpacu.id/2025/03/12/hut-ke-1-olxmobbi-bertabur-promo-diskon-tiap-transaksi",
        "https://dapurpacu.id/2025/07/25/olxmobbi-tawarkan-promo-cashback-tiap-trade-in-di-giias-2025",
        "https://dapurpacu.id/2025/07/31/solusi-mudah-tukar-tambah-dan-pembiayaan-mobil-bekas-di-giias-2025",
        "https://dapurpacu.id/2025/08/01/olxmobbi-gandeng-empat-rapper-gaungkan-kampanye-pilihyangahli",
        "https://fixsnews.co.id/kampanye-pilihyangahli-olxmobbi-hadirkan-solusi-jual-beli-mobil-bekas-melalui-musik",
        "https://garduoto.com/38803/olxmobbi-bagikan-cashback-hingga-rp-68-juta-untuk-trade-in-di-tempat-di-giias-2025",
        "https://genz.id/5-tips-tukar-tambah-mobil-bekas-yang-aman-gen-z-wajib-tahu",
        "https://gi-media.com/2025/08/14/pilihyangahli-olxmobbi-guncang-giias-2025-trade-in-kilat-dengan-cashback-fantastis",
        "https://iotomagz.com/olxmobbi-kembali-hadir-di-giias-2025-jangan-lewatkan-cashback-spesial-hingga-rp-68-juta-untuk-trade-in-mobil-impianmu",
        "https://jabar.tribunnews.com/2025/08/06/mobkas-kian-diminati-begini-cara-trade-in-mobil-bekas-dari-olxmobbi",
        "https://jadwalbalap.com/no-drama-no-ribet-trade-in-mobil-simpel-ala-olxmobbi-di-giias-2025",
        "https://jawapos.com/otomotif/016351476/tukar-tambah-makin-dilirik-alternatif-praktis-di-tengah-ribetnya-jual-beli-mobil-bekas",
        "https://krjogja.com/otomotif/1246401867/mobkas-kian-diminati-ini-kemudahan-dari-astra-financial-dan-olxmobbi-di-giias-2025",
        "https://liputan6.com/otomotif/read/6115074/begini-trik-supaya-mobil-bekas-dihargai-tinggi?page=2",
        "https://marketeers.com/dorong-pasar-mobil-bekas-olxmobbi-bawa-kemudahan-trade-in-di-giias-2025",
        "https://marketing.co.id/tawarkan-cashback-hingga-rp-68-juta-olxmobbi-gandeng-rapper-dalam-kampanye-pilihyangahli-di-giias-2025",
        "https://mobilinanews.com/artikel/36352/Kunjungi-Booth-OLXmobbi-di-GIIAS-2025-Tukar-Mobil-Bekas-dan-Bawa-Pulang-Unit-Baru",
        "https://mobilinanews.com/artikel/36551/Inovasi-Layanan-OLXmobbi-Mobil-Kredit-Belum-Lunas-Bisa-Trade-in-dengan-Mobil-Baru-di-GIIAS-2025",
        "https://mobilinanews.com/mobile/artikel/36352/Kunjungi-Booth-OLXmobbi-di-GIIAS-2025-Tukar-Mobil-Bekas-dan-Bawa-Pulang-Unit-Baru",
        "https://motomobinews.id/berita-motomobi/astra-financial-dan-olxmobbi-sebar-program-menarik-di-giias",
        "https://moveroad.id/2025/08/03/olxmobbi-satu-tahun-bersama-astra-group",
        "https://neraca.co.id/article/223529/cara-cerdas-wujudkan-mobil-impian-tanpa-drama",
        "https://neraca.co.id/article/223532/olxmobbi-jual-mobil-makin-sat-set-anti-ribet",
        "https://netralnews.com/director-olxmobbi-perhatikan-hal-sepele-ini-agar-harga-jual-mobil-bekas-tetap-tinggi/MkYyV2labFozUkp3SnVsSnFLZDJBQT09",
        "https://nevbuzz.com/4-rapper-ungkap-keunggulan-jual-beli-mobil-bekas-di-olxmobbi-3266-2",
        "https://nevbuzz.com/olxmobbi-beri-solusi-tukar-tambah-mobil-di-giias-2025di-giias-2025",
        "https://nevbuzz.com/olxmobbi-solusi-jual-beli-mobkas-berkualitas-berbasis-teknologi",
        "https://oto.mounture.com/ragam/menemukan-cara-baru-jual-mobil-bekas-bersama-olxmobbi",
        "https://otobanten.id/2025/07/olxmobbi-hadir-kembali-di-giias-2025.html",
        "https://otobisnis.id/lewat-lagu-olxmobbi-ajak-masyarakat-cerdas-pilih-mobkas",
        "https://otobisnis.id/olxmobbi-hadirkan-promo-trade-in-dan-cashback-di-giias-2025",
        "https://otobisnis.id/olxmobbi-lengkapi-ekosistem-bisnis-astra-financial",
        "https://otobisnis.id/olxmobbi-sukses-jual-27-300-unit-mobil-bekas-dalam-setahun",
        "https://otoblitz.net/news/penjualan-mobil-bekas-melalui-olxmobbi-capai-27-ribu-unit",
        "https://otodiva.id/11240-olxmobbi-tawarkan-cashback-menarik-di-giias-2025",
        "https://otoexpo.com/olxmobbi-kembali-hadir-di-giias-2025-dengan-promo-trade-in-semua-merek-mobil",
        "https://otoexpo.com/tukar-tambah-kendaraan-tanpa-drama-via-olxmobbi-dengan-pilihyangahli",
        "https://otomotif.kompas.com/read/2025/07/30/141336315/kemudahan-jual-mobil-bekas-di-giias-2025-dengan-olxmobbi",
        "https://otomotif.sindonews.com/read/1597877/183/giias-2025-beri-jaminan-jual-mobil-bekas-dengan-harga-tinggi-1753456043?showpage=all",
        "https://otosia.com/berita/olxmobbi-ubah-skeptis-jadi-yakin-sekarang-zamannya-pilihyangahli-454035-mvk.html?page=8",
        "https://pojokoto.com/hadir-mentereng-di-giias-2025-olx-pertegas-pilih-yang-ahli",
        "https://radarbandung.id/2025/08/06/kolaborasi-astra-financial-dan-olxmobbi-buka-akses-pembiayaan-mobil-bekas-aman-di-giias",
        "https://rajabalapotomotif.com/gak-mau-rugi-olxmobbi-tawarkan-cashback-hingga-rp68-juta-di-giias-2025-ini-cara-dapatinnya",
        "https://risks.id/2025/07/31/olxmobbi-inovasi-dan-transformasi-digital-di-industri-mobil-bekas",
        "https://rockomotif.com/2025/07/olxmobbi-gandeng-rappers-indonesia-untuk-kampanyekan-pilihyangahli",
        "https://selular.id/2025/07/olxmobbi-kembali-di-giias-2025-tawarkan-cashback-rp-68-juta-untuk-trade-in",
        "https://speednride.com/2025/07/27/olxmobbi-hadir-kembali-di-giias-2025-bagikan-cashback-hingga-rp-68-juta-untuk-trade-in-di-tempat",
        "https://speednride.com/2025/08/15/olxmobbi-gandeng-yacko-hingga-iwa-k-ajak-masyarakat-transaksi-mobil-bekas-dengan-aman",
        "https://sumateraekspres.bacakoran.co/read/91186/trade-in-instan-ala-olxmobbi-memacu-transaksi-giias-meningkatkan-ekonomi",
        "https://tabloidpulsa.id/olxmobbi-hadirkan-cashback-hingga-rp-68-juta-di-giias-2025",
        "https://thenext.id/wow-ini-solusi-finansial-dan-kemudahan-trade-in-mobil-bekas",
        "https://viva.co.id/otomotif/1839494-tukar-tambah-mobil-lama-ke-baru-di-giias-2025-cuma-1-jam"
    ]


    for data in links:
        scraper.process_url(data)
        
    
    #scraper.process_url('https://www.kabargayo.com/2025/01/18/pertamina-secara-bertahap-akan-memulai-produksi-biodiesel-b40/', '2025-01-18T18:17:04')
    #scraper.process_url('https://www.mobilinanews.com/artikel/34112/Biodiesel-B40-Mulai-Mengaspal-Pertamina-Salurkan-Secara-Bertahap-ke-SPBU/', '2025-01-19T10:10:00')
    #scraper.process_url('https://voi.id/ekonomi/475741/pis-angkut-30-400-metrik-ton-lembaran-baja-ke-cilegon ', datepub='2025-04-15T12:34:00+07:00')
    #scraper.process_url('https://mistar.id/news/asahan/polisi-tangkap-pria-yang-aniaya-seorang-bapak-55-tahun-di-asahan') #, datepub='2025-05-07T10:09:32+07:00')        #, datepub='2025-04-28T11:35:00+07:00')

    #scraper.process_url('https://swa.co.id/read/462229/mobil-bekas-kian-diminati-olxmobbi-tawarkan-solusi-jual-beli-yang-praktis-dan-aman', manual=True)

    links = []
    #with open('scrapers/zyte/tribunnews_maret.txt', 'r') as f:
    #    for line in f:
    #        url = line.strip()
    #        if url and 'tribunnews.com' in url:
    #            links.append(url)
    
    for link in links:
        pass
        #scraper.process_url(link)
