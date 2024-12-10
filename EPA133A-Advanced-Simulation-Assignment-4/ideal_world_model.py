from mesa import Model
from mesa.time import BaseScheduler
from mesa.space import ContinuousSpace
from ideal_world_components import Source, Sink, SourceSink, Bridge, Link, Intersection
import pandas as pd
from collections import defaultdict
import networkx as nx


# ---------------------------------------------------------------
def set_lat_lon_bound(lat_min, lat_max, lon_min, lon_max, edge_ratio=0.02):
    """
    Set the HTML continuous space canvas bounding box (for visualization)
    give the min and max latitudes and Longitudes in Decimal Degrees (DD)

    Add white borders at edges (default 2%) of the bounding box
    """

    lat_edge = (lat_max - lat_min) * edge_ratio
    lon_edge = (lon_max - lon_min) * edge_ratio

    x_max = lon_max + lon_edge
    y_max = lat_min - lat_edge
    x_min = lon_min - lon_edge
    y_min = lat_max + lat_edge
    return y_min, y_max, x_min, x_max


# ---------------------------------------------------------------
class BangladeshModel(Model):
    """
    The main (top-level) simulation model

    One tick represents one minute; this can be changed
    but the distance calculation need to be adapted accordingly

    Class Attributes:
    -----------------
    step_time: int
        step_time = 1 # 1 step is 1 min

    path_ids_dict: defaultdict
        Key: (origin, destination)
        Value: the shortest path (Infra component IDs) from an origin to a destination

        Only straight paths in the Demo are added into the dict;
        when there is a more complex network layout, the paths need to be managed differently

    sources: list
        all sources in the network

    sinks: list
        all sinks in the network

    """

    step_time = 1

    file_name = '../data/processed/cleaned_data_final.csv'
    weighted_roads_path = '../data/processed/road_weights.csv'

    def __init__(self, seed=None, x_max=500, y_max=500, x_min=0,
                 y_min=0, category_chances=[0,0,0,0]):

        self.schedule = BaseScheduler(self)
        self.running = True
        self.path_ids_dict = defaultdict(lambda: pd.Series())
        self.space = None
        self.sources = []
        self.sinks = []

        # Divide chances by 100 to get decimal chance
        self.category_chances = category_chances
        self.percCatA = self.category_chances[0] / 100
        self.percCatB = self.category_chances[1] / 100
        self.percCatC = self.category_chances[2] / 100
        self.percCatD = self.category_chances[3] / 100

        # Used to store to be analysed variables
        self.driving_times = []
        self.waiting_times_dic = {}
        self.breakdown_chances_list = []
        self.truck_counter_bridge_dic = {}

        self.generate_model()

    def generate_model(self):
        """
        generate the simulation model according to the csv file component information

        Warning: the labels are the same as the csv column labels
        """

        df = pd.read_csv(self.file_name)
        df['length'] = df['length'].fillna(0)

        def generate_network():
            # Create graph that can be accessed outside this function
            global G
            G = nx.Graph()

            # Iterate each row and create node based on lat and lon
            # Add weight equal to the length of the LRP
            for i, row in df.iterrows():
                G.add_node(row['id'], pos=(row['lon'], row['lat']))
                # Edges are connected to the node before the current node
                if row['LRPName'] != 'LRPS': # Start and end of roads are treated differently
                    G.add_edge(df.iloc[i]['id'], df.iloc[i - 1]['id'])
                    G.add_edge(df.iloc[i]['id'], df.iloc[i - 1]['id'], weight=df.iloc[i]['length'])
                elif i + 1 == len(df):  # For the last node in the dataframe
                    G.add_edge(df.iloc[i]['id'], df.iloc[i - 1]['id'])
                    G.add_edge(df.iloc[i]['id'], df.iloc[i - 1]['id'], weight=df.iloc[i]['length'])
                elif df.iloc[i]['road'] != df.iloc[i + 1]['road']:  # Check for the end of the road
                    G.add_edge(df.iloc[i]['id'], df.iloc[i - 1]['id'])
                    G.add_edge(df.iloc[i]['id'], df.iloc[i - 1]['id'], weight=df.iloc[i]['length'])

            pos = nx.get_node_attributes(G, 'pos')
            nx.draw(G, pos, with_labels=False, node_color='orange')

        generate_network()

        # a list of names of roads to be generated
        # TODO You can also read in the road column to generate this list automatically

        roads = df['road'].unique()
        df_objects_all = []
        for road in roads:
            # Select all the objects on a particular road in the original order as in the cvs
            df_objects_on_road = df[df['road'] == road]
            if not df_objects_on_road.empty:
                df_objects_all.append(df_objects_on_road)

                """
                Set the path 
                1. get the serie of object IDs on a given road in the cvs in the original order
                2. add the (straight) path to the path_ids_dict
                3. put the path in reversed order and reindex
                4. add the path to the path_ids_dict so that the vehicles can drive backwards too
                """
                path_ids = df_objects_on_road['id']
                path_ids.reset_index(inplace=True, drop=True)
                self.path_ids_dict[path_ids[0], path_ids.iloc[-1]] = path_ids
                self.path_ids_dict[path_ids[0], None] = path_ids
                path_ids = path_ids[::-1]
                path_ids.reset_index(inplace=True, drop=True)
                self.path_ids_dict[path_ids[0], path_ids.iloc[-1]] = path_ids
                self.path_ids_dict[path_ids[0], None] = path_ids

        # put back to df with selected roads so that min and max and be easily calculated
        df_original = pd.concat(df_objects_all)
        y_min, y_max, x_min, x_max = set_lat_lon_bound(
            df['lat'].min(),
            df['lat'].max(),
            df['lon'].min(),
            df['lon'].max(),
            0.05
        )

        # ContinuousSpace from the Mesa package;
        # not to be confused with the SimpleContinuousModule visualization
        self.space = ContinuousSpace(x_max, y_max, True, x_min, y_min)

        # Dictionary used to set weights of SourceSinks
        df_weighted_roads = pd.read_csv(self.weighted_roads_path)
        road_weight_dict = df_weighted_roads.set_index('Road')['Weight'].to_dict()

        for df in df_objects_all:
            for _, row in df.iterrows():  # index, row in ...

                # create agents according to model_type
                model_type = row['model_type'].strip()
                agent = None
                name = row['name']
                if pd.isna(name):
                    name = ""
                else:
                    name = name.strip()
                if model_type == 'source':
                    agent = Source(row['id'], self, row['length'], name, row['road'])
                    self.sources.append(agent.unique_id)
                elif model_type == 'sink':
                    agent = Sink(row['id'], self, row['length'], name, row['road'])
                    self.sinks.append(agent.unique_id)
                elif model_type == 'sourcesink':
                    if len(df_original.loc[df_original['id'] == row['id']]) == 1: # Check if it is an only sourcesink
                        agent = SourceSink(row['id'], self, row['length'], name, row['road'], road_weight_dict[row['road']])
                        self.sources.append(agent.unique_id)
                        self.sinks.append(agent.unique_id)
                elif model_type == 'bridge':
                    agent = Bridge(row['id'], self, row['length'], name, row['road'], row['condition'], row['lanes'], row['vul_cat'])
                elif model_type == 'link':
                    agent = Link(row['id'], self, row['length'], name, row['road'])
                elif model_type == 'intersection':
                    if not row['id'] in self.schedule._agents:
                        agent = Intersection(row['id'], self, row['length'], name, row['road'])

                if agent:
                    self.schedule.add(agent)
                    y = row['lat']
                    x = row['lon']
                    self.space.place_agent(agent, (x, y))
                    agent.pos = (x, y)


    def get_random_route(self, source):
        """
        pick up a random route given an origin
        """
        while True:
            # different source and sink
            sink = self.random.choice(self.sinks)
            if sink is not source:
                break
        return sink

    # TODO
    def get_route(self, source):
        """
        set sink given a source
        if the route is known, follow that route
        if not, calculate the shortest path
        """
        sink = self.get_random_route(source)
        if (source, sink) in self.path_ids_dict:
            return self.path_ids_dict[source, sink]
        elif not (source, sink) in self.path_ids_dict:
            return self.calculate_route(source, sink)
        elif sink == None:
            return self.get_straight_route(source)

    def calculate_route(self, source, sink):
        self.path_ids_dict[source, sink] = nx.dijkstra_path(G, source, sink)
        return self.path_ids_dict[source, sink]

    def get_straight_route(self, source):
        """
        pick up a straight route given an origin
        """
        return self.path_ids_dict[source, None]

    def calculate_average_driving_time(self):
        if len(self.driving_times) > 0:
            self.average_driving_times = sum(self.driving_times) / len(self.driving_times)
            return self.average_driving_times
        else:
            return self.average_driving_times

    #def collect_vehicle_counts(self):



    def step(self):
        """
        Advance the simulation by one step.
        """
        self.schedule.step()


# EOF -----------------------------------------------------------
