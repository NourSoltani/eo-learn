"""
The following objects and functions are the core of eo-learn package
"""
from .constants import FeatureType, FeatureTypeSet, OverwritePermission
from .eodata import EOPatch
from .eotask import EOTask
from .eonode import EONode, linearly_connect_tasks
from .eoworkflow import EOWorkflow, WorkflowResults
from .eoworkflow_tasks import OutputTask
from .eoexecution import EOExecutor, execute_with_mp_lock

from .core_tasks import (
    CopyTask,
    DeepCopyTask,
    SaveTask,
    LoadTask,
    AddFeature,
    RemoveFeature,
    RenameFeature,
    DuplicateFeature,
    InitializeFeature,
    MoveFeature,
    AddFeatureTask,
    RemoveFeatureTask,
    RenameFeatureTask,
    DuplicateFeatureTask,
    InitializeFeatureTask,
    MoveFeatureTask,
    MergeFeatureTask,
    MapFeatureTask,
    ZipFeatureTask,
    ExtractBandsTask,
    CreateEOPatchTask,
    SaveToDisk,
    LoadFromDisk,
    MergeEOPatchesTask,
)

from .fs_utils import get_filesystem, load_s3_filesystem
from .utilities import deep_eq, negate_mask, constant_pad, get_common_timestamps, bgr_to_rgb, FeatureParser


__version__ = "1.0.0"
