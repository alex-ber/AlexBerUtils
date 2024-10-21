import logging
import random as _random
import math
from .thread_locals import validate_param, RootMixin

# Initialize a logger for this module
logger = logging.getLogger(__name__)

# Try to import NumPy
try:
    import numpy as np
    USE_NUMPY = True
except ImportError:
    USE_NUMPY = False

class BaseSampler(RootMixin):
    """
    Base class for sampling from various statistical distributions with configurable parameters.

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
                       For exponential, it is used directly as the mean of the distribution.
        lower_bound (float): Lower bound for the sampled value. Default is None (interpreted as -Inf).
        upper_bound (float): Upper bound for the sampled value. Default is None (interpreted as +Inf).
    """

    def __init__(self, distribution: str, shape: float, scale: float,
                 lower_bound: float = None, upper_bound: float = None):
        """
        Initialize the BaseSampler with required and optional parameters.

        :param distribution: The distribution to sample from.
        :param shape: Shape parameter for the distribution.
        :param scale: Scale parameter for the distribution.
        :param lower_bound: Lower bound for the sampled value. Default is None (interpreted as unbounded).
        :param upper_bound: Upper bound for the sampled value. Default is None (interpreted as unbounded).
        """
        logger.info("__init__()")
        super().__init__(distribution, shape, scale, lower_bound, upper_bound)

        validate_param(distribution, "distribution")

        # Validate distribution
        self.supported_distributions = {
            'lognormvariate', 'normalvariate', 'expovariate', 'vonmisesvariate',
            'gammavariate', 'gauss', 'betavariate', 'paretovariate', 'weibullvariate'
        }

        if distribution not in self.supported_distributions:
            raise ValueError(f"Unsupported distribution: {distribution}")

        self.distribution = distribution
        self.shape = shape
        validate_param(self.shape, "shape")
        self.scale = scale
        validate_param(self.scale, "scale")

        # Interpret None bounds as -Inf and +Inf
        self.lower_bound = lower_bound if lower_bound is not None else -math.inf
        self.upper_bound = upper_bound if upper_bound is not None else math.inf

    def get_sample(self) -> float:
        """
        Get a sample from the specified distribution.

        :return: A sample from the specified distribution within the specified bounds.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

if USE_NUMPY:
    class Sampler(BaseSampler):
        """
        A class to sample from various statistical distributions using NumPy.
        """

        def __init__(self, distribution: str, shape: float, scale: float,
                     lower_bound: float = None, upper_bound: float = None,
                     random_seed: int = None, random_state: np.random.RandomState = None):
            super().__init__(distribution, shape, scale, lower_bound, upper_bound)

            # Use the provided random_state or create a new one
            if random_state is not None:
                self.random_state = random_state
            else:
                self.random_state = np.random.RandomState(random_seed)

        def get_sample(self) -> float:
            logger.info("get_sample()")

            # Map distribution names to numpy random methods
            distribution_methods = {
                'lognormvariate': lambda: self.random_state.lognormal(math.log(self.scale), self.shape),
                'normalvariate': lambda: self.random_state.normal(self.scale, self.shape),
                'expovariate': lambda: self.random_state.exponential(self.scale),
                'vonmisesvariate': lambda: self.random_state.vonmises(self.scale, self.shape),
                'gammavariate': lambda: self.random_state.gamma(self.shape, self.scale),
                'gauss': lambda: self.random_state.normal(self.scale, self.shape),
                'betavariate': lambda: self.random_state.beta(self.shape, self.scale),
                'paretovariate': lambda: self.random_state.pareto(self.shape),
                'weibullvariate': lambda: self.random_state.weibull(self.shape) * self.scale
            }

            while True:
                sampled_value = distribution_methods[self.distribution]()
                if self.lower_bound <= sampled_value <= self.upper_bound:
                    return sampled_value
else:
    class Sampler(BaseSampler):
        """
        A class to sample from various statistical distributions using the standard random module.

        Note: The expovariate method has been adjusted to align with NumPy's exponential function,
        using the scale directly as the mean of the distribution.
        """

        def __init__(self, distribution: str, shape: float, scale: float,
                     lower_bound: float = None, upper_bound: float = None,
                     random_seed: int = None, random_instance: _random.Random = None):
            super().__init__(distribution, shape, scale, lower_bound, upper_bound)

            # Use the provided random_instance or create a new one
            if random_instance is not None:
                self.random_instance = random_instance
            else:
                self.random_instance = _random.Random(random_seed)

        def get_sample(self) -> float:
            logger.info("get_sample()")

            # Map distribution names to random instance methods
            distribution_methods = {
                'lognormvariate': lambda: self.random_instance.lognormvariate(math.log(self.scale), self.shape),
                'normalvariate': lambda: self.random_instance.normalvariate(self.scale, self.shape),
                'expovariate': lambda: self.random_instance.expovariate(self.scale),  # Adjusted to use scale as mean
                'vonmisesvariate': lambda: self.random_instance.vonmisesvariate(self.scale, self.shape),
                'gammavariate': lambda: self.random_instance.gammavariate(self.shape, self.scale),
                'gauss': lambda: self.random_instance.gauss(self.scale, self.shape),
                'betavariate': lambda: self.random_instance.betavariate(self.shape, self.scale),
                'paretovariate': lambda: self.random_instance.paretovariate(self.shape),
                'weibullvariate': lambda: self.random_instance.weibullvariate(self.shape, self.scale)
            }

            while True:
                sampled_value = distribution_methods[self.distribution]()
                if self.lower_bound <= sampled_value <= self.upper_bound:
                    return sampled_value