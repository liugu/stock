#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用在线OCR API识别图片文字"""
import requests, json, base64, os

img_dir = r'C:\Users\Administrator\AppData\Local\hermes\cache\images'
files = ['img_e50212a78764.jpg', 'img_5b76861ecaa8.jpg', 'img_8d254b2368ea.jpg']

# 用免费OCR API
for f in files:
    path = os.path.join(img_dir, f)
    if not os.path.exists(path):
        continue
    
    with open(path, 'rb') as img:
        b64 = base64.b64encode(img.read()).decode()
    
    print(f'\n=== {f} ===')
    
    # OCR.space API (free tier)
    try:
        r = requests.post('https://api.ocr.space/parse/image',
            data={
                'base64Image': f'data:image/jpeg;base64,{b64}',
                'language': 'chs',  # 简体中文
                'OCREngine': 2,
                'scale': True,
                'isTable': True,
            },
            headers={'apikey': 'helloworld'},  # free demo key
            timeout=30
        )
        data = r.json()
        if data.get('ParsedResults'):
            text = data['ParsedResults'][0].get('ParsedText', '')
            if text.strip():
                print('OCR结果:')
                print(text[:2000])
            else:
                print('OCR未识别到文字')
        else:
            err = data.get('ErrorMessage', 'unknown')
            print(f'OCR错误: {err}')
    except Exception as e:
        print(f'OCR请求失败: {e}')
    
    # 备用: 用百度OCR (需要API Key)
    # ...