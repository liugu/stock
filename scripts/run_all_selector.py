#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键执行所有选股策略并输出JSON格式结果"""
import sys, os, subprocess, json, re
from datetime import date
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

ROOT = 'E:/量化研究/workspace/stock'
PY = ROOT + '/venv/Scripts/python'

STRATEGIES = [
    ('老鸭头形态', 'scripts/select_old_duck_head.py'),
    ('金蜘蛛形态', 'scripts/select_golden_spider.py'),
    ('红三兵形态', 'scripts/select_red_three_soldiers.py'),
    ('早晨之星', 'scripts/select_morning_star.py'),
    ('突破选股', 'scripts/select_breakthrough.py'),
    ('回调买入', 'scripts/select_pullback_buy.py'),
    ('均线粘合', 'scripts/select_ma_convergence.py'),
    ('回调支撑', 'scripts/select_pullback_support.py'),
    ('稳健长牛', 'scripts/select_stable_longterm.py'),
    ('趋势向上', 'scripts/select_uptrend.py'),
    ('放量上涨', 'scripts/select_volume_bullish.py'),
    ('连续小阳线', 'scripts/select_consecutive_bullish.py'),
]

def extract_stocks_from_output(name, output):
    """从输出中提取股票列表"""
    stocks = []
    lines = output.split('\n')
    
    # 查找选股结果区域
    in_result = False
    found_headers = {'代码', '名称', '价格', '涨幅'}
    
    # 常见股票行格式: 代码+名称+数字
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # 跳过标题行
        if any(kw in line for kw in ['====', '日期', '选股结果', '共找到', '策略', '获取', '筛选',
                                      '其中', '精选', '推荐', '其他', '候选', '结果已保存', '未找到',
                                      '--', '买点', '信号', '量比', 'MACD', 'MA5', 'MA10', 'MA20',
                                      '文件', '输出']):
            continue
            
        # 匹配股票行: 开头是代码(6位数字) 或 名称+代码
        m = re.match(r'[（(]?\s*(\d{6})\s*[)）]?\s*$', line_stripped)
        if m:
            code = m.group(1)
            # 往前看有没有名字
            stocks.append(code)
            continue
        
        # 匹配 "股票名 代码" 格式
        m = re.match(r'[【\[]?(.+?)[】\]]?\s*[（(]?(\d{6})[)）]?', line_stripped)
        if m:
            name, code = m.group(1), m.group(2)
            stocks.append(code)
            continue
        
        # 匹配纯6位数字开头
        m = re.match(r'(\d{6})\s', line_stripped)
        if m:
            stocks.append(m.group(1))
    
    return list(set(stocks))  # 去重

results = {}

for name, script in STRATEGIES:
    full_path = os.path.join(ROOT, script)
    if not os.path.exists(full_path):
        print(json.dumps({'strategy': name, 'status': 'SKIP', 'count': 0, 'error': '脚本不存在'}))
        continue
    
    try:
        r = subprocess.run([PY, full_path], capture_output=True, text=True, timeout=120, cwd=ROOT)
        output = r.stdout
        # 过滤警告
        clean = '\n'.join(l for l in output.split('\n') if 'UserWarning' not in l and 'pandas only supports' not in l)
        
        # 提取股票数量
        count_match = re.search(r'共找到\s*(\d+)\s*只', clean)
        if count_match:
            count = int(count_match.group(1))
        else:
            # 尝试其他计数方式
            count_match = re.search(r'(\d+)\s*只\s*股票', clean)
            count = int(count_match.group(1)) if count_match else 0
        
        # 提取具体股票代码
        codes = extract_stocks_from_output(name, clean)
        
        # 提取涨跌幅等信息
        info_lines = []
        for line in clean.split('\n'):
            line = line.strip()
            if re.match(r'.*?\d{6}.*', line) and '选股结果' not in line and '====' not in line:
                info_lines.append(line)
        
        result = {
            'strategy': name,
            'status': 'OK',
            'count': count,
            'codes': codes[:20],  # 限制显示
            'total_codes': len(codes),
            'info_preview': info_lines[:10],
            'output_summary': clean[-800:] if len(clean) > 800 else clean
        }
        results[name] = result
        print(json.dumps(result, ensure_ascii=False, indent=2)[:200])
        
    except subprocess.TimeoutExpired:
        result = {'strategy': name, 'status': 'TIMEOUT', 'count': 0}
        results[name] = result
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        result = {'strategy': name, 'status': 'ERROR', 'error': str(e)[:100]}
        results[name] = result
        print(json.dumps(result, ensure_ascii=False))

# 最终汇总
print('\n' + '='*60)
print(f'选股执行完毕 - {date.today()}')
print('='*60)
for name, r in results.items():
    emoji = '✅' if r.get('status') == 'OK' else '❌'
    c = r.get('count', 0) or r.get('total_codes', 0) or 0
    print(f'  {emoji} {name}: {c}只')

total = sum(r.get('count', 0) or r.get('total_codes', 0) or 0 for r in results.values())
print(f'\n共 {len(results)} 个策略，选出 {total} 只次')
