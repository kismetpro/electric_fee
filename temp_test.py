import requests
from bs4 import BeautifulSoup
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
LOGIN_URL = "https://electricfee.vip.cpolar.cn/default.aspx"
r = requests.get(LOGIN_URL, headers=headers)
print('Status:', r.status_code)
print('Final URL:', r.url)
print('Text preview:', r.text[:500])
try:
    s = BeautifulSoup(r.text, 'html.parser')
    select = s.find('select', {'id': 'drlouming'})
    print('Select found:', bool(select))
    if select:
        print('Options count:', len(select.find_all('option')))
    else:
        print('No select, possible error page')
except Exception as e:
    print('Parse error:', e)