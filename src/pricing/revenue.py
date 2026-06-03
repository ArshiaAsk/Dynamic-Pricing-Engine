import numpy as np


class RevenueCalculator:

    def compute(self, price, predicted_demand):

        revenue = price * predicted_demand

        return revenue
