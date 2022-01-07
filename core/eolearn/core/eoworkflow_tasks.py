"""
Module implementing tasks that have a special effect in `EOWorkflow`
"""
from typing import Optional
from .eotask import EOTask
from .eodata import EOPatch
from .utilities import generate_uid


class InputTask(EOTask):
    """ Introduces data into an EOWorkflow, where the data can be specified at initialization or at execution
    """
    def __init__(self, value: Optional[object] = None):
        """
        :param value: Default value that the task should provide as a result. Can be overridden in execution arguments
        """
        self.value = value

    def execute(self, *, value: Optional[object] = None) -> object:
        """
        :param value: A value that the task should provide as it's result. If not set uses the value from initialization
        :return: Directly returns `value`
        """
        return value or self.value


class OutputTask(EOTask):
    """ Stores data as an output of `EOWorkflow` results
    """
    def __init__(self, name: Optional[str] = None, features=...):
        """
        :param name: A name under which the data will be saved in `WorkflowResults`, auto-generated if `None`
        :param features: A collection of features to be kept if the data is an `EOPatch`
        :type features: an object supported by the :class:`FeatureParser<eolearn.core.utilities.FeatureParser>`
        """
        self._name = name or generate_uid('output')
        self.features = features

    @property
    def name(self) -> str:
        """ Provides a name under which data will be saved in `WorkflowResults`

        :return: A name
        """
        return self._name

    def execute(self, data: object) -> object:
        """
        :param data: input data
        :return: Same data, to be stored in results (for `EOPatch` returns shallow copy containing only `features`)
        """
        if isinstance(data, EOPatch):
            return data.copy(features=self.features)
        return data
