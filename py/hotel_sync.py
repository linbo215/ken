import os
import re
import requests
import base64
import time
import shutil
from urllib.parse import urlparse

# ================= 配置区 =================
SOURCE_URLS = [
    "https://boyu.ccwu.cc/sub1",
    "https://iptv-spider-production.up.railway.app/sub?rGzNKN5g=txt"
]
GITHUB_REPO = "linbo215/lives"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = os.getenv("LIVE_TOKEN")
REMOTE_FOLDER = "hotel"
OUTPUT_DIR = "temp_hotel" # 落地临时目录，方便 Debug

IP_API = "http://ip-api.com/json/{}?fields=status,regionName,city&lang=zh-CN"
# ==========================================

def get_ip_location(ip):
    try:
        time.sleep(1) # 频率限制保护
        r = requests.get(IP_API.format(ip), timeout=5)
        data = r.json()
        if data.get('status') == 'success':
            reg = data.get('regionName', '').replace('省', '').replace('市', '')
            cit = data.get('city', '').replace('省', '').replace('市', '')
            return reg if reg == cit else f"{reg}{cit}"
    except: 
        pass
    return "未知属地"

def upload_to_github(file_path, file_name):
    """安全且带有超时的 GitHub 上传逻辑"""
    if not GITHUB_TOKEN:
        print(f"❌ 缺失 Token，无法上传 {file_name}")
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{REMOTE_FOLDER}/{file_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    sha = None
    try:
        get_res = requests.get(url, headers=headers, timeout=10)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")
    except Exception as e:
        print(f"⚠️ 获取 SHA 失败 ({file_name}): {e}")

    try:
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        data = {
            "message": f"🤖 Auto-update hotel: {file_name}",
            "content": content,
            "branch": GITHUB_BRANCH
        }
        if sha:
            data["sha"] = sha

        put_res = requests.put(url, headers=headers, json=data, timeout=15)
        if put_res.status_code in [200, 201]:
            print(f"✅ GitHub 同步成功: {file_name}")
        else:
            print(f"❌ GitHub 同步失败 ({file_name}): {put_res.status_code}")
    except Exception as e:
        print(f"❌ 上传过程发生异常 ({file_name}): {e}")

def run():
    print("📥 正在运行 Hotel 同步...")
    if not GITHUB_TOKEN:
        print("❌ 警告：未检测到环境中的 LIVE_TOKEN！")

    # 初始化本地工作目录
    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ip_groups = {}
    total_lines_parsed = 0
    
    for url in SOURCE_URLS:
        print(f"📥 正在获取源数据: {url}")
        try:
            res = requests.get(url, timeout=15)
            res.encoding = 'utf-8' 
            lines = res.text.split('\n')
            print(f"   成功下载，共获取到 {len(lines)} 行原始数据。")
        except Exception as e:
            print(f"❌ 获取源失败 ({url}): {e}")
            continue 

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or "," not in line or "#genre#" in line: 
                continue
                
            try:
                name, stream_url = line.split(',', 1)
                name = name.strip()
                stream_url = stream_url.strip()
                
                if not stream_url.startswith("http"): continue
                host = urlparse(stream_url).netloc
                if not host: continue
                
                if re.search(r'(CCTV)(\d+)', name, re.IGNORECASE):
                    name = re.sub(r'(CCTV)(\d+)', r'\1-\2', name, flags=re.IGNORECASE)
                
                if host not in ip_groups:
                    if ':' in host:
                        ip, port = host.split(':', 1)
                    else:
                        ip, port = host, "80"
                    
                    print(f"🔍 发现新 IP 节点: {ip} ... ", end="", flush=True)
                    loc = get_ip_location(ip)
                    print(f"结果: {loc}")
                    
                    ip_groups[host] = {
                        "filename": f"{loc}_{ip.replace('.', '_')}_{port}.m3u", 
                        "channels": [],
                        "seen_sign": set() # 通过组合特征去重
                    }
                
                # 唯一特征签名字段，杜绝同一个文件内出现完全相同的频道行
                sign = f"{name}_{stream_url}"
                if sign not in ip_groups[host]["seen_sign"]:
                    ip_groups[host]["channels"].append({"name": name, "url": stream_url})
                    ip_groups[host]["seen_sign"].add(sign)
                    total_lines_parsed += 1
                    
            except Exception as line_err:
                continue

    print(f"\n📊 解析阶段结束。共清洗出 {total_lines_parsed} 个有效频道。")
    if not ip_groups:
        print("⚠️ 未解析到任何有效的酒店源数据。")
        return

    print(f"🚀 开始写盘并同步到 GitHub (共 {len(ip_groups)} 个 IP 节点)...")
    for host, data in ip_groups.items():
        filename = data["filename"]
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # 写入本地临时文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in data["channels"]:
                f.write(f'#EXTINF:-1 group-title="Hotel_{host}",{ch["name"]}\n{ch["url"]}\n')
        
        # 调用强壮版上传函数
        upload_to_github(filepath, filename)
        
    print("\n✨ Hotel 酒店源同步任务全部完成！")

if __name__ == "__main__":
    run()
