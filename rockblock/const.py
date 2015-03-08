import re

reg_ok = re.compile(b"OK\r")
reg_ciev_registered = re.compile(b"\+CIEV:[0-9],[^0]")
reg_num = re.compile(b"[0-9]+")
reg_ready = re.compile(b"READY")
reg_time = re.compile(b"\+CCLK:[0-9]+/[0-9]+/[0-9]+,[0-9]+:[0-9]+:[0-9]+")
reg_quality = re.compile(b"\+CSQ:[0-9]+")

com_echo_off = b"ATE0\r"
com_set_alerts = b"AT+CIER=1,1,0,0\r"
com_set_ring_alert = b"AT+SBDMTA=1\r"
com_set_registration = b"AT+SBDAREG=1\r"
com_session = b"AT+SBDIX\r"
com_session_ring = b"AT+SBDIXA\r"
com_ask_time = b"AT+CCLK?\r"
com_ask_quality = b"AT+CSQ\r"
com_read = b"AT+SBDRB"

ans_session_start = b"+SBDIX:"
