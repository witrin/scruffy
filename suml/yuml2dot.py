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

# Creates class diagrams in .dot format from yUML syntax
#   http://yuml.me/diagram/class/draw

'''
Class   [Customer]
Directional [Customer]->[Order]
Bidirectional   [Customer]<->[Order]
Aggregation [Customer]+-[Order] or [Customer]<>-[Order]
Composition [Customer]++-[Order]
Inheritance [Customer]^[Cool Customer], [Customer]^[Uncool Customer]
Dependencies    [Customer]uses-.->[PaymentStrategy]
Cardinality [Customer]<1-1..2>[Address]
Labels  [Person]customer-billingAddress[Address]
Notes   [Person]-[Address],[Address]-[note: Value Object]
Full Class  [Customer|Forename;Surname;Email|Save()]
Splash of Colour    [Customer{bg:orange}]<>1->*[Order{bg:green}]
Comment:        // Comments

[Foo|valueProp]
[Foo]entityRef->[Bar]
[Foo]entityComp++->ownedBy[Baz]
[Foo]oneToMany->*[FooBar]
[Bar|name]
[FooBar|value]
[FooBar]^[Bar]

'''

import textwrap
import common
import xml.etree.ElementTree as etree

def escape_token_escapes(spec):
    return spec.replace('\\[', '\\u005b').replace('\\]', '\\u005d')

def unescape_token_escapes(spec):
    return spec.replace('\\u005b', '[').replace('\\u005d', ']')

def escape_label(label):
    """ Escape label string for DOT
        TODO: check spec if everything is here
    """
    label = label.replace('{', '\\{').replace('}', '\\}')
    label = label.replace(';', '\\n')
    label = label.replace(' ', '\\ ')
    label = label.replace('<', '\\<').replace('>', '\\>')
    label = label.replace('\\n\\n', '\\n')
    return label

def yumlExpr(spec):
    expr = []
    
    for part in common.splitYUML(escape_token_escapes(spec)):        
        if not part: continue
        # End of line, eat multiple empty lines (part is like ',,,,')
        if len(part) > 0 \
                and (len(part.strip(',')) == 0 or part.strip(',').startswith('//')):
            if expr: yield expr
            expr = []
        elif part == '^':
            expr.append(('edge', 'empty', '', 'none', '', 'solid'))

        # [something like this]
        # [something like this {bg:color}]
        # [note: something like this {bg:color}]
        elif part[0] == '[' and part[-1] == ']':
            part = part[1:-1]
            bg = ''
            if part[-1] == '}':
                x = part.split('{bg:')
                assert len(x) == 2
                part = x[0]
                bg = x[1][:-1]

            if part.startswith('note:'):
                expr.append(('note', unescape_token_escapes(part[5:].strip()), bg))
            elif '[' in part and ']' in part:
        
                p = part.split('[')
                part = p[0]
                nodes = [node.replace(']', '').strip() for node in p[1:]]
                expr.append(('cluster', unescape_token_escapes(part.strip()), bg, nodes))
            else:
                expr.append(('record', unescape_token_escapes(part.strip()), bg))
        elif '-' in part:
            if '-.-' in part:
                style = 'dashed'
                x = part.split('-.-')
            else:
                style = 'solid'
                x = part.split('-')

            assert len(x) == 2
            left, right = x

            def processLeft(left):
                if left.startswith('<>'):
                    return ('odiamond', left[2:])
                elif left.startswith('++'):
                    return ('diamond', left[2:])
                elif left.startswith('+'):
                    return ('odiamond', left[1:])
                elif left.startswith('<') or left.startswith('>'):
                    return ('vee', left[1:])
                elif left.startswith('^'):
                    return ('empty', left[1:])
                else:
                    return ('none', left )

            lstyle, ltext = processLeft(left)

            if right.endswith('<>'):
                rstyle = 'odiamond'
                rtext = right[:-2]
            elif right.endswith('++'):
                rstyle = 'diamond'
                rtext = right[:-2]
            elif right.endswith('+'):
                rstyle = 'odiamond'
                rtext = right[:-1]
            elif right.endswith('>'):
                rstyle = 'vee'
                rtext = right[:-1]
            elif right.endswith('^'):
                rstyle = 'empty'
                rtext = right[:-1]
            else:
                # zOMG, it seams valid
                rstyle, rtext = processLeft(right)

            expr.append(('edge', lstyle, ltext, rstyle, rtext, style))
    if expr: yield expr

def recordName(label):
    # for classes/records allow first entry with all attributes and later only with class name
    name = label.split('|')[0].strip()
    return name

def yuml2dot(spec, options):
    uids = {}
    class Foo:
        def __init__(self, label):
            self.uid = label

    exprs = list(yumlExpr(spec))

    if len(exprs) > 5: options.rankdir = 'TD'
    else: options.rankdir = 'LR'

    dot = []
    dot.append('digraph G {')
    dot.append('    ranksep = 1')
    dot.append('    rankdir = %s' % (options.rankdir))

    for expr in exprs:
        for elem in expr:
            if elem[0] == 'cluster':
                label = elem[1]
                if recordName(label) in uids: continue
                uid = 'cluster_A' + str(len(uids))
                uids[recordName(label)] = Foo(uid)

                dot.append('    subgraph %s {' % (uid))
                dot.append('        label = "%s"' % (label))
                dot.append('        fontsize = 10')

                if options.font:
                    dot.append('        fontname = "%s"' % (options.font))
                for node in elem[3]:
                    dot.append('        %s' % (uids[node].uid))
                dot.append('    }')
            elif elem[0] in ('note', 'record'):
                label = elem[1]
                if recordName(label) in uids: continue
                uid = 'A' + str(len(uids))
                uids[recordName(label)] = Foo(uid)

                dot.append('    node [')
                dot.append('        shape = "%s"' % (elem[0]))
                dot.append('        height = 0.50')
                #dot.append('        margin = 0.11,0.055')
                dot.append('        fontsize = 10')
                if options.font:
                    dot.append('        fontname = "%s"' % (options.font))
                dot.append('        margin = "0.20,0.05"')
                dot.append('    ]')
                dot.append('    %s [' % (uid))

                # Looks like table / class with attributes and methods
                if '|' in label:
                    label = label + '\\n'
                    label = label.replace('|', '\\n|')
                else:
                    lines = []
                    for line in label.split(';'):
                        lines.extend(textwrap.wrap(line, 20, break_long_words=False))
                    label = '\\n'.join(lines)

                label = escape_label(label)

                if '|' in label and options.rankdir == 'TD':
                    label = '{' + label + '}'

                dot.append('        label = "%s"' % (label))
                if elem[2]:
                    dot.append('        style = "filled"')
                    dot.append('        fillcolor = "%s"' % (elem[2]))
                dot.append('    ]')

        if len(expr) == 3 and expr[1][0] == 'edge':
            elem = expr[1]
            dot.append('    edge [')
            dot.append('        shape = "%s"' % (elem[0]))
            dot.append('        dir = "both"')
            # Dashed style for notes
            if expr[0][0] == 'note' or expr[2][0] == 'note':
                dot.append('        style = "dashed"')
            else:
                dot.append('        style = "%s"' % (elem[5]))
            dot.append('        arrowtail = "%s"' % (elem[1]))
            dot.append('        taillabel = "%s"' % (elem[2]))
            dot.append('        arrowhead = "%s"' % (elem[3]))
            dot.append('        headlabel = "%s"' % (elem[4]))
            dot.append('        labeldistance = 2')
            dot.append('        fontsize = 10')
            if options.font:
                dot.append('        fontname = "%s"' % (options.font))
            dot.append('    ]')
            dot.append('    %s -> %s' % (uids[recordName(expr[0][1])].uid, uids[recordName(expr[2][1])].uid))

    dot.append('}')
    return '\n'.join(dot) + '\n'

def transform(expr, fout, options):
    dot = yuml2dot(expr, options)

    if options.png or options.svg:
        import subprocess
        import StringIO

        svg = subprocess.Popen(['dot', '-Tsvg'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(input=dot)[0]
        
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
        fout.write(dot)
