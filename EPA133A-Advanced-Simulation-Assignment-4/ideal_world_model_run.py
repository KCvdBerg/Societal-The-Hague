from ideal_world_model import BangladeshModel
import random
import pandas as pd

# ---------------------------------------------------------------
def RunExperiments(scenario, replications, runtime): # Runs per scenario
    """
    Function to run a simulation with the Bangladesh model
    for a given scenario and a number of replications.
    The results are collected in one dataframe.
    """

    # Create a dataframes for saving the results
    scenario_drive_data = pd.DataFrame(columns=['replication', 'avg_driving_time'])
    scenario_bridge_waiting_data = pd.DataFrame(columns=['replication', 'waiting_time', 'bridge_id','road'])
    scenario_bridge_breakdown_chances = pd.DataFrame(columns=['replication',  'bridge_id',  'condition', 'breakdown_chance'])
    scenario_bridge_truck_counter= pd.DataFrame(columns=['replication', 'truck_counter', 'bridge_id', 'road'])

    # To create the seeds randomly given x replications
    # If you want to replicate, change this to your own seeds for x amount of replications
    # You need a list of length x to create x replications
    seeds = [random.randint(1000000, 9999999) for _ in range(replications)]

    for replication_nr, seed in enumerate(seeds):
        sim_model = BangladeshModel(seed=seed, category_chances=scenario)
        for step in range(runtime):
            sim_model.step()

        # Extract the vehicle driving times from the model
        drive_data = sim_model.driving_times
        replication_drive_data = pd.DataFrame(drive_data, columns=['vehicle_id', 'driving_time'])
        avg_drive_data = replication_drive_data['driving_time'].mean()

        # Extract the different bridge attributes from the model
        bridge_data_wait = sim_model.waiting_times_dic
        bridge_data_breakdown = sim_model.breakdown_chances_list
        bridge_data_truck_counter = sim_model.truck_counter_bridge_dic

        # Keep track of the number of replications
        replication = replication_nr + 1

        # Add average driving time with replication
        replication_average_drive_data = pd.DataFrame([[replication, avg_drive_data]], columns=['replication',
                                                                                                 'avg_driving_time'])

        # Add the waiting times, breakdown chances and truck counter with replication
        keys_list_wait=list(bridge_data_wait.keys())
        replications_bridge_data_wait = pd.DataFrame.from_dict(bridge_data_wait, orient='index', columns = ['waiting_time','road'])
        replications_bridge_data_wait['bridge_id'] = keys_list_wait

        replications_bridge_data_breakdown = pd.DataFrame(bridge_data_breakdown, columns=[ 'bridge_id', 'condition', 'breakdown_chance'])

        keys_list_truck_counter = list(bridge_data_truck_counter.keys())
        replications_bridge_data_truck_counter = pd.DataFrame.from_dict(bridge_data_truck_counter, orient='index', columns = ['truck_counter', 'road'])
        replications_bridge_data_truck_counter['bridge_id'] = keys_list_truck_counter

        # Add the replication numbers to the dataframes as a column
        replications_bridge_data_breakdown['replication'] = replication
        replications_bridge_data_wait['replication'] = replication
        replications_bridge_data_truck_counter['replication'] = replication


        # Add the results from this replication to the scenario results
        scenario_drive_data = pd.concat([scenario_drive_data,replication_average_drive_data], ignore_index=True)
        scenario_bridge_waiting_data = pd.concat([scenario_bridge_waiting_data, replications_bridge_data_wait],
                                                 ignore_index=True)
        scenario_bridge_breakdown_chances = pd.concat([scenario_bridge_breakdown_chances, replications_bridge_data_breakdown],
                                                 ignore_index=True)
        scenario_bridge_truck_counter = pd.concat([scenario_bridge_truck_counter, replications_bridge_data_truck_counter],
                                                 ignore_index=True)

        # Show progress
        print("scenario {}, replication {} done".format(scenario, replication_nr + 1))

    return scenario_drive_data, scenario_bridge_waiting_data, scenario_bridge_breakdown_chances, scenario_bridge_truck_counter


# ---------------------------------------------------------------
'''Run the simulation in multiple scenarios for a set runtime
and number of replications. Save the results in csv files.'''

# Create a list of lists with each scenario (including scenario 0)
scenarios = [[0, 0, 0, 0]]
#
# Define the run time and the number of replications
run_length = 5 * 24 * 60
replications = 30

# Run the simulation for each scenario and save
for scenario_nr, scenario in enumerate(scenarios):
    scenario_drive_data, scenario_bridge_waiting_data, scenario_bridge_breakdown_chances,  scenario_bridge_truck_counter = RunExperiments(scenario,
                                                                                                          replications,
                                                                                                          run_length)
    scenario_drive_data.to_csv('../experiment/scenario{}.csv'.format(scenario_nr), index=False)
    scenario_bridge_waiting_data.to_csv('../experiment/scenario{}_bridges_wait.csv'.format(scenario_nr), index=False)
    scenario_bridge_breakdown_chances.to_csv('../experiment/scenario{}_bridges_breakdown.csv'.format(scenario_nr),index=False)
    scenario_bridge_truck_counter.to_csv('../experiment/scenario{}_bridges_truck_counter.csv'.format(scenario_nr),index=False)