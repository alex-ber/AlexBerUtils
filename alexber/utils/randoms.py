import logging
import random as _random
import math
from .thread_locals import validate_param

# Initialize a logger for this module
logger = logging.getLogger(__name__)

class LogNormSampler:
    """
    A class to sample from a log-normal distribution with configurable parameters.

    Attributes:
        shape (float): Shape parameter (sigma of the underlying normal distribution).
        scale (float): Scale parameter (exp(mu) of the underlying normal distribution).
        lower_bound (float): Lower bound for the sampled value.
        upper_bound (float): Upper bound for the sampled value.
        random_instance (random.Random): Random instance for generating random numbers.
    """

    def __init__(self, shape: float = None, scale: float = None,
                 lower_bound: float = None, upper_bound: float = None,
                 random_seed: int = None, random_instance: _random.Random = None):
        """
        Initialize the LogNormSampler with optional parameters.

        :param shape: Shape parameter (sigma of the underlying normal distribution).
        :param scale: Scale parameter (exp(mu) of the underlying normal distribution).
        :param lower_bound: Lower bound for the sampled value.
        :param upper_bound: Upper bound for the sampled value.
        :param random_seed: Seed for the random number generator.
        :param random_instance: An instance of random.Random for generating random numbers.
        """
        # Assign default values if parameters are None
        self.shape = shape if shape is not None else 0.5
        self.scale = scale if scale is not None else math.exp(0.001)
        self.lower_bound = lower_bound if lower_bound is not None else 0.001
        self.upper_bound = upper_bound if upper_bound is not None else 2.0

        # Use the provided random_instance or create a new one
        if random_instance is not None:
            self.random_instance = random_instance
        else:
            self.random_instance = _random.Random(random_seed) if random_seed is not None else _random.Random()

    def get_sample(self) -> float:
        """
        Get a sample from the log-normal distribution.

        :return: A sample from the log-normal distribution within the specified bounds.
        """
        logger.info("get_sample()")

        # Validate input parameters
        validate_param(self.shape, "shape")
        validate_param(self.scale, "scale")
        validate_param(self.lower_bound, "lower_bound")
        validate_param(self.upper_bound, "upper_bound")
        validate_param(self.random_instance, "random_instance")

        while True:
            # Sample from the log-normal distribution
            sampled_time = self.random_instance.lognormvariate(math.log(self.scale), self.shape)
            # Check if the sampled value is within the desired range
            if self.lower_bound <= sampled_time <= self.upper_bound:
                return sampled_time