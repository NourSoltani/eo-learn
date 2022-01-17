"""
Module with utilities for vizualizing EOExecutor

Credits:
Copyright (c) 2017-2019 Matej Aleksandrov, Matej Batič, Andrej Burja, Eva Erzin (Sinergise)
Copyright (c) 2017-2019 Grega Milčinski, Matic Lubej, Devis Peresutti, Jernej Puc, Tomislav Slijepčević (Sinergise)
Copyright (c) 2017-2019 Blaž Sovdat, Nejc Vesel, Jovan Višnjić, Anže Zupanc, Lojze Žust (Sinergise)

This source code is licensed under the MIT license found in the LICENSE
file in the root directory of this source tree.
"""
import os
import importlib
import inspect
import warnings
import base64
import datetime as dt
from collections import defaultdict

try:
    import matplotlib.pyplot as plt
except ImportError:
    import matplotlib
    matplotlib.use('agg')
    import matplotlib.pyplot as plt

import graphviz
import pygments
import pygments.lexers
from pygments.formatters.html import HtmlFormatter
from jinja2 import Environment, FileSystemLoader

from eolearn.core import EOExecutor
from eolearn.core.exceptions import EOUserWarning


class EOExecutorVisualization:
    """ Class handling EOExecutor visualizations, particularly creating reports
    """

    def __init__(self, eoexecutor: EOExecutor):
        """
        :param eoexecutor: An instance of EOExecutor
        """
        self.eoexecutor = eoexecutor

    def make_report(self, include_logs: bool = True):
        """ Makes a html report and saves it into the same folder where logs are stored.
        """
        if self.eoexecutor.execution_results is None:
            raise RuntimeError('Cannot produce a report without running the executor first, check EOExecutor.run '
                               'method')

        if os.environ.get('DISPLAY', '') == '':
            plt.switch_backend('Agg')

        try:
            dependency_graph = self._create_dependency_graph()
        except graphviz.backend.ExecutableNotFound as ex:
            dependency_graph = None
            warnings.warn(
                f"{ex}.\nPlease install the system package 'graphviz' (in addition to the python package) to have "
                f"the dependency graph in the final report!",
                EOUserWarning
            )

        formatter = HtmlFormatter(linenos=True)

        template = self._get_template()

        execution_log_filenames = [os.path.basename(log_path) for log_path in self.eoexecutor.get_log_paths()]
        if self.eoexecutor.save_logs:
            execution_logs = self.eoexecutor.read_logs() if include_logs else None
        else:
            execution_logs = ["No logs saved"] * len(self.eoexecutor.execution_kwargs)

        html = template.render(
            title=f'Report {self._format_datetime(self.eoexecutor.start_time)}',
            dependency_graph=dependency_graph,
            general_stats=self.eoexecutor.general_stats,
            task_descriptions=self._get_node_descriptions(),
            task_sources=self._render_task_sources(formatter),
            execution_results=self.eoexecutor.execution_results,
            execution_tracebacks=self._render_execution_tracebacks(formatter),
            execution_logs=execution_logs,
            execution_log_filenames=execution_log_filenames,
            execution_names=self.eoexecutor.execution_names,
            code_css=formatter.get_style_defs()
        )

        os.makedirs(self.eoexecutor.report_folder, exist_ok=True)

        with open(self.eoexecutor.get_report_filename(), 'w') as fout:
            fout.write(html)

    def _create_dependency_graph(self):
        """ Provides an image of dependency graph
        """
        dot = self.eoexecutor.workflow.dependency_graph()
        return base64.b64encode(dot.pipe()).decode()

    def _get_node_descriptions(self):
        """ Prepares a list of node names and initialization parameters of their tasks
        """
        descriptions = []
        name_counts = defaultdict(lambda: 0)

        for node in self.eoexecutor.workflow.get_nodes():
            node_name = node.get_custom_name(name_counts[node.name])
            name_counts[node.name] += 1

            descriptions.append({
                'name': f'{node_name} ({node.uid})',
                'uid': node.uid,
                'args': {
                    key: value.replace('<', '&lt;').replace('>', '&gt;') for key, value in
                    node.task.private_task_config.init_args.items()
                }
            })

        return descriptions

    def _render_task_sources(self, formatter):
        """ Renders source code of EOTasks
        """
        lexer = pygments.lexers.get_lexer_by_name("python", stripall=True)
        sources = {}

        for node in self.eoexecutor.workflow.get_nodes():
            task = node.task

            key = f"{task.__class__.__name__} ({task.__module__})"
            if key in sources:
                continue

            if task.__module__.startswith("eolearn"):
                subpackage_name = '.'.join(task.__module__.split('.')[:2])
                subpackage = importlib.import_module(subpackage_name)
                subpackage_version = subpackage.__version__ if hasattr(subpackage, "__version__") else "unknown"
                source = subpackage_name, subpackage_version
            else:
                try:
                    source = inspect.getsource(task.__class__)
                    source = pygments.highlight(source, lexer, formatter)
                except TypeError:
                    # Jupyter notebook does not have __file__ method to collect source code
                    # StackOverflow provides no solutions
                    # Could be investigated further by looking into Jupyter Notebook source code
                    source = None

            sources[key] = source

        return sources

    def _render_execution_tracebacks(self, formatter):
        """ Renders stack traces of those executions which failed
        """
        tb_lexer = pygments.lexers.get_lexer_by_name("py3tb", stripall=True)

        tracebacks = []
        for results in self.eoexecutor.execution_results:
            if results.workflow_failed():
                failed_node_stats = results.stats[results.error_node_uid]
                traceback = pygments.highlight(failed_node_stats.exception_traceback, tb_lexer, formatter)
            else:
                traceback = None

            tracebacks.append(traceback)

        return tracebacks

    def _get_template(self):
        """ Loads and sets up a template for report
        """
        templates_dir = os.path.join(os.path.dirname(__file__), 'report_templates')
        env = Environment(loader=FileSystemLoader(templates_dir))
        env.filters['datetime'] = self._format_datetime
        env.globals.update(timedelta=self._format_timedelta)
        template = env.get_template(self.eoexecutor.REPORT_FILENAME)

        return template

    @staticmethod
    def _format_datetime(value: dt.datetime) -> str:
        """ Method for formatting datetime objects into report
        """
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _format_timedelta(value1: dt.datetime, value2: dt.datetime) -> str:
        """ Method for formatting time delta into report
        """
        return str(value2 - value1)
