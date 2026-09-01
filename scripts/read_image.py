#!/usr/bin/env python
"""尝试从图片中提取文字 - 使用PIL基础处理"""
from PIL import Image
import struct, os

img_dir = r'C:\Users\Administrator\AppData\Local\hermes\cache\images'
files = ['img_e50212a78764.jpg', 'img_5b76861ecaa8.jpg', 'img_8d254b2368ea.jpg']

for f in files:
    path = os.path.join(img_dir, f)
    if not os.path.exists(path):
        print(f'{f}: 不存在')
        continue
    img = Image.open(path)
    print(f'\n=== {f} ===')
    print(f'尺寸: {img.size}, 模式: {img.mode}')
    
    # 如果图片是截图且有清晰文字区域，取中间部分
    w, h = img.size
    # 取左侧1/3到中间2/3区域（通常股票列表在这里）
    crop = img.crop((0, 0, w, h//3))
    # 保存裁剪后的图片
    crop_path = path.replace('.jpg', '_crop.jpg')
    crop.save(crop_path, 'JPEG', quality=95)
    print(f'裁剪区域(上1/3)已保存: {crop_path}')
    
    # 尝试读取exif/metadata
    info = img.info
    if info:
        print(f'元数据: {list(info.keys())[:5]}')
    
    # 计算平均颜色判断是否为截图
    colors = img.getcolors(maxcolors=1000)
    if colors:
        print(f'主色调数量: {len(colors)}')