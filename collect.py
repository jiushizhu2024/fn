#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions 版 Clash & V2Ray 节点订阅收集器
================================================
收集全网免费代理节点，支持非 raw.githubusercontent.com 链接优先采集，
自动转换为 Clash 标准格式和 V2Ray base64 格式，每日自动更新。

输出文件:
  clashnode.yaml  — 标准 Clash proxies 订阅
  v2raynode.txt   — 标准 V2Ray 订阅 (Base64 编码)
"""

import os, re, sys, json, time, base64, zlib, subprocess, urllib.request, ssl, traceback, socket
from urllib.parse import urlparse, parse_qs, urlencode, quote, unquote

socket.setdefaulttimeout(10)

try:
    import yaml
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    import yaml

# ============================================================
#  全局配置
# ============================================================

OUTPUT_CLASH = "clashnode.yaml"
OUTPUT_V2RAY = "v2raynode.txt"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, '..', '..') if 'workflows' in SCRIPTS_DIR else os.path.dirname(os.path.abspath(__file__)) or os.getcwd())
CLASH_PATH = os.path.join(REPO_ROOT, OUTPUT_CLASH)
V2RAY_PATH = os.path.join(REPO_ROOT, OUTPUT_V2RAY)

TIMEOUT = 15
MIN_LINKS = 48
MAX_LINKS = 66
CONCURRENT = 20

# ============================================================
#  网络请求
# ============================================================

def http_get(url, timeout=TIMEOUT):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': '*/*',
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        if resp.getcode() == 200:
            data = resp.read()
            if data[:2] == b'\x1f\x8b':
                import gzip
                data = gzip.decompress(data)
            content = data.decode('utf-8', errors='replace')
            if content and len(content) > 50 and '404 Not Found' not in content[:100]:
                return content
    except: pass
    proxy = os.environ.get('PROXY_SOCKS5', '')
    if proxy:
        try:
            r = subprocess.run(["curl", "-s", "--max-time", str(timeout), "--proxy", proxy, "-L", url],
                               capture_output=True, text=True, timeout=timeout+5)
            if r.returncode == 0 and r.stdout and '404 Not Found' not in r.stdout[:200]:
                return r.stdout
        except: pass
    try:
        r = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-L", url, "-k"],
                           capture_output=True, text=True, timeout=timeout+5)
        if r.returncode == 0 and r.stdout and len(r.stdout) > 50 and '404 Not Found' not in r.stdout[:200]:
            return r.stdout
    except: pass
    return None


# ============================================================
#  (A) 用户指定的有效链接池 (非raw.githubusercontent.com — 优先采集)
# ============================================================

def priority_links():
    """
    用户指定链接中的 「非 raw.githubusercontent.com」 链接。
    这些链接优先在第一轮采集。
    含 {Ymd} 占位符的会被替换为实际日期。
    """
    now = time.localtime()
    ymd = time.strftime('%Y%m%d', now)
    y_m_d = time.strftime('%Y/%m/%d', now)
    md = time.strftime('%m%d', now)

    raw = [
        # 非 raw.githubusercontent.com
        "https://chromego-sub.netlify.app/sub/merged_proxies_new.yaml",
        "https://git.io/emzclash",
        "https://tt.vg/freeclash",
        "https://cdn.jsdelivr.net/gh/vxiaov/free_proxies@main/clash/clash.provider.yaml",
        "https://github.com/ermaozi/get_subscribe/raw/refs/heads/main/subscribe/clash.yml",
        "https://github.com/anaer/Sub/raw/refs/heads/main/clash.yaml",
        "https://nodefree.org/dy/2023/02/20230214.txt",
        "https://links.bocchi2b.top/clash",
        # 以下含日期占位符
        "https://www.freeclashnode.com/sub/clash/{Ymd}.yaml",
        "https://nodeclash.github.io/sub/clash.yaml",
        "https://clashxiazai.com/sub/{Ymd}.yaml",
        "https://clashios.com/sub/clash.yaml",
        "https://clashsub.net/sub/{Ymd}.yaml",
        "https://clashgithub.com/sub/clash.yaml",
        "https://www.cfmem.com/sub/clash/{Ymd}.yaml",
    ]
    # 替换日期占位符，并移除重复
    expanded = set()
    for link in raw:
        link = link.replace('{Ymd}', ymd).replace('{Y/m/d}', y_m_d).replace('{Md}', md)
        expanded.add(link)
    return sorted(expanded)


def priority_raw_links():
    """用户列表中纯 raw.githubusercontent.com 链接 —— 加入常规池"""
    return [
        "https://raw.githubusercontent.com/firefoxmmx2/v2rayshare_subcription/main/subscription/clash_sub.yaml",
        "https://raw.githubusercontent.com/Q3dlaXpoaQ/V2rayN_Clash_Node_Getter/refs/heads/main/APIs/sc0.yaml",
        "https://raw.githubusercontent.com/mahdibland/SSAggregator/master/sub/sub_merge_yaml.yml",
        "https://raw.githubusercontent.com/snakem982/proxypool/main/source/clash-meta.yaml",
        "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.yml",
        "https://raw.githubusercontent.com/zhangkaiitugithub/passcro/main/speednodes.yaml",
        "https://raw.githubusercontent.com/aiboboxx/v2rayfree/refs/heads/main/README.md",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/nodes.meta.yml",
        "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml",
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/main/all_configs.txt",
        "https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash",
        "https://raw.githubusercontent.com/go4sharing/sub/main/sub.yaml",
        "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.meta.yml",
        "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
        "https://raw.githubusercontent.com/vxiaov/free_proxies/main/clash/clash.provider.yaml",
        "https://raw.githubusercontent.com/free-nodes/clashfree/refs/heads/main/clash.yml",
        "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity.yml",
        "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
        "https://raw.githubusercontent.com/xiaoji235/airport-free/refs/heads/main/clash/naidounode.txt",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.meta.yml",
        "https://raw.githubusercontent.com/anaer/Sub/refs/heads/main/clash.yaml",
        "https://raw.githubusercontent.com/free18/v2ray/refs/heads/main/c.yaml",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.yml",
        "https://raw.githubusercontent.com/Pawdroid/Free-servers/refs/heads/main/sub",
        "https://raw.githubusercontent.com/aiboboxx/v2rayfree/refs/heads/main/v2",
        "https://raw.githubusercontent.com/acymz/AutoVPN/main/data/V2.txt",
        "https://raw.githubusercontent.com/ggborr/FREEE-VPN/refs/heads/main/6V2ray",
        "https://raw.githubusercontent.com/Barabama/FreeNodes/main/nodes/wenode.txt",
        "https://raw.githubusercontent.com/Barabama/FreeNodes/main/nodes/v2rayshare.txt",
        "https://raw.githubusercontent.com/Barabama/FreeNodes/main/nodes/nodefree.txt",
        "https://raw.githubusercontent.com/Barabama/FreeNodes/main/nodes/ndnode.txt",
        "https://raw.githubusercontent.com/Barabama/FreeNodes/main/nodes/clashmeta.txt",
        "https://raw.githubusercontent.com/xiaoji235/airport-free/main/v2ray/v2rayshare.txt",
        "https://raw.githubusercontent.com/xiaoji235/airport-free/main/v2ray.txt",
        "https://raw.githubusercontent.com/xiaoji235/airport-free/main/clash/naidounode.txt",
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/all_configs.txt",
        "https://raw.githubusercontent.com/Q3dlaXpoaQ/V2rayN_Clash_Node_Getter/refs/heads/main/APIs/sc1.yaml",
        "https://raw.githubusercontent.com/Q3dlaXpoaQ/V2rayN_Clash_Node_Getter/refs/heads/main/APIs/sc2.yaml",
        "https://raw.githubusercontent.com/Q3dlaXpoaQ/V2rayN_Clash_Node_Getter/refs/heads/main/APIs/sc3.yaml",
        "https://raw.githubusercontent.com/Q3dlaXpoaQ/V2rayN_Clash_Node_Getter/refs/heads/main/APIs/sc4.yaml",
        "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
        "https://raw.githubusercontent.com/mgit0001/test_clash/refs/heads/main/heima.txt",
        "https://raw.githubusercontent.com/shahidbhutta/Clash/refs/heads/main/Router",
        "https://raw.githubusercontent.com/mfbpn/tg_mfbpn_sub/main/trial.yaml",
        "https://raw.githubusercontent.com/mfuu/v2ray/master/clash.yaml",
        "https://raw.githubusercontent.com/free-nodes/clashfree/main/clash.yaml",
        "https://raw.githubusercontent.com/sun9426/sun9426.github.io/main/clash.yaml",
        "https://raw.githubusercontent.com/clashzhuanxian/clashzhuanxian.github.io/main/clash.yaml",
        "https://raw.githubusercontent.com/nodev2rayclash/nodev2rayclash.github.io/main/clash.yaml",
        "https://raw.githubusercontent.com/biancheng-net/freenode-share/main/clash.yaml",
        "https://raw.githubusercontent.com/John19187/v2ray-SSR-Clash-Verge-Shadowrocke/main/clash.yaml",
        "https://raw.githubusercontent.com/crossxx-labs/free-proxy/main/clash.yaml",
        "https://raw.githubusercontent.com/free-nodes/v2rayfree/main/clash.yaml",
        "https://raw.githubusercontent.com/OpenRunner/clash-freenode/main/clash.yaml",
        "https://raw.githubusercontent.com/Helpsoftware/fanqiang/main/clash.yaml",
        "https://raw.githubusercontent.com/Fukki-Z/nodefree/main/clash.yaml",
        "https://raw.githubusercontent.com/hwanz/SSR-V2ray-Trojan-vpn/main/clash.yaml",
        "https://raw.githubusercontent.com/freefq/free/main/clash.yaml",
        "https://raw.githubusercontent.com/aiboboxx/clashfree/main/clash.yaml",
        "https://raw.githubusercontent.com/actionsfz/v2ray/refs/heads/master/all.yaml",
    ]


# ============================================================
#  (B) 原有候选池
# ============================================================

def known_links():
    return [
        "https://raw.githubusercontent.com/snakem982/proxypool/main/source/clash-meta.yaml",
        "https://raw.githubusercontent.com/snakem982/proxypool/main/source/clash-meta-2.yaml",
        "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.meta.yml",
        "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.yml",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.meta.yml",
        "https://raw.githubusercontent.com/ovmvo/FreeSub/refs/heads/main/sub/permanent/mihomo.yaml",
        "https://raw.githubusercontent.com/ovmvo/FreeSub/refs/heads/main/sub/latest/62330149.yaml",
        "https://raw.githubusercontent.com/free18/v2ray/refs/heads/main/c.yaml",
        "https://raw.githubusercontent.com/free18/v2ray/refs/heads/main/v.txt",
        "https://raw.githubusercontent.com/shaoyouvip/free/refs/heads/main/all.yaml",
        "https://raw.githubusercontent.com/shaoyouvip/free/main/mihomo.yaml",
        "https://raw.githubusercontent.com/ts-sf/fly/main/clash",
        "https://raw.githubusercontent.com/futianhang/freeNodes/master/clash.yaml",
        "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/Clash.yaml",
        "https://raw.githubusercontent.com/mfuu/v2ray/master/clash.yaml",
        "https://raw.githubusercontent.com/futianhang/freeNodes/master/v2ray.txt",
        "https://raw.githubusercontent.com/skka3134/Free-servers/main/sub",
        "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
        "https://cdn.jsdelivr.net/gh/chengaopan/AutoMergePublicNodes@master/list.meta.yml",
        "https://fastly.jsdelivr.net/gh/chengaopan/AutoMergePublicNodes@master/list.meta.yml",
        "https://testingcf.jsdelivr.net/gh/chengaopan/AutoMergePublicNodes@master/list.meta.yml",
        "https://gcore.jsdelivr.net/gh/chengaopan/AutoMergePublicNodes@master/list.meta.yml",
        "https://cdn.jsdelivr.net/gh/peasoft/NoMoreWalls@master/list.meta.yml",
        "https://fastly.jsdelivr.net/gh/peasoft/NoMoreWalls@master/list.meta.yml",
        "https://testingcf.jsdelivr.net/gh/peasoft/NoMoreWalls@master/list.meta.yml",
        "https://gcore.jsdelivr.net/gh/peasoft/NoMoreWalls@master/list.meta.yml",
        "https://cdn.jsdelivr.net/gh/anaer/Sub@main/clash.yaml",
        "https://cdn.jsdelivr.net/gh/shaoyouvip/free@refs/heads/main/mihomo.yaml",
        "https://cdn.jsdelivr.net/gh/free18/v2ray@refs/heads/main/c.yaml",
        "https://fastly.jsdelivr.net/gh/ripaojiedian/freenode@main/clash.yaml",
        "https://gcore.jsdelivr.net/gh/ripaojiedian/freenode@main/v2ray",
        "https://free-clash-v2ray.github.io/uploads/2026/06/3-20260603.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/3-20260604.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/3-20260605.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/3-20260606.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/3-20260607.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/2-20260603.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/2-20260604.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/2-20260605.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/2-20260606.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/2-20260607.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/0-20260603.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/0-20260604.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/0-20260605.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/0-20260606.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/0-20260607.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/1-20260603.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/1-20260604.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/1-20260607.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/2-20260602.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/0-20260602.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/3-20260602.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/1-20260602.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/05/2-20260531.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/05/1-20260531.yaml",
        "https://free-clash-v2ray.github.io/uploads/2026/06/2-20260607.txt",
        "https://anaer.github.io/Sub/clash.yaml",
        "https://ghfast.top/https://raw.githubusercontent.com/free18/v2ray/refs/heads/main/c.yaml",
        "https://ghproxy.net/https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.meta.yml",
        "https://raw.githubusercontent.com/alanbobs999/TopFreeProxies/master/sub/sub_merge_yaml.yml",
        "https://raw.githubusercontent.com/alanbobs999/TopFreeProxies/master/sub/sub_merge_base64.txt",
        "https://raw.githubusercontent.com/vpei/Free-TVUrl/main/Node",
        "https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash.yaml",
        "https://raw.githubusercontent.com/ripaojiedian/freenode/main/v2ray",
        "https://raw.githubusercontent.com/yudouuu/freeclashnode/main/subscribe/clash.yaml",
        "https://raw.githubusercontent.com/yudouuu/freeclashnode/main/subscribe/v2ray.txt",
        "https://raw.githubusercontent.com/colatiger/v2ray-nodes/main/clash.yaml",
        "https://raw.githubusercontent.com/colatiger/v2ray-nodes/main/v2ray.txt",
        "https://raw.githubusercontent.com/sunwuzhou03/ClashNode/master/sub",
        "https://raw.githubusercontent.com/freefq/free/master/v2ray",
        "https://raw.githubusercontent.com/freefq/free/master/clash.yaml",
        "https://raw.githubusercontent.com/freefq/free/master/subscribe.txt",
        "https://raw.githubusercontent.com/NodeFree/free/main/clash.yaml",
        "https://raw.githubusercontent.com/NodeFree/free/main/v2ray",
        "https://raw.githubusercontent.com/AzadNetCH/Clash/main/Azadnet.yaml",
        "https://raw.githubusercontent.com/mahdibland/ShadowsocksCollector/main/v2ray.txt",
        "https://raw.githubusercontent.com/mahdibland/ShadowsocksCollector/main/clash.yaml",
        "https://raw.githubusercontent.com/mahdibland/SSAggregator/main/sub/subscribe_base64.txt",
        "https://raw.githubusercontent.com/mahdibland/SSAggregator/main/sub/subscribe_clash.yaml",
        "https://raw.githubusercontent.com/v2raycool/v2raycool/main/subscribe.txt",
        "https://raw.githubusercontent.com/a24570/clashnode/main/clash.yaml",
        "https://raw.githubusercontent.com/free-free-vpn/free-nodes/main/v2ray.txt",
        "https://raw.githubusercontent.com/free-free-vpn/free-nodes/main/clash.yaml",
        "https://raw.githubusercontent.com/icewolfz/free-proxy/master/v2ray.txt",
        "https://raw.githubusercontent.com/icewolfz/free-proxy/master/clash.yaml",
        "https://raw.githubusercontent.com/YK-Unit/free-nodes/main/clash.yaml",
        "https://raw.githubusercontent.com/YK-Unit/free-nodes/main/v2ray.txt",
        "https://raw.githubusercontent.com/githubfreeserver/free/main/freessr.txt",
        "https://raw.githubusercontent.com/githubfreeserver/free/main/clash.yaml",
        "https://raw.githubusercontent.com/pojiezhiyuanjun/freenode/main/clash",
        "https://raw.githubusercontent.com/pojiezhiyuanjun/freenode/main/v2ray",
        "https://raw.githubusercontent.com/ziye66666/FreeNode/main/clash.yaml",
        "https://raw.githubusercontent.com/ziye66666/FreeNode/main/v2ray.txt",
        "https://raw.githubusercontent.com/NiceVPN123/NiceVPN/main/clash.yaml",
        "https://raw.githubusercontent.com/NiceVPN123/NiceVPN/main/v2ray.txt",
        "https://raw.githubusercontent.com/kxswa/kxswa/kxswa/clash.yaml",
        "https://raw.githubusercontent.com/kxswa/kxswa/kxswa/v2ray.txt",
        "https://raw.githubusercontent.com/abshare/abshare/main/clash.yaml",
        "https://raw.githubusercontent.com/abshare/abshare/main/v2ray.txt",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy/main/clash.yaml",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy/main/v2ray.txt",
        "https://raw.githubusercontent.com/xrayfree/free-ssr-ss-v2ray-vpn-clash/main/clash.yaml",
        "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
        "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
        "https://raw.githubusercontent.com/adiwzx/freenode/main/adisub.txt",
        "https://raw.githubusercontent.com/xiaowang012/Free-proxy-node/main/free_node.txt",
        "https://raw.githubusercontent.com/fliggyaa/freeproxy/main/clash.yaml",
        "https://raw.githubusercontent.com/joe12801/qwerty/main/Clash.yml",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.yml",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
        "https://raw.githubusercontent.com/akile-io/resources/main/clash.yaml",
        "https://raw.githubusercontent.com/akile-io/resources/main/v2ray.txt",
        "https://raw.githubusercontent.com/menghuaban/free/main/clash.yaml",
        "https://raw.githubusercontent.com/menghuaban/free/main/v2ray.txt",
        "https://raw.githubusercontent.com/jefferyiou/trojans/main/all.yaml",
        "https://raw.githubusercontent.com/jefferyiou/trojans/main/v2ray.txt",
        "https://raw.githubusercontent.com/jefferyiou/trojans/main/clash.yaml",
        "https://raw.githubusercontent.com/MochiDaDaiMa/FreeProxy/main/clash.yaml",
        "https://raw.githubusercontent.com/MochiDaDaiMa/FreeProxy/main/v2ray.txt",
        "https://raw.githubusercontent.com/nicepkg/awesome-proxy/main/bash.yaml",
        "https://raw.githubusercontent.com/nicepkg/awesome-proxy/main/v2ray.txt",
        "https://raw.githubusercontent.com/aloistr/free-node/main/clash.yaml",
        "https://raw.githubusercontent.com/aloistr/free-node/main/v2ray.txt",
        "https://raw.githubusercontent.com/erwynn/free-node/main/clash.yaml",
        "https://raw.githubusercontent.com/erwynn/free-node/main/v2ray.txt",
        "https://raw.githubusercontent.com/kevinzheng516/free-proxy/main/clash.yaml",
        "https://raw.githubusercontent.com/kevinzheng516/free-proxy/main/v2ray.txt",
        "https://raw.githubusercontent.com/zfl9/free-v2ray-clash/main/subscribe.yaml",
        "https://raw.githubusercontent.com/zfl9/free-v2ray-clash/main/subscribe.txt",
        "https://raw.githubusercontent.com/freefq/free/free/v2ray",
        "https://raw.githubusercontent.com/freefq/free/free/ssr",
        "https://raw.githubusercontent.com/freefq/free/free/vmess",
        "https://raw.githubusercontent.com/freefq/free/free/trojan",
        "https://raw.githubusercontent.com/freefq/free/free/clash",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/v2ray",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/ssr",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/trojan",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/ss",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/vmess",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/clash",
        "https://raw.githubusercontent.com/licheng527/Free-servers/main/README.md",
        "https://raw.githubusercontent.com/alimy/mirrors/master/clash.yaml",
        "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/clash.yaml",
        "https://raw.githubusercontent.com/trojan-gfw/trojan-quickstart/main/config.yaml",
        "https://raw.githubusercontent.com/bannedbook/fanqiang/main/v2ray",
        "https://raw.githubusercontent.com/bannedbook/fanqiang/main/ssr",
        "https://raw.githubusercontent.com/bannedbook/fanqiang/main/ss",
        "https://raw.githubusercontent.com/bannedbook/fanqiang/main/trojan",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_1.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_2.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_3.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_4.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_5.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_6.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_7.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_8.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_9.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_10.yaml",
        "https://raw.githubusercontent.com/cmliu/ClashV2rayConfig/main/conf",
        "https://raw.githubusercontent.com/cmliu/Clasehv2rayConfig/main/Vmess",
        "https://raw.githubusercontent.com/cmliu/Clasehv2rayConfig/main/Vless",
        "https://raw.githubusercontent.com/CareyWang/subscriptions/main/free_proxy.txt",
        "https://raw.githubusercontent.com/CareyWang/subscriptions/main/free_proxy.yaml",
    ]


def date_urls():
    urls = set()
    for d in range(10):
        t = time.localtime(time.time() - d * 86400)
        y = str(t.tm_year); m = f"{t.tm_mon:02d}"; dd = f"{t.tm_mday:02d}"
        for i in range(5):
            urls.add(f"https://free-clash-v2ray.github.io/uploads/{y}/{m}/{i}-{y}{m}{dd}.yaml")
    return list(urls)


def extra_urls():
    return [
        "https://raw.githubusercontent.com/freefq/free/master/v2ray",
        "https://raw.githubusercontent.com/freefq/free/master/clash.yaml",
        "https://raw.githubusercontent.com/freefq/free/master/subscribe.txt",
        "https://raw.githubusercontent.com/mahdibland/SSAggregator/main/sub/subscribe_clash.yaml",
        "https://raw.githubusercontent.com/mahdibland/SSAggregator/main/sub/subscribe_base64.txt",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/v2ray",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/ssr",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/ss",
        "https://raw.githubusercontent.com/Alvin9999/new-pac/wiki/trojan",
        "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
        "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.yml",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_1.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_2.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_3.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_4.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_5.yaml",
        "https://raw.githubusercontent.com/bclswl0827/V2Ray-Node-Share/main/subscribe_6.yaml",
        "https://raw.githubusercontent.com/alanbobs999/TopFreeProxies/master/sub/sub_merge_yaml.yml",
        "https://raw.githubusercontent.com/alanbobs999/TopFreeProxies/master/sub/sub_merge_base64.txt",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy/main/clash.yaml",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy/main/v2ray.txt",
        "https://raw.githubusercontent.com/AzadNetCH/Clash/main/Azadnet.yaml",
        "https://raw.githubusercontent.com/freefq/free/free/v2ray",
        "https://raw.githubusercontent.com/freefq/free/free/ssr",
        "https://raw.githubusercontent.com/freefq/free/free/vmess",
        "https://raw.githubusercontent.com/freefq/free/free/trojan",
        "https://raw.githubusercontent.com/freefq/free/free/clash",
        "https://raw.githubusercontent.com/MochiDaDaiMa/FreeProxy/main/clash.yaml",
        "https://raw.githubusercontent.com/MochiDaDaiMa/FreeProxy/main/v2ray.txt",
        "https://raw.githubusercontent.com/shaoyouvip/free/refs/heads/main/all.yaml",
        "https://raw.githubusercontent.com/shaoyouvip/free/main/mihomo.yaml",
        "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/clash.yaml",
        "https://raw.githubusercontent.com/githubfreeserver/free/main/freessr.txt",
    ]


# ============================================================
#  内容验证
# ============================================================

def is_html(content):
    return content.strip()[:100].lower().startswith(('<!doctype', '<html', '<?xml'))

def decode_base64_data(data):
    try:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.b64decode(data).decode('utf-8', errors='replace')
    except:
        return None

def validate(url):
    skip = ['/releases/', '/actions/', '/blob/', '/issues/', '/pull/', '/discussions/',
            '/tree/', '.svg', '.png', '.jpg', '.webp', '.zip', '.exe']
    for s in skip:
        if s in url: return False, None
    if re.search(r'github\.com/[^/]+/[^/]+(?:$|[?#])', url):
        return False, None
    c = http_get(url)
    if not c: return False, None
    c = c.strip()
    if len(c) < 50 or is_html(c): return False, None
    # YAML
    try:
        d = yaml.safe_load(c)
        if isinstance(d, dict) and 'proxies' in d and isinstance(d['proxies'], list) and len(d['proxies']) > 0:
            return True, c
    except: pass
    # base64
    try:
        d = base64.b64decode(c[:5000]).decode('utf-8', errors='replace')
        if re.search(r'(?:vmess|vless|ss|trojan|hysteria2|hy2|socks5|http)://', d):
            return True, c
    except: pass
    # URI plain text
    if re.search(r'(?:vmess|vless|ss|trojan|hysteria2|hy2|socks5|http)://', c[:3000]):
        return True, c
    return False, None


# ============================================================
#  V2Ray URI → Clash Proxy 转换器
# ============================================================

URI_PARSERS = {}

def parse_vmess_uri(uri):
    try:
        b64 = uri[8:].split('#')[0].split('?')[0]
        dec = decode_base64_data(b64)
        if dec:
            obj = json.loads(dec)
            return {"name": obj.get("ps","vmess"),"type":"vmess","server":obj.get("add",""),
                    "port":int(obj.get("port",0)),"uuid":obj.get("id",""),
                    "cipher":obj.get("scy","auto"),"alterId":int(obj.get("aid",0)),
                    "network":obj.get("net","tcp"),"tls":obj.get("tls","")=="tls",
                    "ws-path":obj.get("path",""),"ws-headers":{"Host":obj.get("host","")} if obj.get("host") else {}}
    except: pass
    m = re.match(r'vmess://(.+)', uri)
    if m:
        try:
            raw = m.group(1).split('#')[0].split('?')[0]
            dec = decode_base64_data(raw)
            if dec and '@' in dec:
                parts = dec.split('@')
                uid = parts[0].split(':')[-1] if ':' in parts[0] else parts[0]
                hp = parts[1].split(':')
                return {"name":"vmess","type":"vmess","server":hp[0],"port":int(hp[1]) if len(hp)>1 and hp[1].isdigit() else 0,
                        "uuid":uid,"cipher":"auto","alterId":0,"network":"tcp","tls":False,"ws-path":"","ws-headers":{}}
        except: pass
    return None
URI_PARSERS['vmess://'] = parse_vmess_uri

def parse_ss_uri(uri):
    try:
        s = uri[5:].split('#')[0].split('?')[0]
        if '@' in s:
            ui, host = s.split('@', 1)
            hp = host.split(':')
            method, pw = ui.split(':', 1) if ':' in ui else ('aes-256-gcm', ui)
            return {"name":"ss","type":"ss","server":hp[0],"port":int(hp[1]) if len(hp)>1 and hp[1].isdigit() else 0,"cipher":method,"password":pw}
        b64p = s.split('@')[0]
        dec = decode_base64_data(b64p)
        if dec and ':' in dec:
            mp = dec.split(':')
            return {"name":"ss","type":"ss","cipher":mp[0],"password":':'.join(mp[1:])}
    except: pass
    return None
URI_PARSERS['ss://'] = parse_ss_uri

def parse_trojan_uri(uri):
    try:
        p = urlparse(uri)
        pw = unquote(p.username) if p.username else ''
        server = p.hostname or ''
        port = p.port or 443
        q = parse_qs(p.query)
        d = {"name":"trojan","type":"trojan","server":server,"port":port,"password":pw,
             "sni":q.get('sni',[server])[0],"network":q.get('type',['tcp'])[0],"tls":True,
             "skip-cert-verify":q.get('allowInsecure',['false'])[0].lower()=='true'}
        if d['network']=='ws':
            d['ws-path']=q.get('path',['/'])[0]
            d['ws-headers']={"Host":q.get('host',[server])[0]}
        return d
    except: pass
    return None
URI_PARSERS['trojan://'] = parse_trojan_uri

def parse_vless_uri(uri):
    try:
        p = urlparse(uri)
        uid = unquote(p.username) if p.username else ''
        server = p.hostname or ''
        port = p.port or 443
        q = parse_qs(p.query)
        return {"name":"vless","type":"vless","server":server,"port":port,"uuid":uid,
                "flow":q.get('flow',[''])[0],"network":q.get('type',['tcp'])[0],
                "tls":q.get('security',['none'])[0]=='tls','sni':q.get('sni',[''])[0],
                "client-fingerprint":q.get('fp',['chrome'])[0],
                "ws-path":q.get('path',['/'])[0] if q.get('type',['tcp'])[0]=='ws' else '',
                "ws-headers":{"Host":q.get('host',[''])[0]} if q.get('host') else {}}
    except: pass
    return None
URI_PARSERS['vless://'] = parse_vless_uri

def parse_hysteria2_uri(uri):
    try:
        p = urlparse(uri.replace('hysteria2://','http://').replace('hy2://','http://'))
        pw = unquote(p.username) if p.username else ''
        server = p.hostname or ''
        port = p.port or 443
        q = parse_qs(p.query)
        return {"name":"hy2","type":"hysteria2","server":server,"port":port,"password":pw,
                "sni":q.get('sni',[server])[0],"skip-cert-verify":q.get('insecure',['false'])[0].lower()=='true'}
    except: pass
    return None
URI_PARSERS['hysteria2://'] = URI_PARSERS['hy2://'] = parse_hysteria2_uri

def parse_hysteria_uri(uri):
    try:
        p = urlparse(uri.replace('hysteria://','http://'))
        auth = unquote(p.username) if p.username else ''
        server = p.hostname or ''
        port = p.port or 443
        q = parse_qs(p.query)
        return {"name":"hy","type":"hysteria","server":server,"port":port,"auth-str":auth,
                "protocol":q.get('protocol',['udp'])[0],"up":q.get('up',['50'])[0],"down":q.get('down',['100'])[0],
                "sni":q.get('sni',[server])[0],"skip-cert-verify":q.get('insecure',['false'])[0].lower()=='true'}
    except: pass
    return None
URI_PARSERS['hysteria://'] = parse_hysteria_uri

def parse_socks_uri(uri):
    try:
        p = urlparse(uri)
        user = unquote(p.username) if p.username else ''
        pw = unquote(p.password) if p.password else ''
        d = {"name":"socks","type":"socks5","server":p.hostname or '','port':p.port or 1080}
        if user: d['username']=user
        if pw: d['password']=pw
        return d
    except: pass
    return None
URI_PARSERS['socks5://'] = parse_socks_uri

def parse_http_uri(uri):
    try:
        p = urlparse(uri)
        user = unquote(p.username) if p.username else ''
        pw = unquote(p.password) if p.password else ''
        d = {"name":"http","type":"http","server":p.hostname or '','port':p.port or 80}
        if user: d['username']=user
        if pw: d['password']=pw
        return d
    except: pass
    return None
URI_PARSERS['http://'] = parse_http_uri

def uri_to_proxy(uri):
    for prefix, parser in URI_PARSERS.items():
        if uri.startswith(prefix):
            return parser(uri)
    return None


# ============================================================
#  代理提取器
# ============================================================

def extract_yaml_proxies(content):
    try:
        d = yaml.safe_load(content)
        if isinstance(d, dict) and 'proxies' in d:
            return [p for p in d['proxies'] if isinstance(p, dict) and p.get('name') and p.get('type') and p.get('server')]
    except: pass
    return []

def extract_uri_proxies(content):
    results = []
    seen = set()
    for prefix in ['vmess://','ss://','trojan://','vless://','hysteria2://','hy2://','hysteria://','socks5://','http://']:
        for m in re.finditer(re.escape(prefix)+r'[^\s<>"\'\)]+', content):
            uri = m.group(0).rstrip('.,;:!?)').strip()
            if uri in seen: continue
            seen.add(uri)
            p = uri_to_proxy(uri)
            if p: results.append(p)
    return results

def process_content(content):
    proxies = extract_yaml_proxies(content)
    if proxies: return proxies
    proxies = extract_uri_proxies(content)
    if proxies: return proxies
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='replace')
        proxies = extract_uri_proxies(decoded)
    except: pass
    return proxies


# ============================================================
#  Clash Proxy → V2Ray URI 转换器
# ============================================================

def proxy_to_uri(proxy):
    try:
        name=proxy.get('name',''); ptype=proxy.get('type','')
        if ptype=='vmess':
            d={"v":"2","ps":name,"add":proxy.get('server',''),"port":str(proxy.get('port','')),
               "id":proxy.get('uuid',proxy.get('id','')),"aid":"0","scy":proxy.get('cipher','auto'),
               "net":proxy.get('network','tcp'),"type":"none","host":proxy.get('ws-headers',{}).get('Host',''),
               "path":proxy.get('ws-path',''),"tls":""}
            if proxy.get('tls'): d['tls']='tls'
            return f"vmess://{base64.b64encode(json.dumps(d,ensure_ascii=False).encode()).decode()}"
        elif ptype=='vless':
            p={'type':proxy.get('network','tcp'),'security':'tls' if proxy.get('tls') else 'none'}
            if proxy.get('flow'): p['flow']=proxy['flow']
            sni=proxy.get('sni') or proxy.get('servername','')
            if sni: p['sni']=sni
            if proxy.get('client-fingerprint'): p['fp']=proxy['client-fingerprint']
            if proxy.get('network')=='ws':
                p['path']=proxy.get('ws-path','/'); p['host']=proxy.get('ws-headers',{}).get('Host','')
            if proxy.get('network')=='grpc': p['serviceName']=proxy.get('grpc-service-name','')
            uuid=proxy.get('uuid',proxy.get('password',''))
            qs='&'.join(f"{k}={quote(str(v))}" for k,v in p.items() if v)
            return f"vless://{uuid}@{proxy['server']}:{proxy['port']}?{qs}#{quote(name)}"
        elif ptype=='ss':
            m=proxy.get('cipher',proxy.get('method','aes-256-gcm')); pw=proxy.get('password','')
            enc=base64.b64encode(f"{m}:{pw}".encode()).decode()
            q=f"?plugin={quote(proxy['plugin'])}" if proxy.get('plugin') else ''
            return f"ss://{enc}@{proxy['server']}:{proxy['port']}{q}#{quote(name)}"
        elif ptype=='trojan':
            pw=quote(proxy.get('password',''),safe='')
            p={'security':'tls','type':proxy.get('network','tcp')}
            sni=proxy.get('sni') or proxy.get('servername','')
            if sni: p['sni']=sni
            if proxy.get('network')=='ws':
                p['path']=proxy.get('ws-path','/'); p['host']=proxy.get('ws-headers',{}).get('Host','')
            if proxy.get('client-fingerprint'): p['fp']=proxy['client-fingerprint']
            qs='&'.join(f"{k}={quote(str(v))}" for k,v in p.items() if v)
            return f"trojan://{pw}@{proxy['server']}:{proxy['port']}?{qs}#{quote(name)}"
        elif ptype=='hysteria2':
            pw=quote(proxy.get('password',''),safe=''); p={}
            sni=proxy.get('sni') or proxy.get('servername','')
            if sni: p['sni']=sni
            if proxy.get('skip-cert-verify'): p['insecure']='1'
            qs='&'.join(f"{k}={quote(str(v))}" for k,v in p.items() if v)
            return f"hysteria2://{pw}@{proxy['server']}:{proxy['port']}?{qs}#{quote(name)}"
        elif ptype=='hysteria':
            p={'protocol':proxy.get('protocol','udp'),'up':str(proxy.get('up',proxy.get('upload','50'))),'down':str(proxy.get('down',proxy.get('download','100')))}
            sni=proxy.get('sni') or proxy.get('servername','')
            if sni: p['sni']=sni
            if proxy.get('skip-cert-verify'): p['insecure']='1'
            qs='&'.join(f"{k}={quote(str(v))}" for k,v in p.items() if v)
            auth=quote(proxy.get('auth-str',proxy.get('auth_str','')),safe='')
            return f"hysteria://{auth}@{proxy['server']}:{proxy['port']}?{qs}#{quote(name)}"
        elif ptype=='socks5':
            a=''
            if proxy.get('username'): a=f"{quote(proxy['username'])}:{quote(proxy.get('password',''))}@"
            return f"socks5://{a}{proxy['server']}:{proxy['port']}#{quote(name)}"
        elif ptype=='http':
            a=''
            if proxy.get('username'): a=f"{quote(proxy['username'])}:{quote(proxy.get('password',''))}@"
            return f"http://{a}{proxy['server']}:{proxy['port']}#{quote(name)}"
    except: pass
    return None


# ============================================================
#  采集主循环（三阶段：优先级 → 常规 → 补充）
# ============================================================

def collect(max_links=MAX_LINKS):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    valid = []

    # ---- 第1轮：优先级链接（非 raw.githubusercontent.com） ----
    prio = priority_links()
    print(f"\n[第1轮/优先级] 非raw.githubusercontent.com链接: {len(prio)} 个")
    executor = ThreadPoolExecutor(max_workers=CONCURRENT)
    try:
        futs = {executor.submit(validate, url): url for url in prio}
        done = 0
        for f in as_completed(futs):
            done += 1
            url = futs[f]
            ok, content = f.result() if not f.exception() else (False, None)
            if ok:
                valid.append((url, content))
                status = f"✓ [{len(valid)}]"
            else: status = "✗"
            short = url[:65] + '...' if len(url) > 65 else url
            print(f"  [{done}/{len(prio)}] {status} {short}")
            if len(valid) >= max_links: break
    finally:
        executor.shutdown(wait=False)

    # ---- 第2轮：常规候选 ----
    candidates = list(set(known_links() + date_urls() + priority_raw_links()))
    print(f"\n[第2轮/常规] 候选链接: {len(candidates)} 个 (已有 {len(valid)} 条有效)")
    executor2 = ThreadPoolExecutor(max_workers=CONCURRENT)
    try:
        futs2 = {executor2.submit(validate, url): url for url in candidates if url not in [v[0] for v in valid]}
        done = 0
        total = len(futs2)
        for f in as_completed(futs2):
            done += 1
            url = futs2[f]
            ok, content = f.result() if not f.exception() else (False, None)
            if ok:
                valid.append((url, content))
                status = f"✓ [{len(valid)}]"
            else: status = "✗"
            short = url[:65] + '...' if len(url) > 65 else url
            print(f"  [{done}/{total}] {status} {short}")
            if len(valid) >= max_links: break
    finally:
        executor2.shutdown(wait=False)

    valid = valid[:max_links]
    print(f"\n[采集] 有效: {len(valid)}/{len(set(prio+candidates))} 条")

    # ---- 第3轮：补充 ----
    if len(valid) < MIN_LINKS:
        print(f"[采集] 不足{MIN_LINKS}条，触发补充...")
        executor3 = ThreadPoolExecutor(max_workers=CONCURRENT)
        try:
            futs3 = {executor3.submit(validate, url): url for url in extra_urls() if url not in [v[0] for v in valid]}
            for f in as_completed(futs3):
                url = futs3[f]
                ok, content = f.result() if not f.exception() else (False, None)
                if ok:
                    valid.append((url, content))
                    print(f"  + [{len(valid)}] {url[:65]}")
                    if len(valid) >= max_links: break
        finally:
            executor3.shutdown(wait=False)
        valid = valid[:max_links]
        print(f"  → 补充后 {len(valid)} 条")

    return valid


# ============================================================
#  去重聚合
# ============================================================

def dedup_and_build(valid_links):
    all_proxies = []
    seen_names = set()
    url_list = []
    for url, content in valid_links:
        url_list.append(url)
        proxies = process_content(content)
        for p in proxies:
            name = p.get('name', '').strip()
            if name and name not in seen_names:
                seen_names.add(name)
                p['name'] = name[:64]
                all_proxies.append(p)
    print(f"\n[聚合] 去重后共 {len(all_proxies)} 个代理节点")
    return all_proxies, url_list


# ============================================================
#  输出：Clash YAML + V2Ray base64
# ============================================================

def write_outputs(proxies, urls):
    now = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())

    # ---- Clash 格式 ----
    os.makedirs(os.path.dirname(CLASH_PATH) or '.', exist_ok=True)
    proxy_yaml = yaml.dump({'proxies': proxies}, allow_unicode=True, sort_keys=False, width=4096, default_flow_style=False)
    with open(CLASH_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# Clash 节点订阅 - GitHub Actions 自动聚合\n")
        f.write(f"# 更新日期: {now}\n")
        f.write(f"# 来源链接: {len(urls)} 条 | 聚合节点: {len(proxies)} 个\n")
        f.write("# RAW加速: https://raw.githubusercontent.com/<user>/<repo>/refs/heads/main/clashnode.yaml\n\n")
        f.write(proxy_yaml)
    size_c = os.path.getsize(CLASH_PATH)
    print(f"[输出] Clash: {CLASH_PATH} ({size_c//1024}KB)")

    # ---- V2Ray 格式 ----
    uri_list = []
    seen_uris = set()
    for p in proxies:
        u = proxy_to_uri(p)
        if u and u not in seen_uris:
            seen_uris.add(u)
            uri_list.append(u)
    encoded = base64.b64encode('\n'.join(uri_list).encode('utf-8')).decode('utf-8')
    with open(V2RAY_PATH, 'w', encoding='utf-8') as f:
        f.write(encoded)
    size_v = os.path.getsize(V2RAY_PATH)
    print(f"[输出] V2Ray: {V2RAY_PATH} ({size_v//1024}KB, {len(uri_list)} URIs)")

    return size_c, size_v


# ============================================================
#  Main
# ============================================================

def main():
    print("=" * 65)
    print("  Clash & V2Ray 节点收集器 — GHA 版")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  输出 Clash:  {CLASH_PATH}")
    print(f"  输出 V2Ray:  {V2RAY_PATH}")
    print("=" * 65)

    valid_links = collect()
    proxies, urls = dedup_and_build(valid_links)
    size_c, size_v = write_outputs(proxies, urls)

    print(f"\n{'='*65}")
    print(f"  总结")
    print(f"  有效订阅链接数: {len(urls)}")
    print(f"  去重聚合节点数: {len(proxies)}")
    print(f"  Clash 文件: {size_c//1024} KB  |  V2Ray 文件: {size_v//1024} KB")
    print(f"{'='*65}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
