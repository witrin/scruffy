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

'''
[class]
[class]message>[class]
[class]<message[class]
'''

import os
import xml.etree.ElementTree as etree
from . import common

sequence_pic = os.path.join(os.path.dirname(__file__), 'sequence.pic')

def sumlExpr(spec):
    expr = []
    for part in common.splitYUML(spec):
        if not part: continue
        if part == ',':
            if expr: yield expr
            expr = []

        # [something like this]
        elif part[0] == '[' and part[-1] == ']':
            part = part[1:-1]
            expr.append(('record', part.strip()))
        # <message
        # >message
        elif part[0] in '<>':
            expr.append((part[0], part[1:].strip()))
        # message>
        # message<
        elif part[-1] in '<>':
            expr.append((part[-1], part[:-1].strip()))

    if expr: yield expr

def getFontWidth():
    return 0.13

def suml2pic(spec, options):
    boxes = common.Boxes()
    exprs = list(sumlExpr(spec))

    pic = []
    pic.append('.PS')
    pic.append('copy "%s";' % (sequence_pic))
    pic.append('underline=0;')

    messages = []
    for expr in exprs:
        assert len(expr) in (1, 3)
        if len(expr) == 1:
            assert expr[0][0] == 'record'
            box = boxes.addBox(expr[0][1])
            if not box.width:
                box.width = len(expr[0][1]) * getFontWidth()

        elif len(expr) == 3:
            assert expr[0][0] == 'record'
            assert expr[2][0] == 'record'

            box1 = boxes.addBox(expr[0][1])
            box2 = boxes.addBox(expr[2][1])

            for x in (box1, box2):
                if not x.width:
                    x.width = len(x.spec) * getFontWidth()

            msg = expr[1][1]
            msg_len = len(msg)
            msg_type = expr[1][0]
            msg_width = msg_len * getFontWidth()

            left_box = box1
            if box2.uid < box1.uid:
                left_box = box2
            right_margin = msg_width - box1.width / 2.0 - box2.width / 2.0
            if right_margin > left_box.right_margin:
                left_box.right_margin = right_margin

            if msg_type == '<':
                box1, box2 = box2, box1

            messages.append('message(%s,%s,"%s");' % (box1.uid, box2.uid, msg))

    all_boxes = boxes.getBoxes()

    for box in all_boxes:
        if not box.right_margin:
            pic.append('object3(%s,"%s",%f);' % (box.uid, box.spec, box.width))
        else:
            pic.append('object3(%s,"%s",%f,%f);' % (box.uid, box.spec, box.width, box.right_margin))
    pic.append('step();')
    for box in all_boxes:
        pic.append('active(%s);' % (box.uid))

    pic.extend(messages)

    pic.append('step();')
    for box in all_boxes:
        pic.append('complete(%s);' % (box.uid))

    pic.append('.PE')
    return '\n'.join(pic) + '\n'

def transform(expr, fout, options):
    pic = suml2pic(expr, options)

    if options.png or options.svg:
        import subprocess
        import StringIO

        svg = subprocess.Popen(['pic2plot', '-Tsvg'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(input=pic)[0]
        
        etree.register_namespace('', 'http://www.w3.org/2000/svg')
        root = etree.parse(StringIO.StringIO(svg)).getroot()

        common.clear(root)

        if options.scruffy:
            import scruffy

            scruffy.transform(root, options)
        
        svg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n' + etree.tostring(root) + '\n'
        
        if options.png:
            png = subprocess.Popen(['convert', '-', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(input=svg)[0]
            fout.write(png)
        elif options.svg:
            fout.write(svg)
    else:
        fout.write(pic)
