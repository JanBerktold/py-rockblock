import serial
import threading
import time
import exceptions
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
	executor = futures.ThreadPoolExecutor(max_workers=1)

	def __init__(self, addr):
		self.port = serial.Serial(addr, 19200)
		self.serial = SerialPoller(self, self.port)

		# setup
		self._echo_off()
		self._set_settings()

	def _echo_off(self):
		self.port.write("ATE0\r")
		self.serial.wait_for("OK\r")

	def _get_info(self, name):
		self.port.write("AT+" + name + "\r")
		last, logs = self.serial.read_until("OK\r")
		for s in logs:
			if len(s) > 0:
				return s

	def _initiate_session(self):
		print("now")

	def _set_settings(self):
		self.port.write("AT+SBDMTA=1\r")
		self.serial.wait_for("OK\r")
		self.port.write("AT+CIER=1,1,0,0\r")
		self.serial.wait_for("OK\r")
		self.port.write("AT+SBDAREG=1\r")
		self.serial.wait_for("OK\r")

	def _send_message(self, msg):
		msg = _prepare_byte(msg)
		self.port.write("AT+SBDWB=" + str(len(msg)-2) + "\r")
		self.serial.wait_for("READY")
		self.port.write(msg)
		code = self.serial.wait_for("[0-9]")
		if code != "0":
			raise DeviceError("Expected code '0', got " + code)
		return self._initiate_session()

	def _handle_signal(self, msg):
		print("RECIEVED UPDATE: " + msg)

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
