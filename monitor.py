#!/usr/bin/env python3
import os, re, json, hashlib, feedparser, requests

USERNAMES   = [u.strip() for u in os.environ.get('X_USERNAMES', '').split(',') if u.strip()]
NTFY_TOPIC  = os.environ.get('NTFY_TOPIC', '')
RSSHUB_BASE = os.environ.get('RSSHUB_BASE', 'https://rsshub.app').rstrip('/')
SEEN_FILE   = 'seen_ids.json'

print(f'监控账号: {USERNAMES}')
print(f'ntfy频道: {NTFY_TOPIC}')

def is_first_run(): return not os.path.exists(SEEN_FILE)
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f: return json.load(f)
    return {}
def save_seen(seen):
    with open(SEEN_FILE, 'w') as f: json.dump(seen, f)
def make_id(entry):
    raw = entry.get('id') or entry.get('link') or ''
    return hashlib.md5(raw.encode()).hexdigest()
def strip_html(text): return re.sub(r'<[^>]+>', '', text).strip()
def send_ntfy(title, body, url=''):
    if not NTFY_TOPIC:
        print('未设置NTFY_TOPIC，跳过通知')
        return
    headers = {'Title': title.encode(), 'Priority': 'default'}
    if url: headers['Click'] = url
    try:
        r = requests.post(f'https://ntfy.sh/{NTFY_TOPIC}', data=body.encode(), headers=headers, timeout=10)
        print(f'ntfy响应: {r.status_code}')
    except Exception as e:
        print(f'ntfy发送失败: {e}')

def check_user(username, seen, first_run):
    url = f'{RSSHUB_BASE}/twitter/user/{username}'
    print(f'获取RSS: {url}')
    try:
        feed = feedparser.parse(url)
        print(f'获取到 {len(feed.entries)} 条推文')
    except Exception as e:
        print(f'RSS获取失败: {e}')
        return seen
    known = set(seen.get(username, []))
    new_ids = []
    for entry in feed.entries:
        eid = make_id(entry)
        if eid not in known:
            new_ids.append(eid)
            if not first_run:
                body = strip_html(entry.get('summary', ''))[:200]
                send_ntfy(f'𝕏 @{username} 发了新推文', body or '点击查看', entry.get('link',''))
    print(f'新推文: {len(new_ids)} 条，首次运行: {first_run}')
    seen[username] = (new_ids + list(known))[:100]
    return seen

first_run = is_first_run()
seen = load_seen()
for u in USERNAMES: seen = check_user(u, seen, first_run)
save_seen(seen)
print('✅ 完成')
