import logging
import random as _random
import math
import warnings
from typing import Union, Optional
from .warnings import OptionalNumpyWarning

# Initialize a logger for this module
logger = logging.getLogger(__name__)

class SamplingError(Exception):
    """Custom exception raised when sampling fails after maximum retries.

    Attributes:
        distribution (str): The distribution from which sampling was attempted.
        retries (int): The number of retries attempted before failure.
        lower_bound (Optional[float]): The lower bound for the sampled value.
        upper_bound (Optional[float]): The upper bound for the sampled value.
    """
    def __init__(self, message, distribution, retries, lower_bound, upper_bound):
        """
        Initialize the SamplingError with a message, distribution, retries, and bounds.

        :param message: The error message.
        :param distribution: The distribution from which sampling was attempted.
        :param retries: The number of retries attempted before failure.
        :param lower_bound: The lower bound for the sampled value.
        :param upper_bound: The upper bound for the sampled value.
        """
        super().__init__(message)
        self.distribution = distribution
        self.retries = retries
        self.lower_bound = lower_bound if lower_bound != -math.inf else None
        self.upper_bound = upper_bound if upper_bound != math.inf else None

    def __str__(self):
        """Return a user-friendly string representation of the error."""
        bounds_info = f"Lower bound: {self.lower_bound}, Upper bound: {self.upper_bound}"
        return (f"{self.args[0]} (Distribution: {self.distribution}, "
                f"Retries: {self.retries}, {bounds_info})")

    def __repr__(self):
        """Return a detailed string representation of the error for debugging."""
        bounds_info = f"lower_bound={self.lower_bound!r}, upper_bound={self.upper_bound!r}"
        return (f"SamplingError(message={self.args[0]!r}, distribution={self.distribution!r}, "
                f"retries={self.retries!r}, {bounds_info})")


# Try to import NumPy
try:
    import numpy as np
    USE_NUMPY = True
except ImportError:
    warning_message = (
        "NumPy module wasn't found. Falling back to standard Python. "
        "Using NumPy may lead to a performance boost. "
        "You can install it by running 'python -m pip install alex-ber-utils[numpy]'."
    )
    warnings.warn(warning_message, OptionalNumpyWarning)
    USE_NUMPY = False

class BaseSampler:
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
        shape (Union[float, np.float32, np.float64]): Shape parameter for the distribution, controlling the spread and skewness.
                       For log-normal, it represents sigma of the underlying normal distribution.
        scale (Union[float, np.float32, np.float64]): Scale parameter for the distribution, shifting the distribution and determining its median.
                       For log-normal, it represents exp(mu) of the underlying normal distribution.
                       For exponential, it is used directly as the mean of the distribution.
        lower_bound (Optional[Union[float, np.float32, np.float64]]): Lower bound for the sampled value. Default is None (interpreted as unbounded).
        upper_bound (Optional[Union[float, np.float32, np.float64]]): Upper bound for the sampled value. Default is None (interpreted as unbounded).
        max_retries (int): Maximum number of attempts to sample a valid value. Default is 1000.
    """

    # Class-level attribute for supported distributions
    supported_distributions = {
        'lognormvariate', 'normalvariate', 'expovariate', 'vonmisesvariate',
        'gammavariate', 'gauss', 'betavariate', 'paretovariate', 'weibullvariate'
    }

    def __init__(self, **kwargs):
        """
        Initialize the BaseSampler with required and optional parameters.

        :param kwargs: Keyword arguments for initialization.
        """
        logger.info("__init__()")

        self.distribution = kwargs.get('distribution', None)
        self.shape = kwargs.get('shape', None)
        self.scale = kwargs.get('scale', None)
        self.lower_bound = kwargs.get('lower_bound', -math.inf)
        self.upper_bound = kwargs.get('upper_bound', math.inf)
        self.max_retries = kwargs.get('max_retries', 1000)

        self.validate_distribution()
        self.validate_bounds()

    def validate_distribution(self):
        """
        Validate that the specified distribution is supported.
        """
        if self.distribution not in self.supported_distributions:
            raise ValueError(f"Unsupported distribution: {self.distribution}")

    def validate_bounds(self):
        """
        Validate that the lower bound is less than the upper bound.
        """
        if not (self.lower_bound < self.upper_bound):
            raise ValueError("lower_bound must be less than upper_bound")

    def validate_random_parameters(self, seed, instance):
        """
        Validate that only one of random_seed or random_state/random_instance is provided.

        :param seed: The random seed.
        :param instance: The random state or instance.
        """
        if seed is not None and instance is not None:
            raise ValueError("Specify only one of random_seed or random_state/random_instance")

    def get_sample(self) -> Union[float, 'np.float32', 'np.float64']:
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

        def __init__(self, **kwargs):
            """
            Initialize the Sampler with NumPy-specific parameters.

            :param kwargs: Keyword arguments for initialization.
            """
            random_seed = kwargs.pop('random_seed', None)
            random_state = kwargs.pop('random_state', None)
            self.validate_random_parameters(random_seed, random_state)

            super().__init__(**kwargs)

            if random_state is not None:
                self.random_state = random_state
            else:
                self.random_state = np.random.RandomState(random_seed)

        def get_sample(self) -> Union[float, 'np.float32', 'np.float64']:
            """
            Get a sample from the specified distribution using NumPy.

            :return: A sample from the specified distribution within the specified bounds.
            """
            logger.info("get_sample()")

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

            for _ in range(self.max_retries):
                sampled_value = distribution_methods[self.distribution]()
                if self.lower_bound <= sampled_value <= self.upper_bound:
                    return sampled_value
            raise SamplingError(
                "Failed to sample a valid value within the specified bounds after max retries.",
                self.distribution,
                self.max_retries,
                self.lower_bound,
                self.upper_bound
            )
else:
    class Sampler(BaseSampler):
        """
        A class to sample from various statistical distributions using the standard random module.

        Note: The expovariate method has been adjusted to align with NumPy's exponential function,
        using the scale directly as the mean of the distribution.
        """

        def __init__(self, **kwargs):
            """
            Initialize the Sampler with standard random module-specific parameters.

            :param kwargs: Keyword arguments for initialization.
            """
            random_seed = kwargs.pop('random_seed', None)
            random_instance = kwargs.pop('random_instance', None)
            self.validate_random_parameters(random_seed, random_instance)

            super().__init__(**kwargs)

            if random_instance is not None:
                self.random_instance = random_instance
            else:
                self.random_instance = _random.Random(random_seed)

        def get_sample(self) -> Union[float, 'np.float32', 'np.float64']:
            """
            Get a sample from the specified distribution using the standard random module.

            :return: A sample from the specified distribution within the specified bounds.
            """
            logger.info("get_sample()")

            distribution_methods = {
                'lognormvariate': lambda: self.random_instance.lognormvariate(math.log(self.scale), self.shape),
                'normalvariate': lambda: self.random_instance.normalvariate(self.scale, self.shape),
                'expovariate': lambda: self.random_instance.expovariate(self.scale),
                'vonmisesvariate': lambda: self.random_instance.vonmisesvariate(self.scale, self.shape),
                'gammavariate': lambda: self.random_instance.gammavariate(self.shape, self.scale),
                'gauss': lambda: self.random_instance.gauss(self.scale, self.shape),
                'betavariate': lambda: self.random_instance.betavariate(self.shape, self.scale),
                'paretovariate': lambda: self.random_instance.paretovariate(self.shape),
                'weibullvariate': lambda: self.random_instance.weibullvariate(self.shape, self.scale)
            }

            for _ in range(self.max_retries):
                sampled_value = distribution_methods[self.distribution]()
                if self.lower_bound <= sampled_value <= self.upper_bound:
                    return sampled_value
            raise SamplingError(
                "Failed to sample a valid value within the specified bounds after max retries.",
                self.distribution,
                self.max_retries,
                self.lower_bound,
                self.upper_bound
            )