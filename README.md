Work I did for UChicago Trading Competition 2021 as part of the Financial Markets Program.

I worked on 2/3 of the Cases in the Competition, specifically Case 2 which was the Options Market Making case and Case 3 which was the Portfolio Allocation case.

The case packet and platform we used for the competition are also provided.

# Case 2
The Options Market Making Case.

We are given a highly volatile equity with unknown fundamentals as our underlying, and have to make markets on European call & put options across 5 different strike prices. In addition, risk limits on delta, gamma, vega, and theta of the portfolio as a whole are also imposed, with penalties should they be violated.

## Strategy
1) Estimate the "true" annualized instantaneous volatility of the underlying by taking a weighted average of historical volatility & implied volatility.
2) Compute the "fair price" of all 10 options using the BSM formula.
3) Adjust this theoretical fair price by our positions for each option. Intuition being that if we have large positive or negative positions as a market maker, clearly our "fair price" is biased upwards or downwards.
4) Quote a spread around this adjusted fair price.
5) In addition, only quote bids when theta gets too negative/vega gets too positive, and only quote asks when vega gets too negative to conform to the risk limits imposed.
6) Delta hedge using the underlying.

# Case 3
The classic Portfolio Allocation case.

We are given the 10 year historical data of the prices of 8 stocks, 8 bonds, and 8 commodities, for a total of 24 assets. We are then asked to come up with an asset allocation strategy to maximize Sharpe ratio for the next 10 years. Specifically, we need to compute weights for each of the 24 assets for each timestep in the next 10 years, and can only take long positions.

## Strategy
The historical data we were given was first split into 8 years training/validation and 2 years testing.

For each timestep in the future, we used weights that were the argmax for historical Sharpe ratio over some lookback window. This was computed using Scipy.minimize. This lookback window was then optimized over the training/validation data.

Alternatives strategies considered but that did not make the cut included computing weights that minimized portfolio variance over some lookback period.

In addtiton, I had to code up a backtesting framework for this case.