import urllib.request
import urllib.parse
import re
import zipfile
import io
import os
import shutil

class DaFontDownloader:
    """Utility class to search and download fonts from dafont.com."""
    
    BASE_URL = "https://www.dafont.com"
    SEARCH_URL = "https://www.dafont.com/search.php?q="
    
    @staticmethod
    def search_and_download(font_display_name: str, download_dir: str) -> str | None:
        """
        Mencari font di DaFont berdasarkan namanya dan mendownloadnya.
        Mengembalikan path ke file .ttf atau .otf yang berhasil didownload dan diekstrak,
        atau None jika gagal/tidak ditemukan.
        """
        try:
            # 1. Cari di search page
            query_url = DaFontDownloader.SEARCH_URL + urllib.parse.quote(font_display_name)
            req = urllib.request.Request(query_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('ISO-8859-1', errors='ignore')
                
            # 2. Ambil link download pertama
            links = re.findall(r'href="([^"]*dl[^"]*)"', html)
            if not links:
                print(f"[DaFont] No download links found for '{font_display_name}'")
                return None
                
            dl_url = links[0]
            if dl_url.startswith('//'):
                dl_url = 'https:' + dl_url
            elif dl_url.startswith('/'):
                dl_url = DaFontDownloader.BASE_URL + dl_url
                
            print(f"[DaFont] Found download link for '{font_display_name}': {dl_url}")
            
            # 3. Download file ZIP
            dl_req = urllib.request.Request(dl_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(dl_req, timeout=30) as dl_res:
                zip_data = dl_res.read()
                
            # 4. Ekstrak file .ttf atau .otf
            os.makedirs(download_dir, exist_ok=True)
            
            extracted_path = None
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                for name in z.namelist():
                    if name.lower().endswith(('.ttf', '.otf', '.ttc', '.otc')):
                        # Hilangkan path direktori di dalam ZIP (jika ada folder)
                        basename = os.path.basename(name)
                        if not basename:
                            continue
                            
                        # Tulis isinya ke folder tujuan
                        dest_path = os.path.join(download_dir, basename)
                        with z.open(name) as source, open(dest_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        
                        extracted_path = dest_path
                        print(f"[DaFont] Successfully downloaded and extracted: {basename}")
                        break # Ambil font pertama yang ditemukan saja
                        
            return extracted_path
            
        except Exception as e:
            print(f"[DaFont] Error downloading '{font_display_name}': {e}")
            return None
