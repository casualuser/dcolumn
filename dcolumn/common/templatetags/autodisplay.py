#
# dcolumn/common/templatetags/autodisplay.py
#

import os, logging
from StringIO import StringIO

from django import template
from django.utils.safestring import mark_safe

from dcolumn.dynamic_columns.models import DynamicColumn

log = logging.getLogger(u'dcolumn.templates')
register = template.Library()


@register.tag(name='auto_display')
def auto_display(parser, token):
    """
    This tag returns an HTML element.

    Arguments::

      relation -- One object from the 'relations' template object.
      prefix   -- A keyword argument used as a prefix in the element id and
                  name attributes.
      option   -- A keyword argument that is in the 'dynamicColumns' context.
                  The entire 'dynamicColumns' context can be supplied or just
                  the object for this relation.
      display  -- True use <span> for all tags else False use various tag types.

    Assume data structures below for examples::

      {
        'dynamicColumns': {
          'book': [
            [0, 'Choose a value'],
            [2, 'HTML5 Pocket Reference'],
            [1, 'SQL Pocket Guide'],
            [3, 'Raspberry Pi Hacks']
          ]
        },
        'relations': {
          '1': {
            'name': 'Project ID',
            'required': false,
            'relation': null,
            'location': 'top-container',
            'value_type': 0,
            'order': 3,
            'value': '12345'
          },
          '12': {
            'name': 'Book',
            'required': false,
            'relation': 1,
            'location': 'bottom-container',
            'key': 'book',
            'value_type': 6,
            'order': 1,
            'value': 2
          }
        }
      }

    Usage Examples::

      {% auto_display relation %}

      {% auto_display relation prefix=test- %}

      {% auto_display relation options=books %}

      {% auto_display relation options=books display=True %}

      {% auto_display relation prefix=test- options=dynamicColumns %}
    """
    tokens = token.split_contents()
    size = len(tokens)
    keywords = (u'prefix', u'options', u'display')
    kwargs = {u'prefix': u'', u'options': None, u'display': u'False'}

    if size == 2:
        tag_name, relation = tokens
        kwargs = {}
    elif size == 3:
        tag_name, relation, value1 = tokens
        kwargs.update({k: v for k,d,v in [v.partition('=')
                                          for v in (value1,)]})
    elif size == 4:
        tag_name, relation, value1, value2 = tokens
        kwargs.update({k: v for k,d,v in [v.partition('=')
                                          for v in (value1, value2)]})
    elif size == 5:
        tag_name, relation, value1, value2, value3 = tokens
        kwargs.update({k: v for k,d,v in [v.partition('=')
                                          for v in (value1, value2, value3)]})
    else:
        msg = (u"Invalue number of arguments should be 1 - 4, "
               u"found: {}").format(size-1)
        raise template.TemplateSyntaxError(msg)

    if size > 2 and not all([key in keywords for key in kwargs]):
        msg = u"Invalid keyword name, should be one of {}".format(keywords)
        raise template.TemplateSyntaxError(msg)

    return AutoDisplayNode(tag_name, relation, **kwargs)


class AutoDisplayNode(template.Node):
    TRUE_FALSE = {u'True': True, u'False': False}
    ERROR_MSG = (u"Invalid relation object--please note steps that "
                 u"led to this error and file a bug report.")
    YES_NO = ((1, u'Unknown'), (2, u'Yes'), (3, u'No'),)
    ELEMENT_TYPES = {
        DynamicColumn.INTEGER: (u'<input id="{}" name="{}" type="number" '
                                 u'value="{}" />'),
        DynamicColumn.CHARACTER: (u'<input id="{}" name="{}" size="50" '
                                   u'type="text" value="{}" />'),
        DynamicColumn.TEXT: (u'<textarea class="large-text-field" id="{}" '
                              u'name="{}" cols="40" rows="10">{}</textarea>\n'),
        DynamicColumn.DATE: (u'<input id="{}" class="wants_datepicker" '
                              u'name="{}" size="12" type="text" value="{}" />'),
        DynamicColumn.BOOLEAN: u'<select id="{}" name="{}">\n',
        DynamicColumn.FLOAT: (u'<input id="{}" name="{}" type="text" '
                               'value="{}" />'),
        DynamicColumn.FORIEGN_KEY: u'<select id="{}" name="{}">\n',
        }

    def __init__(self, tag_name, relation, prefix=u'', options=None,
                 display=False):
        self.tag_name = tag_name
        self.relation = template.Variable(relation)
        self.prefix = prefix
        self.fk_options = options and template.Variable(options) or None
        self.display = display

    def render(self, context):
        try:
            relation = self.relation.resolve(context)
        except template.VariableDoesNotExist:
            relation = {}

        display = self.TRUE_FALSE.get(self.display, False)
        log.debug("relation: %s, display: %s", relation, display)

        if relation:
            value_type = relation.get(u'value_type')

            if display:
                elem = u'<span id="{}" name="{}">{}</span>'
            else:
                elem = self.ELEMENT_TYPES.get(value_type, u'')

            attr = u"{}{}".format(self.prefix, relation.get(u'slug'))

            # Foriegn Keys are a special case since we need to determine
            # what the options will be.
            if value_type == DynamicColumn.FORIEGN_KEY:
                try:
                    fk_options = self.fk_options.resolve(context)
                except Exception:
                    fk_options = {}

                options = self._find_options(relation, fk_options)

                if display:
                    elem = self._find_value(elem, attr, options, relation)
                else:
                    elem = self._add_options(elem, attr, options, relation)
            elif value_type == DynamicColumn.BOOLEAN:
                if display:
                    elem = self._find_value(elem, attr, self.YES_NO, relation)
                else:
                    elem = self._add_options(elem, attr, self.YES_NO, relation)
            else:
                elem = elem.format("id-" + attr, attr,
                                   relation.get(u'value', u''))
        else:
            elem = u"<span>{}</span>".format(self.ERROR_MSG)

        return mark_safe(elem)

    def _find_options(self, relation, fk_options):
        if isinstance(fk_options, (list, tuple,)):
            options = fk_options
        else:
            slug = relation.get(u'slug')

            if slug:
                options = fk_options.get(slug, {})
            else:
                msg = u'Invalid key for relation, {}'.format(relation)
                raise template.TemplateSyntaxError(msg)

        return options

    def _add_options(self, elem, attr, options, relation):
        elem = elem.format("id-" + attr, attr)
        buff = StringIO(elem)
        buff.seek(0, os.SEEK_END)
        value = relation.get(u'value', u'')
        value = value.isdigit() and int(value) or value

        for k, v in options:
            s = k == value and u" selected" or u""
            buff.write(u'<option value="{}"{}>{}</option>\n'.format(k, s, v))

        buff.write(u'</select>\n')
        elem = buff.getvalue()
        buff.close()
        return elem

    def _find_value(self, elem, attr, options, relation):
        key = relation.get(u'value', u'')
        key = key.isdigit() and int(key) or key
        value = dict(options).get(key, u'')
        elem = elem.format("id-" + attr, attr, value)
        return elem


@register.tag(name='combine_contexts')
def combine_contexts(parser, token):
    """
    Combines two context variables. Helps make the HTML a less cluttered.

    Arguments::

      obj      -- The primary object in the context.
      variable -- The object that needs to identify specificity.

    Usage Examples::

      {% combine_contexts form.errors relation.slug %}
    """
    try:
        tag_name, obj, variable = token.split_contents()
    except ValueError:
        msg = "{} tag requires two arguments."
        raise template.TemplateSyntaxError(
            msg.format(token.contents.split()[0]))

    return CombineContextsNode(tag_name, obj, variable)


class CombineContextsNode(template.Node):

    def __init__(self, tag_name, obj, variable):
        self.tag_name = tag_name
        self.obj = template.Variable(obj)
        self.variable = template.Variable(variable)

    def render(self, context):
        result = self.obj.resolve(context).get(self.variable.resolve(context))
        return result and result or u''


if __name__ == '__main__':
    import sys, traceback
    from django.template import Template, Context

    context = {}
    context.update({u'relation': {u'name': u"Project Name"}})

    fk_options = {
        u"dynamicColumns": {
            u"book": [
                [0, u"Choose a value"],
                [2, u"HTML5 Pocket Reference"],
                [1, u"SQL Pocket Guide"],
                [3, u"Raspberry Pi Hacks"]
                ]
            },
        }

    for i in range(len(DynamicColumn.VALUE_TYPES)):
        relation = context.get(u'relation')
        relation[u'value_type'] = i

        if i == DynamicColumn.FORIEGN_KEY:
            rel = context.get(u'relation')
            rel[u'key'] = u'book'
            cmd = (u"{% auto_display relation prefix=test- "
                   u"options=dynamicColumns %}")
            context.update(fk_options)
        else:
            cmd = u"{% auto_display relation %}"
            rel = context.get(u'relation')
            rel.pop(u'key', None)
            context.pop(u'dynamicColumns', None)

        try:
            print 'Test {}--{}'.format(i+1, cmd)
            c = Context(context)
            command = u"Element: {}".format(cmd)
            t = Template(u"{% load autodisplay %}" + command)
            print 'Context Data:', c
            print t.render(c)
            print
        except Exception, e:
            print "{}: {}\n".format(sys.exc_info()[0], sys.exc_info()[1])
            traceback.print_tb(sys.exc_info()[2])
