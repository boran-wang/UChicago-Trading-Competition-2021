import numpy as np
import pandas as pd
from scipy import optimize

#compute the sharpe ratio
def compute_sharpe(weights, mean_vector, cov_matrix):
    mean = np.dot(weights,mean_vector)
    var = np.dot(np.dot(weights,cov_matrix),weights.T)
    return mean/np.sqrt(var)

#objective function to be minimized
def objective_func(weights, mean_vector, cov_matrix):
    return -compute_sharpe(weights, mean_vector, cov_matrix)

#compute weights to max the sharpe ratio given fixed mean_vector and cov_matrix
def compute_optimal_weights(mean_vector,cov_matrix,starting_weights):
    res = optimize.minimize(objective_func,x0=starting_weights,args=(mean_vector,cov_matrix),method='SLSQP',bounds=24*[(0,None)],constraints={'type':'eq','fun':lambda x: x.sum()-1})
    return res.x

#given past data, calculate the starting weights
def compute_starting_weights(past_prices):
    past_returns = past_prices.pct_change().dropna()

    mean_vector = past_returns.mean(axis=0)
    cov_matrix = past_returns.cov()

    return compute_optimal_weights(mean_vector,cov_matrix,np.repeat(1/24,24))

past_prices = pd.read_csv('Case3HistoricalPrices.csv',index_col=0)[-50:]
current_weight = compute_starting_weights(past_prices)

#the actual thing I need to work on
def allocate_portfolio(new_prices):
    global past_prices
    past_prices = past_prices.append(new_prices)
    past_returns = past_prices.pct_change().dropna()
    past_prices = past_prices[1:]
    #compute the mean_vector and cov_matrix
    mean_vector = past_returns.mean(axis=0)
    cov_matrix = past_returns.cov()
    
    global current_weight
    res = compute_optimal_weights(mean_vector,cov_matrix,current_weight)
    current_weight = res
    return res