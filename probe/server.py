#!/usr/bin/env python3
import ipaddress,json,os,socket,ssl,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import urlopen,Request
PORT=int(os.getenv('PROBE_PORT','8787')); TIMEOUT=float(os.getenv('PROBE_TIMEOUT_MS','2500'))/1000; MAX_BATCH=int(os.getenv('PROBE_MAX_BATCH','128'))
req=Request('https://www.cloudflare.com/ips-v4',headers={'User-Agent':'cf-probe/1.0'})
with urlopen(req,timeout=15) as r: NETS=[ipaddress.ip_network(x.strip()) for x in r.read().decode().splitlines() if x.strip()]
def allowed(ip):
    try: a=ipaddress.ip_address(ip); return any(a in n for n in NETS)
    except ValueError: return False
def test(ip):
    try:
        t=time.perf_counter()
        with socket.create_connection((ip,443),timeout=TIMEOUT): tcp=(time.perf_counter()-t)*1000
        ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
        t=time.perf_counter()
        with socket.create_connection((ip,443),timeout=TIMEOUT) as raw:
            with ctx.wrap_socket(raw,server_hostname='speed.cloudflare.com'): pass
        tls=(time.perf_counter()-t)*1000
        return {'ip':ip,'tcp_ms':round(tcp,2),'tls_ms':round(tls,2),'score':round(tcp+tls,2)}
    except Exception: return None
class H(BaseHTTPRequestHandler):
    def out(self,code,obj):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        self.out(200,{'ok':True,'probe':os.getenv('PROBE_NAME','unknown')}) if self.path=='/health' else self.out(404,{'error':'not_found'})
    def do_POST(self):
        if self.path!='/scan': return self.out(404,{'error':'not_found'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>65536: raise ValueError('request too large')
            body=json.loads(self.rfile.read(n) or b'{}'); ips=body.get('ips',[])
            if not isinstance(ips,list) or not 1<=len(ips)<=MAX_BATCH: raise ValueError('invalid ips batch')
            if any(not isinstance(x,str) or not allowed(x) for x in ips): raise ValueError('IP outside Cloudflare IPv4 ranges')
            results=[]
            for ip in ips:
                result=test(ip)
                if result: results.append(result)
            self.out(200,{'results':results})
        except Exception as e: self.out(400,{'error':str(e)})
    def log_message(self,*args): pass
ThreadingHTTPServer(('0.0.0.0',PORT),H).serve_forever()
