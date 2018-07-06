"""
IMPORTANT: When you import :code:`buzzard` for the first time, you should always do it from the main thread.
"""

# Import osgeo before cv2
import osgeo as _
import cv2 as _

from buzzard._footprint import Footprint
from buzzard._datasource import DataSource

from buzzard._proxy import Proxy
from buzzard._raster import Raster
from buzzard._vector import Vector
from buzzard._raster_physical import RasterPhysical
from buzzard._raster_recipe import RasterRecipe

from buzzard._env import Env, env
import buzzard.srs
import buzzard.algo

# Gather version
import os
version_file = open(os.path.join('.', 'VERSION'))
version = version_file.read().strip()

__version__ = version
