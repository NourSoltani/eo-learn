"""
Module containing integrations with Ray framework

In order to use this module you have to install `ray` Python package.

Credits:
Copyright (c) 2021-2022 Matej Aleksandrov, Žiga Lukšič (Sinergise)

This source code is licensed under the MIT license found in the LICENSE
file in the root directory of this source tree.
"""
from typing import Any, Callable, Generator, Iterable, List, Optional, Tuple, TypeVar, cast

try:
    import ray
except ImportError as exception:
    raise ImportError("This module requires an installation of Ray Python package") from exception
from tqdm.auto import tqdm

from ..eoexecution import EOExecutor, _ProcessingData
from ..eoworkflow import WorkflowResults
from ..utils.parallelize import _make_copy_and_empty_given, _ProcessingType

# pylint: disable=invalid-name
_InputType = TypeVar("_InputType")
_OutputType = TypeVar("_OutputType")


class RayExecutor(EOExecutor):
    """A special type of `EOExecutor` that works with Ray framework"""

    def run(self) -> List[WorkflowResults]:
        """Runs the executor using a Ray cluster

        Before calling this method make sure to initialize a Ray cluster using `ray.init`.

        :return: A list of EOWorkflow results
        """
        if not ray.is_initialized():
            raise RuntimeError("Please initialize a Ray cluster before calling this method")

        workers = ray.available_resources().get("CPU")
        return super().run(workers=workers, multiprocess=True)

    @classmethod
    def _run_execution(cls, processing_args: List[_ProcessingData], *_, **__) -> List[WorkflowResults]:
        """Runs ray execution"""
        futures = [_ray_workflow_executor.remote(workflow_args) for workflow_args in processing_args]
        return join_ray_futures(futures)

    @staticmethod
    def _get_processing_type(*_, **__) -> _ProcessingType:
        """Provides a type of processing for later references."""
        return _ProcessingType.RAY


@ray.remote
def _ray_workflow_executor(workflow_args: _ProcessingData) -> WorkflowResults:
    """Called to execute a workflow on a ray worker"""
    # pylint: disable=protected-access
    return RayExecutor._execute_workflow(workflow_args)


def parallelize_with_ray(
    function: Callable[[_InputType], _OutputType], *params: Iterable[_InputType], **tqdm_kwargs: Any
) -> List[_OutputType]:
    """Parallelizes function execution with Ray.

    Note that this function will automatically connect to a Ray cluster, if a connection wouldn't exist yet. But it
    won't automatically shut down the connection.

    :param function: A normal function that is not yet decorated by `ray.remote`.
    :param params: Iterables of parameters that will be used with given function.
    :param tqdm_kwargs: Keyword arguments that will be propagated to `tqdm` progress bar.
    :return: A list of results in the order that corresponds with the order of the given input `params`.
    """
    ray.init(address="auto", ignore_reinit_error=True)

    ray_function = ray.remote(function)
    futures = [ray_function.remote(*function_params) for function_params in zip(*params)]
    return join_ray_futures(futures, **tqdm_kwargs)


def join_ray_futures(futures: List[ray.ObjectRef], **tqdm_kwargs: Any) -> List[Any]:
    """Resolves futures, monitors progress, and returns a list of results.

    :param futures: A list of futures to be joined. Note that this list will be reduced into an empty list as a side
        effect of this function. This way Ray future objects will get cleared from memory already during the execution
        and this will free memory from Ray Plasma store. But this can be achieved only if future objects aren't kept in
        memory outside `futures` list.
    :param tqdm_kwargs: Keyword arguments that will be propagated to `tqdm` progress bar.
    :return: A list of results in the order that corresponds with the order of the given input `futures`.
    """
    results: List[Optional[Any]] = [None] * len(futures)
    for position, result in join_ray_futures_iter(futures, **tqdm_kwargs):
        results[position] = result

    return cast(List[Any], results)


def join_ray_futures_iter(
    futures: List[ray.ObjectRef], update_interval: float = 0.5, **tqdm_kwargs: Any
) -> Generator[Tuple[int, Any], None, None]:
    """Resolves futures, monitors progress, and serves as an iterator over results.

    :param futures: A list of futures to be joined. Note that this list will be reduced into an empty list as a side
        effect of this function. This way Ray future objects will get cleared from memory already during the execution
        and this will free memory from Ray Plasma store. But this can be achieved only if future objects aren't kept in
        memory outside `futures` list.
    :param update_interval: A number of seconds to wait between consecutive updates of a progress bar.
    :param tqdm_kwargs: Keyword arguments that will be propagated to `tqdm` progress bar.
    :return: A generator that will be returning pairs `(index, result)` where `index` will define the position of future
        in the original list to which `result` belongs to.
    """
    if not isinstance(futures, list):
        raise ValueError(f"Parameters 'futures' should be a list but {type(futures)} was given")
    futures = _make_copy_and_empty_given(futures)

    id_to_position_map = {id(future): index for index, future in enumerate(futures)}

    with tqdm(total=len(futures), **tqdm_kwargs) as pbar:
        while futures:
            done, futures = ray.wait(futures, num_returns=len(futures), timeout=float(update_interval))
            for future, result in zip(done, ray.get(done)):
                pbar.update(1)
                yield id_to_position_map[id(future)], result
