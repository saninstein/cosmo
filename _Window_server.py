from itertools import chain
from abc import ABCMeta, abstractmethod
from collections import defaultdict
import tkinter as tk
import random
import asyncio
import socket
import datetime
import time
import json
import os
import uuid
from game import Bonus, BonusCreator, Asteroid, Rocket, СontainerWithIds

MODE = 1

def onclose(root, loop):
	for task in asyncio.Task.all_tasks():
		task.cancel()
	asyncio.ensure_future(exit(loop))


async def exit(loop):
	loop.stop()


class Server:

	def __init__(self, loop):
		self.loop = loop
		self.MODE = 1
		self.connections = []
		self.asteroids = СontainerWithIds()
		self.WIDTH = 500
		self.HEIGHT = 680

		self.sock = socket.socket()
		self.sock.bind(('localhost', 5678))
		self.sock.listen(2)
		self.sock.setblocking(False)
		print("=======Server run=======")
		self.tasks = defaultdict(None)
		self.tasks['accept_connections'] = asyncio.ensure_future(self.accept_connections())

	async def accept_connections(self):
		while True:
			print('accept')
			conn, addr = await loop.sock_accept(self.sock)
			self.connections.append(conn)
			print("New conn:", addr, len(self.connections))
			if len(self.connections) == 2:
				self.tasks['get_msg'] = asyncio.ensure_future(self.get_req())
				return 0

	async def update(self):
		await asyncio.sleep(2.5)
		while self.MODE == 1:
			msg = defaultdict(list)
			current_time = datetime.datetime.now().time()
			pick = random.randint(1, self.WIDTH)
			await asyncio.sleep(0.0005)

			if pick % 2 == 0 and len(self.asteroids) < 9:
				new_asteroids = [Asteroid(random.randint(10, self.WIDTH - 10), 0, random.randint(1, 5)) for x in range(random.randint(1, 2))]
				msg['create'] += [x.serialize() for x in new_asteroids]
				for new_asteroid in new_asteroids:
					self.asteroids.append(new_asteroid)

			print("A:{} B:{}".format(len(self.asteroids), len(self.bonuses)))
			if 'create' in msg or 'dispose' in msg:
				print("POST S[{}]".format(datetime.datetime.now().time()), msg)
				await self.send_msg(json.dumps(msg))

			self.asteroids = СontainerWithIds([x for x in self.asteroids if x])

			for objs in (self.asteroids,):
				for obj in objs:
					if obj.y < 0 or obj.y > self.HEIGHT:
						obj.сease_to_exist()
						objs.remove_by_id(obj.id)

	async def send_msg(self, msg, ignore=None):
		for conn in self.connections:
			if conn is not ignore:
				await self.loop.sock_sendall(conn, msg.encode())

	async def get_req(self):
		while True:

			await asyncio.sleep(0.00005)
			print('get')
			for conn in self.connections:
				try:
					msg = conn.recv(1024)
					msg_decoded = msg.decode()

					print("GET S [{}]".format(datetime.datetime.now().time()), msg_decoded)
					if msg_decoded == "/duel":
						self.MODE = 2
						continue
					elif msg_decoded == "/co":
						self.MODE = 1
						self.tasks['update'] = asyncio.ensure_future(self.update())
						continue
					elif msg_decoded == "/close" or not msg:
						self.MODE = 0
						self.connections.remove(conn)
						await self.send_msg("/close")
						asyncio.ensure_future(self.accept_connections())
						return 0

					msg_decoded = json.loads(msg_decoded)

					if 'dispose' in msg_decoded:
						for item in msg_decoded['dispose']:
							_id = item['id']
							self.asteroids.remove_by_id(_id)
					await self.send_msg(msg, ignore=conn)
				except json.decoder.JSONDecodeError:
					print("JSON Error")
				except socket.error:
					print("socket Error")


loop = asyncio.get_event_loop()

server = Server(loop)

try:
	loop.run_forever()
finally:
	loop.close()
