#!/usr/bin/env python3
import concurrent.futures, ipaddress, json, os, socket, ssl, time
from pathlib import Path
import requests

PORT=int(os.getenv("PORT","443")); TOP_N=int(os.getenv("TOP_N","50"))
TIMEOUT=float(os.getenv("TIMEOUT_MS","2500"))/1000
MAX_IPS_PER_CIDR=int(os.getenv("MAX_IPS_PER_CIDR","128")); OUT=Path("results"); OUT.mkdir(exist_ok=True)
CF_RANGES_URL="https://www.cloudflare.com/ips-v4"

def get_ranges():
    r=requests.get(CF_RANGES_URL,timeout=15); r.raise_for_status()
    return [x.strip() for x in r.text.splitlines() if x.strip()]

def expand_network(cidr):
    net=ipaddress.ip_network(cidr); hosts=list(net.hosts())
    if len(hosts)<=MAX_IPS_PER_CIDR: return hosts
    step=max(1,len(hosts)//MAX_IPS_PER_CIDR); return hosts[::step][:MAX_IPS_PER_CIDR]

def test_ip(ip):
    try:
        t=time.perf_counter()
        with socket.create_connection((str(ip),PORT),timeout=TIMEOUT): tcp=(time.perf_counter()-t)*1000
        ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
        t=time.perf_counter()
        with socket.create_connection((str(ip),PORT),timeout=TIMEOUT) as raw:
            with ctx.wrap_socket(raw,server_hostname="speed.cloudflare.com"): pass
        tls=(time.perf_counter()-t)*1000
        return {"ip":str(ip),"tcp_ms":round(tcp,2),"tls_ms":round(tls,2),"score":round(tcp+tls,2)}
    except Exception: return None

def local_scan(candidates):
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as p:
        r=[x for x in p.map(test_ip,candidates) if x]
    return sorted(r,key=lambda x:(x["score"],x["tcp_ms"]))

def remote_scan(url,candidates):
    r=requests.post(url.rstrip("/")+"/scan",json={"ips":[str(x) for x in candidates],"port":PORT},timeout=300)
    r.raise_for_status(); return r.json().get("results",[])

def write_list(name,results):
    results=sorted(results,key=lambda x:(x["score"],x["tcp_ms"]))[:TOP_N]
    lines=[str(x["ip"])+":"+str(PORT)+"#CF-Best | "+name+" | "+str(round(x["tcp_ms"]))+"ms" for x in results]
    (OUT/(name+".txt")).write_text("\n".join(lines)+("\n" if lines else ""),encoding="utf-8")
    return results

def main():
    candidates=[ip for cidr in get_ranges() for ip in expand_network(cidr)]
    print("Testing",len(candidates),"sampled Cloudflare IPv4 addresses...")
    global_results=local_scan(candidates); write_list("all",global_results)
    probes=json.loads(os.getenv("PROBES_JSON","{}") or "{}")
    raw={"global":global_results[:TOP_N]}
    for name in ("ctcc","cucc","cmcc"):
        url=probes.get(name)
        if not url:
            (OUT/(name+".txt")).write_text("",encoding="utf-8"); continue
        try:
            r=remote_scan(url,candidates); write_list(name,r); raw[name]=sorted(r,key=lambda x:x["score"])[:TOP_N]
            print(name,":",len(r),"successful results")
        except Exception as e:
            print(name,": probe failed:",e); (OUT/(name+".txt")).write_text("",encoding="utf-8"); raw[name]=[]
    (OUT/"raw.json").write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__": main()
