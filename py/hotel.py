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
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
TIMEOUT = 25 

# 端口字典：根据你刚才的成功日志，85, 9901, 8888 都是大热门
PRIMARY_PORTS = [9999, 85, 9901, 8888, 8000, 8080, 9001, 8082, 888, 808, 8090, 8081, 50001]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 加载黑名单
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    
    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 源码文件缺失"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取所有 IP
        b64_list = re.findall(r"gotoIP\('([^']+)',\s*'hotel'\)", content)
        all_found_ips = []
        for b in b64_list:
            try:
                decoded = base64.b64decode(b).decode('utf-8')
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded) and decoded not in all_found_ips:
                    all_found_ips.append(decoded)
            except: continue

        # 我们只看网页前 6 个 IP
        target_ips = all_found_ips[:6]
        log(f"🎯 网页识别到 {len(target_ips)} 个目标 IP")

        for idx, ip in enumerate(target_ips, 1):
            if ip in history_ips:
                log(f"📡 [{idx}/6] IP: {ip} >> 【已在黑名单，跳过】")
                continue
            
            log(f"📡 [{idx}/6] 正在探测新 IP: {ip}")
            success = False
            
            for port in PRIMARY_PORTS:
                # 实时显示正在尝试的端口，不换行
                sys.stdout.write(f"  --> {port} ")
                sys.stdout.flush()

                url = f"http://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
                try:
                    time.sleep(random.uniform(2.0, 4.0)) # 适度延迟
                    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://iptv.cqshushu.com/"}
                    res = requests.get(url, headers=headers, timeout=TIMEOUT)
                    
                    if res.status_code == 200 and "#EXTINF" in res.text:
                        sys.stdout.write("【✅ 成功】\n")
                        m = re.search(r'group-title="([^"]+)"', res.text)
                        tag = re.sub(r'[\\/:*?"<>|]', '', m.group(1).split()[-1] if m else "Hotel")
                        
                        fn = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                        with open(os.path.join(OUTPUT_DIR, fn), "w", encoding="utf-8") as f:
                            f.write(res.text)
                        
                        with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                            hf.write(f"{ip}:{port}\n")
                        success = True
                        break
                    else:
                        sys.stdout.write("✕ ")
                except:
                    sys.stdout.write("⏰ ")
                sys.stdout.flush()
            
            if not success:
                print(f"\n❌ {ip} 扫描结束，无响应")
            time.sleep(5)

    except Exception as e:
        log(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    main()
