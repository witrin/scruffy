#!/usr/bin/env python
# Copyright (C) 2011 by Aivars Kalvans <aivars.kalvans@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Makes SVG shapes look hand-drawn like "scruffy" UML diagrams:
#   http://yuml.me/diagram/scruffy/class/samples
#
# Adds new points (with slight offsets) between existing points.
# Changes font to ..?
# Adds shadows to polygons
# Adds gradient

import sys
import math
import random
import xml.etree.ElementTree as etree

# python2.6 support
if sys.version_info[0:2] < (2, 7, 0):
    etree.register_namespace = lambda x, y: None

gCoordinates = 'px'

def getPixels(n):
    if gCoordinates == 'px': return n
    elif gCoordinates == 'in': return n * 96.0

def putPixels(n):
    if gCoordinates == 'px': return n
    elif gCoordinates == 'in': return n / 96.0

def parsePoints(points):
    points = points.split()
    return [(getPixels(float(x)), getPixels(float(y))) for x, y in [point.split(',') for point in points]]

def lineLength(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)

def splitLine(p1, p2, l):
    ''' find point on line l points away from p1 '''
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    lp = math.sqrt(dx * dx + dy * dy)
    ax = dx / lp
    ay = dy / lp
    return (p1[0] + l * ax, p1[1] + l * ay)

def frandrange(start, stop):
    ''' random.randrange for floats '''
    start, stop = int(start * 10.0), int(stop * 10.0)
    r = random.randrange(start, stop)
    return r / 10.0

SVG_NS = 'http://www.w3.org/2000/svg'
def ns(tag):
    return '{%s}%s' % (SVG_NS, tag)

def transformRect2Polygon(elem):
    elem.tag = ns('polygon')
    x = float(elem.attrib['x'])
    y = float(elem.attrib['y'])
    w = float(elem.attrib['width'])
    h = float(elem.attrib['height'])
    elem.attrib['points'] = '%f,%f %f,%f %f,%f %f,%f' % (
            x, y,
            x + w, y,
            x + w, y + h,
            x, y + h
            )

def transformLine2Polyline(elem):
    elem.tag = ns('polyline')
    elem.attrib['points'] = '%(x1)s,%(y1)s %(x2)s,%(y2)s' % elem.attrib
    for key in ('x1', 'x2', 'y1', 'y2'): del elem.attrib[key]

def transformPolyline(elem):
    points = parsePoints(elem.attrib['points'])
    newPoints = []
    for i in xrange(len(points) - 1):
        p1, p2 = points[i], points[i + 1]

        newPoints.append(p1)
        l = lineLength(p1, p2)
        if l > 10:
            p = splitLine(p1, p2, frandrange(4, l - 4))
            newPoints.append((
                p[0] + frandrange(0.5, 2) * random.choice([1, -1]),
                p[1] + frandrange(0.5, 2) * random.choice([1, -1])
            ))

    newPoints.append(points[-1])

    elem.attrib['points'] = ' '.join(['%f,%f' % (putPixels(p[0]), putPixels(p[1])) for p in newPoints])

_usedColors = {}

def transformPolygon(elem):
    transformPolyline(elem)
    fill = elem.get('fill', '')
    if not fill or fill == 'none':
        elem.attrib['fill'] = 'white'

def transformText(elem, font):
    elem.attrib['font-family'] = font

def transformAddShade(root, elem):
    # Need to prepend element of the same shape
    shade = root.makeelement(elem.tag, elem.attrib)
    for i, child in enumerate(root):
        if child == elem:
            root.insert(i, shade)
            break

    shade.attrib['fill'] = '#999999'
    shade.attrib['stroke'] = '#999999'
    shade.attrib['stroke-width'] = shade.attrib.get('stroke-width', '1')
    # check for transform
    #shade.attrib['transform'] = 'translate(%f, %f)' % (putPixels(4), putPixels(-4))
    shade.attrib['transform'] = 'translate(%f, %f) ' % (putPixels(4), putPixels(4))
    #shade.attrib['style'] = 'opacity:0.75;filter:url(#filterBlur)'

def transformAddGradient(elem):
    fill = elem.get('fill', '')
    if fill == 'none':
        elem.attrib['fill'] = 'white'
    elif fill != 'black' and fill:
        _usedColors[fill] = True
        elem.attrib['style'] = 'fill:url(#' + fill + ');' + elem.attrib.get('style', '')

def _transform(root, options, level=0):
    for child in root[:]:

        if child.tag == ns('rect'):
            transformRect2Polygon(child)
        elif child.tag == ns('line'):
            transformLine2Polyline(child)

        # Skip background rect/polygon
        if child.tag == ns('polygon') and level != 0:
            transformPolygon(child)
            if options.shadow:
                transformAddShade(root, child)
            transformAddGradient(child)

        elif child.tag == ns('path'):
            #transformAddShade(root, child)
            pass
        elif child.tag == ns('polyline'):
            transformPolyline(child)
            #see class diagram - shade of inside line
            #transformAddShade(root, child)
        elif child.tag == ns('text'):
            if options.font:
                transformText(child, options.font)

        _transform(child, options, level + 1)

    if level == 0:
        defs = root.makeelement(ns('defs'), {})
        root.insert(0, defs)
        filterBlur = etree.SubElement(defs, ns('filter'), {'id': 'filterBlur'})
        etree.SubElement(filterBlur, ns('feGaussianBlur'), {'stdDeviation': '0.69', 'id':'feGaussianBlurBlur'})
        for name in _usedColors:
            gradient = etree.SubElement(defs, ns('linearGradient'), {'id': name, 'x1':"0%", 'xy':"0%", 'x2':"100%", 'y2':"100%"})
            etree.SubElement(gradient, ns('stop'), {'offset':'0%', 'style':'stop-color:white;stop-opacity:1'})
            etree.SubElement(gradient, ns('stop'), {'offset':'50%', 'style':'stop-color:%s;stop-opacity:1' % name})

def transform(root, options):
    w, h = root.attrib.get('width', ''), root.attrib.get('height', '')
    if w.endswith('in') or h.endswith('in'):
        global gCoordinates
        gCoordinates = 'in'

    _transform(root, options)
