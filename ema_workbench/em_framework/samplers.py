"""

This module contains various classes that can be used for specifying different
types of samplers. These different samplers implement basic sampling
techniques including Full Factorial sampling, Latin Hypercube sampling, and
Monte Carlo sampling.

"""
import abc
import itertools
import operator

import numpy as np
import scipy.stats as stats

from ema_workbench.em_framework import util
from ema_workbench.em_framework.points import Policy, Scenario, Point
from ema_workbench.em_framework.parameters import (
    IntegerParameter,
    BooleanParameter,
    CategoricalParameter,
)
from ema_workbench.util.ema_exceptions import EMAError

# Created on 16 aug. 2011
#
# .. codeauthor:: jhkwakkel <j.h.kwakkel (at) tudelft (dot) nl>

__all__ = [
    "AbstractSampler",
    "LHSSampler",
    "MonteCarloSampler",
    "FullFactorialSampler",
    "UniformLHSSampler",
    "sample_parameters",
    "sample_levers",
    "sample_uncertainties",
    "determine_parameters",
    "DefaultDesigns",
]


class AbstractSampler(metaclass=abc.ABCMeta):
    """
    Abstract base class from which different samplers can be derived.

    In the simplest cases, only the sample method needs to be overwritten.
    generate_designs` is the only method called from outside. The
    other methods are used internally to generate the designs.

    """

    def sample(self, distribution, size):
        """
        method for sampling a number of samples from a particular distribution.
        The various samplers differ with respect to their implementation of
        this method.

        Parameters
        ----------
        distribution : scipy frozen distribution
        size : int
               the number of samples to generate

        Returns
        -------
        numpy array
            the samples for the distribution and specified parameters

        """

    def generate_samples(self, parameters, size):
        """
        The main method of :class: `~sampler.Sampler` and its
        children. This will call the sample method for each of the
        parameters and return the resulting designs.

        Parameters
        ----------
        parameters : collection
                     a collection of :class:`~parameters.RealParameter`,
                     :class:`~parameters.IntegerParameter`,
                     and :class:`~parameters.CategoricalParameter`
                     instances.
        size : int
               the number of samples to generate.


        Returns
        -------
        dict
            dict with the parameter.name as key, and the sample as value

        """
        return {param.name: self.sample(param.dist, size) for param in parameters}

    def generate_designs(self, parameters, nr_samples):
        """external interface for Sampler. Returns the computational experiments
        over the specified parameters, for the given number of samples for each
        parameter.

        Parameters
        ----------
        parameters : list
                        a list of parameters for which to generate the
                        experimental designs
        nr_samples : int
                     the number of samples to draw for each parameter


        Returns
        -------
        generator
            a generator object that yields the designs resulting from
            combining the parameters
        int
            the number of experimental designs

        """
        parameters = sorted(parameters, key=operator.attrgetter("name"))
        sampled_parameters = self.generate_samples(parameters, nr_samples)
        designs = zip(*[sampled_parameters[u.name] for u in parameters])
        designs = DefaultDesigns(designs, parameters, nr_samples)

        return designs


class LHSSampler(AbstractSampler):
    """
    generates a Latin Hypercube sample for each of the parameters
    """

    def sample(self, distribution, size):
        """
        generate a Latin Hypercube Sample.

        Parameters
        ----------
        distribution : scipy frozen distribution
        size : int
               the number of samples to generate

        Returns
        -------
        dict
            with the paramertainty.name as key, and the sample as value

        """

        perc = np.arange(0, 1.0, 1.0 / size)
        np.random.shuffle(perc)
        smp = stats.uniform(perc, 1.0 / size).rvs()
        samples = distribution.ppf(smp)

        # TODO::
        # corner case fix (try siz=49)
        # is not a proper fix, it means that perc is wrong
        # so your intervals are wrong
        samples = samples[np.isnan(samples) == False]

        return samples


class UniformLHSSampler(LHSSampler):
    def generate_samples(self, parameters, size):
        """

        Parameters
        ----------
        parameters : collection
        size : int

        Returns
        -------
        dict
            dict with the parameter.name as key, and the sample as value

        """

        samples = {}
        for param in parameters:
            lower_bound = param.lower_bound
            upper_bound = param.upper_bound

            if isinstance(param.dist, stats.rv_continuous):
                dist = stats.uniform(lower_bound, upper_bound - lower_bound)
            else:
                dist = stats.randint(lower_bound, upper_bound + 1)
            samples[param.name] = self.sample(dist, size)
        return samples




class MonteCarloSampler(AbstractSampler):
    """
    generates a Monte Carlo sample for each of the parameters.

    """

    def sample(self, distribution, size):
        """
        generate a Monte Carlo Sample.

        Parameters
        ----------
        distribution : scipy frozen distribution
        size : int
               the number of samples to generate

        Returns
        -------
        dict
            with the paramertainty.name as key, and the sample as value

        """

        return distribution.rvs(size)


class FullFactorialSampler(AbstractSampler):
    """
    generates a full factorial sample.

    If the parameter is non categorical, the resolution is set the
    number of samples. If the parameter is categorical, the specified value
    for samples will be ignored and each category will be used instead.

    """

    def generate_samples(self, parameters, size):
        """
        The main method of :class: `~sampler.Sampler` and its
        children. This will call the sample method for each of the
        parameters and return the resulting samples

        Parameters
        ----------
        parameters : collection
                        a collection of :class:`~parameters.Parameter`
                        instances
        size : int
                the number of samples to generate.

        Returns
        -------
        dict
            with the paramertainty.name as key, and the sample as value
        """
        samples = {}
        for param in parameters:
            cats = param.resolution
            if not cats:
                cats = np.linspace(param.lower_bound, param.upper_bound, size)
                if isinstance(param, IntegerParameter):
                    cats = np.round(cats, 0)
                    cats = set(cats)
                    cats = (int(entry) for entry in cats)
                    cats = sorted(cats)
            samples[param.name] = cats

        return samples

    def generate_designs(self, parameters, nr_samples):
        """
        This method provides an alternative implementation to the default
        implementation provided by :class:`~sampler.Sampler`. This
        version returns a full factorial design across the parameters.

        Parameters
        ----------
        parameters : list
                        a list of parameters for which to generate the
                        experimental designs
        nr_samples : int
                     the number of intervals to use on each
                     Parameter. Categorical parameters always
                     return all their categories

        Returns
        -------
        generator
            a generator object that yields the designs resulting from
            combining the parameters
        int
            the number of experimental designs

        """
        parameters = sorted(parameters, key=operator.attrgetter("name"))

        samples = self.generate_samples(parameters, nr_samples)
        zipped_samples = itertools.product(*[samples[u.name] for u in parameters])

        n_designs = self.determine_nr_of_designs(samples)
        designs = DefaultDesigns(zipped_samples, parameters, n_designs)

        return designs

    def determine_nr_of_designs(self, sampled_parameters):
        """
        Helper function for determining the number of experiments that will
        be generated given the sampled parameters.

        Parameters
        ----------
        sampled_parameters : list
                        a list of sampled parameters, as
                        the values return by generate_samples

        Returns
        -------
        int
            the total number of experimental design
        """
        nr_designs = 1
        for value in sampled_parameters.values():
            nr_designs *= len(value)
        return nr_designs




def determine_parameters(models, attribute, union=True):
    """determine the parameters over which to sample

    Parameters
    ----------
    models : a collection of AbstractModel instances
    attribute : {'uncertainties', 'levers'}
    union : bool, optional
            in case of multiple models, sample over the union of
            levers, or over the intersection of the levers

    Returns
    -------
    collection of Parameter instances

    """
    return util.determine_objects(models, attribute, union=union)


def sample_parameters(parameters, n_samples, sampler=LHSSampler(), kind=Point):
    """generate cases by sampling over the parameters

    Parameters
    ----------
    parameters : collection of AbstractParameter instances
    n_samples : int
    sampler : Sampler instance, optional
    kind : {Case, Scenario, Policy}, optional
            the class into which the samples are collected

    Returns
    -------
    generator yielding Case, Scenario, or Policy instances

    """

    samples = sampler.generate_designs(parameters, n_samples)
    samples.kind = kind

    return samples


def sample_levers(models, n_samples, union=True, sampler=LHSSampler()):
    """generate policies by sampling over the levers

    Parameters
    ----------
    models : a collection of AbstractModel instances
    n_samples : int
    union : bool, optional
            in case of multiple models, sample over the union of
            levers, or over the intersection of the levers
    sampler : Sampler instance, optional

    Returns
    -------
    generator yielding Policy instances

    """
    levers = determine_parameters(models, "levers", union=union)

    if not levers:
        raise EMAError("You are trying to sample policies, but no levers have been defined")

    return sample_parameters(levers, n_samples, sampler, Policy)


def sample_uncertainties(models, n_samples, union=True, sampler=LHSSampler()):
    """generate scenarios by sampling over the uncertainties

    Parameters
    ----------
    models : a collection of AbstractModel instances
    n_samples : int
    union : bool, optional
            in case of multiple models, sample over the union of
            uncertainties, or over the intersection of the uncertainties
    sampler : Sampler instance, optional

    Returns
    -------
    generator yielding Scenario instances

    """
    uncertainties = determine_parameters(models, "uncertainties", union=union)

    if not uncertainties:
        raise EMAError("You are trying to sample scenarios, but no uncertainties have been defined")

    return sample_parameters(uncertainties, n_samples, sampler, Policy)




def from_experiments(models, experiments):
    """generate scenarios from an existing experiments DataFrame

    Parameters
    ----------
    models : collection of AbstractModel instances
    experiments : DataFrame

    Returns
    -------
     generator
        yielding Scenario instances

    """
    policy_names = np.unique(experiments["policy"])
    model_names = np.unique(experiments["model"])

    # we sample ff over models and policies so we need to ensure
    # we only get the experiments for a single model policy combination
    logical = (experiments["model"] == model_names[0]) & (experiments["policy"] == policy_names[0])

    experiments = experiments[logical]

    uncertainties = util.determine_objects(models, "uncertainties", union=True)
    samples = {unc.name: experiments[:, unc.name] for unc in uncertainties}

    scenarios = DefaultDesigns(samples, uncertainties, experiments.shape[0])
    scenarios.kind = Scenario

    return scenarios


class DefaultDesigns:
    """iterable for the experimental designs"""

    def __init__(self, designs, parameters, n):
        self.designs = list(designs)
        self.parameters = parameters
        self.params = [p.name for p in parameters]
        self.kind = None
        self.n = n

    @abc.abstractmethod
    def __iter__(self):
        """should return iterator"""

        return design_generator(self.designs, self.parameters, self.kind)

    def __str__(self):
        return f"ema_workbench.DefaultDesigns, {self.n} designs on {len(self.params)} parameters"






def design_generator(designs, params, kind):
    """generator that combines the sampled parameters with their correct
    name in order to return dicts.

    Parameters
    ----------
    designs : iterable of tuples
    params : iterable of str
    kind : cls

    Yields
    ------
    dict
        experimental design dictionary

    """

    for design in designs:
        design_dict = {}
        for param, value in zip(params, design):
            if isinstance(param, IntegerParameter):
                value = int(value)
            if isinstance(param, BooleanParameter):
                value = bool(value)
            if isinstance(param, CategoricalParameter):
                # categorical parameter is an integer parameter, so
                # conversion to int is already done
                value = param.cat_for_index(value).value

            design_dict[param.name] = value

        yield kind(**design_dict)
