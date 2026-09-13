"""printprep - prepare finished artwork for garment printing.

Cut artwork off its background without eating the parts that share the background colour, fit it
to a print canvas without distortion, and measure the result instead of eyeballing it.

    from printprep import key_ground, fit_to_canvas, check_master

Every function takes a PIL image or a numpy array and returns plain data you can inspect. Nothing
here calls a network service or a generative model.
"""
from .key import KeyResult, estimate_ground, ground_distance, key_ground, measure_grain
from .plate import cut_plate, fit_quadrilateral
from .fit import FitResult, fit_to_canvas, save_master
from .qc import PlateException, alpha_report, check_master, fidelity, halo
from .route import analyse, choose_enlargement
from .ink import sample_ink
from .measure import midpoint_threshold, region_luminance

__version__ = "0.1.0"

__all__ = [
    "KeyResult", "estimate_ground", "ground_distance", "key_ground", "measure_grain",
    "cut_plate", "fit_quadrilateral",
    "FitResult", "fit_to_canvas", "save_master",
    "PlateException", "alpha_report", "check_master", "fidelity", "halo",
    "analyse", "choose_enlargement",
    "sample_ink",
    "midpoint_threshold", "region_luminance",
    "__version__",
]
