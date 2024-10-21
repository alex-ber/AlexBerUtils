import logging
import random as _random
import math
from .thread_locals import validate_param

# Initialize a logger for this module
logger = logging.getLogger(__name__)


class Sampler:
    """
    A class to sample from various statistical distributions with configurable parameters.

    Supported Distributions:
        - 'lognormvariate': Log-normal distribution.
        - 'normalvariate': Normal distribution.
        - 'expovariate': Exponential distribution.
        - 'vonmisesvariate': Von Mises distribution.
        - 'gammavariate': Gamma distribution.
        - 'gauss': Gaussian distribution.
        - 'betavariate': Beta distribution.
        - 'paretovariate': Pareto distribution.
        - 'weibullvariate': Weibull distribution.

    Attributes:
        distribution (str): The distribution to sample from.
        shape (float): Shape parameter for the distribution, controlling the spread and skewness.
                       For log-normal, it represents sigma of the underlying normal distribution.
        scale (float): Scale parameter for the distribution, shifting the distribution and determining its median.
                       For log-normal, it represents exp(mu) of the underlying normal distribution.
                       For exponential, it is the inverse of the rate parameter (1/lambda).
        lower_bound (float): Lower bound for the sampled value. Default is None (interpreted as -Inf).
        upper_bound (float): Upper bound for the sampled value. Default is None (interpreted as +Inf).
        random_instance (random.Random): Random instance for generating random numbers.
    """

    def __init__(self, distribution: str, shape: float, scale: float,
                 lower_bound: float = None, upper_bound: float = None,
                 random_seed: int = None, random_instance: _random.Random = None):
        """
        Initialize the Sampler with required and optional parameters.

        :param distribution: The distribution to sample from.
        :param shape: Shape parameter for the distribution, controlling the spread and skewness.
                      For log-normal, it represents sigma of the underlying normal distribution.
        :param scale: Scale parameter for the distribution, shifting the distribution and determining its median.
                      For log-normal, it represents exp(mu) of the underlying normal distribution.
                      For exponential, it is the inverse of the rate parameter (1/lambda).
        :param lower_bound: Lower bound for the sampled value. Default is None (interpreted as -Inf).
        :param upper_bound: Upper bound for the sampled value. Default is None (interpreted as +Inf).
        :param random_seed: Seed for the random number generator. Default is None.
        :param random_instance: An instance of random.Random for generating random numbers. Default is None.
        """
        logger.info("__init__()")

        validate_param(distribution, "distribution")

        # Validate distribution
        supported_distributions = {
            'lognormvariate', 'normalvariate', 'expovariate', 'vonmisesvariate',
            'gammavariate', 'gauss', 'betavariate', 'paretovariate', 'weibullvariate'
        }

        if distribution not in supported_distributions:
            raise ValueError(f"Unsupported distribution: {distribution}")

        self.distribution = distribution

        self.shape = shape
        validate_param(self.shape, "shape")
        self.scale = scale
        validate_param(self.scale, "scale")

        # Interpret None bounds as -Inf and +Inf
        self.lower_bound = lower_bound if lower_bound is not None else -math.inf
        self.upper_bound = upper_bound if upper_bound is not None else math.inf

        # Use the provided random_instance or create a new one
        if random_instance is not None:
            self.random_instance = random_instance
        else:
            self.random_instance = _random.Random(random_seed) if random_seed is not None else _random.Random()

    def get_sample(self) -> float:
        """
        Get a sample from the specified distribution.

        :return: A sample from the specified distribution within the specified bounds.
        """
        logger.info("get_sample()")

        # Map distribution names to random instance methods
        distribution_methods = {
            'lognormvariate': lambda: self.random_instance.lognormvariate(math.log(self.scale), self.shape),
            'normalvariate': lambda: self.random_instance.normalvariate(self.scale, self.shape),
            'expovariate': lambda: self.random_instance.expovariate(1 / self.scale),
            'vonmisesvariate': lambda: self.random_instance.vonmisesvariate(self.scale, self.shape),
            'gammavariate': lambda: self.random_instance.gammavariate(self.shape, self.scale),
            'gauss': lambda: self.random_instance.gauss(self.scale, self.shape),
            'betavariate': lambda: self.random_instance.betavariate(self.shape, self.scale),
            'paretovariate': lambda: self.random_instance.paretovariate(self.shape),
            'weibullvariate': lambda: self.random_instance.weibullvariate(self.shape, self.scale)
        }

        while True:
            # Sample from the specified distribution
            sampled_value = distribution_methods[self.distribution]()
            # Check if the sampled value is within the desired range
            if self.lower_bound <= sampled_value <= self.upper_bound:
                return sampled_value