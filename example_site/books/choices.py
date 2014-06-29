#
# example_site/books/choices.py
#

"""
The objects in this module mimic database models, so they will work in the
ChoiceManager class.
"""

from dcolumn.dcolumns.manager import dcolumn_manager


#
# Language
#
class LanguageManager(object):

    def dynamic_column(self):
        from .choices import Language

        languages = (u'Chinese', u'English', u'Russian', u'Japanese',)
        result = []

        for pk, name in enumerate(languages, start=1):
            lc = Language()
            lc.pk = pk
            lc.name = name
            result.append(lc)

        return result


class Language(object):
    pk = 0
    name = u''

    objects = LanguageManager()

dcolumn_manager.register_choice(Language, 1, u'name')