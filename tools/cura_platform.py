#!/usr/bin/env python3
"""UltiMaker Cura's bed meshes (resources/meshes, a definition's "platform" and "platform_offset") in the bed frame of
the pack's bed_model: millimetres, Z up, X and Y as the printer's, the bed's centre where the pack's bed polygon has it.

Cura places a platform as follows (Cura and Uranium, at the commit of sources.json):
- an STL or OBJ point (x, y, z) of the file is (x, z, -y) in Cura's scene (Y up);
- a 3MF file gives the raw vertices of the object with the most faces (its build item's transformation, unit and
  the turn to Y up are not applied), centred on itself when it is the only part of a group;
- the scene node is moved by platform_offset;
- a scene point (x, y, z) is (x, -z, y) on the printer, around the bed's centre.

Usage as a module: platform_triangles(path, offset) -> triangles in the printer frame around the bed's centre.
"""

import os
import re
import struct
import xml.etree.ElementTree as ET
import zipfile


def _stl_triangles(path):
    """The triangles of an STL file (binary, or ASCII with one or more solids), as the file has them."""
    data = open(path, 'rb').read()
    if len(data) >= 84:
        n = struct.unpack_from('<I', data, 80)[0]
        if 84 + 50 * n == len(data):
            out = []
            for i in range(n):
                v = struct.unpack_from('<12f', data, 84 + 50 * i)
                out.append((v[3:6], v[6:9], v[9:12]))
            return out
    text = data.decode('utf-8', 'replace')
    points = [tuple(float(x) for x in m.groups())
              for m in re.finditer(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', text)]
    return [tuple(points[i:i + 3]) for i in range(0, len(points) - 2, 3)]


def _obj_triangles(path):
    """The triangles of an OBJ file as Uranium's reader makes them: polygons as fans from their first corner, an
    index out of range taken as the first vertex."""
    vertices, faces = [], []
    pending = []
    for line in open(path, encoding='utf-8', errors='ignore'):
        parts = pending + line.split()
        pending = []
        if not parts:
            continue
        if parts[-1] == '\\':
            pending = parts[:-1]
            continue
        if parts[0] == 'v':
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == 'f':
            idx = []
            for p in parts[1:]:
                i = int(p.split('/')[0])
                idx.append(i + len(vertices) + 1 if i < 0 else i)
            for k in range(1, len(idx) - 1):
                faces.append((idx[0], idx[k], idx[k + 1]))
    out = []
    for face in faces:
        tri = []
        for i in face:
            i -= 1
            tri.append(vertices[i] if 0 <= i < len(vertices) else vertices[0])
        out.append(tuple(tri))
    return out


def _3mf_triangles(path):
    """The triangles of the part of a 3MF file that Cura shows as a platform (raw vertices, see above)."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('3D/3dmodel.model'))
    ns = root.tag.split('}')[0] + '}' if root.tag.startswith('{') else ''
    objects = {}
    for obj in root.iter(ns + 'object'):
        mesh = obj.find(ns + 'mesh')
        tris = []
        if mesh is not None:
            vs = [(float(v.get('x')), float(v.get('y')), float(v.get('z')))
                  for v in mesh.find(ns + 'vertices').iter(ns + 'vertex')]
            tris = [(vs[int(t.get('v1'))], vs[int(t.get('v2'))], vs[int(t.get('v3'))])
                    for t in mesh.find(ns + 'triangles').iter(ns + 'triangle')]
        comps = obj.find(ns + 'components')
        children = [c.get('objectid') for c in comps.iter(ns + 'component')] if comps is not None else []
        objects[obj.get('id')] = (tris, children)
    build = root.find(ns + 'build')
    items = [i.get('objectid') for i in build.iter(ns + 'item')] if build is not None else list(objects)
    candidates = []  # (triangles, centred) of every node with a mesh

    def visit(oid, alone):
        tris, children = objects.get(oid, ([], []))
        if tris:
            candidates.append((tris, alone))
        for c in children:
            visit(c, not tris and len(children) == 1 and not objects.get(c, ([], []))[1])
    for oid in items:
        visit(oid, False)
    if not candidates:
        return []
    tris, centred = max(candidates, key=lambda c: len(c[0]))
    if centred:
        xs = [p[k] for t in tris for p in t for k in (0,)]
        ys = [p[1] for t in tris for p in t]
        zs = [p[2] for t in tris for p in t]
        c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
        tris = [tuple((p[0] - c[0], p[1] - c[1], p[2] - c[2]) for p in t) for t in tris]
    return tris


def scene_triangles(path):
    """The platform's triangles in Cura's scene (Y up), before platform_offset."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.3mf':
        return _3mf_triangles(path)
    tris = _stl_triangles(path) if ext == '.stl' else _obj_triangles(path) if ext == '.obj' else None
    if tris is None:
        raise ValueError('not a platform mesh Cura reads: ' + path)
    return [tuple((p[0], p[2], -p[1]) for p in t) for t in tris]


def platform_triangles(path, offset=None):
    """The platform's triangles on the printer (Z up), around the bed's centre."""
    ox, oy, oz = (list(offset) + [0, 0, 0])[:3] if offset else (0, 0, 0)
    return [tuple((p[0] + ox, -(p[2] + oz), p[1] + oy) for p in t) for t in scene_triangles(path)]


def binary_stl(triangles, header=b'Tisma profile pack: bed of UltiMaker Cura (LGPL-3.0)'):
    """A binary STL of triangles (normals left at 0, as readers compute them)."""
    out = [header[:80].ljust(80, b' '), struct.pack('<I', len(triangles))]
    for t in triangles:
        out.append(struct.pack('<12fH', 0, 0, 0, *t[0], *t[1], *t[2], 0))
    return b''.join(out)


def plate_coverage(triangles, bed, tolerance=3.0):
    """The share of the bed polygon's bounding box (bed frame) under faces of the mesh that face up and lie within
    tolerance mm of Z 0: the bed's surface where the printer has it."""
    xs, ys = [p[0] for p in bed], [p[1] for p in bed]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    area = 0.0
    for t in triangles:
        if max(abs(p[2]) for p in t) > tolerance:
            continue
        cx, cy = sum(p[0] for p in t) / 3, sum(p[1] for p in t) / 3
        if not (x0 <= cx <= x1 and y0 <= cy <= y1):
            continue
        nz = (t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])
        if nz > 0:
            area += nz / 2
    return area / ((x1 - x0) * (y1 - y0)) if x1 > x0 and y1 > y0 else 0.0


def read_binary_stl(data):
    """The triangles of a binary STL (bytes)."""
    n = struct.unpack_from('<I', data, 80)[0]
    return [tuple(tuple(struct.unpack_from('<3f', data, 84 + 50 * i + 12 + 12 * k)) for k in range(3))
            for i in range(n)]


def bed_model(path, offset, bed):
    """(binary STL, plate coverage) of a Cura platform in the pack's bed frame: around the centre of the bed polygon,
    as Cura has it around the build volume's centre."""
    xs, ys = [p[0] for p in bed], [p[1] for p in bed]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    tris = [tuple((p[0] + cx, p[1] + cy, p[2]) for p in t) for t in platform_triangles(path, offset)]
    return binary_stl(tris), plate_coverage(tris, bed)
