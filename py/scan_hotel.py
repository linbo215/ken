import os, re, requests, concurrent.futures
from urllib.parse import urlparse

# ================= 配置区 =================
HOTEL_DIR = "./hotel"
RESULT_TXT = "hotel_output.txt" 
TIMEOUT = 3 
MAX_WORKERS = 150 # 爆破时线程数建议保持在高位
HEADERS = {"User-Agent": "Lavf/58.29.100"}
# ==========================================

def check_url(url):
    try:
        r = requests.get(url.replace('&amp;', '&'), headers=HEADERS, timeout=TIMEOUT, stream=True)
        return url if r.status_code in [200, 206] else None
    except: return None

def extract_from_m3u(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    pattern = r'#EXTINF:.*?,(.*?)\n(https?://[^\s,\"\']+)'
    items = re.findall(pattern, content)
    if not items: return None
    first_url = items[0][1].replace('&amp;', '&')
    host = urlparse(first_url).netloc
    channels = []
    for name, url in items:
        p = urlparse(url.replace('&amp;', '&'))
        channels.append({"name": name.strip(), "path": p.path + (f"?{p.query}" if p.query else "")})
    return {"host": host, "channels": channels}

def save_realtime(host, channels, tag=""):
    """实时写入并打印"""
    with open(RESULT_TXT, "a", encoding="utf-8") as f:
        f.write(f"{host},#genre#\n")
        for c in channels:
            f.write(f"{c['name']},http://{host}{c['path']}\n")
        f.write("\n")
    print(f"✨ [{tag}] 已上线: {host}")

def run_scan():
    if os.path.exists(RESULT_TXT): os.remove(RESULT_TXT)
    
    print("📂 正在聚合原始基因...")
    all_genes = {}
    m3u_files = [f for f in os.listdir(HOTEL_DIR) if f.lower().endswith(".m3u")]
    for f in m3u_files:
        gene = extract_from_m3u(os.path.join(HOTEL_DIR, f))
        if gene: all_genes[gene['host']] = gene['channels']

    final_live_hosts = set()
    failed_genes = {}

    # --- 阶段 1: 快速检测 ---
    print(f"⚡ 阶段 1: 快速检测 {len(all_genes)} 个原始 IP...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_host = {executor.submit(check_url, f"http://{h}{c[0]['path']}"): (h, c) for h, c in all_genes.items()}
        for future in concurrent.futures.as_completed(future_to_host):
            host, channels = future_to_host[future]
            if future.result():
                save_realtime(host, channels, tag="现成")
                final_live_hosts.add(host)
            else:
                failed_genes[host] = channels

    # --- 阶段 2: C 段爆破 ---
    print(f"\n📡 阶段 2: 启动 C 段深度扫描 (剩余 {len(failed_genes)} 个待处理网段)...")
    processed_nets = set()
    
    for host, channels in failed_genes.items():
        # 提取网段
        ip_parts = host.split(':')[0].split('.')
        if len(ip_parts) < 4: continue
        prefix = ".".join(ip_parts[:3])
        port = host.split(':')[1] if ':' in host else "80"
        
        # 策略：如果该网段已经有活着的 IP 了，或者已经扫过了，就跳过
        if prefix in processed_nets: continue
        if any(h.startswith(prefix) for h in final_live_hosts): continue
        
        processed_nets.add(prefix)
        print(f"🔍 正在扫荡网段: {prefix}.x:{port}...")
        
        scan_urls = [f"http://{prefix}.{i}:{port}{channels[0]['path']}" for i in range(1, 255)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 同样使用 as_completed 保证爆破时也是出一个弹一个
            future_to_url = {executor.submit(check_url, url): url for url in scan_urls}
            for future in concurrent.futures.as_completed(future_to_url):
                res_url = future.result()
                if res_url:
                    new_host = urlparse(res_url).netloc
                    if new_host not in final_live_hosts:
                        save_realtime(new_host, channels, tag="复活")
                        final_live_hosts.add(new_host)

    print("\n✅ 深度扫描结束！")

if __name__ == "__main__":
    run_scan()
