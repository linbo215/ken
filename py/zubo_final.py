import requests
import re
import os
import time
import base64
import random
import sys
from datetime import datetime

# ======================
# 配置区
# ======================
LOCAL_SOURCE = "data/shushu_home.html"
OUTPUT_DIR = "zubo"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.txt")
TIMEOUT = 25  # 增加超时容忍度

# 重新排列端口：把你确定的 8880 放在最前面，增加成功率
PRIMARY_PORTS = [6636, 16888, 5002, 3333, 8188, 8055, 8288, 8822, 5050, 8880, 5555, 55555, 58888, 7000, 7700, 6003, 9988, 9999, 8012, 6011, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8003, 6001, 8899
]


def get_random_ua():
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(ua_list)

def log_process(msg, end='\n'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    sys.stdout.write(f"[{timestamp}] {msg}{end}")
    sys.stdout.flush()

def scan_zubo(ip, port):
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    sys.stdout.write(f"    🔎 尝试端口 {port: <5} ... ")
    sys.stdout.flush()
    
    try:
        # 更加随机的等待，模拟人工操作
        time.sleep(random.uniform(4, 7))
        
        headers = {
            "User-Agent": get_random_ua(),
            "Referer": "https://iptv.cqshushu.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }
        
        # 组播探测
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if res.status_code == 200:
            content = res.text
            # --- 降低门槛：只要有播放链接就算成功 ---
            if "#EXTM3U" in content and ("rtp://" in content or "http" in content):
                rtp_count = content.count("rtp://")
                http_count = content.count("http") - 1
                total = rtp_count + http_count
                
                if total > 0:
                    sys.stdout.write(f"【✅ 成功: 发现 {total} 条频道】\n")
                    return content
                else:
                    sys.stdout.write("【✕ 列表为空】\n")
            elif "请稍候" in content:
                sys.stdout.write("【🛡️ 被拦截/需验证】\n")
            else:
                sys.stdout.write("【✕ 非直播流文件】\n")
        else:
            sys.stdout.write(f"【✕ 状态码 {res.status_code}】\n")
            
    except Exception as e:
        sys.stdout.write(f"【⏰ 失败/超时】\n")
    
    sys.stdout.flush()
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_process("🚀 组播源深度采集任务启动")
    
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())

    if not os.path.exists(LOCAL_SOURCE):
        log_process(f"❌ 找不到源码: {LOCAL_SOURCE}")
        return

    with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
        html = f.read()

    # 提取所有 gotoIP 里面的 multicast IP
    matches = re.findall(r"gotoIP\('([^']+)',\s*'multicast'\)", html)
    
    extracted_ips = []
    for b64_str in matches:
        try:
            b64_str += '=' * (-len(b64_str) % 4)
            ip = base64.b64decode(b64_str).decode('utf-8')
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                if ip not in extracted_ips:
                    extracted_ips.append(ip)
        except: continue

    # 取最新的 10 个组播源
    target_ips = extracted_ips[::-1][:10]
    log_process(f"📊 扫描到 {len(target_ips)} 个有效 IP 目标")

    for idx, ip in enumerate(target_ips, 1):
        if ip in history_ips:
            log_process(f"⏭️  [{idx}/{len(target_ips)}] 跳过已存 IP: {ip}")
            continue
        
        log_process(f"📡 [{idx}/{len(target_ips)}] 扫描目标: {ip}")
        found = False
        
        for port in PRIMARY_PORTS:
            content = scan_zubo(ip, port)
            if content:
                # 寻找供应商标签
                m = re.search(r'group-title="([^"]+)"', content)
                tag = re.sub(r'[\\/:*?"<>|]', '', m.group(1).split()[-1] if m else "Zubo")
                
                filename = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                
                with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                    hf.write(f"{ip}:{port}\n")
                
                found = True
                break
        
        if not found:
            log_process(f"❌ {ip} 暂未探测到开放的组播服务")
        
        time.sleep(3)

    log_process("✨ 任务结束")

if __name__ == "__main__":
    main()
