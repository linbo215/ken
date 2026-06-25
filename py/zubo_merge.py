import os
import re

M3U_DIR = "zubo"
OUTPUT_FILE = os.path.join(M3U_DIR, "zuboall.m3u")

def main():
    if not os.path.exists(M3U_DIR):
        return

    # 排除输出文件本身
    files = [f for f in os.listdir(M3U_DIR) if f.lower().endswith(".m3u") and f != "zuboall.m3u"]
    files.sort()

    if not files:
        print("⚠️ 没找到散件文件，跳过合并")
        return

    merged_lines = ["#EXTM3U"]

    for filename in files:
        group_name = os.path.splitext(filename)[0] # 自动拿文件名做组名
        file_path = os.path.join(M3U_DIR, filename)
        
        try:
            with open(file_path, "r", encoding="utf-8", errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#EXTM3U"):
                        continue
                    
                    if line.startswith("#EXTINF"):
                        # 统一注入 group-title
                        if 'group-title="' in line:
                            line = re.sub(r'group-title="[^"]+"', f'group-title="{group_name}"', line)
                        else:
                            line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
                        merged_lines.append(line)
                    else:
                        merged_lines.append(line)
        except:
            continue

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(merged_lines))
    
    print(f"✅ 合并完成: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
