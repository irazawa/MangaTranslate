import os
import json
import hashlib
import cv2
import numpy as np

class ResultCache:
    def __init__(self, filename="ocr_translation_cache.json"):
        # Determine the root directory of the project
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.cache_dir = os.path.join(self.root_dir, '.cache')
        self.cache_file = os.path.join(self.cache_dir, filename)
        
        # Ensure cache directory exists
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception:
                pass
                
        self.cache = {}
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as fh:
                    self.cache = json.load(fh)
            except Exception as e:
                print(f"Error loading cache: {e}")
                self.cache = {}

    def save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as fh:
                json.dump(self.cache, fh, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")

    @staticmethod
    def image_to_bytes(cropped_cv_img):
        try:
            if cropped_cv_img is None:
                return b''
            # Encode image to PNG format to get portable bytes
            success, encoded_img = cv2.imencode('.png', cropped_cv_img)
            if success:
                return encoded_img.tobytes()
        except Exception:
            pass
        return b''

    @staticmethod
    def compute_hash(img_bytes):
        if not img_bytes:
            return ''
        return hashlib.sha256(img_bytes).hexdigest()

    def get(self, image_hash):
        if not image_hash:
            return None
        # Returns a tuple (original_text, translated_text) or None
        data = self.cache.get(image_hash)
        if isinstance(data, list) and len(data) >= 2:
            return (data[0], data[1])
        return None

    def put(self, image_hash, original_text, translated_text):
        if not image_hash:
            return
        self.cache[image_hash] = [original_text, translated_text]
        self.save_cache()

# Create a singleton instance
ocr_translation_cache = ResultCache()
