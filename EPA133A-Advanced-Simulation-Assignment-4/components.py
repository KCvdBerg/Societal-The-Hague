from mesa import Agent
from enum import Enum
import random


# ---------------------------------------------------------------
class Infra(Agent):
    """
    Base class for all infrastructure components

    Attributes
    __________
    vehicle_count : int
        the number of vehicles that are currently in/on (or totally generated/removed by)
        this infrastructure component

    length : float
        the length in meters
    ...

    """

    def __init__(self, unique_id, model, length=0,
                 name='Unknown', road_name='Unknown'):
        super().__init__(unique_id, model)
        self.length = length
        self.name = name
        self.road_name = road_name
        self.vehicle_count = 0
        self.vehicle_total = 0 # Added to collect final vehicle counts

    def step(self):
        pass

    def __str__(self):
        return type(self).__name__ + str(self.unique_id)


# ---------------------------------------------------------------
class Bridge(Infra):
    """
    Creates delay time

    Attributes
    __________
    condition:
        condition of the bridge

    delay_time: int
        the delay (in ticks) caused by this bridge
    ...

    """

    def __init__(self, unique_id, model, length=0,
                 name='Unknown', road_name='Unknown',
                 condition='Unknown', numLanes = 1, vul_cat= 1.0,
                 breakdown = False, breakdown_chance = 0, truck_counter_bridge = 0):
        super().__init__(unique_id, model, length, name, road_name)

        self.length = length
        self.condition = condition
        self.numLanes = numLanes
        self.vul_cat = vul_cat/2
        self.truck_counter_bridge = truck_counter_bridge
        self.breakdown = breakdown
        self.breakdown_chance = breakdown_chance

        # Attributes used for the assignment
        self.delay_time = self.get_delay_time()
        self.breakdown_chance_function()


    # Delay time set by length and number of lanes
    # The capacity of the bridge is determined by the number of lanes
    def get_delay_time(self):
        if self.breakdown:  # Only delays when the bridge is broken down
            if self.length > 200:
                self.delay_time = (self.random.triangular(60, 120, 240) / self.numLanes)
            elif self.length <= 200 and self.length > 50:
                self.delay_time = (self.random.uniform(45, 90) / self.numLanes)
            elif self.length <= 50 and self.length > 10:
                self.delay_time = (self.random.uniform(15, 60) / self.numLanes)
            elif self.length <= 10:
                self.delay_time = (self.random.uniform(10, 20) / self.numLanes)

            return self.delay_time
        else:
            self.delay_time = 0
            return self.delay_time


    # Breakdown chance determined by condition category
    def breakdown_chance_function(self):
        # Based on the vulnerability index the bridge receives (based on location) and
        # the chances of breakdown the bridges with a specific type of condition get, the bridge is broken down
        # or not.
        if self.condition == 'A':
            breakdown_chance_bridge = self.model.percCatA + self.vul_cat

            if self.random.random() < breakdown_chance_bridge:
                self.breakdown = True
                self.breakdown_chance = breakdown_chance_bridge
            else:
                self.breakdown = False
                self.breakdown_chance = breakdown_chance_bridge
            # For every bridge, the breakdown chances are added to the model attribute breakdown_chances_list
            self.model.breakdown_chances_list.append([self.unique_id, self.condition, self.breakdown_chance])

        if self.condition == 'B':
            breakdown_chance_bridge = self.model.percCatB + self.vul_cat

            if self.random.random() < breakdown_chance_bridge:
                self.breakdown = True
                self.breakdown_chance = breakdown_chance_bridge
            else:
                self.breakdown = False
                self.breakdown_chance = breakdown_chance_bridge
            self.model.breakdown_chances_list.append([self.unique_id, self.condition, self.breakdown_chance])

        if self.condition == 'C':
            breakdown_chance_bridge = self.model.percCatC + self.vul_cat

            if self.random.random() < breakdown_chance_bridge:
                self.breakdown = True
                self.breakdown_chance = breakdown_chance_bridge
            else:
                self.breakdown = False
                self.breakdown_chance = breakdown_chance_bridge
            self.model.breakdown_chances_list.append([self.unique_id, self.condition, self.breakdown_chance])

        if self.condition == 'D':
            breakdown_chance_bridge = self.model.percCatD + self.vul_cat

            if self.random.random() < breakdown_chance_bridge:
                self.breakdown = True
                self.breakdown_chance = breakdown_chance_bridge
            else:
                self.breakdown = False
                self.breakdown_chance = breakdown_chance_bridge
            self.model.breakdown_chances_list.append([self.unique_id, self.condition, self.breakdown_chance])


# ---------------------------------------------------------------
class Link(Infra):
    def __init__(self, unique_id, model, length=0,
                 name='Unknown', road_name='Unknown'):
        super().__init__(unique_id, model, length,
                         name, road_name)


# ---------------------------------------------------------------
class Intersection(Infra):
    pass


# ---------------------------------------------------------------
class Sink(Infra):
    """
    Sink removes vehicles

    Attributes
    __________
    vehicle_removed_toggle: bool
        toggles each time when a vehicle is removed
    ...

    """
    vehicle_removed_toggle = False

    def remove(self, vehicle):
        self.model.schedule.remove(vehicle)
        self.vehicle_removed_toggle = not self.vehicle_removed_toggle
        #print(str(self) + ' REMOVE ' + str(vehicle))


# ---------------------------------------------------------------

class Source(Infra):
    """
    Source generates vehicles

    Class Attributes:
    -----------------
    truck_counter : int
        the number of trucks generated by ALL sources. Used as Truck ID!

    Attributes
    __________
    generation_frequency: int
        the frequency (the number of ticks) by which a truck is generated

    vehicle_generated_flag: bool
        True when a Truck is generated in this tick; False otherwise
    ...

    """

    truck_counter = 0
    generation_frequency = 5
    vehicle_generated_flag = False

    def generate_truck(self):
        """
        Generates a truck, sets its path, increases the global and local counters
        """
        try:
            agent = Vehicle('Truck' + str(Source.truck_counter), self.model, self)
            if agent:
                self.model.schedule.add(agent)
                agent.set_path()
                Source.truck_counter += 1
                self.vehicle_count += 1
                self.vehicle_generated_flag = True
                #print(str(self) + " GENERATE " + str(agent))
        except Exception as e:
            print("Oops!", e.__class__, "occurred.")


# ---------------------------------------------------------------
class SourceSink(Source, Sink):
    """
    Generates and removes trucks
    """

    def __init__(self, unique_id, model, length=0,
                 name='Unknown', road_name='Unknown',
                 traffic_weight=0):

        super().__init__(unique_id, model, length,
                 name, road_name)
        self.traffic_weight = traffic_weight

    def step(self):
        if random.choices([True, False], weights=[self.traffic_weight, 1-self.traffic_weight])[0]:
            self.generate_truck()
        else:
            self.vehicle_generated_flag = False

# ---------------------------------------------------------------
class Vehicle(Agent):
    """

    Attributes
    __________
    speed: float
        speed in meter per minute (m/min)

    step_time: int
        the number of minutes (or seconds) a tick represents
        Used as a base to change unites

    state: Enum (DRIVE | WAIT)
        state of the vehicle

    location: Infra
        reference to the Infra where the vehicle is located

    location_offset: float
        the location offset in meters relative to the starting point of
        the Infra, which has a certain length
        i.e. location_offset < length

    path_ids: Series
        the whole path (origin and destination) where the vehicle shall drive
        It consists the Infras' uniques IDs in a sequential order

    location_index: int
        a pointer to the current Infra in "path_ids" (above)
        i.e. the id of self.location is self.path_ids[self.location_index]

    waiting_time: int
        the time the vehicle needs to wait

    generated_at_step: int
        the timestamp (number of ticks) that the vehicle is generated

    removed_at_step: int
        the timestamp (number of ticks) that the vehicle is removed
    ...

    """

    # 48 km/h translated into meter per min
    speed = 48 * 1000 / 60
    # One tick represents 1 minute
    step_time = 1

    class State(Enum):
        DRIVE = 1
        WAIT = 2

    def __init__(self, unique_id, model, generated_by,
                 location_offset=0, path_ids=None):
        super().__init__(unique_id, model)
        self.generated_by = generated_by
        self.generated_at_step = model.schedule.steps
        self.location = generated_by
        self.location_offset = location_offset
        self.pos = generated_by.pos
        self.path_ids = path_ids
        # default values
        self.state = Vehicle.State.DRIVE
        self.location_index = 0
        self.waiting_time = 0
        self.waited_at = None
        self.removed_at_step = None

    def __str__(self):
        return "Vehicle" + str(self.unique_id) + \
               " +" + str(self.generated_at_step) + " -" + str(self.removed_at_step) + \
               " " + str(self.state) + '(' + str(self.waiting_time) + ') ' + \
               str(self.location) + '(' + str(self.location.vehicle_count) + ') ' + str(self.location_offset)

    def set_path(self):
        """
        Set the origin destination path of the vehicle
        """
        self.path_ids = self.model.get_route(self.generated_by.unique_id)

    def step(self):
        """
        Vehicle waits or drives at each step
        """
        if self.state == Vehicle.State.WAIT:
            self.waiting_time = max(self.waiting_time - 1, 0)
            if self.waiting_time == 0:
                self.waited_at = self.location
                self.state = Vehicle.State.DRIVE

        if self.state == Vehicle.State.DRIVE:
            self.drive()

        """
        To print the vehicle trajectory at each step
        """
        #print(self)

    def drive(self):

        # the distance that vehicle drives in a tick
        # speed is global now: can change to instance object when individual speed is needed
        distance = Vehicle.speed * Vehicle.step_time
        distance_rest = self.location_offset + distance - self.location.length

        if distance_rest > 0:
            # go to the next object
            self.drive_to_next(distance_rest)
        else:
            # remain on the same object
            self.location_offset += distance

    def drive_to_next(self, distance):
        """
        vehicle shall move to the next object with the given distance
        """

        self.location_index += 1
        next_id = self.path_ids[self.location_index]
        next_infra = self.model.schedule._agents[next_id]  # Access to protected member _agents
        if isinstance(next_infra, Sink):
            # arrive at the sink
            self.arrive_at_next(next_infra, 0)
            self.removed_at_step = self.model.schedule.steps
            # Driving times of the vehicle are appended to the model attribute driving_times
            self.model.driving_times.append(
                [self.unique_id, self.removed_at_step - self.generated_at_step])  # Added to register driving time
            self.location.remove(self)
            return
        elif isinstance(next_infra, Bridge):
            self.waiting_time = next_infra.get_delay_time()
            # Counting the number of trucks passing the specific bridge
            next_infra.truck_counter_bridge += 1
            # These values are added per bridge to a dictionary, defined as a model attribute
            if next_infra.unique_id in self.model.truck_counter_bridge_dic.keys():
                if self.model.truck_counter_bridge_dic[next_infra.unique_id][0] < next_infra.truck_counter_bridge:
                    self.model.truck_counter_bridge_dic[next_infra.unique_id] = [next_infra.truck_counter_bridge, next_infra.road_name]
            else:
                self.model.truck_counter_bridge_dic[next_infra.unique_id] = [next_infra.truck_counter_bridge, next_infra.road_name]

            if self.waiting_time > 0:
                # arrive at the bridge and wait
                self.arrive_at_next(next_infra, 0)
                self.state = Vehicle.State.WAIT

                #Total waiting times are collected in the dictionary attribute of the model, for each bridge.
                if next_infra.unique_id in self.model.waiting_times_dic.keys():
                    self.model.waiting_times_dic[next_infra.unique_id] += self.waiting_time
                else:
                    self.model.waiting_times_dic[next_infra.unique_id] = self.waiting_time
                return
            # else, continue driving

        if next_infra.length > distance:
            # stay on this object:
            self.arrive_at_next(next_infra, distance)
        else:
            # drive to next object:
            self.drive_to_next(distance - next_infra.length)



    def arrive_at_next(self, next_infra, location_offset):
        """
        Arrive at next_infra with the given location_offset
        """
        self.location.vehicle_count -= 1
        self.location = next_infra
        self.location_offset = location_offset
        self.location.vehicle_count += 1
        next_infra.vehicle_total += 1

# EOF -----------------------------------------------------------
