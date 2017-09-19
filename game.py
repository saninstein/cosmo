from abc import ABCMeta, abstractmethod, abstractproperty
from resources import Resources
import uuid
import os
import asyncio




class Specials(metaclass=ABCMeta):

	@abstractmethod
	def special(self):
		raise NotImplementedError


class JSONSerializable(metaclass=ABCMeta):

	@abstractmethod
	def to_JSON(self):
		raise NotImplementedError


class Uniqueable:
	def __init__(self):
		self.__id = uuid.uuid4().hex

	@property
	def id(self):
		return self.__id

	@id.setter
	def id(self, value):
		self.__id = value


class Positionable:

	def __init__(self, x, y):
		self.__x = x
		self.__y = y

	@property
	def x(self):
		return self.__x

	@x.setter
	def x(self, value):
		self.__x = value

	@property
	def y(self):
		return self.__y

	@y.setter
	def y(self, value):
		self.__y = value


class Serilizeable:

	def serilize(self):
		pass


class PositionDecorator(Positionable):
	def __init__(self, positionable):
		self.__positionable = positionable

	@property
	def x(self):
		return self.__positionable.x

	@x.setter
	def x(self, value):
		self.__positionable.x = value

	@property
	def y(self):
		return self.__positionable.y

	@y.setter
	def y(self, value):
		self.__positionable.y = value

	def get_revolving_obj(self):
		return self.__positionable

	def __str__(self):
		return str(self.__positionable)


class Drawable:
	def __init__(self, canvas, resource=None):
		self.__resource = resource
		self.__canvas = canvas
		self.__img = None

	def draw(self, x, y):
		if self.__dict__.get('__img') is None:
			self.__img = self.__canvas.create_image(
				x, y, image=self.__resource)
		else:
			raise TypeError

	def redraw(self, x, y):
		self.__canvas.coords(self.__img, x, y)

	def get_boundbox(self):
		return self.__canvas.bbox(self.__img)

	def dispose(self):
		self.__canvas.delete(self.__img)

	def get_canvas(self):
		return self.__canvas


class Existable:
	def __init__(self, exist=True):
		self.__exist = exist

	def сease_to_exist(self):
		self.__exist = False

	def __bool__(self):
		return self.__exist


class SpaceObject(Serilizeable, Uniqueable, Positionable, Existable):
	def __init__(self, x, y):
		Positionable.__init__(self, x, y)
		Uniqueable.__init__(self)
		Existable.__init__(self, True)


class Label(Positionable, Drawable):
	def __init__(self, canvas, x, y, text='', **kwargs):
		self.text = text
		Positionable.__init__(self, x, y)
		Drawable.__init__(self, canvas)
		self._Drawable__img = self.get_canvas().create_text(
			self.x, self.y, text=self.text, **kwargs)

	def redraw(self):
		canvas = self.get_canvas()
		canvas.itemconfig(self._Drawable__img, text=self.text)
		Drawable.redraw(self, self.x, self.y)




class Flyable(metaclass=ABCMeta):

	@abstractmethod
	def fly(self):
		raise NotImplementedError


class BonusCreator:
	@classmethod
	def createBonus(cls, param, x, y):
		if param % 2 == 0:
			return Bonus(x, y, Laser)
		else:
			return Bonus(x, y, Wave)

class ShipDrawCreator:
	@classmethod
	def createShip(cls, ship, canvas, _type='self'):
		if _type == 'self':
			return ShipDrawDecorator(ship, canvas)
		elif _type == "reverse":
			return ShipDrawDecorator(
				ship, canvas,
				resource=Resources.ship_reversed_enemy_img
			)
		else:
			return ShipDrawDecorator(ship, canvas, resource=Resources.ship_enemy_img)


def point_in_bbox(x, y, bbox):
	return x >= bbox[0] and x <= bbox[2] and y <= bbox[3] and y >= bbox[1]


def bbox_in_bbox(Ax0, Ay0, Ax1, Ay1, Bx0, By0, Bx1, By1):
	return all((Ax0 < Bx1, Ax1 > Bx0, Ay0 < By1, Ay1 > By0))


class Bonus(SpaceObject, Flyable):

	def __init__(self, x, y, kind):
		Positionable.__init__(self, x, y)
		Uniqueable.__init__(self)
		Existable.__init__(self, True)
		self.kind = kind

	def install_special(self, ship):
		ship.specials.append(self.kind)

	def fly(self):
		self.y += 0.5

	def serialize(self):
		return {
			'type': type(self).__name__,
			'id': self.id,
			'coords': (self.x, self.y)
		}


class BonusDrawDecorator(Bonus, Drawable, PositionDecorator):

	def __init__(self, bonus, canvas):
		self.bonus = bonus
		Drawable.__init__(self, canvas, resource=Resources.bonus_img)
		PositionDecorator.__init__(self, bonus)
		self.draw(bonus.x, bonus.y)

	def fly(self):
		self.bonus.fly()
		self.redraw(self.bonus.x, self.bonus.y)

	def install_special(self, ship):
		self.bonus.install_special(ship)

	def dispose(self):
		self.bonus.сease_to_exist()
		Drawable.dispose(self)

	def serilize(self):
		self.bonus.serilize()


class Ship(SpaceObject):

	def __init__(self, x, y, name="Ship"):
		self.name = name
		SpaceObject.__init__(self, x, y)
		self.specials = []
		self._health = 100

	@property
	def health(self):
		return self._health

	@health.setter
	def health(self, value):
		self._health = value

	def fire(self):
		pass

	def special(self, other):
		pass

	def serialize(self):
		return {
			'type': type(self).__name__,
			'id': self.id,
			'coords': (self.x, self.y),
			'health': self.health
		}


class ShipDrawDecorator(Ship, Drawable, PositionDecorator):

	def __init__(self, ship, canvas, resource=Resources.ship_img):
		self.ship = ship
		self.name = ship.name
		self.specials = self.ship.specials
		Drawable.__init__(self, canvas, resource=resource)
		PositionDecorator.__init__(self, ship)
		self.draw(ship.x, ship.y)

	def fire(self):
		return Rocket(self.x, self.get_boundbox()[1], self)

	def redraw(self):
		Drawable.redraw(self, self.ship.x, self.ship.y)

	def dispose(self):
		Drawable.dispose(self)
		self.ship.сease_to_exist()

	def special(self, other):
		try:
			special = self.ship.specials.pop(0)
			special(
				self.x, self.get_boundbox()[1], self.get_canvas(), owner=self
			).special(other)
		except IndexError:
			pass

	@property
	def health(self):
		return self.ship.health

	@health.setter
	def health(self, value):
		self.ship.health = value

	def serialize(self):
		return self.ship.serialize()


class Asteroid(SpaceObject, Flyable):

	def __init__(self, x, y, speed=0.5):
		SpaceObject.__init__(self, x, y)
		self.killer = None
		self.speed = speed

	def fly(self):
		self.y += self.speed

	async def destroy(self):
		self.сease_to_exist()

	def __str__(self):
		return "<Asteroid ({}, {}) exist={}>".format(self.x, self.y, bool(self))

	def serialize(self):
		return {
			'type': type(self).__name__,
			'id': self.id,
			'coords': (self.x, self.y)
		}


class AsteroidDrawDecorator(Asteroid, Drawable, PositionDecorator):

	def __init__(self, asteroid, canvas):
		self.asteroid = asteroid
		Drawable.__init__(
			self, canvas, resource=Resources.asteroid_img)
		PositionDecorator.__init__(self, asteroid)
		self.draw(asteroid.x, asteroid.y)

	def fly(self):
		self.asteroid.fly()
		self.redraw(self.asteroid.x, self.asteroid.y)

	@property
	def killer(self):
		return self.asteroid.killer

	@killer.setter
	def killer(self, value):
		self.asteroid.killer = value

	async def destroy(self):
		await self.asteroid.destroy()
		self.dispose()
		smoke = self.get_canvas().create_image(
			self.x, self.y, image=Resources.asteroid_smoke_img)
		await asyncio.sleep(0.5)
		self.get_canvas().delete(smoke)

	def dispose(self):
		Drawable.dispose(self)
		self.asteroid.сease_to_exist()

	def get_revolving_obj(self):
		return self.asteroid

	def serialize(self):
		return self.asteroid.serialize()

	def __bool__(self):
		return bool(self.asteroid)


class Rocket(SpaceObject):

	def __init__(self, x, y, owner=None):
		SpaceObject.__init__(self, x, y)
		self.owner = owner

	def fly(self):
		self.y -= 7

	def serialize(self):
		return {
			'type': type(self).__name__,
			'id': self.id,
			'coords': (self.x, self.y)
		}


class ReversedRocketDecorator(Rocket, Uniqueable, PositionDecorator):

	def __init__(self, rocket):
		self.rocket = rocket
		self.owner = rocket.owner
		self.id = rocket.id
		PositionDecorator.__init__(self, self.rocket)

	def cease_to_exist(self):
		self.rocket.cease_to_exist()

	def fly(self):
		self.y += 7

	def serialize(self):
		return self.rocket.serialize()

	def __bool__(self):
		return bool(self.rocket)


class RocketDrawDecorator(Rocket, Drawable, PositionDecorator):

	def __init__(self, rocket, canvas, resource=Resources.rocket_img):
		self.rocket = rocket
		Drawable.__init__(self, canvas, resource=resource)
		PositionDecorator.__init__(self, rocket)
		self.draw(rocket.x, rocket.y)
		self.id = rocket.id

	def fly(self):
		self.rocket.fly()
		self.redraw(self.rocket.x, self.rocket.y)

	def dispose(self):
		self.rocket.сease_to_exist()
		Drawable.dispose(self)

	@property
	def owner(self):
		return self.rocket.owner

	def serialize(self):
		return self.rocket.serialize()


class Laser(Specials, SpaceObject, Drawable):

	def __init__(self, x, y, canvas, owner=None):
		self.owner = owner
		SpaceObject.__init__(self, x, y)
		Drawable.__init__(self, canvas)
		self._Drawable__img = self.get_canvas().create_line(
				self.x, self.y, self.x, 0, fill="red", width=3)

	async def dispose(self):
		self.сease_to_exist()
		await asyncio.sleep(0.05)
		Drawable.dispose(self)

	def special(self, other):
		for item in other:
			try:
				if item:
					x0, y0, x1, y1 = item.get_boundbox()
					if self.x > x0 and self.x < x1 and y0 <= self.y:
						item.killer = self.owner
						asyncio.ensure_future(item.destroy())
			except TypeError:
				pass
		asyncio.ensure_future(self.dispose())


class Wave(Specials, Drawable, SpaceObject):

	def __init__(self, x, y, canvas, owner=None, width=30):
		Uniqueable.__init__(self)
		Positionable.__init__(self, x, y)
		Drawable.__init__(self, canvas)
		Existable.__init__(self, True)
		self.owner = owner
		self.width = width
		self._Drawable__img = self.get_canvas().create_line(
			x - self.width, y, x + self.width, y, fill="blue", width=3)

	def special(self, other):
		asyncio.ensure_future(self.__special(other))

	async def __special(self, other):
		while self.y > 0:
			xa = self.x - self.width
			xb = self.x + self.width
			for item in other:
				if item:
					try:
						x0, y0, x1, y1 = item.get_boundbox()
						f = any((xa < x0 and xb > x1, xa > x0 and xa < x1, xb > x0 and xb < x1))
						if self.y > y0 and self.y < y1 and f:
							item.killer = self.owner
							asyncio.ensure_future(item.destroy())
					except TypeError:
						pass

			self.width += 1.25
			self.y -= 15
			self.dispose()
			self._Drawable__img = self.get_canvas().create_line(
				xa, self.y, xb, self.y, fill="blue", width=3)
			await asyncio.sleep(0.00005)
		self.dispose()
		self.сease_to_exist()


class СontainerWithIds():

	def __init__(self, iters=None, id_getter=lambda x: x.id, item_getter=None):
		if iters is None:
			self.iters = []
		else:
			self.iters = iters
		self.id_getter = id_getter
		self.item_getter = item_getter

	def get_by_id(self, _id):
		for item in self:
			if self.id_getter(item) == _id:
				return item
		return None

	def remove(self, obj):
		try:
			self.iters.remove(obj)
		except ValueError:
			pass

	def remove_by_id(self, _id):
		try:
			self.iters.remove(self.get_by_id(_id))
			return True
		except ValueError:
			return False

	def append(self, obj):
		self.iters.append(obj)

	def __len__(self):
		return len(self.iters)

	def __iter__(self):
		return iter(self.iters)

	def __str__(self):
		return "<{} :{}>".format(type(self).__name__, self.iters)


class SmartConteiner(СontainerWithIds):

	def __init__(self, id_getter=lambda x: x.id, item_getter=None):
		СontainerWithIds.__init__(self, id_getter=id_getter, item_getter=item_getter)

	def remove_not_exists(self):
		self.iters = [x for x in self if x.get_revolving_obj()]


class BattleFiled:
	def __init__(self, canvas):
		pass
