import os, shutil, re

HOTEL_OUTPUT = "hotel_output.txt"
REBORN_DIR = "./hotels"
LOGO_BASE_URL = "https://tb.yubo.qzz.io/logo/"

def clean_channel_name(name):
    name = re.sub(r'(高清|标清|普清|超清|超高清|H\.265|4K|HD|SD|hd|sd)', '', name, flags=re.I)
    name = re.sub(r'[\(\)\[\]\-\s]+', '', name)
    return name.strip()

def rebuild():
    if not os.path.exists(HOTEL_OUTPUT): return
    if os.path.exists(REBORN_DIR): shutil.rmtree(REBORN_DIR)
    os.makedirs(REBORN_DIR)

    with open(HOTEL_OUTPUT, "r", encoding="utf-8") as f:
        content = f.read().strip().split("\n\n")

    all_m3u = ["#EXTM3U"]
    for section in content:
        lines = section.strip().split("\n")
        if not lines: continue
        host = lines[0].split(",")[0]
        safe_host = host.replace('.', '_').replace(':', '_')
        
        single_m3u = ["#EXTM3U"]
        for cl in lines[1:]:
            if "," in cl:
                name, url = cl.split(",", 1)
                clean_n = clean_channel_name(name)
                header = f'#EXTINF:-1 tvg-name="{clean_n}" tvg-logo="{LOGO_BASE_URL}{clean_n}.png" group-title="Hotel_{host}",{clean_n}'
                single_m3u.extend([header, url])
                all_m3u.extend([header, url])
        
        with open(os.path.join(REBORN_DIR, f"REBORN_{safe_host}.m3u"), "w", encoding="utf-8") as f_out:
            f_out.write("\n".join(single_m3u))

    with open(os.path.join(REBORN_DIR, "ALL.m3u"), "w", encoding="utf-8") as f_all:
        f_all.write("\n".join(all_m3u))
    print(f"🌟 洗版完成！")

if __name__ == "__main__":
    rebuild()
