import os
import re
import requests
import shutil
import base64
import time

# --- 配置区 ---
SOURCE_URLS = [
    "https://boyu.ccwu.cc/sub2",
    "https://iptv-spider-production.up.railway.app/sub?21KOJtUp=txt"
]
OUTPUT_DIR = "temp_zubo"

# 🛠️ 修复点：这里加上了注释符号 #，不再报错
# GitHub 配置
GITHUB_TOKEN = os.getenv("LIVE_TOKEN")
GITHUB_REPO = "linbo215/lives"
GITHUB_BRANCH = "main"
GITHUB_FOLDER = "zubo"
# --- --- --- ---

def translate_isp(raw_isp):
    if not raw_isp: return "其他"
    isp_str = raw_isp.upper()
    if any(x in isp_str for x in ["CHINANET", "TELECOM", "电信"]): return "电信"
    if any(x in isp_str for x in ["CNC", "UNICOM", "联通"]): return "联通"
    if any(x in isp_str for x in ["MOBILE", "CMI", "铁通", "移动"]): return "移动"
    if any(x in isp_str for x in ["CERNET", "教育网"]): return "教育网"
    if any(x in isp_str for x in ["CRTC", "BROADCAST", "广电"]): return "广电"
    cleaned = re.sub(r'[a-zA-Z\s\.\-_]', '', raw_isp)
    return cleaned if cleaned else "其他"

def get_ip_info(ip):
    try:
        time.sleep(1) # 限制频率
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            region = data.get('regionName', '').replace("省", "").replace("市", "")
            isp = translate_isp(data.get('isp', ''))
            return f"{region}{isp}"
    except:
        pass
    return "未知"

def upload_to_github(file_path, file_name):
    """加入坚固 Timeout 防御的上传逻辑"""
    if not GITHUB_TOKEN:
        print(f"❌ 缺失 Token，无法上传 {file_name}")
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}/{file_name}"
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
            "message": f"🤖 Auto-update zubo: {file_name}",
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
        print(f"❌ 上传异常 ({file_name}): {e}")

def main():
    if not GITHUB_TOKEN:
        print("❌ 未检测到 LIVE_TOKEN，请检查 GitHub Secrets 配置！")
        return

    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ip_groups = {}
    
    for source_url in SOURCE_URLS:
        print(f"\n📥 正在获取源数据: {source_url}")
        try:
            r = requests.get(source_url, timeout=15)
            r.encoding = 'utf-8'
            lines = r.text.split('\n')
        except Exception as e:
            print(f"❌ 获取源失败 ({source_url}): {e}")
            continue

        for line in lines:
            line = line.strip()
            if ',' not in line or "#genre#" in line: continue
            parts = line.split(',', 1)
            if len(parts) < 2: continue
            name, url = parts[0].strip(), parts[1].strip()
            
            if re.search(r'(CCTV)(\d+)', name, re.IGNORECASE):
                name = re.sub(r'(CCTV)(\d+)', r'\1-\2', name, flags=re.IGNORECASE)
            
            match = re.search(r'://([\d\.]+):(\d+)', url)
            if match:
                host = match.group(1)
                port = match.group(2)
                key = f"{host}:{port}"
                
                if key not in ip_groups:
                    print(f"🔍 发现新组播 IP 节点: {host} ... ", end="", flush=True)
                    info = get_ip_info(host)
                    print(f"结果: {info}")
                    
                    ip_groups[key] = {
                        "filename": f"{info}_{host.replace('.', '_')}_{port}.m3u",
                        "channels": [],
                        "seen_urls": set() # 用于应用内 URL 去重
                    }
                
                if url not in ip_groups[key]["seen_urls"]:
                    ip_groups[key]["channels"].append({"name": name, "url": url})
                    ip_groups[key]["seen_urls"].add(url)

    if not ip_groups:
        print("\n⚠️ 未从所有源中解析到任何新的有效数据")
        return

    print(f"\n🚀 开始上传 {len(ip_groups)} 个组播 IP 节点到 GitHub...")
    for key, data in ip_groups.items():
        filename = data["filename"]
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in data["channels"]:
                f.write(f"#EXTINF:-1,{ch['name']}\n{ch['url']}\n")
        
        upload_to_github(filepath, filename)

    print("\n✨ Zubo 多源同步任务全部完成！")

if __name__ == "__main__":
    main()
