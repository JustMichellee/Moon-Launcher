"""
Moon Launcher Phase 3 P2P Engine:
- RFC 5389 STUN NAT Discovery on bound UDP socket
- Simultaneous UDP Hole Punching via Cloudflare Worker signaling
- AES-128-GCM Encrypted Reliable Ordered Multiplexed TCP-over-UDP Stream Tunnel
- Automatic Playit/Public Relay fallback on strict Symmetric NAT / CGNAT
- Pure-Python Minecraft servers.dat NBT reader/injector (1-click in-game appear)
"""

import hashlib
import hmac
import json
import os
import secrets
import socket
import struct
import threading
import time

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:
    AESGCM = None

STUN_SERVERS = [
    ("stun.l.google.com", 19302),
    ("stun1.l.google.com", 19302),
    ("stun.cloudflare.com", 3478),
]

MAGIC = b"MN"
PKT_PUNCH = 1
PKT_PUNCH_ACK = 2
PKT_OPEN = 3
PKT_DATA = 4
PKT_ACK = 5
PKT_CLOSE = 6
PKT_KEEPALIVE = 7

HDR_FMT = "!BBIIIH"  # ptype, flags, stream_id, seq, ack, payload_len
HDR_LEN = struct.calcsize(HDR_FMT)
MAX_CHUNK = 1080


def get_local_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def stun_discover(udp_sock, timeout=1.6):
    """Sends RFC 5389 STUN Binding Request over udp_sock to discover public IP & mapped port."""
    cookie = 0x2112A442
    old_timeout = udp_sock.gettimeout()
    udp_sock.settimeout(timeout)
    try:
        for host, port in STUN_SERVERS:
            try:
                txid = secrets.token_bytes(12)
                req = struct.pack("!HHI12s", 0x0001, 0, cookie, txid)
                udp_sock.sendto(req, (host, port))
                data, _ = udp_sock.recvfrom(1024)
                if len(data) < 20:
                    continue
                mtype, mlen, mcookie, rtxid = struct.unpack("!HHI12s", data[:20])
                if mtype != 0x0101 or mcookie != cookie or rtxid != txid:
                    continue
                pos = 20
                end = min(len(data), 20 + mlen)
                while pos + 4 <= end:
                    atype, alen = struct.unpack("!HH", data[pos:pos + 4])
                    pos += 4
                    val = data[pos:pos + alen]
                    pos += (alen + 3) & ~3
                    if atype == 0x0020 and len(val) >= 8 and val[1] == 0x01:
                        xport = struct.unpack("!H", val[2:4])[0] ^ (cookie >> 16)
                        ip_bytes = bytes(val[4 + i] ^ ((cookie >> (24 - 8 * i)) & 0xFF) for i in range(4))
                        return socket.inet_ntoa(ip_bytes), int(xport)
                    if atype == 0x0001 and len(val) >= 8 and val[1] == 0x01:
                        mport = struct.unpack("!H", val[2:4])[0]
                        return socket.inet_ntoa(val[4:8]), int(mport)
            except Exception:
                continue
    finally:
        try:
            udp_sock.settimeout(old_timeout)
        except Exception:
            pass
    return "", udp_sock.getsockname()[1]


def _seal_packet(psk_bytes, inner_bytes):
    nonce = secrets.token_bytes(12)
    if AESGCM is not None:
        ct = AESGCM(psk_bytes[:16]).encrypt(nonce, inner_bytes, b"MOONP2P")
        return MAGIC + nonce + ct
    mac = hmac.new(psk_bytes, nonce + inner_bytes, hashlib.sha256).digest()[:16]
    return MAGIC + nonce + mac + inner_bytes


def _open_packet(psk_bytes, raw):
    if len(raw) < 2 + 12 + 16 or raw[:2] != MAGIC:
        return None
    nonce = raw[2:14]
    body = raw[14:]
    try:
        if AESGCM is not None:
            return AESGCM(psk_bytes[:16]).decrypt(nonce, body, b"MOONP2P")
        mac = body[:16]
        plain = body[16:]
        exp = hmac.new(psk_bytes, nonce + plain, hashlib.sha256).digest()[:16]
        if hmac.compare_digest(mac, exp):
            return plain
    except Exception:
        return None
    return None


def _pack_frame(psk_bytes, ptype, stream_id=0, seq=0, ack=0, payload=b""):
    hdr = struct.pack(HDR_FMT, ptype, 0, stream_id, seq, ack, len(payload))
    return _seal_packet(psk_bytes, hdr + payload)


def _unpack_frame(psk_bytes, raw):
    plain = _open_packet(psk_bytes, raw)
    if not plain or len(plain) < HDR_LEN:
        return None
    ptype, flags, stream_id, seq, ack, plen = struct.unpack(HDR_FMT, plain[:HDR_LEN])
    payload = plain[HDR_LEN:HDR_LEN + plen]
    if len(payload) != plen:
        return None
    return ptype, flags, stream_id, seq, ack, payload


class _ReliableStream:
    """Reliable ordered byte stream over multiplexed UDP frames attached to a local TCP socket."""

    def __init__(self, stream_id, tcp_sock, send_udp_fn, on_close_cb):
        self.stream_id = int(stream_id)
        self.tcp_sock = tcp_sock
        self.send_udp = send_udp_fn
        self.on_close_cb = on_close_cb

        self.lock = threading.Lock()
        self.send_next = 0
        self.send_acked = 0
        self.unacked = {}  # seq -> [first_ts, last_tx_ts, raw_wire_pkt]

        self.recv_next = 0
        self.ooo = {}  # seq -> bytes
        self.fin_seq = None
        self.closed = False
        self.local_eof_sent = False
        self.remote_eof_done = False

    def send_open_ctrl(self):
        with self.lock:
            pkt = _pack_frame_ref(self, PKT_OPEN, seq=0)
            self.unacked[-1] = [time.time(), time.time(), pkt]
        self.send_udp(pkt)

    def pump_tcp_to_udp(self):
        hard_err = False
        try:
            self.tcp_sock.settimeout(0.25)
            while not self.closed:
                with self.lock:
                    in_flight = len(self.unacked)
                if in_flight >= 64:
                    time.sleep(0.01)
                    continue
                try:
                    chunk = self.tcp_sock.recv(MAX_CHUNK)
                except socket.timeout:
                    continue
                except OSError:
                    hard_err = True
                    break
                if not chunk:
                    break
                with self.lock:
                    seq = self.send_next
                    self.send_next += 1
                    pkt = _pack_frame_ref(self, PKT_DATA, seq=seq, payload=chunk)
                    now = time.time()
                    self.unacked[seq] = [now, now, pkt]
                self.send_udp(pkt)
        finally:
            if hard_err:
                self.close_local()
            else:
                self.send_eof()

    def on_remote_data(self, seq, payload):
        deliver = []
        ack_val = 0
        should_finish = False
        with self.lock:
            if self.closed or self.remote_eof_done:
                return
            if seq == self.recv_next:
                deliver.append(payload)
                self.recv_next += 1
                while self.recv_next in self.ooo:
                    deliver.append(self.ooo.pop(self.recv_next))
                    self.recv_next += 1
            elif seq > self.recv_next and seq not in self.ooo and len(self.ooo) < 256:
                self.ooo[seq] = payload
            ack_val = self.recv_next
            if self.fin_seq is not None and self.recv_next >= self.fin_seq:
                should_finish = True

        for d in deliver:
            if d:
                try:
                    self.tcp_sock.sendall(d)
                except OSError:
                    self.close_local()
                    return

        self.send_udp(_pack_frame_ref(self, PKT_ACK, ack=ack_val))
        if should_finish:
            self._finish_remote_eof()

    def on_remote_close(self, fin_seq):
        with self.lock:
            self.fin_seq = fin_seq
            done_now = (not self.remote_eof_done) and (self.recv_next >= self.fin_seq)
        self.send_udp(_pack_frame_ref(self, PKT_ACK, ack=self.recv_next))
        if done_now:
            self._finish_remote_eof()

    def _finish_remote_eof(self):
        close_all = False
        with self.lock:
            if self.remote_eof_done:
                return
            self.remote_eof_done = True
            close_all = self.local_eof_sent and not self.unacked
        try:
            self.tcp_sock.shutdown(socket.SHUT_WR)
        except Exception:
            pass
        if close_all:
            self.shutdown()

    def on_remote_ack(self, ack_next):
        close_all = False
        with self.lock:
            for k in list(self.unacked.keys()):
                if k >= 0 and k < ack_next:
                    self.unacked.pop(k, None)
            if ack_next > self.send_acked:
                self.send_acked = ack_next
            close_all = self.local_eof_sent and self.remote_eof_done and not self.unacked
        if close_all:
            self.shutdown()

    def retransmit_tick(self, now):
        resend = []
        dead = False
        with self.lock:
            if self.closed:
                return
            for seq, meta in list(self.unacked.items()):
                first_ts, last_ts, pkt = meta
                if now - first_ts > 8.0:
                    dead = True
                    break
                if now - last_ts >= 0.12:
                    meta[1] = now
                    resend.append(pkt)
        if dead:
            self.shutdown()
            return
        for pkt in resend:
            self.send_udp(pkt)

    def send_eof(self):
        pkt = None
        close_all = False
        with self.lock:
            if self.local_eof_sent or self.closed:
                return
            self.local_eof_sent = True
            fin_s = self.send_next
            pkt = _pack_frame_ref(self, PKT_CLOSE, seq=fin_s)
            close_all = self.remote_eof_done and not self.unacked
        if pkt:
            self.send_udp(pkt)
        if close_all:
            self.shutdown()

    def close_local(self):
        self.send_eof()
        self.shutdown()

    def shutdown(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.unacked.clear()
            self.ooo.clear()
        try:
            self.tcp_sock.close()
        except Exception:
            pass
        if self.on_close_cb:
            self.on_close_cb(self.stream_id)


def _pack_frame_ref(stream_obj, ptype, seq=0, ack=0, payload=b""):
    return _pack_frame(stream_obj.psk_bytes, ptype, stream_obj.stream_id, seq, ack, payload)


class _UdpMuxSession:
    """Handles bidirectional encrypted UDP packets and TCP stream multiplexing for one peer link."""

    def __init__(self, udp_sock, psk_bytes, target_host=None, target_port=None):
        self.udp_sock = udp_sock
        self.psk_bytes = psk_bytes
        self.target_host = target_host
        self.target_port = target_port

        self.lock = threading.Lock()
        self.remote_addr = None
        self.streams = {}
        self.running = True
        self.last_rx = 0.0
        self.rtt_ms = 0
        self.connected_event = threading.Event()
        self.candidate_addrs = []
        self._next_stream_id = 1
        self._last_keepalive_tx = 0.0

    def add_candidates(self, addrs):
        with self.lock:
            for ip, port in addrs:
                if ip and port and (ip, int(port)) not in self.candidate_addrs:
                    self.candidate_addrs.append((ip, int(port)))

    def send_udp(self, raw_pkt):
        with self.lock:
            dest = self.remote_addr
            cands = list(self.candidate_addrs)
        try:
            if dest:
                self.udp_sock.sendto(raw_pkt, dest)
            else:
                for c in cands:
                    self.udp_sock.sendto(raw_pkt, c)
        except OSError:
            pass

    def punch_burst(self):
        pkt = _pack_frame(self.psk_bytes, PKT_PUNCH, seq=int(time.time() * 1000) & 0xFFFFFFFF)
        with self.lock:
            cands = list(self.candidate_addrs)
        for c in cands:
            try:
                self.udp_sock.sendto(pkt, c)
            except OSError:
                pass

    def _remove_stream(self, sid):
        with self.lock:
            self.streams.pop(sid, None)

    def _make_stream(self, sid, tcp_sock):
        st = _ReliableStream(sid, tcp_sock, self.send_udp, self._remove_stream)
        st.psk_bytes = self.psk_bytes
        return st

    def attach_client_tcp(self, client_sock):
        with self.lock:
            sid = self._next_stream_id
            self._next_stream_id += 2
            st = self._make_stream(sid, client_sock)
            self.streams[sid] = st
        self.send_udp(_pack_frame(self.psk_bytes, PKT_OPEN, stream_id=sid))
        threading.Thread(target=st.pump_tcp_to_udp, daemon=True).start()

    def _handle_open_from_peer(self, sid):
        with self.lock:
            if sid in self.streams:
                self.send_udp(_pack_frame(self.psk_bytes, PKT_ACK, stream_id=sid, ack=1))
                return
        if not self.target_host or not self.target_port:
            return
        try:
            srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv_sock.settimeout(3.0)
            srv_sock.connect((self.target_host, int(self.target_port)))
            st = self._make_stream(sid, srv_sock)
            with self.lock:
                self.streams[sid] = st
            self.send_udp(_pack_frame(self.psk_bytes, PKT_ACK, stream_id=sid, ack=1))
            threading.Thread(target=st.pump_tcp_to_udp, daemon=True).start()
        except Exception:
            self.send_udp(_pack_frame(self.psk_bytes, PKT_CLOSE, stream_id=sid, seq=0))

    def process_udp_packet(self, raw, addr):
        unpacked = _unpack_frame(self.psk_bytes, raw)
        if not unpacked:
            return
        ptype, _flags, sid, seq, ack, payload = unpacked
        now = time.time()
        with self.lock:
            if self.remote_addr != addr:
                self.remote_addr = addr
            self.last_rx = now

        if ptype == PKT_PUNCH:
            ack_pkt = _pack_frame(self.psk_bytes, PKT_PUNCH_ACK, seq=seq)
            try:
                self.udp_sock.sendto(ack_pkt, addr)
            except OSError:
                pass
            self.connected_event.set()
            return

        if ptype == PKT_PUNCH_ACK:
            t_low = int(now * 1000) & 0xFFFFFFFF
            rtt = (t_low - seq) & 0xFFFFFFFF
            if 0 <= rtt < 5000:
                self.rtt_ms = rtt
            self.connected_event.set()
            return

        if ptype == PKT_KEEPALIVE:
            return

        if ptype == PKT_OPEN:
            self._handle_open_from_peer(sid)
            return

        with self.lock:
            st = self.streams.get(sid)
        if not st:
            return

        if ptype == PKT_DATA:
            st.on_remote_data(seq, payload)
        elif ptype == PKT_ACK:
            st.on_remote_ack(ack)
        elif ptype == PKT_CLOSE:
            st.on_remote_close(seq)

    def tick(self):
        now = time.time()
        with self.lock:
            streams = list(self.streams.values())
        for st in streams:
            st.retransmit_tick(now)
        if self.connected_event.is_set() and now - self._last_keepalive_tx > 2.5:
            self._last_keepalive_tx = now
            self.send_udp(_pack_frame(self.psk_bytes, PKT_KEEPALIVE))

    def close(self):
        self.running = False
        with self.lock:
            streams = list(self.streams.values())
            self.streams.clear()
        for st in streams:
            st.shutdown()


class P2PHostManager:
    """Host-side STUN + Cloudflare Signaling + Multi-Peer UDP Hole Punching multiplexer."""

    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.room_code = ""
        self.host_id = ""
        self.host_name = ""
        self.local_port = 25565
        self.friends_only = True
        self.fallback_addr = ""
        self.stun_ip = ""
        self.stun_port = 0
        self.lan_ip = ""
        self.psk_hex = ""
        self.udp_sock = None
        self.sessions = {}  # addr -> _UdpMuxSession (or default single mux by peer)
        self.peer_sessions = {}  # peer_id -> _UdpMuxSession
        self._threads = []

    def start(self, host_id, host_name, local_port=25565, friends_only=True, fallback_addr="", skip_stun=False):
        self.stop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 0))
        sock.settimeout(0.15)
        self.udp_sock = sock
        self.lan_ip = get_local_lan_ip()
        local_udp_port = sock.getsockname()[1]

        if skip_stun:
            self.stun_ip, self.stun_port = self.lan_ip, local_udp_port
        else:
            pub_ip, pub_port = stun_discover(sock)
            self.stun_ip = pub_ip or self.lan_ip
            self.stun_port = pub_port or local_udp_port

        self.host_id = str(host_id).strip().upper()
        self.host_name = str(host_name).strip() or self.host_id
        self.local_port = int(local_port)
        self.friends_only = bool(friends_only)
        self.fallback_addr = str(fallback_addr or "").strip()
        self.psk_hex = secrets.token_hex(16)
        self.running = True

        import network_hub
        res = network_hub.cloud_api_request("/api/p2p/offer", "POST", {
            "host_id": self.host_id,
            "host_name": self.host_name,
            "local_port": self.local_port,
            "stun_ip": self.stun_ip,
            "stun_port": self.stun_port,
            "lan_ip": self.lan_ip,
            "lan_port": local_udp_port,
            "friends_only": self.friends_only,
            "fallback_addr": self.fallback_addr,
            "psk_hex": self.psk_hex,
        })
        if not res or not res.get("success"):
            self.stop()
            return {"success": False, "error": (res or {}).get("error", "Cloudflare P2P signaling failed")}

        self.room_code = res.get("room_code", "")
        t_rx = threading.Thread(target=self._rx_loop, daemon=True, name="MoonP2PHostRX")
        t_sig = threading.Thread(target=self._signal_loop, daemon=True, name="MoonP2PHostSig")
        t_rx.start()
        t_sig.start()
        self._threads = [t_rx, t_sig]
        return self.status()

    def _get_or_create_peer_session(self, peer_id, cands):
        psk = bytes.fromhex(self.psk_hex)
        with self.lock:
            sess = self.peer_sessions.get(peer_id)
            if not sess:
                sess = _UdpMuxSession(self.udp_sock, psk, target_host="127.0.0.1", target_port=self.local_port)
                self.peer_sessions[peer_id] = sess
            sess.add_candidates(cands)
            return sess

    def _rx_loop(self):
        psk = bytes.fromhex(self.psk_hex)
        while self.running and self.udp_sock:
            try:
                raw, addr = self.udp_sock.recvfrom(4096)
            except socket.timeout:
                with self.lock:
                    vals = list(self.peer_sessions.values())
                for s in vals:
                    s.tick()
                continue
            except OSError:
                break

            # Route packet to existing session matching remote_addr or open first valid authenticated packet
            target_sess = None
            with self.lock:
                for s in self.peer_sessions.values():
                    if s.remote_addr == addr or addr in s.candidate_addrs:
                        target_sess = s
                        break
                if target_sess is None and self.peer_sessions:
                    for s in self.peer_sessions.values():
                        if _open_packet(psk, raw) is not None:
                            target_sess = s
                            break
                if target_sess is None and _open_packet(psk, raw) is not None:
                    # Direct anonymous/unpolled valid authenticated peer packet (e.g. instant LAN)
                    key = f"{addr[0]}:{addr[1]}"
                    target_sess = _UdpMuxSession(self.udp_sock, psk, target_host="127.0.0.1", target_port=self.local_port)
                    target_sess.add_candidates([addr])
                    self.peer_sessions[key] = target_sess
            if target_sess:
                target_sess.process_udp_packet(raw, addr)

    def _signal_loop(self):
        import network_hub
        while self.running:
            try:
                data = network_hub.cloud_api_request(f"/api/p2p/candidates?room_code={self.room_code}", "GET")
                for c in (data or {}).get("candidates", []):
                    pid = c.get("peer_id") or ""
                    cands = []
                    if c.get("lan_ip") and c.get("lan_port"):
                        cands.append((c["lan_ip"], int(c["lan_port"])))
                    if c.get("stun_ip") and c.get("stun_port"):
                        cands.append((c["stun_ip"], int(c["stun_port"])))
                    if pid and cands:
                        sess = self._get_or_create_peer_session(pid, cands)
                        if not sess.connected_event.is_set():
                            sess.punch_burst()
            except Exception:
                pass
            for _ in range(10):
                if not self.running:
                    break
                time.sleep(0.1)

    def status(self):
        with self.lock:
            connected_peers = sum(1 for s in self.peer_sessions.values() if s.connected_event.is_set())
        return {
            "success": True,
            "running": self.running,
            "room_code": self.room_code,
            "host_id": self.host_id,
            "local_port": self.local_port,
            "stun_endpoint": f"{self.stun_ip}:{self.stun_port}" if self.stun_ip else "",
            "friends_only": self.friends_only,
            "fallback_addr": self.fallback_addr,
            "connected_peers": connected_peers,
        }

    def stop(self):
        was_running = self.running
        room = self.room_code
        hid = self.host_id
        self.running = False
        with self.lock:
            for s in self.peer_sessions.values():
                s.close()
            self.peer_sessions.clear()
        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass
            self.udp_sock = None
        if was_running and (room or hid):
            try:
                import network_hub
                network_hub.cloud_api_request("/api/p2p/close", "POST", {"room_code": room, "host_id": hid})
            except Exception:
                pass
        self.room_code = ""
        return {"success": True}


class P2PClientProxy:
    """Peer-side local 127.0.0.1:<port> TCP proxy bridged over STUN/UDP P2P or automatic relay fallback."""

    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.mode = "IDLE"  # PUNCHING | P2P_DIRECT | RELAY_FALLBACK
        self.room_code = ""
        self.host_name = ""
        self.local_tcp_port = 0
        self.fallback_addr = ""
        self.udp_sock = None
        self.tcp_srv = None
        self.session = None

    def connect(self, peer_id, peer_name, target_room_or_host, punch_timeout=3.8, skip_stun=False, version_dir=None):
        self.stop()
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(("0.0.0.0", 0))
        udp_sock.settimeout(0.15)
        lan_ip = get_local_lan_ip()
        local_udp_port = udp_sock.getsockname()[1]

        if skip_stun:
            stun_ip, stun_port = lan_ip, local_udp_port
        else:
            pub_ip, pub_port = stun_discover(udp_sock)
            stun_ip = pub_ip or lan_ip
            stun_port = pub_port or local_udp_port

        import network_hub
        resp = network_hub.cloud_api_request("/api/p2p/connect", "POST", {
            "peer_id": str(peer_id).strip().upper(),
            "peer_name": str(peer_name).strip(),
            "target": str(target_room_or_host).strip(),
            "stun_ip": stun_ip,
            "stun_port": stun_port,
            "lan_ip": lan_ip,
            "lan_port": local_udp_port,
        })
        if not resp or not resp.get("success"):
            udp_sock.close()
            return {"success": False, "error": (resp or {}).get("error", "Unable to reach P2P host")}

        self.room_code = resp.get("room_code", "")
        self.host_name = resp.get("host_name") or resp.get("host_id") or "Friend"
        self.fallback_addr = resp.get("fallback_addr") or ""
        psk_hex = resp.get("psk_hex") or ""
        if not psk_hex:
            udp_sock.close()
            return {"success": False, "error": "Missing P2P session key"}

        psk_bytes = bytes.fromhex(psk_hex)
        cands = []
        if resp.get("host_lan_ip") and resp.get("host_lan_port"):
            cands.append((resp["host_lan_ip"], int(resp["host_lan_port"])))
        if resp.get("host_stun_ip") and resp.get("host_stun_port"):
            cands.append((resp["host_stun_ip"], int(resp["host_stun_port"])))

        tcp_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_srv.bind(("127.0.0.1", 0))
        tcp_srv.listen(16)
        tcp_srv.settimeout(0.3)

        self.udp_sock = udp_sock
        self.tcp_srv = tcp_srv
        self.local_tcp_port = tcp_srv.getsockname()[1]
        self.running = True
        self.mode = "PUNCHING"

        sess = _UdpMuxSession(udp_sock, psk_bytes)
        sess.add_candidates(cands)
        self.session = sess

        threading.Thread(target=self._rx_loop, daemon=True, name="MoonP2PPeerRX").start()
        threading.Thread(target=self._accept_loop, daemon=True, name="MoonP2PPeerTCP").start()

        # Perform simultaneous UDP hole-punching burst up to punch_timeout
        deadline = time.time() + float(punch_timeout)
        while self.running and time.time() < deadline:
            sess.punch_burst()
            if sess.connected_event.wait(0.18):
                self.mode = "P2P_DIRECT"
                break

        if self.mode != "P2P_DIRECT":
            if self.fallback_addr:
                self.mode = "RELAY_FALLBACK"
            else:
                self.stop()
                return {
                    "success": False,
                    "error": "Strict NAT blocked direct UDP P2P and host has no Playit relay fallback active",
                }

        local_addr = f"127.0.0.1:{self.local_tcp_port}"
        if version_dir and os.path.isdir(version_dir):
            try:
                inject_p2p_server_entry(version_dir, f"Moon P2P: {self.host_name}", local_addr)
            except Exception:
                pass

        return {
            "success": True,
            "mode": self.mode,
            "room_code": self.room_code,
            "host_name": self.host_name,
            "local_address": local_addr,
            "rtt_ms": sess.rtt_ms if self.mode == "P2P_DIRECT" else None,
            "fallback_addr": self.fallback_addr,
        }

    def _rx_loop(self):
        while self.running and self.udp_sock and self.session:
            try:
                raw, addr = self.udp_sock.recvfrom(4096)
                self.session.process_udp_packet(raw, addr)
            except socket.timeout:
                self.session.tick()
            except OSError:
                break

    def _accept_loop(self):
        while self.running and self.tcp_srv:
            try:
                cli, _ = self.tcp_srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            if self.mode == "RELAY_FALLBACK" and self.fallback_addr:
                threading.Thread(target=self._bridge_relay_tcp, args=(cli,), daemon=True).start()
            elif self.session:
                self.session.attach_client_tcp(cli)
            else:
                cli.close()

    def _bridge_relay_tcp(self, cli_sock):
        try:
            host, port = (self.fallback_addr.split(":", 1)[0], int(self.fallback_addr.split(":", 1)[1])) if ":" in self.fallback_addr else (self.fallback_addr, 25565)
            up = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            up.settimeout(5.0)
            up.connect((host, port))
            up.settimeout(None)
            cli_sock.settimeout(None)

            def _pipe(src, dst):
                try:
                    while self.running:
                        buf = src.recv(8192)
                        if not buf:
                            break
                        dst.sendall(buf)
                except OSError:
                    pass
                finally:
                    try:
                        dst.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass

            t1 = threading.Thread(target=_pipe, args=(cli_sock, up), daemon=True)
            t2 = threading.Thread(target=_pipe, args=(up, cli_sock), daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        except Exception:
            pass
        finally:
            try:
                cli_sock.close()
            except Exception:
                pass

    def status(self):
        return {
            "running": self.running,
            "mode": self.mode,
            "room_code": self.room_code,
            "host_name": self.host_name,
            "local_address": f"127.0.0.1:{self.local_tcp_port}" if self.local_tcp_port else "",
            "rtt_ms": self.session.rtt_ms if self.session else 0,
        }

    def stop(self):
        self.running = False
        self.mode = "IDLE"
        if self.session:
            self.session.close()
            self.session = None
        if self.tcp_srv:
            try:
                self.tcp_srv.close()
            except Exception:
                pass
            self.tcp_srv = None
        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass
            self.udp_sock = None
        self.local_tcp_port = 0
        return {"success": True}


# ==============================================================================
# MINECRAFT servers.dat PURE-PYTHON NBT READER / INJECTOR
# ==============================================================================

def _nbt_read_str(buf, idx):
    ln = struct.unpack_from(">H", buf, idx)[0]
    idx += 2
    return buf[idx:idx + ln].decode("utf-8", errors="replace"), idx + ln


def _nbt_write_str(s):
    b = str(s).encode("utf-8")
    return struct.pack(">H", len(b)) + b


def _nbt_read_payload(tag_id, buf, idx):
    if tag_id == 1:
        return struct.unpack_from(">b", buf, idx)[0], idx + 1
    if tag_id == 2:
        return struct.unpack_from(">h", buf, idx)[0], idx + 2
    if tag_id == 3:
        return struct.unpack_from(">i", buf, idx)[0], idx + 4
    if tag_id == 4:
        return struct.unpack_from(">q", buf, idx)[0], idx + 8
    if tag_id == 5:
        return struct.unpack_from(">f", buf, idx)[0], idx + 4
    if tag_id == 6:
        return struct.unpack_from(">d", buf, idx)[0], idx + 8
    if tag_id == 7:
        n = struct.unpack_from(">i", buf, idx)[0]
        return bytes(buf[idx + 4:idx + 4 + n]), idx + 4 + n
    if tag_id == 8:
        return _nbt_read_str(buf, idx)
    if tag_id == 9:
        sub_type = buf[idx]
        count = struct.unpack_from(">i", buf, idx + 1)[0]
        idx += 5
        items = []
        for _ in range(max(0, count)):
            val, idx = _nbt_read_payload(sub_type, buf, idx)
            items.append(val)
        return (sub_type, items), idx
    if tag_id == 10:
        comp = {}
        while idx < len(buf):
            t = buf[idx]
            idx += 1
            if t == 0:
                break
            name, idx = _nbt_read_str(buf, idx)
            val, idx = _nbt_read_payload(t, buf, idx)
            comp[name] = (t, val)
        return comp, idx
    if tag_id == 11:
        n = struct.unpack_from(">i", buf, idx)[0]
        return list(struct.unpack_from(f">{n}i", buf, idx + 4)), idx + 4 + n * 4
    if tag_id == 12:
        n = struct.unpack_from(">i", buf, idx)[0]
        return list(struct.unpack_from(f">{n}q", buf, idx + 4)), idx + 4 + n * 8
    raise ValueError(f"Unsupported NBT tag: {tag_id}")


def _nbt_write_payload(tag_id, val):
    if tag_id == 1:
        return struct.pack(">b", int(val))
    if tag_id == 2:
        return struct.pack(">h", int(val))
    if tag_id == 3:
        return struct.pack(">i", int(val))
    if tag_id == 4:
        return struct.pack(">q", int(val))
    if tag_id == 5:
        return struct.pack(">f", float(val))
    if tag_id == 6:
        return struct.pack(">d", float(val))
    if tag_id == 7:
        return struct.pack(">i", len(val)) + val
    if tag_id == 8:
        return _nbt_write_str(val)
    if tag_id == 9:
        sub_type, items = val
        out = [bytes([sub_type]) + struct.pack(">i", len(items))]
        for it in items:
            out.append(_nbt_write_payload(sub_type, it))
        return b"".join(out)
    if tag_id == 10:
        out = []
        for k, (t, v) in val.items():
            out.append(bytes([t]))
            out.append(_nbt_write_str(k))
            out.append(_nbt_write_payload(t, v))
        out.append(b"\x00")
        return b"".join(out)
    if tag_id == 11:
        return struct.pack(f">i{len(val)}i", len(val), *val)
    if tag_id == 12:
        return struct.pack(f">i{len(val)}q", len(val), *val)
    raise ValueError(f"Unsupported NBT tag: {tag_id}")


def read_servers_dat(version_dir):
    """Reads <version_dir>/servers.dat as a list of dicts [{name, ip, icon?, acceptTextures?}]."""
    path = os.path.join(version_dir, "servers.dat")
    if not os.path.exists(path):
        return []
    raw = open(path, "rb").read()
    if len(raw) < 4 or raw[0] != 10:
        return []
    _, idx = _nbt_read_str(raw, 1)
    root, _ = _nbt_read_payload(10, raw, idx)
    srv_tag = root.get("servers")
    if not srv_tag or srv_tag[0] != 9:
        return []
    _sub_t, items = srv_tag[1]
    out = []
    for comp in items:
        if isinstance(comp, dict):
            out.append({
                "name": comp.get("name", (8, ""))[1],
                "ip": comp.get("ip", (8, ""))[1],
                "icon": comp.get("icon", (8, ""))[1] if "icon" in comp else "",
                "acceptTextures": comp.get("acceptTextures", (1, 1))[1],
            })
    return out


def inject_p2p_server_entry(version_dir, display_name, ip_addr):
    """Prepends or updates a Moon P2P server entry inside <version_dir>/servers.dat cleanly."""
    if not version_dir or not os.path.isdir(version_dir):
        return False
    existing = []
    try:
        existing = read_servers_dat(version_dir)
    except Exception:
        existing = []

    kept = [s for s in existing if not str(s.get("name", "")).startswith("Moon P2P:") and s.get("ip") != ip_addr]
    new_list = [{"name": display_name, "ip": ip_addr, "icon": "", "acceptTextures": 1}] + kept

    comp_items = []
    for s in new_list:
        c = {
            "name": (8, str(s.get("name") or "Minecraft Server")),
            "ip": (8, str(s.get("ip") or "")),
            "acceptTextures": (1, int(s.get("acceptTextures", 1))),
        }
        if s.get("icon"):
            c["icon"] = (8, str(s["icon"]))
        comp_items.append(c)

    root = {"servers": (9, (10, comp_items))}
    blob = b"\x0a" + _nbt_write_str("") + _nbt_write_payload(10, root)
    path = os.path.join(version_dir, "servers.dat")
    with open(path, "wb") as f:
        f.write(blob)
    return True


GLOBAL_P2P_HOST = P2PHostManager()
GLOBAL_P2P_PEER = P2PClientProxy()
