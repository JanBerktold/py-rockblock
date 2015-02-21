import serial
import threading
import time
import re
from concurrent import futures

class SerialJob:
	done = False
	result = ""
	regex = ""

	def __init__(self, regex):
		self.regex = regex

class SerialPoller:
	jobs = []
	logs = []
	buf = ""

	def __init__(self, dev, serial):
		self.device = dev
		self.serial = serial
		self.thread = threading.Thread(target=self.worker)
		self.thread.start()

	def worker(self):
		while True:
			byte = self.serial.read(1)
			self.buf += byte

			for job in self.jobs:
				if re.match(job.regex, self.buf) != None:
					job.done = True
					self.jobs.remove(job)

			if byte == "\r" or byte == "\n":
				self.logs.append(self.buf[:-1])
				self.buf = ""

	def _reset(self):
		self.jobs = []
		self.buffer = ""
		self.logs = []

	def read_until(self, regex):
		self._reset()
		job = SerialJob(regex)
		self.jobs.append(job)
		while not job.done:
			time.sleep(0.5)
		return job.result, self.logs

	def wait_for(self, regex):
		self._reset()
		job = SerialJob(regex)
		self.jobs.append(job)
		while not job.done:
			time.sleep(0.5)
		return job.result

class Device:
	executor = futures.ThreadPoolExecutor(max_workers=1)

	def __init__(self, addr):
		self.port = serial.Serial(addr, 19200)
		self.serial = SerialPoller(self, self.port)

		# setup
		self._echo_off()

	def sendMessage(self, msg):
		print(msg)

	def _echo_off(self):
		self.port.write("ATE0\r")
		self.serial.wait_for("OK\r")

	def _get_info(self, name):
		self.port.write("AT+" + name + "\r")
		last, logs = self.serial.read_until("OK\r")
		for s in logs:
			if len(s) > 0:
				return s

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
