
import dimod
import pandas as pd
import sys
from dwave.system import LeapHybridDQMSampler

def build_knapsack_dqm(costs, weights, numbers, weight_capacity):
  """Construct DQM for the knapsack problem
    Args:
        costs (array-like):
            Array of costs associated with the items
        weights (array-like):
            Array of weights associated with the items
        numbers (array-like):
            Array of maximum quantity of each item that is available
        weight_capacity (int):
            Maximum allowable weight
    Returns:
        Discrete quadratic model instance
  """
  # intialize DQM
  dqm = dimod.DiscreteQuadraticModel()

   # Lagrangian multiplier
  # First guess as suggested in Lucas's paper (might want to change)
  lagrange = max(costs)

  # Number of different items
  x_size = len(costs)
  
  # Build the DQM starting by adding variables
  for item in range(x_size):
    dqm.add_variable(numbers[item] + 1, label = 'x' + str(item))

  # add y
  dqm.add_variable(weight_capacity, label = 'y')

  # Hamiltonian xi terms
  for k in range(x_size):
    dqm.set_linear('x' + str(k), [-costs[k] * i + lagrange * weights[k] ** 2 * i ** 2 for i in range(numbers[k] + 1)])

  # Hamiltonian xi-xj terms
  for i in range(x_size):
    for j in range(i + 1, x_size):
      xixj_values = [[xi * xj * 2 * lagrange * weights[i] * weights[j] for xi in range(numbers[i] + 1)] for xj in range(numbers[j] + 1)]
      dqm.set_quadratic('x' + str(i), 'x' + str(j), xixj_values)

  # Hamiltonian y-y term
  dqm.set_linear('y', [lagrange * i ** 2 for i in range(1,weight_capacity + 1)])

  # Hamiltonian x-y terms
  for i in range(x_size):
    xy_values = [[-2 * lagrange * weights[i] * x * y for x in range(numbers[i] + 1)] for y in range(1,weight_capacity + 1)]
    dqm.set_quadratic('x' + str(i), 'y', xy_values)

  return dqm
  

def solve_knapsack(costs, weights, numbers, weight_capacity, sampler=None):
    """Construct DQM and solve the knapsack problem

    Args:
        costs (array-like):
            Array of costs associated with the items
        weights (array-like):
            Array of weights associated with the items
        numbers (array-like):
            Array of the number associated with each item
        weight_capacity (int):
            Maximum allowable weight
        sampler (DQM sampler instance or None):
            A DQM sampler instance or None, in which case
            LeapHybridDQMSampler is used by default

    Returns:
        Tuple:
            Dictionary keyed by indices of selected items and containing the number of each item 
            Solution energy
    """
    dqm = build_knapsack_dqm(costs, weights, numbers, weight_capacity)
    
    if sampler is None:
        sampler = LeapHybridDQMSampler()

    sampleset = sampler.sample_dqm(dqm, label='Example - Knapsack')
    sample = sampleset.first.sample
    energy = sampleset.first.energy
    print(sample)

    selected_items = {}

    for varname, value in sample.items():
      # For each "x" variable, check whether its value is >0, which indicates that the corresponding item is included in the knapsack
      if (value>0) and varname.startswith('x'):
        #The index into the weight array is retrieved from the variable name
        selected_items[int(varname[1:])] = value

    return selected_items, energy

if __name__ == '__main__':

    data_file_name = sys.argv[1] if len(sys.argv) > 1 else "large.csv"
    weight_capacity = int(sys.argv[2]) if len(sys.argv) > 2 else 70

    # parse input data
    df = pd.read_csv(data_file_name, names=['cost', 'weight', 'number'])

    selected_items, energy = solve_knapsack(df['cost'], df['weight'], df['number'], weight_capacity)
    selected_item_indices = selected_items.keys()
    number_of_items = list(selected_items.values())
    
    selected_weights = list(df.loc[selected_item_indices,'weight'])
    selected_costs = list(df.loc[selected_item_indices,'cost'])
    #multiplying each of the selected items weights and costs by the number of each item included
    total_selected_weights = [selected_weights[i]*number_of_items[i] for i in range(len(selected_weights))]
    total_selected_costs = [selected_costs[i]*number_of_items[i] for i in range(len(selected_costs))]

    print("Found solution at energy {}".format(energy))
    print("Selected item numbers (0-indexed) and corresponding number of items:", selected_items)
    print("Selected item weights: {}, selected item weights times number of each item: {}, total = {}".format(selected_weights, total_selected_weights, sum(total_selected_weights)))
    print("Selected item costs: {}, selected item costs times number of each item: {}, total = {}".format(selected_costs, total_selected_costs, sum(total_selected_costs)))