import serial
import threading
import time
import re

from threading import Lock
from datetime import datetime
from concurrent.futures import *

from .exceptions import *
from .const import *
from .poller import SerialPoller

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

class Device(object):
	# The ThreadPoolExecutor actualls serves two purposes:
	#	1.) Provide a way to return results asynchronously
	# 	2.) Limit amount of concurrent interacting processes to one (not true)
	# Concurrency is being handled by my_lock.
	executor = ThreadPoolExecutor(max_workers=1)
	my_lock = Lock()
	message_event = threading.Event()
	signal_strength = None
	message_available = False
	had_session = False

	def __init__(self, addr):
		self.port = serial.Serial(addr, 19200, timeout=None)
		self.serial = SerialPoller(self, self.port)
		self.session_timeout = 10

		# setup
		self._echo_off()
		self._set_settings()

	def _echo_off(self):
		with self.my_lock:
			self.port.write(com_echo_off)
			self.serial.wait_for(reg_ok)

	def _get_info(self, name):
		with self.my_lock:
			self.port.write(b"AT+" + name + b"\r")
			last, logs = self.serial.read_until(reg_ok)
			for s in logs:
				if len(s) > 0:
					return s

	def _initiate_session(self, response):
		had_session = True
		print("WAIT FOR NETWORK")
		self._wait_for_network()
		print("GOT NETWORK")
		self.port.write(response and com_session_ring or com_session)
		last, logs = self.serial.read_until(reg_ok)
		for msg in logs:
			if msg[:7] == ans_session_start:
				values = re.findall(reg_num, msg[7:])
				print(values)
				if values[2] == 1:
					print("GOT MESSAGES")
					message_available = True
					self.message_event.set()

				if values[0] < 5:
					print("SUCCESS")
					# return momsn code
					return values[1]
				else:
					raise DeviceError("Session failed with code " + str(values[0]))

	def _initiate_session_with_lock(self, response):
		with self.my_lock:
			self._initiate_session(response)

	def _set_settings(self):
		with self.my_lock:
			for com in [com_set_ring_alert, com_set_alerts, com_set_registration]:
				self.port.write(com)
				self.serial.wait_for(reg_ok)

	def _send_message(self, msg):
		with self.my_lock:
			msg = _prepare_byte(msg)
			self.port.write(b"AT+SBDWB=" + bytes(str(len(msg)-2).encode('utf-8')) + b"\r")
			self.serial.wait_for(reg_ready)
			self.port.write(msg)
			code = self.serial.wait_for(reg_num)
			if code != b"0":
				raise DeviceError("Expected code '0', got " + code)
			return self._initiate_session(False)

	def _interpret_registration(self, msg):
		print("REG: " + msg)

	def _wait_for_network(self):
		# Reporting should already be enabled, but ye
		# Expects lock to be already obtained
		self.port.write(com_set_alerts)
		self.serial.wait_for(reg_ciev_registered, self.session_timeout)

	def _get_time(self):
		with self.my_lock:
			self.port.write(com_ask_time)
			last, logs = self.serial.read_until(reg_ok)
			for string in logs:
				if reg_time.match(string) != None:
					numbers = reg_num.findall(string)
					for i in range(len(numbers)):
						numbers[i] = int(numbers[i])
					return datetime(
						year = numbers[0] + 2000,
						month = numbers[1],
						day = numbers[2],
						hour = numbers[3],
						minute = numbers[4],
						second = numbers[5]
					)

	def _get_signal_quality(self):
		with self.my_lock:
			self.port.write(com_ask_quality)
			last = self.serial.wait_for(reg_quality)
			return int(reg_num.findall(last)[0])

	# does the actual reading, assumes lock is already obtained
	def _actual_read_message(self):
		self.port.write(com_read)

	def _read_message(self):
		if not self.message_available:
			self._initiate_session_with_lock(False)

		print("attempted to read message")
		if not self.message_available:
			self.message_event.wait()
			self.message_event.clear()

		with self.my_lock:
			message_available = False
			print("RECIEVE MESSAGE")
			msg = self._actual_read_message()
			print(msg)

		return 2

	def _initiate_session_async(self, msg, response):
		"""Attempts to start a session async.

		Should only be used by the GlobalJob triggered by SBDRING.
		"""
		self.executor.submit(self._initiate_session_with_lock, response)

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
		return self.executor.submit(self._get_info, b"CGMI")

	def get_model(self):
		"""Queries the modem's model.

		Returns a future object.
		"""
		return self.executor.submit(self._get_info, b"CGMM")

	def get_revision(self):
		"""Queries the modem's revision.

		Returns a future object.
		"""
		return self.executor.submit(self._get_info, b"CGMR")

	def get_serial(self):
		"""Queries the modem's serial number.

		Returns a future object.
		"""
		return self.executor.submit(self._get_info, b"CGSN")

	def get_time(self):
		"""Queries the iridium network's system time.

		Returns a future object.
		"""
		return self.executor.submit(self._get_time)

	def get_signal_quality(self):
		"""Queries the modem's signal quality.

		Returns a future object.
		"""
		return self.executor.submit(self._get_signal_quality)

	def send_message(self, msg):
		return self.executor.submit(self._send_message, msg)

	def read_message(self):
		return self.executor.submit(self._read_message)

	def set_session_timeout(self, s):
		self.session_timeout = s
