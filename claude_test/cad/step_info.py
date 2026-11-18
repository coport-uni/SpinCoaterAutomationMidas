# Print size, volume and cylinder radii of a STEP file, and write an
# ASCII STL for rendering. Used for the DB9 bracket numbers in the README.
"""Measure a STEP solid with OpenCascade.

Usage:
    step_info.py IN.step OUT.stl

Needs ``cadquery-ocp`` (``pip install cadquery-ocp``).
"""

import sys
from collections import Counter

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.GProp import GProp_GProps
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

mesh_tolerance_mm = 0.05


def main():
    step_path, stl_path = sys.argv[1], sys.argv[2]
    reader = STEPControl_Reader()
    reader.ReadFile(step_path)
    reader.TransferRoots()
    shape = reader.OneShape()

    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box, False)
    low, high = box.CornerMin(), box.CornerMax()
    size = [high.X() - low.X(), high.Y() - low.Y(), high.Z() - low.Z()]
    print("size mm", [round(value, 2) for value in size])

    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties)
    print("volume mm3", round(properties.Mass(), 1))

    cylinders = Counter()
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        surface = BRepAdaptor_Surface(TopoDS.Face(explorer.Current()))
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            axis = cylinder.Axis().Direction()
            key = (
                round(cylinder.Radius(), 2),
                (round(axis.X(), 2), round(axis.Y(), 2), round(axis.Z(), 2)),
            )
            cylinders[key] += 1
        explorer.Next()
    for (radius, axis), faces in sorted(cylinders.items()):
        print(f"cylinder radius {radius} mm, axis {axis}, faces {faces}")

    BRepMesh_IncrementalMesh(shape, mesh_tolerance_mm)
    StlAPI_Writer().Write(shape, stl_path)


if __name__ == "__main__":
    main()
