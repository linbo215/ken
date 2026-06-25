import os
import re
import requests
import concurrent.futures
import random

# ===============================
# 配置区
# ===============================
M3U_DIR = "zubo"
SAMPLE_COUNT = 3
CHECK_TIMEOUT = 10  # 稍微缩短，提高 Action 效率
SKIP_FILE = "zuboall.m3u" # 汇合大文件不参与清理探测

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check_link(url):
    try:
        # 组播源有些不支持 HEAD，直接用 GET 请求前 1KB
        response = requests.get(url, headers=HEADERS, timeout=CHECK_TIMEOUT, stream=True)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def is_m3u_alive(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors='ignore') as f:
            content = f.read()
        
        if not content.strip() or "#EXTM3U" not in content:
            return False
        
        # 更加宽松的正则，抓取所有有效 URL
        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        
        if not links:
            return False
        
        random.shuffle(links)
        test_links = links[:SAMPLE_COUNT]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=SAMPLE_COUNT) as executor:
            results = list(executor.map(check_link, test_links))
        
        return any(results)
    except:
        return False

def main():
    if not os.path.exists(M3U_DIR):
        print(f"❌ 目录 {M3U_DIR} 不存在")
        return
    
    print(f"🔍 开始清理失效的 M3U 文件...")
    
    # 获取目录下所有 m3u，并排除 zuboall.m3u
    files = [f for f in os.listdir(M3U_DIR) if f.lower().endswith(".m3u") and f != SKIP_FILE]
    
    removed_count = 0
    kept_count = 0
    
    for filename in files:
        file_path = os.path.join(M3U_DIR, filename)
        print(f"📄 正在检测: {filename} ... ", end="", flush=True)
        
        if is_m3u_alive(file_path):
            print("✅ [存活] 保留")
            kept_count += 1
        else:
            print("❌ [失效] 删除")
            os.remove(file_path)
            removed_count += 1
    
    print(f"\n✨ 清理统计: 保留 {kept_count}，删除 {removed_count}")

if __name__ == "__main__":
    main()
