#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将图片转为灰度+放大，尝试提取文字区域信息"""
from PIL import Image, ImageFilter, ImageEnhance
import os

img_dir = r'C:\Users\Administrator\AppData\Local\hermes\cache\images'
files = ['img_e50212a78764.jpg', 'img_5b76861ecaa8.jpg', 'img_8d254b2368ea.jpg']

for f in files:
    path = os.path.join(img_dir, f)
    img = Image.open(path).convert('L')  # 灰度
    w, h = img.size
    
    # 增强对比度
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    
    # 保存增强版
    enhanced_path = path.replace('.jpg', '_enhanced.jpg')
    img.save(enhanced_path, 'JPEG', quality=95)
    
    print(f'\n=== {f} ({w}x{h}) ===')
    
    # 分析像素分布来确定文字区域
    pixels = list(img.getdata())
    # 计算哪些行有大量暗像素（文字）
    text_lines = []
    for y in range(h):
        row = pixels[y*w:(y+1)*w]
        dark_pixels = sum(1 for p in row if p < 128)
        text_ratio = dark_pixels / w
        if text_ratio > 0.05:  # 该行有>5%的暗像素，可能是文字行
            text_lines.append(y)
    
    # 合并连续行成区域
    regions = []
    if text_lines:
        start = text_lines[0]
        end = text_lines[0]
        for y in text_lines[1:]:
            if y - end <= 2:
                end = y
            else:
                regions.append((start, end))
                start = y
                end = y
        regions.append((start, end))
    
    print(f'检测到 {len(regions)} 个文字区域:')
    for i, (y1, y2) in enumerate(regions[:10]):
        height = y2 - y1
        print(f'  区域{i+1}: y={y1}-{y2} (高度{height}px)')
    
    print(f'增强版已保存: {enhanced_path}')