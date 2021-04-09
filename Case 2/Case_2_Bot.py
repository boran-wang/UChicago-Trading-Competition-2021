#!/usr/bin/env python

from dataclasses import astuple
from utc_bot import UTCBot, start_bot
import proto.utc_bot as pb
import betterproto

import asyncio
import random

import numpy as np
import math
import py_vollib.black_scholes_merton.implied_volatility as bsmv
import py_vollib.black_scholes_merton as bsm
import py_vollib.black_scholes_merton.greeks.analytical as bsmga

option_strikes = [90, 95, 100, 105, 110]


class Case2_Bot(UTCBot):
    """
    An example bot for Case 2 of the 2021 UChicago Trading Competition. We recommend that you start
    by reading through this bot and understanding how it works. Then, make a copy of this file and
    start trying to write your own bot!
    """

    async def handle_round_started(self):
        """
        This function is called when the round is started. You should do your setup here, and
        start any tasks that should be running for the rest of the round.
        """

        # This variable will be a map from asset names to positions. We start out by initializing it
        # to zero for every asset.
        self.positions = {}

        self.positions["UC"] = 0
        for strike in option_strikes:
            for flag in ["C", "P"]:
                self.positions[f"UC{strike}{flag}"] = 0

        # Stores the current day (starting from 0 and ending at 5). This is a floating point number,
        # meaning that it includes information about partial days
        self.current_day = 0

        # Stores the current value of the underlying asset
        self.underlying_price = 100

        # stores a list of past underlying prices
        self.past_underlying_prices = []

        # stores the current prices of the 10 options
        self.options_prices = {}
        for strike in option_strikes:
            for flag in ["C", "P"]:
                self.options_prices[f"UC{strike}{flag}"] = -1

    def compute_exchange_implied_vol(self) -> float:
        '''
        function to compute implied volatility suggested by the exchange
        '''
        if self.options_prices['UC100C'] == -1:
            return None

        total_vol = 0
        total_weight = 0

        for strike in option_strikes:
            for flag in ["C", "P"]:
                # Weight to be used for the weighted average
                # (for motivation, look up how vega is computed in B-S model)
                weight = math.exp(0.5 * math.log(self.underlying_price / strike) ** 2)

                # This function should compute the Black-Scholes implied volatility
                time_to_expiry = (26-self.current_day)/252 
                vol = bsmv.implied_volatility(
                    self.options_prices[f"UC{strike}{flag}"],
                    self.underlying_price,
                    strike,
                    time_to_expiry,
                    0,
                    0,
                    flag.lower()
                )

                total_vol += weight * vol
                total_weight += weight

        exchange_vol_estimate = total_vol / total_weight
        return exchange_vol_estimate


    def compute_vol_estimate(self) -> float:
        """
        This function is used to provide an estimate of underlying's volatility. Because this is
        an example bot, we just use a placeholder value here. We recommend that you look into
        different ways of finding what the true volatility of the underlying is.
        """
        implied_vol = self.compute_exchange_implied_vol()
        if implied_vol == None:
            return None
        historical_vol = np.array(self.past_underlying_prices).std() * np.sqrt(252*200)
        
        weight_on_historical = self.current_day/152

        vol_estimate = weight_on_historical*historical_vol + (1-weight_on_historical) * implied_vol
        if len(self.past_underlying_prices)<100:
            return implied_vol
        return vol_estimate

    def compute_options_price(
        self,
        flag: str,
        underlying_px: float,
        strike_px: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """
        This function should compute the price of an option given the provided parameters. Some
        important questions you may want to think about are:
            - What are the units associated with each of these quantities?
            - What formula should you use to compute the price of the option?
            - Are there tricks you can use to do this more quickly?
        You may want to look into the py_vollib library, which is installed by default in your
        virtual environment.
        """
        return round(bsm.black_scholes_merton(flag.lower(), underlying_px, strike_px, time_to_expiry, 0, volatility, 0),1)
    
    def compute_delta(self):
        res = 0
        time_to_expiry = (26-self.current_day)/252
        vol = self.compute_vol_estimate()
        for strike in option_strikes:
            for flag in ["C", "P"]:
                delta = bsmga.delta(flag.lower(), self.underlying_price, strike, time_to_expiry, 0, vol, 0)
                res += delta * 100 *self.positions[f"UC{strike}{flag}"]
        return res + self.positions['UC']

    def compute_vega(self):
        res = 0
        time_to_expiry = (26-self.current_day)/252
        vol = self.compute_vol_estimate()
        for strike in option_strikes:
            for flag in ["C", "P"]:
                vega = bsmga.vega(flag.lower(), self.underlying_price, strike, time_to_expiry, 0, vol, 0)
                res += vega *self.positions[f"UC{strike}{flag}"]
        return res

    def compute_theta(self):
        res = 0
        time_to_expiry = (26-self.current_day)/252
        vol = self.compute_vol_estimate()
        for strike in option_strikes:
            for flag in ["C", "P"]:
                theta = bsmga.theta(flag.lower(), self.underlying_price, strike, time_to_expiry, 0, vol, 0)
                res += -theta *self.positions[f"UC{strike}{flag}"]
        return res

    async def update_options_quotes(self):
        """
        This function will update the quotes that the bot has currently put into the market.

        In this example bot, the bot won't bother pulling old quotes, and will instead just set new
        quotes at the new theoretical price every time a price update happens. We don't recommend
        that you do this in the actual competition
        """
        # What should this value actually be?
        time_to_expiry = (26-self.current_day)/252 
        vol = self.compute_vol_estimate()

        vega = self.compute_vega()
        theta = self.compute_theta()

        if theta <-15 or vega>25:
            for strike in option_strikes:
                for flag in ["C", "P"]:
                    asset_name = f"UC{strike}{flag}"
                    position = self.positions[asset_name]
                    theo = self.compute_options_price(
                        flag, self.underlying_price, strike, time_to_expiry, vol
                    )
                    theo -= position//10
                    bid_response = await self.cancel_order(
                        asset_name+'bid'
                    )

                    ask_response = await self.modify_order(
                        asset_name+'ask',
                        asset_name,
                        pb.OrderSpecType.LIMIT,
                        pb.OrderSpecSide.ASK,
                        1,
                        theo + 0.30,
                    )
                    assert ask_response.ok

        elif vega <-25:
            for strike in option_strikes:
                for flag in ["C", "P"]:
                    asset_name = f"UC{strike}{flag}"
                    position = self.positions[asset_name]
                    theo = self.compute_options_price(
                        flag, self.underlying_price, strike, time_to_expiry, vol
                    )

                    theo -= position//10

                    bid_response = await self.modify_order(
                        asset_name+'bid',
                        asset_name,
                        pb.OrderSpecType.LIMIT,
                        pb.OrderSpecSide.BID,
                        1,  # How should this quantity be chosen?
                        theo - 0.30,  # How should this price be chosen?
                    )
                    assert bid_response.ok

                    ask_response = await self.cancel_order(
                        asset_name+'ask',
                    )
    
        else:    
            for strike in option_strikes:
                for flag in ["C", "P"]:
                    asset_name = f"UC{strike}{flag}"
                    position = self.positions[asset_name]
                    theo = self.compute_options_price(
                        flag, self.underlying_price, strike, time_to_expiry, vol
                    )

                    theo -= position//10

                    bid_response = await self.modify_order(
                        asset_name+'bid',
                        asset_name,
                        pb.OrderSpecType.LIMIT,
                        pb.OrderSpecSide.BID,
                        1,  # How should this quantity be chosen?
                        theo - 0.20,  # How should this price be chosen?
                    )
                    assert bid_response.ok

                    ask_response = await self.modify_order(
                        asset_name+'ask',
                        asset_name,
                        pb.OrderSpecType.LIMIT,
                        pb.OrderSpecSide.ASK,
                        1,
                        theo + 0.30,
                    )
                    assert ask_response.ok
        
        #delta hedging
        delta = round(self.compute_delta())
        if delta >0:
            sell_underlying = await self.modify_order(
                    'UC_sell',
                    'UC',
                    pb.OrderSpecType.MARKET,
                    pb.OrderSpecSide.ASK,
                    delta,
            )
            assert sell_underlying.ok
        elif delta <0:
            buy_underlying = await self.modify_order(
                    'UC_buy',
                    'UC',
                    pb.OrderSpecType.MARKET,
                    pb.OrderSpecSide.BID,
                    -delta,
            )
            assert buy_underlying.ok
        else:
            pass


    async def handle_exchange_update(self, update: pb.FeedMessage):
        kind, _ = betterproto.which_one_of(update, "msg")

        if kind == "pnl_msg":
            # When you hear from the exchange about your PnL, print it out
            print("My PnL:", update.pnl_msg.m2m_pnl)

        elif kind == "fill_msg":
            # When you hear about a fill you had, update your positions
            fill_msg = update.fill_msg

            if fill_msg.order_side == pb.FillMessageSide.BUY:
                self.positions[fill_msg.asset] += update.fill_msg.filled_qty
            else:
                self.positions[fill_msg.asset] -= update.fill_msg.filled_qty

        elif kind == "market_snapshot_msg":
            # When we receive a snapshot of what's going on in the market, update our information
            # about the underlying price.
            book = update.market_snapshot_msg.books["UC"]

            #store the previous underlying price into past prices
            self.past_underlying_prices.append(self.underlying_price)

            # Compute the mid price of the market and store it
            self.underlying_price = (
                float(book.bids[0].px) + float(book.asks[0].px)
            ) / 2

            # store the current prices of the 10 options
            for strike in option_strikes:
                for flag in ["C", "P"]:
                    asset_name = f"UC{strike}{flag}"
                    book = update.market_snapshot_msg.books[asset_name]
                    self.options_prices[asset_name] = (float(book.bids[0].px) + float(book.asks[0].px)) / 2

            await self.update_options_quotes()

        elif (
            kind == "generic_msg"
            and update.generic_msg.event_type == pb.GenericMessageType.MESSAGE
        ):
            # The platform will regularly send out what day it currently is (starting from day 0 at
            # the start of the case)
            self.current_day = float(update.generic_msg.message)

        elif kind == "order_cancelled_msg":  # NEW IN VERSION 1.0.4
            # An order that you placed was cancelled. Please refer to the documentation for details
            # on what this message means. You should use this block to update which orders you have
            # marked as currently active
            oc_msg = update.order_cancelled_msg

        elif kind == "trade_msg":
            # There are other pieces of information the exchange provides feeds for. See if you can
            # find ways to use them to your advantage (especially when more than one competitor is
            # in the market)
            pass


if __name__ == "__main__":
    start_bot(Case2_Bot)