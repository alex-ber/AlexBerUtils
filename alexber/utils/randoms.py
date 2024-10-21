import logging
import random as _random
import math
from .thread_locals import validate_param

logger = logging.getLogger(__name__)

SHAPE = None
SCALE = None
LOWER_BOUND = None
UPPER_BOUND = None
RANDOM_INSTANCE = None

def get_lognorm():
    logger.info(f"get_lognorm()")
    return calc_lognorm(SHAPE, SCALE, LOWER_BOUND, UPPER_BOUND, RANDOM_INSTANCE)

def calc_lognorm(shape, scale, lower_bound, upper_bound, random_instance):
    """
    Function to sample from log-normal distribution.

    :param shape:
    :param scale:
    :param lower_bound:
    :param upper_bound:
    :param random_instance:
    :return:
    """
    logger.info(f"calc_lognorm()")

    validate_param(shape, "shape")
    validate_param(scale, "scale")
    validate_param(lower_bound, "lower_bound")
    validate_param(upper_bound, "upper_bound")
    validate_param(random_instance, "random_instance")


    while True:
        # Sample a time from the log-normal distribution
        sampled_time = random_instance.lognormvariate(math.log(scale), shape)
        # Check if the sampled time is within the desired range
        if lower_bound <= sampled_time <= upper_bound:
            return sampled_time

def initConfig(**kwargs):
    scale = kwargs.get('scale', None)
    if scale is None:
        scale = math.exp(0.001)  # Scale parameter (exp(mu) of the underlying normal distribution),  shifts the distribution and determines its median. X-axis
    global SCALE
    SCALE = scale

    shape = kwargs.get('shape', None)
    if shape is None:
        shape = 0.5  # Shape parameter (sigma of the underlying normal distribution), controls the spread and skewness of the distribution. Y-axis
    global SHAPE
    SHAPE = shape

    lower_bound = kwargs.get('lower_bound', None)
    if lower_bound is None:
        lower_bound = 0.001
    global LOWER_BOUND
    LOWER_BOUND = lower_bound

    upper_bound = kwargs.get('upper_bound', None)
    if upper_bound is None:
        upper_bound = 2.0
    global UPPER_BOUND
    UPPER_BOUND = upper_bound

    random_instance = kwargs.get('random_instance', None)
    if random_instance is None:
        random_seed = kwargs.get('random_seed', None)
        if random_seed is None:
            random_instance = _random.Random()
        else:
            random_instance = _random.Random(random_seed)

    global RANDOM_INSTANCE
    RANDOM_INSTANCE = random_instance

