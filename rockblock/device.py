import serial
import threading
import time
import exceptions
import re
import const
from concurrent import futures
from poller import SerialPoller

def _prepare_byte(msg):
	array = bytearray(msg)
	sum = 0

	for by in array:
		sum += by

	first = sum&0xff
	sum >>= 8
	second = sum&0xff

	array.append(second)
	array.append(first)
	return array

class Device:
	# The ThreadPoolExecutor actualls serves two purposes:
	#	1.) Provide a way to return results asynchronously
	# 	2.) Limit amount of concurrent interacting processes to one
	executor = futures.ThreadPoolExecutor(max_workers=1)
	signal_strength = None

	def __init__(self, addr):
		self.port = serial.Serial(addr, 19200, timeout=0.5)
		self.serial = SerialPoller(self, self.port)

		# setup
		self._echo_off()
		self._set_settings()

	def _echo_off(self):
		self.port.write(com_echo_off)
		self.serial.wait_for(reg_ok)

	def _get_info(self, name):
		self.port.write("AT+" + name + "\r")
		last, logs = self.serial.read_until(reg_ok)
		for s in logs:
			if len(s) > 0:
				return s

	def _initiate_session_async(self, msg, response):
		"""Attempts to start a session async.

		Should only be used by the GlobalJob triggered by SBDRING.
		"""
		self.executor.submit(self._initiate_session, response)

	def _initiate_session(self, response):
		print(response)
		print("WAIT FOR NETWORK")
		self._wait_for_network()
		print("GOT NETWORK")
		self.port.write(response and com_session_ring or com_session)
		last, logs = self.serial.read_until(reg_ok)
		for msg in logs:
			if msg[:7] == "+SBDIX:":
				values = re.findall(reg_num, msg[7:])
				if values[0] < 4:
					print("SUCCESS")
				else:
					raise DeviceError ("Session failed with code " + str(values[0]))
				break

	def _set_settings(self):
		for com in ["AT+SBDMTA=1\r", com_set_alerts, com_set_registration]:
			self.port.write(com)
			self.serial.wait_for(reg_ok)

	def _send_message(self, msg):
		msg = _prepare_byte(msg)
		self.port.write("AT+SBDWB=" + str(len(msg)-2) + "\r")
		self.serial.wait_for(reg_ready)
		self.port.write(msg)
		code = self.serial.wait_for(reg_num)
		if code != "0":
			raise DeviceError("Expected code '0', got " + code)
		return self._initiate_session(False)

	def _interpret_registration(self, msg):
		print("REG: " + msg)

	def _handle_signal(self, msg):
		print("RECIEVED UPDATE: " + msg)

	def _wait_for_network(self):
		# Reporting should already be enabled, but ye
		self.port.write(com_set_alerts)
		print(self.serial.wait_for(reg_ciev_registered))

	def close(self):
		"""Terminates all outgoing connections.

		Device instance is afterwards not going to be useful:
		There is currently no implemented way to reopen a port.
		"""
		self.serial.running = False
		self.port.close()

	def get_manufacturer(self):
		"""Queries the modem's manufacturer.

		Returns a future object.
		"""
		return self.executor.submit(self._get_info, "CGMI")

	def get_model(self):
		"""Queries the modem's model.

		Returns a future object.
		"""
		return self.executor.submit(self._get_info, "CGMM")

	def get_revision(self):
		"""Queries the modem's revision.

		Returns a future object.
		"""
		return self.executor.submit(self._get_info, "CGMR")

	def get_serial(self):
		"""Queries the modem's serial number.

		Returns a future object.
		"""
		return self.executor.submit(self._get_info, "CGSN")

	def send_message(self, msg):
		return self.executor.submit(self._send_message, msg)
