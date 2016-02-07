# -*- coding: utf-8 -*-
#
# dcolumn/dcolumns/templatetags/autodisplay.py
#

"""
Template tags used for displaying dynamic columns.

by: Carl J. Nobile

email: carl.nobile@gmail.com
"""
__docformat__ = "restructuredtext en"

import os, logging
import datetime
from StringIO import StringIO
from dateutil import parser

from django import template
from django.utils.safestring import mark_safe

from dcolumn.dcolumns.models import DynamicColumn, KeyValue
from dcolumn.dcolumns.manager import dcolumn_manager

log = logging.getLogger('dcolumns.dcolumns.templatetags')
register = template.Library()


#
# auto_display
#
# NOTE: Formatting of the doc string is to conform with django docs not epydoc.
#
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
      display  -- True use <span> for all tags else False use default tag types.

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
    keywords = ('prefix', 'options', 'display')
    kwargs = {'prefix': '', 'options': None, 'display': 'False'}

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
        msg = ("Invalid number of arguments should be 1 - 4, "
               "found: {}").format(size-1)
        raise template.TemplateSyntaxError(msg)

    if size > 2 and not all([key in keywords for key in kwargs]):
        msg = "Invalid keyword name, should be one of {}".format(keywords)
        raise template.TemplateSyntaxError(msg)

    return AutoDisplayNode(tag_name, relation, **kwargs)


class AutoDisplayNode(template.Node):
    """
    Node class for the `auto_display` tag.
    """
    ERROR_MSG = ("Invalid relation object--please note steps that "
                 "led to this error and file a bug report.")
    YES_NO = ((1, 'Unknown'), (2, 'Yes'), (3, 'No'),)
    DISPLAY_TAG = '<span id="{}">{}</span>'
    STORE_WRAPPER = '<div class="storage-wrapper">{}{}</div>'
    ELEMENT_TYPES = {
        DynamicColumn.BOOLEAN: '<select id="{}" name="{}">\n',
        DynamicColumn.CHOICE: '<select id="{}" name="{}">\n',
        DynamicColumn.DATE: ('<input id="{}" type="date" name="{}" '
                             'value="{}" />'),
        DynamicColumn.DATETIME: ('<input id="{}" type="datetime" name="{}" '
                                 'value="{}" />'),
        DynamicColumn.FLOAT: ('<input id="{}" name="{}" type="text" '
                              'value="{}" />'),
        DynamicColumn.NUMBER: ('<input id="{}" name="{}" type="number" '
                               'value="{}" />'),
        DynamicColumn.TEXT: ('<input id="{}" name="{}" size="50" type="text" '
                             'value="{}" />'),
        DynamicColumn.TEXT_BLOCK: ('<textarea class="large-text-field" '
                                   'id="{}" name="{}">{}</textarea>\n'),
        DynamicColumn.TIME: ('<input id="{}" type="time" name="{}" '
                             'value="{}" />'),
        }

    def __init__(self, tag_name, relation, prefix='', options=None,
                 display='False'):
        self.tag_name = tag_name
        self.relation = template.Variable(relation)
        self.prefix = prefix
        self.fk_options = options and template.Variable(options) or None
        self.display = eval(display)

    def render(self, context):
        """
        Render the results in an HTML friendly way.

        :Parameters:
          context
            The context as profided bt django.

        :Return:
          The HTML element rendered for a specific dynamic column slug.
        """
        try:
            relation = self.relation.resolve(context)
        except template.VariableDoesNotExist:
            relation = {}

        log.debug("relation: %s, display: %s", relation, self.display)

        if relation:
            value_type = relation.get('value_type')

            if self.display:
                elem = self.DISPLAY_TAG
            else:
                elem = self.ELEMENT_TYPES.get(value_type, '')

            attr = "{}{}".format(self.prefix, relation.get('slug'))

            # Choices are a special case since we need to determine
            # what the options will be.
            if value_type == DynamicColumn.CHOICE:
                try:
                    fk_options = self.fk_options.resolve(context)
                except Exception:
                    fk_options = {}

                options = self._find_options(relation, fk_options)

                if self.display:
                    elem = self._find_value(elem, attr, options, relation)
                else:
                    elem = self._add_options(elem, attr, options, relation)

                    if (relation.get('store_relation', False) and
                        'selected' not in elem):
                        tmp_elem = self._find_value(
                            self.DISPLAY_TAG, 'store-' + attr, {}, relation)
                        elem = self.STORE_WRAPPER.format(elem, tmp_elem)
            elif value_type == DynamicColumn.BOOLEAN:
                if self.display:
                    elem = self._find_value(elem, attr, self.YES_NO, relation)
                else:
                    elem = self._add_options(elem, attr, self.YES_NO, relation)
            elif self.display:
                elem = elem.format("id-" + attr,
                                   relation.get('value', ''))
            else:
                elem = elem.format("id-" + attr, attr,
                                   relation.get('value', ''))
        else:
            elem = "<span>{}</span>".format(self.ERROR_MSG)

        return mark_safe(elem)

    def _find_options(self, relation, fk_options):
        """
        Find the options for this relation.

        The fk_option argument can either be the options we need in a list or
        tuple or a dict of all options for all choice type objects.

        :Parameters:
          relation : dict
            The meta data for a dynamic column.
          fk_options : list or dict
            Can be the list of a specific slug's display options or the full
            `dynamicColumns` dict object.

        :Returns:
          The list of options.
        """
        if isinstance(fk_options, (list, tuple,)):
            options = fk_options
        else:
            slug = relation.get('slug')

            if slug:
                options = fk_options.get(slug, {})
            else:
                msg = 'Invalid key for relation, {}'.format(relation)
                log.error(msg)
                raise template.TemplateSyntaxError(msg)

        log.debug("relation: %s, fk_options: %s, options: %s",
                  relation, fk_options, options)
        return options

    def _add_options(self, elem, attr, options, relation):
        """
        Find the value in the options if it exists and set the selected
        property on the appropriate option. In the case of a stored relation
        find the selected option by the actual value as the PK is not
        available in this case.

        :Parameters:
          elem : str
            The HTML element.
          attr : str
            Text object to be used when creating the element's attributes.
          options : list
            The options used when creating the HTML select element.
          relation : dict
            The meta data for a dynamic column.

        :Returns:
          The populated HTML element.
        """
        elem = elem.format("id-" + attr, attr)
        buff = StringIO(elem)
        buff.seek(0, os.SEEK_END)
        value = relation.get('value', '')

        # Get the ID if the value is stored not the pk.
        if relation.get('store_relation', False):
            value = [k for k, v in options if v == value]
            value = len(value) >= 1 and value[0] or 0

        value = unicode(value).isdigit() and int(value) or value

        for k, v in options:
            s = ""

            if k == value and unicode(value).isdigit() and int(value) != 0:
                s = " selected"

            buff.write('<option value="{}"{}>{}</option>\n'.format(k, s, v))

        buff.write('</select>\n')
        elem = buff.getvalue()
        buff.close()
        log.debug("elem: %s, attr: %s, options: %s, relation: %s, value: %s",
                  elem, attr, options, relation, value)
        return elem

    def _find_value(self, elem, attr, options, relation):
        """
        Produce the element filled with the value. This method is used only
        for display mode and the element is usually a <span>.

        :Parameters:
          elem : str
            The HTML element.
          attr : str
            Text object to be used when creating the element's attributes.
          options : list
            The options used when creating the HTML select element.
          relation : dict
            The meta data for a dynamic column.

        :Returns:
          The populated HTML element.
        """
        log.debug("elem: %s, attr: %s, options: %s, relation: %s",
                  elem, attr, options, relation)
        value = relation.get('value', '')

        # Get the value is the ID then get the value.
        if relation.get('store_relation', False):
            if value == '0':
                value = ''
        else:
            key = value.isdigit() and int(value) or value
            value = dict(options).get(key, '')

        elem = elem.format("id-" + attr, value)
        return elem


#
# single_display
#
# NOTE: Formatting of the doc string is to conform with django docs not epydoc.
#
@register.tag(name='single_display')
def single_display(parser, token):
    """
    Returns a context variable containing a single value where the data type is
    based on the type of object. You will need to warp the result in an html
    tag of your choice.

    Arguments::

      obj  -- A CollectionBase derived model object.
      slug -- The slug for the DynamicColumn type.
      as   -- Manditory delimiter.
      name -- Name for context variable similar to the slug name.

    Usage Examples::

      {% single_display <object> <slug> as <context name>  %}

      {% single_display obj country as country %}
    """
    try:
        tag_name, obj, slug, delimiter, name = token.split_contents()
    except ValueError:
        msg = "{} tag requires four arguments."
        raise template.TemplateSyntaxError(
            msg.format(token.contents.split()[0]))

    if delimiter != 'as':
        raise template.TemplateSyntaxError(
            "The second argument must be the word 'as' found '{}'.".format(
                delimiter))

    return SingleDisplayNode(tag_name, obj, slug, name)


class SingleDisplayNode(template.Node):
    """
    Node class for the `single_display` tag.
    """

    def __init__(self, tag_name, obj, slug, name):
        self.tag_name = tag_name
        self.obj = template.Variable(obj)
        self.slug = slug
        self.name = name

    def _fix_boolean(self, dc, value):
        return {0: 'Unknown', 1: 'Yes', 2: 'No'}.get(value, '')

    def _fix_choice(self, dc, value):
        choice_name = dcolumn_manager.choice_relation_map[dc.relation]
        obj, field = dcolumn_manager.choice_map[choice_name]
        value = int(value)

        for choice in obj.objects.model_objects():
            if getattr(choice, 'pk') == value:
                value = getattr(choice, field)
                break

        return (value != 0) and value or ''

    def _fix_date(self, dc, value):
        # 1985-04-12 RFC-3339
        return datetime.date(*self._split_date(value))

    def _fix_datetime(self, dc, value):
        # 1985-04-12T23:20:50.52<+/-00:00>/Z RFC-3339
        return parser.parse(value)

    def _fix_float(self, dc, value):
        return float(value)

    def _fix_number(self, dc, value):
        return value

    def _fix_text(self, dc, value):
        return value

    def _fix_text_block(self, dc, value):
        return value

    def _fix_time(self, dc, value):
        # 23:20:50.52<+/-00:00>/Z RFC-3339
        return parser.parse(value).timetz()

    def _split_date(self, value):
        return [int(v) for v in value.split('-') if v.isdigit()]

    METHOD_MAP = {
        DynamicColumn.BOOLEAN: _fix_boolean,
        DynamicColumn.CHOICE: _fix_choice,
        DynamicColumn.DATE: _fix_date,
        DynamicColumn.DATETIME: _fix_datetime,
        DynamicColumn.FLOAT: _fix_float,
        DynamicColumn.NUMBER: _fix_number,
        DynamicColumn.TEXT: _fix_text,
        DynamicColumn.TEXT_BLOCK: _fix_text_block,
        DynamicColumn.TIME: _fix_time,
        }

    def render(self, context):
        try:
            obj = self.obj.resolve(context)
        except template.VariableDoesNotExist:
            obj = None

        value = ''

        try:
            key_value = obj.keyvalue_pairs.select_related(
                'dynamic_column__slug').get(dynamic_column__slug=self.slug)
            dc = key_value.dynamic_column
            value_type = dc.value_type

            if key_value.value:
                if dc.store_relation and not key_value.value.isdigit():
                    value_type = DynamicColumn.TEXT

                value = self.METHOD_MAP[value_type](self, dc, key_value.value)
        except KeyValue.DoesNotExist:
            log.warn("KeyValue pair does not exist for slug %s", self.slug)

        context[self.name] = value
        return ''


#
# combine_contexts
#
# NOTE: Formatting of the doc string is to conform with django docs not epydoc.
#
@register.tag(name='combine_contexts')
def combine_contexts(parser, token):
    """
    Combines two context variables. Helps make the HTML a less cluttered.

    Arguments::

      obj      -- An object in the contect that has member objects.
      variable -- A variable that defines a member object name.

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
    """
    Node class for the `combine_contexts` tag.
    """

    def __init__(self, tag_name, obj, variable):
        self.tag_name = tag_name
        self.obj = template.Variable(obj)
        self.variable = template.Variable(variable)

    def render(self, context):
        result = self.obj.resolve(context).get(self.variable.resolve(context))
        return result and result or ''


if __name__ == '__main__':
    import sys, traceback
    from django.template import Template, Context

    context = {}
    context.update({'relation': {'name': "Project Name"}})

    fk_options = {
        "dynamicColumns": {
            "book": [
                [0, "Choose a value"],
                [2, "HTML5 Pocket Reference"],
                [1, "SQL Pocket Guide"],
                [3, "Raspberry Pi Hacks"]
                ]
            },
        }

    for i in range(len(DynamicColumn.VALUE_TYPES)):
        relation = context.get('relation')
        relation['value_type'] = i

        if i == DynamicColumn.CHOICE:
            rel = context.get('relation')
            rel['key'] = 'book'
            cmd = ("{% auto_display relation prefix=test- "
                   "options=dynamicColumns %}")
            context.update(fk_options)
        else:
            cmd = "{% auto_display relation %}"
            rel = context.get('relation')
            rel.pop('key', None)
            context.pop('dynamicColumns', None)

        try:
            print 'Test {}--{}'.format(i+1, cmd)
            c = Context(context)
            command = "Element: {}".format(cmd)
            t = Template("{% load autodisplay %}" + command)
            print 'Context Data:', c
            print t.render(c)
            print
        except Exception, e:
            print "{}: {}\n".format(sys.exc_info()[0], sys.exc_info()[1])
            traceback.print_tb(sys.exc_info()[2])
