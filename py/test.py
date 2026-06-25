import requests
import random
import time
import os
import sys
import json

# ============ 强制实时输出（关键！让 GitHub Actions 日志实时滚动） ============
sys.stdout.reconfigure(line_buffering=True)

# ============ 环境变量读取与检查 ============
print("正在加载配置...", flush=True)

required_vars = ["IP_URL", "CF_ACCOUNTS"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print(f"❌ 错误：缺少必需的环境变量: {', '.join(missing)}", flush=True)
    sys.exit(1)

SUBDOMAIN_PREFIX = os.getenv("SUBDOMAIN_PREFIX", "hao").strip() or "hao"
TTL = int(os.getenv("TTL", "120").strip() or "120")
PROXIED = os.getenv("PROXIED", "false").strip().lower() == "true"
RECORDS_PER_DOMAIN = int(os.getenv("RECORDS_PER_DOMAIN", "4").strip() or "4")
IP_URL = os.getenv("IP_URL").strip()

# 解析 CF_ACCOUNTS JSON
CF_ACCOUNTS_JSON = os.getenv("CF_ACCOUNTS")
try:
    CF_ACCOUNTS = json.loads(CF_ACCOUNTS_JSON)
except json.JSONDecodeError as e:
    print(f"❌ CF_ACCOUNTS JSON 格式错误: {e}", flush=True)
    sys.exit(1)

print(f"✅ 配置加载完成：前缀={SUBDOMAIN_PREFIX}, TTL={TTL}, Proxied={PROXIED}, 每域名记录数={RECORDS_PER_DOMAIN}", flush=True)
print(f"✅ 共 {len(CF_ACCOUNTS)} 个 Cloudflare 账号，涉及 {sum(len(acc['domains']) for acc in CF_ACCOUNTS)} 个域名", flush=True)

# ============ 函数定义 ============
def get_random_ips_from_url(ip_url, count):
    print(f"正在从 {ip_url} 下载 IP 列表...", flush=True)
    try:
        r = requests.get(ip_url, timeout=15)
        r.raise_for_status()
        ips = [line.strip() for line in r.text.splitlines() if line.strip()]
        if len(ips) < count:
            raise Exception(f"IP 数量不足（需要 {count}，实际 {len(ips)}）")
        selected = random.sample(ips, count)
        print(f"✅ 成功获取并随机选择 {len(selected)} 个 IP", flush=True)
        return selected
    except Exception as e:
        raise Exception(f"获取 IP 失败: {e}")

def get_zone_id(domain, token):
    url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data["success"] and data["result"]:
        return data["result"][0]["id"]
    raise Exception(f"获取 Zone ID 失败: {data.get('errors')}")

def get_existing_a_records(zone_id, subdomain, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={subdomain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json().get("result", [])

def delete_record(zone_id, record_id, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.delete(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data["success"]:
        print(f"✅ 删除旧记录成功: {record_id}", flush=True)
    else:
        print(f"❌ 删除失败: {record_id} -> {data.get('errors')}", flush=True)

def add_a_record(zone_id, subdomain, ip, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "type": "A",
        "name": subdomain,
        "content": ip,
        "ttl": TTL,
        "proxied": PROXIED
    }
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data["success"]:
        print(f"✅ 添加成功: {subdomain} -> {ip}", flush=True)
    else:
        print(f"❌ 添加失败: {subdomain} -> {ip} | 错误: {data.get('errors')}", flush=True)

# ============ 主函数 ============
def main():
    print(f"\n🚀 开始执行 Cloudflare DNS 更新任务 - {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    total_domains = sum(len(acc["domains"]) for acc in CF_ACCOUNTS)
    needed_ips = RECORDS_PER_DOMAIN * total_domains

    try:
        ips_to_add = get_random_ips_from_url(IP_URL, needed_ips)
    except Exception as e:
        print(f"❌ {e}", flush=True)
        sys.exit(1)

    ip_index = 0
    for account_idx, account in enumerate(CF_ACCOUNTS, 1):
        token = account["token"]
        print(f"\n📡 处理第 {account_idx}/{len(CF_ACCOUNTS)} 个账号...", flush=True)
        for domain in account["domains"]:
            subdomain = f"{SUBDOMAIN_PREFIX}.{domain}"
            print(f"\n🔄 更新子域名: {subdomain}", flush=True)

            try:
                zone_id = get_zone_id(domain, token)
            except Exception as e:
                print(f"❌ 获取 Zone ID 失败 ({domain}): {e}", flush=True)
                continue

            # 删除旧记录
            existing = get_existing_a_records(zone_id, subdomain, token)
            print(f"   发现 {len(existing)} 条旧 A 记录，正在删除...", flush=True)
            for rec in existing:
                delete_record(zone_id, rec["id"], token)
                time.sleep(0.2)

            # 添加新记录
            print(f"   添加 {RECORDS_PER_DOMAIN} 条新 A 记录...", flush=True)
            for _ in range(RECORDS_PER_DOMAIN):
                if ip_index >= len(ips_to_add):
                    print("⚠️ IP 池已耗尽，停止添加", flush=True)
                    break
                ip = ips_to_add[ip_index]
                ip_index += 1
                try:
                    add_a_record(zone_id, subdomain, ip, token)
                    time.sleep(0.2)
                except Exception as e:
                    print(f"❌ 添加失败: {e}", flush=True)

    print(f"\n🎉 所有任务完成！- {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

if __name__ == "__main__":
    main()
