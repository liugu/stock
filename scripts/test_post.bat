@echo off
cd /d E:\量化研究\workspace\stock
venv\Scripts\python -c "
import requests, json

s = requests.Session()

# Read ALL cookies
with open('output/xueqiu_cookies.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            name, value = line.split('=', 1)
            s.cookies.set(name, value, domain='.xueqiu.com')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# Post a very simple status
r = s.post('https://xueqiu.com/statuses/update.json',
           headers=headers,
           data={'status': 'test'},
           timeout=30)
print('Status:', r.status_code)
print('Response:', r.text[:300])

# Try getting the user's own profile
r2 = s.get('https://xueqiu.com/settings/profile',
           headers={**headers, 'Accept': 'text/html,application/xhtml+xml'},
           timeout=30)
print()
print('Profile page:', r2.status_code)
if 'screen_name' in r2.text:
    import re
    name = re.search(r'screen_name[^>]*>([^<]+)', r2.text)
    if name:
        print('Logged in as:', name.group(1))
else:
    print('Not logged in or WAF blocked')
"