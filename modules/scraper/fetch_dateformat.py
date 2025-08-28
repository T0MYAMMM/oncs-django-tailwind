import requests
from bs4 import BeautifulSoup
import re
import brotli
import json
import gzip
import zlib
from datetime import datetime
from dateutil import parser
from urllib.parse import urlparse

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
}

bulan_map = {
    "Januari": "January", "Februari": "February", "Maret": "March",
    "April": "April", "Mei": "May", "Juni": "June", "Juli": "July",
    "Agustus": "August", "September": "September", "Oktober": "October",
    "November": "November", "Desember": "December"
}

def decode_response(response):
    raw = response.content
    encoding = response.headers.get('Content-Encoding', '')

    decompressors = {
        'br': lambda r: brotli.decompress(r).decode('utf-8', errors='replace'),
        'gzip': lambda r: zlib.decompress(r, 16 + zlib.MAX_WBITS).decode('utf-8', errors='replace'),
        'deflate': lambda r: zlib.decompress(r).decode('utf-8', errors='replace'),
    }

    for key, func in decompressors.items():
        if key in encoding:
            try:
                return func(raw)
            except Exception:
                continue

    try:
        response.encoding = response.encoding or 'utf-8'
        return response.text
    except Exception as e:
        print(f"Final fallback decoding failed: {e}")
        return None
    
def decode_response2(response):
    content_encoding = response.headers.get('Content-Encoding', '').lower()
    if content_encoding == 'br':
        return brotli.decompress(response.content).decode('utf-8', errors='ignore')
    elif content_encoding == 'gzip':
        return gzip.decompress(response.content).decode('utf-8', errors='ignore')
    else:
        return response.text

def get_okezone_published_date(url: str) -> str:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        decoded_html = decode_response(response)
        if not decoded_html:
            raise ValueError("Unable to decode response")

        soup = BeautifulSoup(decoded_html, 'html.parser')
        meta_tag = soup.find('meta', property='article:published_time')

        if not meta_tag or not meta_tag.get('content'):
            raise ValueError("datePublished meta tag not found")

        return meta_tag['content']

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None
    
def get_gelora_published_date(url: str) -> str:
    """
    Extract the published date from a webpage using multiple methods:
    1. JSON-LD script element
    2. Meta tags
    3. Other common publication date patterns
    
    Args:
        url (str): The URL of the article
        
    Returns:
        str: ISO formatted date string or None if not found
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Assume decode_response is defined elsewhere
        html_content = decode_response(response) if 'decode_response' in globals() else response.text
        
        if not html_content:
            raise ValueError("Unable to decode HTML content")
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Extract from JSON-LD script
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                json_data = json.loads(script.string)
                
                # Handle both direct and nested JSON-LD structures
                if isinstance(json_data, list):
                    for item in json_data:
                        if item.get('datePublished'):
                            return item['datePublished']
                elif isinstance(json_data, dict):
                    # Direct access
                    if json_data.get('datePublished'):
                        return json_data['datePublished']
                    
                    # Check in @graph array if present
                    if '@graph' in json_data and isinstance(json_data['@graph'], list):
                        for graph_item in json_data['@graph']:
                            if graph_item.get('datePublished'):
                                return graph_item['datePublished']
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"Error parsing JSON-LD script: {e}")
                continue
                
        # Method 2: Extract from meta tags
        meta_tags = [
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'name': 'article:published_time'}),
            ('meta', {'property': 'og:published_time'}),
            ('meta', {'name': 'publication_date'}),
            ('meta', {'name': 'parsely-pub-date'}),
            ('meta', {'itemprop': 'datePublished'})
        ]
        
        for tag_name, attrs in meta_tags:
            tag = soup.find(tag_name, attrs)
            if tag and tag.get('content'):
                return tag['content']
                
        # Method 3: Look for time elements with datetime attribute
        time_tags = soup.find_all('time')
        for time_tag in time_tags:
            if time_tag.get('datetime'):
                return time_tag['datetime']
                
        # Method 4: Look for a schema.org datePublished in any element
        date_published_elements = soup.find_all(attrs={'itemprop': 'datePublished'})
        for element in date_published_elements:
            if element.get('content'):
                return element['content']
                
        # If no date was found, try fallback with regex pattern for dates
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})',  # ISO 8601 with timezone
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)',                # ISO 8601 UTC
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'                  # Common format
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
                
        print(f"Could not find published date for URL: {url}")
        return None
        
    except Exception as e:
        print(f"Error processing {url}: {e}", exc_info=True)
        return None

def get_general_published_date(url: str) -> str:
    """
    Extract the published date from a webpage using multiple methods:
    1. JSON-LD script element
    2. Meta tags
    3. Other common publication date patterns
    
    Args:
        url (str): The URL of the article
        
    Returns:
        str: ISO formatted date string or None if not found
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Assume decode_response is defined elsewhere
        html_content = decode_response(response) if 'decode_response' in globals() else response.text
        
        if not html_content:
            raise ValueError("Unable to decode HTML content")
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Extract from JSON-LD script
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                json_data = json.loads(script.string)
                
                # Handle both direct and nested JSON-LD structures
                if isinstance(json_data, list):
                    for item in json_data:
                        if item.get('datePublished'):
                            return item['datePublished']
                elif isinstance(json_data, dict):
                    # Direct access
                    if json_data.get('datePublished'):
                        return json_data['datePublished']
                    
                    # Check in @graph array if present
                    if '@graph' in json_data and isinstance(json_data['@graph'], list):
                        for graph_item in json_data['@graph']:
                            if graph_item.get('datePublished'):
                                return graph_item['datePublished']
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"Error parsing JSON-LD script: {e}")
                continue
                
        # Method 2: Extract from meta tags
        meta_tags = [
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'name': 'article:published_time'}),
            ('meta', {'property': 'og:published_time'}),
            ('meta', {'name': 'publication_date'}),
            ('meta', {'name': 'parsely-pub-date'}),
            ('meta', {'itemprop': 'datePublished'})
        ]
        
        for tag_name, attrs in meta_tags:
            tag = soup.find(tag_name, attrs)
            if tag and tag.get('content'):
                return tag['content']
                
        # Method 3: Look for time elements with datetime attribute
        time_tags = soup.find_all('time')
        for time_tag in time_tags:
            if time_tag.get('datetime'):
                return time_tag['datetime']
                
        # Method 4: Look for a schema.org datePublished in any element
        date_published_elements = soup.find_all(attrs={'itemprop': 'datePublished'})
        for element in date_published_elements:
            if element.get('content'):
                return element['content']
                
        # If no date was found, try fallback with regex pattern for dates
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})',  # ISO 8601 with timezone
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)',                # ISO 8601 UTC
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'                  # Common format
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
                
        print(f"Could not find published date for URL: {url}")
        return None
        
    except Exception as e:
        print(f"Error processing {url}: {e}", exc_info=True)
        return None

def get_fajar_published_date(url: str) -> str:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        decoded_html = decode_response(response)
        if not decoded_html:
            raise ValueError("Unable to decode response")

        soup = BeautifulSoup(decoded_html, 'html.parser')
        meta_tag = soup.find('meta', property='article:published_time')

        if not meta_tag or not meta_tag.get('content'):
            raise ValueError("datePublished meta tag not found")

        return meta_tag['content']

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

def get_thevibes_published_date(url: str) -> str:
    try:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            #'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',

            'Cookie': '_gcl_au=1.1.898236809.1754900430; sticky_lb_sess_id=0ppuyhhu43v; _gid=GA1.2.883091596.1754991752; cf_clearance=_7etxk4CFjs9iq.WI2hyKNe_m.vOE3D5gNQyTBXp.ps-1754991752-1.2.1.1-ArTPEGSnRDLAauWoLJRY6vUHtWxllR_X4Zmu6Pf1GYAqQxG9RK3.Gowlpr3yq.rCMqJs9P3bpY335rpSM6NGnsPBOh1nRogs8On.mz4iWoC_ZOkUt4r5BUnfd1ciuJWD7PZBdSQEYgpjbPB.a0UsLEWUuL3yRaa6Aa4jQK_eHGRPP.H3S22Xk5BVARSy5L8slXrWzZ_BhxUJfamb9ywDxyeVuZshmg_bi4sQoGADfCY; fpestid=-mCZz5fUE073a4aU9Hj6Cg-6RLnrYyMhUn6Umesg64mRNC7IPtL2PV7WZNxQhyPADFNguw; _ga=GA1.1.959521230.1754900430; _ga_8P1ZP8TZGZ=GS2.1.s1754991753$o2$g1$t1754992363$j60$l0$h185396097',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        #print(response.text)

        decoded_html = decode_response(response)
        if not decoded_html:
            raise ValueError("Unable to decode response")

        soup = BeautifulSoup(decoded_html, 'html.parser')
        meta_tag = soup.find('meta', property='article:published_time')

        if not meta_tag or not meta_tag.get('content'):
            raise ValueError("date published meta tag not found")

        return meta_tag['content']

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

def convert_date_pikiranrakyat(date_str):
    bulan_map = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'Mei': '05', 'Jun': '06', 'Jul': '07', 'Agu': '08',
        'Sep': '09', 'Okt': '10', 'Nov': '11', 'Des': '12',
    }

    pattern = r'-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}),\s+(\d{2}):(\d{2})\s+WIB'
    match = re.match(pattern, date_str)

    if match:
        day, month_str, year, hour, minute = match.groups()
        month = bulan_map.get(month_str.capitalize())
        if month:
            return f"{year}-{month}-{day.zfill(2)}T{hour}:{minute}:00+07:00"

    return date_str

def convert_date_antaranews(date_str):
    bulan_map = {
        'Januari': '01', 'Februari': '02', 'Maret': '03', 'April': '04',
        'Mei': '05', 'Juni': '06', 'Juli': '07', 'Agustus': '08',
        'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
    }

    pattern = r'^\w+,\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+(\d{2}):(\d{2})\s+WIB$'
    match = re.match(pattern, date_str)

    if match:
        day, month_str, year, hour, minute = match.groups()
        month = bulan_map.get(month_str)
        if month:
            return f"{year}-{month}-{day.zfill(2)}T{hour}:{minute}:00+07:00"

    return date_str

def convert_date_investorid(date_str):
    """
    Format: '3 Mar 2025 | 10:52 WIB'
    """
    pattern = r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+\|\s+(\d{2}):(\d{2})\s+WIB'
    match = re.match(pattern, date_str.strip())
    
    if match:
        day, month_str, year, hour, minute = match.groups()
        try:
            dt = datetime.strptime(f"{day} {month_str} {year} {hour}:{minute}", "%d %b %Y %H:%M")
            return dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        except Exception as e:
            print(f"Gagal parsing investorid: {e}")
            return None
    return None

def convert_voi_date(date_str: str) -> str | None:
    """
    Convert string tanggal Indonesia ke ISO 8601 (tanpa timezone).
    Contoh: '18 Agustus 2025, 08:00 |' -> '2025-08-18T08:00:00'
    """
    try:
        # Bersihkan spasi dan tanda '|'
        clean_str = date_str.strip().strip("|").strip()
        if not clean_str:
            return None

        # Pisahkan tanggal dan waktu
        if ", " not in clean_str:
            return None
        date_part, time_part = clean_str.split(", ", 1)

        # Pecah tanggal
        parts = date_part.split()
        if len(parts) != 3:
            return None
        day, month_id, year = parts

        # Mapping bulan Indonesia -> Inggris
        month_en = bulan_map.get(month_id)
        if not month_en:
            return None

        # Bangun string bergaya Inggris
        english_date_str = f"{day} {month_en} {year} {time_part}"

        # Parse dengan strptime
        dt = datetime.strptime(english_date_str, "%d %B %Y %H:%M")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    except Exception:
        return None

def convert_indonesian_date(date_str):
    if ',' in date_str:
        date_str = date_str.split(',', 1)[1].strip()

    date_str = date_str.replace("WIB", "").strip()

    for indo, eng in bulan_map.items():
        date_str = date_str.replace(indo, eng)

    try:
        dt = datetime.strptime(date_str, "%d %B %Y %H:%M")
        return dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
    except ValueError as e:
        print("Gagal parsing:", e)
        return None

def convert_date_flex(date_str):
    clean = date_str.replace("WIB", "").replace("WITA", "").replace("WIT", "").strip()

    for indo, eng in bulan_map.items():
        if indo in clean:
            if ',' in clean:
                clean = clean.split(',', 1)[1].strip()
            clean = clean.replace(indo, eng)
            try:
                dt = datetime.strptime(clean, "%d %B %Y %H:%M")
                return dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
            except ValueError as e:
                print("Gagal parsing format Indonesia:", e)
                return None

    try:
        return parser.parse(clean).strftime("%Y-%m-%dT%H:%M:%S%z")
    except Exception as e:
        print("Gagal parsing format internasional:", e)
        return None
    
def convert_date_voi(date_str):
    """
    Format input: '2025-03-31WIB12:15:00+07:00'
    Output: '2025-03-31T12:15:00+07:00'
    """
    try:
        # Remove "WIB" and replace 'WIB' with 'T' for proper ISO format
        date_str_clean = date_str.replace("WIB", "T").strip()
        dt = parser.parse(date_str_clean)
        return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    except Exception as e:
        print(f"Gagal parsing VOI format: {e}")
        return None

def convert_date_voi_2(date_str):
    """
    Format input: '26 Maret 2025, 23:01'
    Output: '2025-03-26T23:01:00+07:00'
    """
    try:
        # Mapping bulan Indonesia ke angka
        bulan_mapping = {
            "Januari": "01", "Februari": "02", "Maret": "03",
            "April": "04", "Mei": "05", "Juni": "06",
            "Juli": "07", "Agustus": "08", "September": "09",
            "Oktober": "10", "November": "11", "Desember": "12"
        }

        # Pisah tanggal dan waktu
        parts = date_str.split(",")
        tanggal_part = parts[0].strip()  # '26 Maret 2025'
        waktu_part = parts[1].strip()    # '23:01'

        # Pisah tanggal menjadi hari, bulan, tahun
        day, bulan, year = tanggal_part.split()
        month = bulan_mapping.get(bulan)
        if not month:
            raise ValueError(f"Bulan tidak dikenali: {bulan}")

        formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)}T{waktu_part}:00+07:00"
        return formatted
    except Exception as e:
        print(f"Gagal parsing VOI_2 format: {e}")
        return None
    
def convert_date_generic_eng(date_str):
    """
    Format input: '01 Mar 2025 11:38:51'
    Output: '2025-03-01T11:38:51+07:00'
    """
    try:
        dt = datetime.strptime(date_str, "%d %b %Y %H:%M:%S")
        formatted = dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return formatted
    except Exception as e:
        print(f"Gagal parsing format generic_eng: {e}")
        return None
    
def convert_date_infopublik(date_str):
    """
    Format input: 'Kamis, 6 Maret 2025 | 11:13 WIB'
    Output: '2025-03-06T11:13:00+07:00'
    """
    try:
        # Hapus nama hari dan 'WIB'
        clean_str = date_str.split(", ")[1].replace(" WIB", "")
        date_part, time_part = clean_str.split(" | ")
        
        # Konversi bulan Indonesia ke angka
        bulan_map = {
            "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
            "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
            "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
        }

        tanggal, bulan_text, tahun = date_part.split()
        bulan = bulan_map.get(bulan_text, "01")
        waktu = f"{tahun}-{bulan.zfill(2)}-{tanggal.zfill(2)}T{time_part}:00+07:00"
        return waktu
    except Exception as e:
        print(f"Gagal parsing format voi_3: {e}")
        return None

def convert_date_serayunews(date_str):
    """
    Format input: 'Jumat, 14 Maret 2025 pukul 21.45'
    Output: '2025-03-14T21:45:00+07:00'
    """
    try:
        # Ambil hanya bagian setelah koma
        clean_str = date_str.split(", ")[1]  # '14 Maret 2025 pukul 21.45'
        parts = clean_str.split(" pukul ")
        tanggal_str = parts[0]  # '14 Maret 2025'
        waktu_str = parts[1]    # '21.45'

        # Map nama bulan
        bulan_map = {
            "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
            "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
            "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
        }

        tanggal, bulan_text, tahun = tanggal_str.split()
        jam, menit = waktu_str.split(".")

        return f"{tahun}-{bulan_map[bulan_text]}-{tanggal.zfill(2)}T{jam.zfill(2)}:{menit.zfill(2)}:00+07:00"
    except Exception as e:
        print(f"Gagal parsing format serayunews: {e}")
        return None
    
def convert_date_klikwarta(date_str):
    """
    Format input: 'Rabu, 05/03/2025 - 21:17'
    Output: '2025-03-05T21:17:00+07:00'
    """
    try:
        # Ambil bagian setelah koma
        clean_str = date_str.split(", ")[1]  # '05/03/2025 - 21:17'
        tanggal_str, waktu_str = clean_str.split(" - ")  # ['05/03/2025', '21:17']
        day, month, year = tanggal_str.split("/")

        return f"{year}-{month.zfill(2)}-{day.zfill(2)}T{waktu_str}:00+07:00"
    except Exception as e:
        print(f"Gagal parsing format klikwarta: {e}")
        return None

def convert_date_industry(date_str):
    """
    Format input: 'Jumat, 21 Maret 2025 06:00 WIB'
    Output: '2025-03-21T06:00:00+07:00'
    """
    try:
        if "| " in date_str:
            date_str = date_str.replace("| ", "")
            date_str = date_str.replace(" - ", " ")

        # Hilangkan nama hari dan WIB
        clean_str = date_str.split(", ")[1].replace(" WIB", "")
        # Pisahkan tanggal dan waktu
        date_part, time_part = clean_str.rsplit(" ", 1)
        tanggal, bulan_text, tahun = date_part.split()

        bulan_map = {
            "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
            "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
            "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
        }

        bulan = bulan_map.get(bulan_text, "01")
        return f"{tahun}-{bulan.zfill(2)}-{tanggal.zfill(2)}T{time_part}:00+07:00"
    except Exception as e:
        print(f"Gagal parsing format WIB text: {e}")
        return None

def convert_date_emiten(date_str):
    """
    Format input: '13/03/2025, 22:26 WIB'
    Output: '2025-03-01T11:38:51+07:00'
    """
    try:
        clean_str = date_str.replace(" WIB", "")
        dt = datetime.strptime(clean_str, "%d/%m/%Y, %H:%M")
        formatted = dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return formatted
    except Exception as e:
        print(f"Gagal parsing format generic_eng: {e}")
        return None

def convert_date_radarbanten(date_str):
    """
    Format input: '2025-03-27 11:22:44Asia/Jakarta'
    Output: '2025-03-01T11:38:51+07:00'
    """
    try:
        clean_str = date_str.replace("Asia/Jakarta", "")
        dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        formatted = dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return formatted
    except Exception as e:
        print(f"Gagal parsing format generic_eng: {e}")
        return None
    
def convert_date_analisadaily(date_str, url):
    """
    Format input: 'Hari ini Pkl. 11:13 WIB'
    Output: '2025-03-01T11:38:51+07:00'
    """
    try:
        clean_str = date_str.replace("Hari ini Pkl. ", "")
        clean_str = clean_str.replace(" WIB", "")

        path = urlparse(url).path
        parts = path.strip("/").split("/")
        year, month, day = parts[2], parts[3], parts[4]
        dt = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
        formatted = dt.strftime("%Y-%m-%dT") + clean_str + ":00+07:00"
        return formatted
    except Exception as e:
        print(f"Gagal parsing format generic_eng: {e}")
        return None
    
def convert_date_fortuneidn(date_str):
    """
    Format input: '18 Jul 2023, 13:14 WIB'
    Output: '2023-07-18T13:14:00+0700'
    """
    try:
        # Parse format
        dt = datetime.strptime(date_str.replace(" WIB", ""), "%d %b %Y, %H:%M")
        
        # Tambahkan offset +0700 untuk WIB
        return dt.strftime("%Y-%m-%dT%H:%M:%S+0700")
    except Exception as e:
        print(f"Gagal parsing WIB format: {e}")
        return None
    
def convert_date_kuatbaca(date_str):
    """
    Format input: '2025-03-27 11:22:44Asia/Jakarta'
    Output: '2025-03-01T11:38:51+07:00'
    """
    try:
        clean_str = date_str.replace(" WIB", "")
        dt = datetime.strptime(clean_str, "%d %B %Y %H:%M")
        formatted = dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        return formatted
    except Exception as e:
        print(f"Gagal parsing kontoolll: {e}")
        return None
    
# Contoh penggunaan
if __name__ == "__main__":
    url = "https://harian.fajar.co.id/2025/03/03/tenri-bangun-ungatawwa-handmade-produk-rajutan-yang-diminati-hingga-luar-negeri/"
    test_date = "18 Agustus 2025, 08:00 |"
    #print(convert_date_analisadaily(test_date, url))
    #print("InvestorID format:", convert_date_investorid(test_date))
    print(convert_voi_date(test_date))

    #test_flex = "Fri, 07 Mar 2025 00:29:20 +0700"
    #print("Flex format:", convert_date_flex(test_flex))
