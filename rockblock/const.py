import re

reg_ok = re.compile("OK\r")
reg_ciev_registered = re.compile("\+CIEV:[0-9],[^0]")
reg_num = re.compile("[0-9]+")
reg_ready = re.compile("READY")
reg_time = re.compile("\+CCLK:[0-9]+/[0-9]+/[0-9]+,[0-9]+:[0-9]+:[0-9]+")

com_echo_off = "ATE0\r"
com_set_alerts = "AT+CIER=1,1,0,0\r"
com_set_ring_alert = "AT+SBDMTA=1\r"
com_set_registration = "AT+SBDAREG=1\r"
com_session = "AT+SBDIX\r"
com_session_ring = "AT+SBDIXA\r"
com_ask_time = "AT+CCLK?\r"

ans_session_start = "+SBDIX:"
